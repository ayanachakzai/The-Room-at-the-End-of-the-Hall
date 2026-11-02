// This scales the live show's frame-based emotion smoothing for real frame durations.
const AUDIO_SMOOTHING = 0.16;

// This keeps chord rebuilds from becoming distracting during rapid reading.
const CORNER_CHANGE_DELAY = 1.2;

// This uses a sixteenth-note position equal to one and a half beats.
const CHORD_DURATION = "0:1:2";

// This recreates the slow PolySynth sound and continuous emotion shaping in Tone.js.
export class Music {
  // This stores fixed music tables and starts with the first cue's emotion values.
  constructor(music, debugUpdate) {
    this.music = music;
    this.debugUpdate = debugUpdate;
    this.ready = false;
    this.lastFrame = 0;
    this.frameId = null;
    this.lastCornerChange = 0;
    this.corner = "tender";
    this.pendingCorner = null;
    this.target = { energy: 0.15, tension: 0, valence: 0.55, pace: 0.15 };
    this.smoothed = { ...this.target };
  }

  // This creates the synth and effects after the visitor's gesture unlocks browser audio.
  async start(firstLine) {
    if (this.ready || !window.Tone) {
      return;
    }

    this.synth = new Tone.PolySynth(Tone.Synth, {
      maxPolyphony: 8,
      oscillator: { type: "sine" },
      envelope: { attack: 0.7, decay: 0.3, sustain: 0.7, release: 2 },
    });
    this.filter = new Tone.Filter(3000, "lowpass");
    this.filter.Q.value = 0.6;
    this.reverb = new Tone.Reverb({ decay: 4, wet: 0.5 });
    this.volume = new Tone.Volume(-80);
    this.synth.chain(this.filter, this.reverb, this.volume, Tone.Destination);
    await this.reverb.generate();
    this.ready = true;
    this.applyCue(firstLine, true);
    this.repeatId = Tone.Transport.scheduleRepeat((time) => {
      this.synth.triggerAttackRelease(
        this.music.chords[this.corner].map((note) => Tone.Frequency(note, "midi")),
        CHORD_DURATION,
        time,
        0.28 + this.smoothed.energy * 0.35,
      );
    }, "2n");
    Tone.Transport.start();
    this.volume.volume.rampTo(-12, 3);
    this.lastFrame = performance.now();
    this.animate(this.lastFrame);
    document.addEventListener("visibilitychange", () => this.handleVisibility());
  }

  // This updates targets immediately and limits how often a new chord sound is rebuilt.
  applyCue(line, force = false) {
    this.target = { energy: line.e, tension: line.t, valence: line.v, pace: line.p };

    if (!this.ready) {
      this.corner = line.corner;
      return;
    }

    const elapsed = performance.now() / 1000 - this.lastCornerChange;

    if (force || (line.corner !== this.corner && elapsed >= CORNER_CHANGE_DELAY)) {
      this.setCorner(line.corner);
      return;
    }

    if (line.corner !== this.corner) {
      this.pendingCorner = line.corner;
    }
  }

  // This sets the waveform and ADSR values that apply to future PolySynth notes.
  setCorner(corner) {
    const [attack, decay, sustain, release] = this.music.adsr[corner];
    const waveform = this.music.wave[corner] === "saw" ? "sawtooth" : this.music.wave[corner];
    this.corner = corner;
    this.pendingCorner = null;
    this.lastCornerChange = performance.now() / 1000;
    this.synth.set({
      oscillator: { type: waveform },
      envelope: { attack, decay, sustain, release },
    });
  }

  // This smooths the emotion values and ramps effect settings to prevent audio clicks.
  animate(now) {
    if (!this.ready || document.hidden) {
      return;
    }

    const deltaSeconds = Math.max(0, (now - this.lastFrame) / 1000);
    const alpha = 1 - Math.pow(1 - AUDIO_SMOOTHING, deltaSeconds * 60);
    this.lastFrame = now;

    for (const key of Object.keys(this.smoothed)) {
      this.smoothed[key] += (this.target[key] - this.smoothed[key]) * alpha;
    }

    this.filter.frequency.rampTo(450 + this.smoothed.valence * 4300, 0.1);
    this.filter.Q.rampTo(0.55 + this.smoothed.tension * 2.8, 0.1);
    this.reverb.wet.rampTo(0.35 + (1 - this.smoothed.valence) * 0.42, 0.1);
    Tone.Transport.bpm.rampTo(28 + this.smoothed.pace * 56, 0.1);

    if (this.pendingCorner && performance.now() / 1000 - this.lastCornerChange >= CORNER_CHANGE_DELAY) {
      this.setCorner(this.pendingCorner);
    }

    this.debugUpdate?.(this.getDebug());
    this.frameId = requestAnimationFrame((time) => this.animate(time));
  }

  // This pauses animation work in a hidden tab and resumes it when the tab returns.
  handleVisibility() {
    if (!this.ready) {
      return;
    }

    if (document.hidden) {
      cancelAnimationFrame(this.frameId);
      return;
    }

    this.lastFrame = performance.now();
    this.frameId = requestAnimationFrame((time) => this.animate(time));
  }

  // This fades audio at the end of the story without abruptly cutting the final chord.
  fadeOut() {
    if (this.ready) {
      this.volume.volume.rampTo(-80, 5);
    }
  }

  // This stops scheduled notes and transport after the end fade has finished.
  stop() {
    if (!this.ready) {
      return;
    }

    cancelAnimationFrame(this.frameId);
    Tone.Transport.clear(this.repeatId);
    Tone.Transport.stop();
    this.synth.releaseAll();
  }

  // This exposes smoothed values for the hidden debug overlay.
  getDebug() {
    return { corner: this.corner, ...this.smoothed };
  }
}
