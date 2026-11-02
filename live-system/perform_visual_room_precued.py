import re
import threading
import queue
import time
import multiprocessing as mp
from difflib import SequenceMatcher

import numpy as np
import cv2
from RealtimeSTT import AudioToTextRecorder
from dorothy import Dorothy
from dorothy.Audio import Sequence, Note, LowPassFilter, Reverb
from diffusion_utils import load_pipe, LivePipe


DEVICE = "mps"
VISUAL_MIN_INTERVAL = 0.8   # minimum seconds between image generation requests
GEN_SIZE = 320               # image generation size before upscaling to the window
AUDIO_SMOOTHING = 0.16       # fraction to move toward the target emotion value each frame

# matching window, how far the cue engine looks from the current script position
LOOK_BACK = 3       # how many cues behind the current position to search
LOOK_AHEAD = 10     # how many cues ahead to search, wider net for fast reading
MAX_SPAN = 4        # try matching up to 4 consecutive cues as a group
MIN_MATCH_SCORE = 0.34  # below this score, stay at current position rather than jumping

DEBUG_MATCH = True  # prints match scores and heard text to terminal during performance


dot = None
sentence_queue = queue.Queue()
last_heard = ""
matched_line = ""
match_score = 0.0
script_index = 0  # tracks which cue we're currently at, only ever moves forward

# starts at quiet/neutral values so the performance doesn't begin too extreme
emotion = {"energy": 0.2, "tension": 0.0, "valence": 0.5, "pace": 0.2, "ms": 0.0}

# visual_lock protects scene_prompt and scene_version from being read mid-update
visual_lock = threading.Lock()
scene_prompt = "room at the end of the hall, golden afternoon light, old books, cardamom tea, cinematic memory, no text"
scene_version = 0  # incremented each time a new prompt is ready

# prefix added to every prompt to keep the visual style consistent across the piece
VISUAL_STYLE = "cinematic memory, painterly film still, soft grain, no text"

