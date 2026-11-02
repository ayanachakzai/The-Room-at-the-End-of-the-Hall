import json
import threading
import queue
import time
import multiprocessing as mp
import numpy as np
import cv2
import ollama
from RealtimeSTT import AudioToTextRecorder
from dorothy import Dorothy
from dorothy.Audio import Sequence, Note, LowPassFilter, Reverb
from diffusion_utils import load_pipe, LivePipe


MODEL  = "qwen3:1.7b"
THINK  = False
DEVICE = "mps"

VISUAL_MIN_INTERVAL = 1.0   # minimum seconds between image generation requests
GEN_SIZE = 320               # image generation size before upscaling to the window
AUDIO_SMOOTHING = 0.1        # fraction to move toward the target emotion value each frame

dot = None
# shared state, updated by the scoring thread, read by the draw loop
emotion = {"energy": 0.5, "tension": 0.5, "valence": 0.5, "pace": 0.5, "ms": 0.0}
sentence_queue = queue.Queue()
last_heard = ""

# visual_lock protects scene_prompt and scene_version from being read mid-update
visual_lock = threading.Lock()
scene_prompt = "room at the end of the hall, west-facing window, golden afternoon light, cardamom tea, old books, cinematic, atmospheric, no text"
scene_version = 0  # incremented each time a new prompt is ready

# prefix added to every prompt to keep the visual style consistent across the piece
VISUAL_STYLE = "cinematic memory, painterly film still, soft grain, no text"

# system prompt sets the emotional context and gives the model concrete examples
system_prompt = """Rate the emotion of the CURRENT spoken line from the performance piece.
Return ONLY JSON with numbers 0.0 to 1.0: energy, tension, valence, pace.
energy = physical activation. tension = threat/dread/conflict. valence = sadness 0.0, neutral 0.5, joy 1.0. pace = urgency.
Tender memories are warm: low tension, medium/high valence. Grief is low energy and low valence, not panic. Panic is high energy and high tension.
Examples:
"The window faced west and everything went gold." -> {"energy":0.1,"tension":0.0,"valence":0.7,"pace":0.1}
"The arguments started that winter." -> {"energy":0.4,"tension":0.8,"valence":0.2,"pace":0.4}
"I sat on the floor of the empty hallway." -> {"energy":0.1,"tension":0.4,"valence":0.1,"pace":0.1}
"I put on music and danced badly." -> {"energy":0.6,"tension":0.0,"valence":0.9,"pace":0.6}
"""

def clamp01(x, default=0.5):
    # keeps the output between 0 and 1, returns default if conversion fails
    try:
        return max(0.0, min(1.0, float(x)))
    except Exception:
        return default


def style_words():
    """Short mood words derived from current emotion, used to colour the image prompt."""
    v, t, e = emotion["valence"], emotion["tension"], emotion["energy"]
    if t > 0.7 and e > 0.45:
        return "ominous shadows, rain, narrow hallway"
    if v < 0.35:
        return "cold blue quiet grief"
    if v > 0.65:
        return "warm golden hopeful light"
    return "muted soft domestic light"


def passage_scene_anchor(text):
    """Map the heard line onto the visual world of the passage using keyword matching."""
    t = text.lower()

    if any(k in t for k in ["cardamom", "old book", "old books", "window", "west", "gold", "child"]):
        return "a yellow bright quiet west-facing room at the end of a hallway, old books by a window sill, cardamom tea being brewed, a teapot steaming on the stove, golden afternoon light rushing into a rustic wooden home library full of books"

    if any(k in t for k in ["radio", "mother", "dance", "dancing", "stove", "table", "sang", "songs", "warm house"]):
        return "a warm kitchen memory, an old vintage radio playing music, a mother dancing in the kitchen next to the stove, green vines growing in a kitchen setting creating a jungle of flowers with woman dancing"

    if any(k in t for k in ["moved", "necessary", "painful", "boxes", "stairs", "empty", "smaller", "look back"]):
        return "moving boxes on stairs, an emptied small bedroom, marks on a door frame keeping a children's growth chart from 4 to 17 years of age, quiet summer afternoon light, a moving truck full of brown moving boxes"

    if any(k in t for k in ["argument", "arguments", "silence", "winter", "barely breathing", "breathing", "cold walls", "leaning", "hallway one night"]):
        return "a narrow winter hallway, icy trails, walls leaning inward, shadows creating empty darkness, thunder clouds approaching from the distance"

    if any(k in t for k in ["rain", "voices", "door", "car", "headlights", "street", "floor of the empty hallway", "very long time"]):
        return "rain at night, thunder clouds, a front door left open, car headlights disappearing down the residential suburban street, a singular car in a dark empty wet street"

    if any(k in t for k in ["three in the morning", "3 in the morning", "colder", "own tea", "make my own tea", "silence without", "name", "mouth"]):
        return "a cold quiet bedroom with a heavy blue atmosphere, one cup of tea far away in an empty blue hue room, an oval picture frame on a table of a woman sitting on a desk"

    if any(k in t for k in ["light comes back", "possible", "letters", "drawer", "fountain pen", "handwriting", "kitchen floor"]):
        return "letters in a drawer of a wooden dresser, fountain pen handwriting on parchment, Envelopes and letters opened spread across a blue kicthen floor, soft returning light after winter, tiny stream of light enters blue moody empty kitchen full of dead plants and vines"

    if any(k in t for k in ["laughed", "laugh", "open", "windows", "music", "danced", "dancing badly", "made cardamom", "golden the way"]):
        return "open windows in the morning with a tiny stream of light entering a blue moody bedroom, cardamom tea on a wooden table with flowers in a vase, music playing on a vintage radio, a woman dancing and twirling around a kitchen full of light, golden light pouring in a dining room with small budding plants beginning to come to life"

    if any(k in t for k in ["carry it", "certain afternoons", "lost", "given", "right here", "feel it again"]):
        return "the rush of golden light in a room glowing inside, window with a stream of afternoon light, flower growing in a old planting pot"

    # fallback keeps the image in the same world rather than generating something unrelated
    return "the room at the end of the hall, quiet family home, hazy memory, streaming light in a hallway, kitchen, golden light and absence"


def make_scene_prompt(text):
    """Combine style, passage anchor and mood into one prompt for SD Turbo.
    Kept short to stay under CLIP's 77-token limit."""
    text = text.strip() or "There is a room I still think about."
    anchor = passage_scene_anchor(text)
    mood = style_words()
    return f"{VISUAL_STYLE}, {anchor}, {mood}"


def on_sentence(text):
    global last_heard
    # strips whitespace and puts the sentence on the queue for processing
    text = text.strip()
    if text:
        last_heard = text
        print("heard:", text, flush=True)
        sentence_queue.put(text)


def stt_loop():
    recorder = AudioToTextRecorder(
        model="base.en",                        # faster than small.en and still accurate enough
        language="en",
        device="cpu",
        compute_type="int8",                    # reduces memory and speeds up CPU inference
        beam_size=1,                            # greedy decoding, fastest option
        batch_size=0,
        post_speech_silence_duration=0.3,       # wait 0.3s of silence before cutting a sentence
        early_transcription_on_silence=200,     # start transcribing after 200ms of quiet mid-sentence
        min_length_of_recording=0.25,
        min_gap_between_recordings=0.05,
        pre_recording_buffer_duration=0.4,
        silero_use_onnx=True,                   # faster voice activity detection
        webrtc_sensitivity=3,                   # noise rejection level (1=low, 3=high)
        spinner=False,
        start_callback_in_new_thread=True,
        print_transcription_time=True,          # prints transcription ms in terminal
    )
    print("recorder ready", flush=True)
    while True:
        recorder.text(on_sentence)