# each cue has: the script line, a corner (emotion category), four emotion values (e/t/v/p),
# and a pre-written scene description for image generation
SCRIPT_CUES = [
    # Tender opening
    {"text": "There is a room I still think about.", "corner": "tender", "e": 0.15, "t": 0.00, "v": 0.55, "p": 0.15,
     "scene": "a yellow bright quiet west-facing room at the end of a hallway, old books by a window sill, cardamom tea being brewed, a teapot steaming on the stove, golden afternoon light rushing into a rustic wooden home library full of books"},
    {"text": "It smelled of cardamom and old books.", "corner": "tender", "e": 0.12, "t": 0.00, "v": 0.62, "p": 0.12,
     "scene": "a yellow bright quiet west-facing room at the end of a hallway, old books by a window sill, cardamom tea being brewed, a teapot steaming on the stove, golden afternoon light rushing into a rustic wooden home library full of books"},
    {"text": "The window faced west, and in the afternoons, everything went gold.", "corner": "tender", "e": 0.15, "t": 0.00, "v": 0.72, "p": 0.15,
     "scene": "a yellow bright quiet west-facing room at the end of a hallway, old books by a window sill, cardamom tea being brewed, a teapot steaming on the stove, golden afternoon light rushing into a rustic wooden home library full of books"},
    
    {"text": "I didn't know it wouldn't always be like this.", "corner": "grief", "e": 0.18, "t": 0.25, "v": 0.38, "p": 0.18,
     "scene": "a yellow bright quiet west-facing room at the end of a hallway, old books by a window sill, cardamom tea being brewed, a teapot steaming on the stove, golden afternoon light rushing into a rustic wooden home library full of books"},

    # Joy / early memory
    {"text": "We used to eat dinner with the radio on.", "corner": "tender", "e": 0.30, "t": 0.00, "v": 0.72, "p": 0.28,
     "scene": "a warm kitchen memory, an old vintage radio playing music, traditional dinner on the table"},
    {"text": "My mother would dance between the stove and the table.", "corner": "joy", "e": 0.58, "t": 0.00, "v": 0.88, "p": 0.55,
     "scene": "a warm kitchen memory, an old vintage radio playing music, a mother dancing in the kitchen next to the stove, green vines growing in a kitchen setting creating a jungle of flowers with woman dancing"},
    {"text": "Badly. Wonderfully badly.", "corner": "joy", "e": 0.70, "t": 0.00, "v": 0.95, "p": 0.70,
     "scene": "a warm kitchen memory, an old vintage radio playing music, a mother dancing in the kitchen next to the stove, green vines growing in a kitchen setting creating a jungle of flowers with woman dancing"},
   
    {"text": "The whole house felt warm.", "corner": "tender", "e": 0.25, "t": 0.00, "v": 0.82, "p": 0.25,
     "scene": "a warm kitchen memory, an old vintage radio playing music, a mother dancing in the kitchen next to the stove, green vines growing in a kitchen setting creating a jungle of flowers with woman dancing"},
   

    # Neutral / building
    {"text": "The summer I turned seventeen, we moved.", "corner": "grief", "e": 0.22, "t": 0.25, "v": 0.42, "p": 0.22,
     "scene": "moving boxes on stairs, an emptied small bedroom, marks on a door frame keeping a children's growth chart from 4 to 17 years of age, quiet summer afternoon light, a moving truck full of brown moving boxes"},
    {"text": "She said it was necessary.", "corner": "grief", "e": 0.20, "t": 0.45, "v": 0.32, "p": 0.20,
     "scene": "moving boxes on stairs, an emptied small bedroom, marks on a door frame keeping a children's growth chart from 4 to 17 years of age, quiet summer afternoon light, a moving truck full of brown moving boxes"},
    
    {"text": "I carried my things down the stairs in boxes.", "corner": "grief", "e": 0.25, "t": 0.20, "v": 0.42, "p": 0.22,
     "scene": "moving boxes on stairs, an emptied small bedroom, marks on a door frame keeping a children's growth chart from 4 to 17 years of age, quiet summer afternoon light, a moving truck full of brown moving boxes"},
   
    {"text": "I didn't look back.", "corner": "grief", "e": 0.18, "t": 0.25, "v": 0.28, "p": 0.20,
     "scene": "moving boxes on stairs, an emptied small bedroom, marks on a door frame keeping a children's growth chart from 4 to 17 years of age, quiet summer afternoon light, a moving truck full of brown moving boxes"},

    # Tension rising
    {"text": "The arguments started that winter.", "corner": "tension", "e": 0.48, "t": 0.82, "v": 0.18, "p": 0.45,
     "scene": "a narrow winter hallway, icy trails, walls leaning inward, shadows creating empty darkness, thunder clouds approaching from the distance"},
    {"text": "Small things at first.", "corner": "tension", "e": 0.35, "t": 0.65, "v": 0.28, "p": 0.32,
     "scene": "a narrow winter hallway, icy trails, walls leaning inward, shadows creating empty darkness, thunder clouds approaching from the distance"},
    {"text": "A door held too long.", "corner": "tension", "e": 0.40, "t": 0.78, "v": 0.20, "p": 0.35,
     "scene": "a red door open down a long hallway in a home"},
    {"text": "A silence that lasted days.", "corner": "tension", "e": 0.25, "t": 0.82, "v": 0.18, "p": 0.22,
     "scene": "icy trails, isolated shadow of a human alone in an empty dark space"},
    {"text": "Then bigger things.", "corner": "tension", "e": 0.42, "t": 0.88, "v": 0.12, "p": 0.38,
     "scene": "a narrow winter hallway, icy trails, walls leaning inward, shadows creating empty darkness, thunder clouds approaching from the distance"},
    
    {"text": "I stood in the hallway one night, not moving.", "corner": "tension", "e": 0.32, "t": 0.85, "v": 0.15, "p": 0.25,
     "scene": "a still barren wooden tree, branches of a winter tree without leaves"},
    {"text": "Barely breathing.", "corner": "tension", "e": 0.55, "t": 0.95, "v": 0.05, "p": 0.55,
     "scene": "a still barren wooden tree, branches of a winter tree without leaves"},
  

    # Panic peak
    {"text": "The night it ended, there was rain.", "corner": "tension", "e": 0.45, "t": 0.78, "v": 0.12, "p": 0.35,
     "scene": "rain at night, thunder clouds, a front door left open, modern suburban lamp post in the residential suburban street"},
    {"text": "There were voices and then there was nothing.", "corner": "tension", "e": 0.62, "t": 0.95, "v": 0.05, "p": 0.62,
     "scene": "shadows of people arguing through a window from the outside of a house in the rain at night"},
    {"text": "A door.", "corner": "tension", "e": 0.55, "t": 0.88, "v": 0.08, "p": 0.55,
     "scene": "a red front door of a home at night in the rain open"},
    {"text": "A car.", "corner": "tension", "e": 0.60, "t": 0.88, "v": 0.08, "p": 0.60,
     "scene": "car headlights disappearing down the residential suburban street, a singular car in a dark empty wet street"},
    {"text": "Headlights disappearing down the street.", "corner": "tension", "e": 0.58, "t": 0.82, "v": 0.10, "p": 0.55,
     "scene": "car headlights disappearing down the residential suburban street, a singular car in a dark empty wet street"},
 
    {"text": "I sat on the floor of the empty hallway.", "corner": "grief", "e": 0.12, "t": 0.45, "v": 0.04, "p": 0.08,
     "scene": "empty house hallway dark"},
  

    # Grief stillness
    {"text": "For months after, I woke at three in the morning.", "corner": "grief", "e": 0.18, "t": 0.25, "v": 0.18, "p": 0.15,
     "scene": "a cold quiet bedroom with a heavy blue atmosphere"},
   
    {"text": "Smaller. Colder.", "corner": "grief", "e": 0.08, "t": 0.10, "v": 0.12, "p": 0.06,
     "scene": "a cold quiet bedroom with a heavy blue atmosphere"},
    {"text": "I learned to make my own tea.", "corner": "grief", "e": 0.15, "t": 0.05, "v": 0.32, "p": 0.12,
     "scene": "one cup of tea far away in an empty blue hue room, an oval picture frame on a table of a woman sitting on a desk"},
    {"text": "I learned to sit with the silence without fighting it.", "corner": "tender", "e": 0.15, "t": 0.00, "v": 0.58, "p": 0.12,
     "scene": "a cold quiet bedroom with a heavy blue atmosphere, one cup of tea far away in an empty blue hue room, an oval picture frame on a table of a woman sitting on a desk"},
  


    # Tender turning
    {"text": "But slowly, the way light comes back after winter without you noticing, things began to feel possible again.", "corner": "tender", "e": 0.25, "t": 0.00, "v": 0.70, "p": 0.22,
     "scene": "soft returning light after winter, tiny stream of light enters blue moody empty kitchen full of dead plants and vines"},
    {"text": "I found her letters in a drawer.", "corner": "tender", "e": 0.22, "t": 0.00, "v": 0.68, "p": 0.20,
     "scene": "letters in a drawer of a wooden dresser, fountain pen handwriting on parchment, Envelopes and letters opened spread across a blue kicthen floor, soft returning light after winter, tiny stream of light enters blue moody empty kitchen full of dead plants and vines"},

    {"text": "Her handwriting was terrible.", "corner": "tender", "e": 0.28, "t": 0.00, "v": 0.74, "p": 0.25,
     "scene": "letters in a drawer of a wooden dresser, fountain pen handwriting on parchment, Envelopes and letters opened spread across a blue kicthen floor, soft returning light after winter, tiny stream of light enters blue moody empty kitchen full of dead plants and vines"},


    # Joy / resolution
    {"text": "The last letter said: don't take any of this too seriously.", "corner": "tender", "e": 0.28, "t": 0.00, "v": 0.70, "p": 0.25,
     "scene": "golden light pouring in a dining room with small budding plants beginning to come to life"},
    {"text": "It's just a life. Make it yours.", "corner": "tender", "e": 0.35, "t": 0.00, "v": 0.78, "p": 0.30,
     "scene": "open windows in the morning with a tiny stream of light entering a blue moody bedroom"},
    {"text": "I laughed out loud when I read that.", "corner": "joy", "e": 0.62, "t": 0.00, "v": 0.92, "p": 0.60,
     "scene": "a woman laughing in a kitchen full of golden light"},
    
    {"text": "Because it was exactly what she would say.", "corner": "tender", "e": 0.35, "t": 0.00, "v": 0.78, "p": 0.32,
     "scene": "open windows in the morning with a tiny stream of light entering a blue moody bedroom, cardamom tea on a wooden table with flowers in a vase, music playing on a vintage radio, a woman dancing and twirling around a kitchen full of light, golden light pouring in a dining room with small budding plants beginning to come to life"},

    {"text": "I opened all the windows that morning.", "corner": "tender", "e": 0.35, "t": 0.00, "v": 0.82, "p": 0.30,
     "scene": "open windows in the morning, fresh air entering the house"},
    {"text": "I made cardamom tea.", "corner": "tender", "e": 0.22, "t": 0.00, "v": 0.72, "p": 0.18,
     "scene": "cardamom tea in morning light, kitchen warmth returning"},
    {"text": "I put on music and I danced badly and wonderfully badly.", "corner": "joy", "e": 0.72, "t": 0.00, "v": 0.96, "p": 0.70,
     "scene": "a mother dancing in the kitchen next to the stove, green vines growing in a kitchen setting creating a jungle of flowers with woman dancing"},
    
    {"text": "The room at the end of the hall is gone now.", "corner": "grief", "e": 0.18, "t": 0.10, "v": 0.35, "p": 0.15,
     "scene": "the absent room at the end of the hall, memory and loss"},
    {"text": "But I carry it.", "corner": "tender", "e": 0.20, "t": 0.00, "v": 0.72, "p": 0.15,
     "scene": "the rush of golden light in a room glowing inside, window with a stream of afternoon light, flower growing in a old planting pot"},
    {"text": "And on certain afternoons, when everything goes gold, I feel it again.", "corner": "tender", "e": 0.22, "t": 0.00, "v": 0.82, "p": 0.18,
     "scene": "the rush of golden light in a room glowing inside, window with a stream of afternoon light, flower growing in a old planting pot"},
   
    {"text": "Right here.", "corner": "tender", "e": 0.15, "t": 0.00, "v": 0.78, "p": 0.10,
     "scene": "the rush of golden light in a room glowing inside, window with a stream of afternoon light, flower growing in a old planting pot"
},
]