def rater_loop():
    global scene_prompt, scene_version
    print("warming up model...", flush=True)
    try:
        # warms up the model so the first real sentence isn't slow
        ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": "hello"}],
            think=THINK,
            keep_alive=-1,
        )
        print("model ready", flush=True)
    except Exception as e:
        print("warmup failed:", e, flush=True)

    while True:
        text = sentence_queue.get()

        # drain stale sentences if Ollama was slow, always score the most recent line
        dropped = 0
        while not sentence_queue.empty():
            try:
                text = sentence_queue.get_nowait()
                dropped += 1
            except queue.Empty:
                break
        if dropped:
            print(f"skipped {dropped} stale line(s); scoring latest", flush=True)

        try:
            t0 = time.time()
            r = ollama.chat(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                think=THINK,
                format="json",                              # forces a JSON response
                keep_alive=-1,                              # keeps model loaded between calls
                options={"temperature": 0.0, "num_predict": 80, "num_ctx": 1024},
                # temperature=0.0 for fully deterministic scores; num_predict caps output length
            )
            elapsed = round(time.time() - t0, 2)
            s = json.loads(r["message"]["content"])

            emotion["energy"]  = clamp01(s.get("energy",  0.5))
            emotion["tension"] = clamp01(s.get("tension", 0.5))
            emotion["valence"] = clamp01(s.get("valence", 0.5))
            emotion["pace"]    = clamp01(s.get("pace",    0.5))
            emotion["ms"]      = elapsed

            # update the scene prompt and bump the version so the visual thread knows
            with visual_lock:
                scene_prompt = make_scene_prompt(text)
                scene_version += 1

            print(f"scored in {elapsed}s:", emotion, "visual version:", scene_version, flush=True)
        except Exception as e:
            print("scoring failed:", e, flush=True)


# each corner has its own chord (midi notes), waveform and envelope
# grief: low sine with slow attack. tender: warm sine. tension: sharp saw. joy: bright triangle
CHORDS = {
    "grief":   [48, 51, 55, 58],
    "tender":  [57, 60, 64, 67],
    "tension": [60, 61, 66, 67],
    "joy":     [72, 76, 79, 84],
}
WAVE = {
    "grief": "sine",
    "tender": "sine",
    "tension": "saw",
    "joy": "triangle",
}
ADSR = {
    "grief":   (1.2, 0.4, 0.7, 3.0),
    "tender":  (1.4, 0.5, 0.45, 3.5),   # longer attack and release for a slow, warm feel
    "tension": (0.01, 0.05, 0.95, 0.08), # almost instant attack, abrupt and nervous
    "joy":     (0.03, 0.12, 0.85, 0.6),
}