def clamp01(x, default=0.5):
    # keeps the output between 0 and 1, returns default if conversion fails
    try:
        return max(0.0, min(1.0, float(x)))
    except Exception:
        return default


def cue_to_emotion(cue):
    # pulls emotion values from the pre-set cue dict
    return {
        "energy": clamp01(cue["e"]),
        "tension": clamp01(cue["t"]),
        "valence": clamp01(cue["v"]),
        "pace": clamp01(cue["p"]),
        "ms": 0.0,
    }


def cue_prompt(cue):
    # builds the image prompt from the cue's pre-written scene description
    return f"{VISUAL_STYLE}, {cue['scene']}"


def normalize_text(text):
    # lowercases and strips punctuation so STT noise doesn't break matching
    # also converts digits to words e.g. "17" → "seventeen"
    t = text.lower()
    t = t.replace("17", "seventeen")
    t = t.replace("3 in the morning", "three in the morning")
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


# pre-compute normalised versions of all cue texts at startup
for cue in SCRIPT_CUES:
    cue["norm"] = normalize_text(cue["text"])


def text_similarity(a, b):
    """Blend sequence similarity with word overlap for noisy STT."""
    a = normalize_text(a)
    b = normalize_text(b)
    if not a or not b:
        return 0.0

    # SequenceMatcher scores character-level similarity
    seq = SequenceMatcher(None, a, b).ratio()
    aw, bw = set(a.split()), set(b.split())
    # word overlap catches cases where order differs but words match
    overlap = len(aw & bw) / max(1, min(len(aw), len(bw)))

    # containment handles partial matches where STT only captured part of a line
    containment = 0.0
    if a in b or b in a:
        containment = 1.0

    return max(seq * 0.65 + overlap * 0.35, containment * 0.85)