class LiveScore:
    def __init__(self):
        dot.start_loop(self.setup, self.draw)

    def setup(self):
        self.s_energy = self.s_tension = self.s_valence = self.s_pace = 0.5
        self.last_corner = "tender"
        self.last_rebuild = 0

        # --- diffusion ---
        self.live = LivePipe(
            load_pipe(device=DEVICE),
            gen_size=GEN_SIZE,      # image is generated at this size then upscaled to fill the window
            sim_threshold=2.0,      # skip generation if the new frame would look too similar to the last
            max_skips=0,            # never skip, always generate
        )
        self.live.warmup()          # run a dummy pass so the first real frame isn't slow
        self.layer = dot.get_layer()
        self.last_visual_version_pushed = -1
        self.last_visual_push_time = 0.0
        self.last_frame = None

        # --- audio ---
        idx = dot.music.start_poly_synth_stream(
            n_voices=8,     # 8 voices so all four chord notes can overlap during transitions
            waveform="sine",# default waveform, overridden per chord in load_chord()
            attack=0.8,     # slow default attack, overridden per chord
            decay=0.3,
            sustain=0.7,
            release=2.5,    # long release so notes fade out slowly
        )
        self.synth  = dot.music.audio_outputs[idx]
        self.lpf    = self.synth.add_effect(LowPassFilter(3000, q=0.6))  # starts open; q = resonance
        self.reverb = self.synth.add_effect(Reverb(room_size=0.8, wet=0.5))  # large room, half wet
        self.clock  = dot.music.get_clock(bpm=35)  # slow starting tempo, changed in draw()
        self.clock.set_tpb(4)                       # 4 ticks per beat
        self.seq = Sequence(steps=4, ticks_per_step=2)  # 4-step sequence, 2 ticks per step
        self.load_chord("tender")
        self.seq.connect(self.clock, self.synth)
        self.clock.play()

    def dominant_corner(self):
        # instead of hard thresholds, calculate which corner has the highest weight
        a = self.s_energy
        v = max(0.0, self.s_valence - self.s_tension * 0.25)  # tension pulls valence darker
        w = {
            "grief":   (1 - v) * (1 - a),
            "tender":  v * (1 - a),
            "tension": (1 - v) * a,
            "joy":     v * a,
        }
        return max(w, key=w.get)

    def load_chord(self, corner):
        pitches = CHORDS[corner]
        wv = WAVE[corner]
        att, _, _, rel = ADSR[corner]   # unpack attack and release; skip decay and sustain
        vel = 0.3 + self.s_energy * 0.35  # louder when energy is high
        self.seq[0] = [
            Note(m, vel=vel, duration=6, waveform=wv, attack=att, release=rel)
            for m in pitches  # all four notes at once
        ]
        for i in range(1, 4):
            self.seq[i] = []  # leave other steps empty, one chord per cycle

    def maybe_request_visual(self):
        now = time.time()
        with visual_lock:
            prompt = scene_prompt
            version = scene_version

        if version == self.last_visual_version_pushed:
            return  # no new scored line yet, skip
        if now - self.last_visual_push_time < VISUAL_MIN_INTERVAL:
            return  # rate limit, don't flood the GPU with requests

        # random noise seed, stops the image drifting into repetitive patterns over time
        seed = np.random.randint(70, 145, (GEN_SIZE, GEN_SIZE, 3), dtype=np.uint8)
        strength = 0.78
        self.live.push(
            seed,
            prompt=prompt,
            num_inference_steps=1,  # single step, relies on high strength to work well
            strength=strength,      # how much the prompt shapes the image vs the seed
            guidance_scale=0.0,     # classifier-free guidance doesn't work at 1 step
        )
        self.last_visual_version_pushed = version
        self.last_visual_push_time = now
        print("visual requested:", prompt[:140], flush=True)

    def paste_visual(self):
        result = self.live.get_frame()
        if result is not None:
            self.last_frame = result  # keep the last frame if no new one is ready yet

        if self.last_frame is not None:
            fb = dot.width * 2  # Retina screens have a 2x framebuffer, resize to match
            result_full = cv2.resize(self.last_frame, (fb, fb))
            dot.paste(result_full, (0, 0), (fb, fb))

    def draw(self):
        dot.background((0, 0, 0))

        # exponential smoothing, moves toward the target by a fraction each frame
        speed = AUDIO_SMOOTHING
        self.s_energy  += (emotion["energy"]  - self.s_energy)  * speed
        self.s_tension += (emotion["tension"] - self.s_tension) * speed
        self.s_valence += (emotion["valence"] - self.s_valence) * speed
        self.s_pace    += (emotion["pace"]    - self.s_pace)    * speed

        # --- audio shaping ---
        self.lpf.cutoff = 500 + self.s_valence * 4000  # brighter sound for positive moments
        self.lpf.q      = 0.6 + self.s_tension * 2.5   # more resonance under tension
        self.reverb.wet = 0.35 + (1 - self.s_valence) * 0.4  # more reverb for darker passages
        self.clock.bpm  = 28 + self.s_pace * 50  # tempo follows urgency of delivery

        corner = self.dominant_corner()
        if corner != self.last_corner and time.time() - self.last_rebuild > 3.0:
            self.load_chord(corner)
            self.last_corner = corner
            self.last_rebuild = time.time()
            print("audio corner:", corner, flush=True)

        # --- visual shaping ---
        self.maybe_request_visual()
        self.paste_visual()

        dot.fill((230, 230, 230))
        dot.text(f"{last_heard}", 30, dot.height - 60, 18)
        dot.text(f"{self.last_corner}  E:{self.s_energy:.2f} T:{self.s_tension:.2f} V:{self.s_valence:.2f}", 30, 30, 14)


def main():
    global dot
    dot = Dorothy(width=512, height=512, title="the living score")
    # stt and scoring run in background threads so they don't block the Dorothy draw loop
    threading.Thread(target=stt_loop,   daemon=True).start()
    threading.Thread(target=rater_loop, daemon=True).start()
    LiveScore()


if __name__ == "__main__":
    mp.freeze_support()
    main()