def find_best_cue(heard, current_index):
    """Search a window around the current position for the best matching cue or span.

    Returns (target_index, score, matched_span_text).
    target_index is the last cue in the matched span so the script advances
    to the furthest line heard when STT groups multiple sentences together.
    """
    n = len(SCRIPT_CUES)
    start = max(0, current_index - LOOK_BACK)
    end = min(n, current_index + LOOK_AHEAD)

    best_i = current_index
    best_j = current_index
    best_score = -1.0
    best_text = SCRIPT_CUES[current_index]["text"]

    for i in range(start, end):
        for span_len in range(1, MAX_SPAN + 1):
            j = min(n - 1, i + span_len - 1)
            if j >= end:
                break
            span_text = " ".join(SCRIPT_CUES[k]["text"] for k in range(i, j + 1))
            score = text_similarity(heard, span_text)

            if i >= current_index:
                score += 0.03   # small bonus to encourage forward movement through the script
            if i < current_index:
                score -= 0.02 * (current_index - i)  # penalty for jumping backwards

            if score > best_score:
                best_score = score
                best_i = i
                best_j = j
                best_text = span_text

    if best_score < MIN_MATCH_SCORE:
        # confidence too low, stay where we are rather than jumping to a wrong line
        return current_index, best_score, SCRIPT_CUES[current_index]["text"]

    return best_j, max(0.0, min(1.0, best_score)), best_text


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
        silero_sensitivity=0.3,                  # lower = stricter, ignores more noise (added for loud performance in crypt)
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


def cue_loop():
    """Replaces the Ollama rater loop, matches heard text to the closest script cue
    and pulls pre-set emotion values and scene prompts from that cue."""
    global script_index, scene_prompt, scene_version, emotion, matched_line, match_score

    print("script cue engine ready, Ollama is NOT used in this version", flush=True)

    # load the first cue immediately so audio and visuals don't start at defaults
    first = SCRIPT_CUES[0]
    emotion.update(cue_to_emotion(first))
    with visual_lock:
        scene_prompt = cue_prompt(first)
        scene_version += 1

    while True:
        text = sentence_queue.get()
        t0 = time.time()

        # drain stale sentences if matching was slow, always match the most recent line
        dropped = 0
        while not sentence_queue.empty():
            try:
                text = sentence_queue.get_nowait()
                dropped += 1
            except queue.Empty:
                break
        if dropped:
            print(f"skipped {dropped} stale fragment(s); matching latest", flush=True)

        new_index, score, span_text = find_best_cue(text, script_index)
        script_index = max(script_index, new_index)  # never go backwards in the script
        cue = SCRIPT_CUES[script_index]

        emotion.update(cue_to_emotion(cue))
        emotion["ms"] = round(time.time() - t0, 3)
        matched_line = cue["text"]
        match_score = score

        with visual_lock:
            scene_prompt = cue_prompt(cue)
            scene_version += 1

        if DEBUG_MATCH:
            print(
                f"matched {script_index + 1}/{len(SCRIPT_CUES)} "
                f"score={score:.2f} in {emotion['ms']}s | cue: {cue['text']}",
                flush=True,
            )
            if score < 0.45:
                print("  low-confidence heard:", text, flush=True)
                print("  closest span:", span_text, flush=True)


# each corner has its own chord (midi notes), waveform and envelope
# grief: low sine with slow attack. tender: warm sine. tension: sharp saw. joy: bright triangle
CHORDS = {
    "grief":   [48, 51, 55, 58],
    "tender":  [60, 64, 67, 71],
    "tension": [60, 61, 65, 67],
    "joy":     [64, 67, 71, 74],
}
WAVE = {"grief": "sine", "tender": "sine", "tension": "saw", "joy": "triangle"}
ADSR = {
    "grief":   (1.2, 0.4, 0.7, 3.0),
    "tender":  (0.7, 0.3, 0.7, 2.0),
    "tension": (0.05, 0.1, 0.6, 0.4),
    "joy":     (0.3, 0.2, 0.7, 1.5),
}
# ADSR order: (attack, decay, sustain, release)


class LiveScore:
    def __init__(self):
        dot.start_loop(self.setup, self.draw)

    def setup(self):
        self.s_energy = emotion["energy"]
        self.s_tension = emotion["tension"]
        self.s_valence = emotion["valence"]
        self.s_pace = emotion["pace"]
        self.last_corner = SCRIPT_CUES[0]["corner"]
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
        self.synth = dot.music.audio_outputs[idx]
        self.lpf = self.synth.add_effect(LowPassFilter(3000, q=0.6))  # starts open; q = resonance
        self.reverb = self.synth.add_effect(Reverb(room_size=0.8, wet=0.5))  # large room, half wet
        self.clock = dot.music.get_clock(bpm=35)  # slow starting tempo, changed in draw()
        self.clock.set_tpb(4)                      # 4 ticks per beat
        self.seq = Sequence(steps=4, ticks_per_step=2)  # 4-step sequence, 2 ticks per step
        self.load_chord(self.last_corner)
        self.seq.connect(self.clock, self.synth)
        self.clock.play()

    def target_corner(self):
        # reads the corner directly from the current script cue, no calculation needed
        return SCRIPT_CUES[script_index]["corner"]

    def load_chord(self, corner):
        pitches = CHORDS[corner]
        wv = WAVE[corner]
        att, _, _, rel = ADSR[corner]   # unpack attack and release; skip decay and sustain
        vel = 0.28 + self.s_energy * 0.35  # louder when energy is high
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
            return  # no new matched cue yet, skip
        if now - self.last_visual_push_time < VISUAL_MIN_INTERVAL:
            return  # rate limit, don't flood the GPU with requests

        # random noise seed, stops the image drifting into repetitive patterns over time
        seed = np.random.randint(70, 145, (GEN_SIZE, GEN_SIZE, 3), dtype=np.uint8)
        self.live.push(
            seed,
            prompt=prompt,
            num_inference_steps=1,  # single step, relies on high strength to work well
            strength=0.78,          # how much the prompt shapes the image vs the seed
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
        self.s_energy += (emotion["energy"] - self.s_energy) * speed
        self.s_tension += (emotion["tension"] - self.s_tension) * speed
        self.s_valence += (emotion["valence"] - self.s_valence) * speed
        self.s_pace += (emotion["pace"] - self.s_pace) * speed

        # --- audio shaping ---
        self.lpf.cutoff = 450 + self.s_valence * 4300  # brighter sound for positive moments
        self.lpf.q = 0.55 + self.s_tension * 2.8       # more resonance under tension
        self.reverb.wet = 0.35 + (1 - self.s_valence) * 0.42  # more reverb for darker passages
        self.clock.bpm = 28 + self.s_pace * 56  # tempo follows urgency of delivery

        corner = self.target_corner()
        if corner != self.last_corner and time.time() - self.last_rebuild > 1.2:
            self.load_chord(corner)
            self.last_corner = corner
            self.last_rebuild = time.time()
            print("audio corner:", corner, flush=True)

        self.maybe_request_visual()
        self.paste_visual()

        # --- overlay text ---
        dot.fill((235, 235, 235))
        dot.text(matched_line, 30, dot.height - 52, 18)

def main():
    global dot
    dot = Dorothy(width=900, height=900, title="the living score, precued")
    # stt and cue matching run in background threads so they don't block the Dorothy draw loop
    threading.Thread(target=stt_loop, daemon=True).start()
    threading.Thread(target=cue_loop, daemon=True).start()
    LiveScore()


if __name__ == "__main__":
    mp.freeze_support()
    main()
