# The Room at the End of the Hall

A playable web version of **The Living Score**, a live performance system by **Muhammad Ayan Achakzai** and **Maria Naqvi**.

**Live site:** https://ayanachakzai.github.io/The-Room-at-the-End-of-the-Hall/

Read a short story aloud. The page follows your voice word by word, and the music and images change with every line.

---

## About the project

The Living Score is a live performance system that turns spoken storytelling into real-time music and images. A performer reads a short story, "The Room at the End of the Hall", aloud. The system listens, works out which line is being read, and shifts a musical score and a series of AI-generated images to match the emotional mood of each line. Sound and image become a second layer over the storytelling.

It was made for the **Performing Data** module of the MSc Applied Machine Learning for Creatives at the **UAL Creative Computing Institute**, and performed live at **The Crypt on 11 June 2026**.

The original system ran in Python on a laptop:

```
performer speaks
  -> RealtimeSTT + Whisper (base.en)   transcribes speech, sentence by sentence
  -> cue matcher                       works out which line of the story was read
  -> Dorothy PolySynth                 music shifts with the mood (chord, filter, reverb, tempo)
  -> SD Turbo                          paints an image for the scene
```

This repository holds two things:

1. **The website** (the root of this repo): a browser version of the performance that anyone can try, with nothing to install.
2. **The live system** (`live-system/`): copies of the Python code that ran at The Crypt, kept as a record.

---

## How the website works

1. **You read aloud.** Your browser's built-in speech recognition turns your voice into text. No speech model is downloaded by this site.
2. **The page follows you.** A matcher lights up each word as you say it. It is a JavaScript port of the fuzzy matcher from the live show, with the same scoring and thresholds, so it can follow you if you run lines together, misread a word or skip a line.
3. **Each line carries a mood.** All 43 lines of the story have four values from the original performance score: energy, tension, valence (how positive it feels) and pace. Each line also belongs to one of four mood "corners": grief, tender, tension or joy.
4. **The music follows the mood.** [Tone.js](https://tonejs.github.io/) rebuilds the show's synth in the browser. Each corner has its own chord, waveform and envelope. Higher valence opens the filter and brightens the sound, tension adds resonance, lower valence adds reverb, and pace sets the tempo. The live values are shown in the bottom-left corner of the screen.
5. **The images follow the scene.** The story has 27 distinct scenes. Each has three images generated in advance with SD Turbo from the show's original scene prompts, and the page slowly crossfades between them.

An About page explains the project and its limitations.

---

## Disclaimers

Please read these before trying the site or using anything in this repository.

**This is a recreation, not the live system.**

- The emotional score (the mood values for each line) was composed by hand for the live performance. The website does **not** analyse the emotion in your voice. Your voice only tells the page where you are in the story.
- The images were generated **in advance** with SD Turbo, not live while you read. They come from the same scene prompts the show used, but they are not the same images that appeared at The Crypt.
- The story, its 43 lines and its 27 scenes are fixed. The site cannot follow a different story. For a system that scores any text live, see `perform_visual_room.py` in `live-system/`.

**Browser support.**

- Speech recognition works in **Google Chrome, Microsoft Edge and Safari**.
- It does **not** work in Firefox, Opera or Brave. The site shows a message if your browser can't listen.
- It is designed for **laptops and desktops**. Phones are not supported.

**Privacy.**

- This site does not record, store or upload anything. It has no application backend, analytics, tracking or cookies.
- However, your **browser's** speech recognition may send your audio to its own service to turn it into text. For example, Chrome sends audio to Google's servers. That happens inside the browser, outside this site's control, and is covered by your browser's own privacy policy.

**Accuracy.**

- Accents, background noise, fast reading and the site's own music can make the page lose its place. It usually recovers on the next line. Use headphones so the microphone hears your voice and not the music.

**AI-generated images.**

- The images were made with SD Turbo by Stability AI. They may contain visual artefacts or odd details, as AI images often do. SD Turbo is released under Stability AI's own licence, so check its model card before reusing the images or the model.

**Course material is not included.**

- The live system depends on `diffusion_utils.py` and the Dorothy library, which come from the Performing Data course materials (taught by Louis McCallum at UAL CCI). They are not ours to republish, so they are not in this repository. Without them, the live system will not run as-is.

**The live-system code is historical.**

- The files in `live-system/` are exact copies of what ran at the performance. They are kept as a record, not maintained, and were built for macOS on Apple Silicon.

---

## Run the website on your own computer

You do not need to do this to try the project: the live site above works in any supported browser. These steps are for anyone who wants to run it locally, change it or study the code.

### What you need

- A laptop or desktop (macOS, Windows or Linux).
- **Google Chrome**, Microsoft Edge or Safari.
- **Python 3**, only to run a tiny local web server. It does not run any of the project's code.
- **Git**, to download the code. Optional: you can download a ZIP instead.
- Headphones and a microphone (a laptop's built-in microphone is fine).

### Step 1: check Python is installed

Open a terminal:

- **macOS:** press Cmd + Space, type "Terminal", press Enter.
- **Windows:** press the Windows key, type "PowerShell", press Enter.
- **Linux:** open your terminal app.

Type this and press Enter:

```bash
python3 --version
```

On Windows, if that does not work, try:

```bash
py --version
```

You should see something like `Python 3.12.4`. Any version from 3.8 upwards is fine. If you see an error, install Python from https://www.python.org/downloads/ and open a new terminal window. On Windows, tick "Add python.exe to PATH" in the installer.

### Step 2: download the code

**Option A, with Git:**

```bash
git clone https://github.com/ayanachakzai/The-Room-at-the-End-of-the-Hall.git
cd The-Room-at-the-End-of-the-Hall
```

If `git` is not found on macOS, run `xcode-select --install`, follow the prompts, then try again. On Windows, install Git from https://git-scm.com/downloads.

**Option B, without Git:**

1. On this repository's GitHub page, click the green **Code** button, then **Download ZIP**.
2. Unzip it.
3. In your terminal, move into the unzipped folder. For example, on macOS if it is in Downloads:

```bash
cd ~/Downloads/The-Room-at-the-End-of-the-Hall-main
```

To check you are in the right place, list the files (`ls` on macOS and Linux, `dir` on Windows). You should see `index.html` in the list.

### Step 3: start a local web server

From inside the project folder, run:

```bash
python3 -m http.server 8000
```

On Windows, use `py -m http.server 8000` if `python3` does not work.

You should see a line like `Serving HTTP on :: port 8000`. Leave this terminal window open while you use the site.

**Why not just double-click `index.html`?** Browsers block the microphone and block the page from loading its story data when a page is opened as a file. They only allow it on `localhost` or a secure `https://` address. The local server gives you `localhost`.

### Step 4: open the site

In Chrome, go to:

```
http://localhost:8000
```

Use `localhost` or `127.0.0.1`, not your computer's network IP address, or the microphone will be blocked.

### Step 5: try it

1. Put on headphones.
2. Click anywhere on the title screen to continue.
3. Read the "Before you begin" notes, then click anywhere to start.
4. When Chrome asks to use your microphone, click **Allow**.
5. Read each line out loud at a natural pace. The words light up as you speak, and the music and image change with the story.

### Step 6: stop the server

Go back to the terminal and press **Ctrl + C**.

### Debug mode

To see what the page is hearing and how it is matching, open:

```
http://localhost:8000/?debug=1
```

An overlay at the bottom shows the live transcript, the current line, the match score and the mood values. In debug mode, the **Right Arrow** key completes the current line, so you can test the music and images without speaking.

### Troubleshooting

| Problem | What to try |
|---|---|
| No microphone prompt appears | Check the address starts with `http://localhost` or `https://`, and that you are in Chrome, Edge or Safari. Click the icon at the left of the address bar and set Microphone to Allow, then reload. |
| "This browser can't listen" | You are in Firefox, Opera or Brave. Open the same address in Chrome, Edge or Safari. |
| Words don't light up | Check the right microphone is selected in your system settings, move somewhere quieter, and read a little more slowly. Try `?debug=1` to see what is being heard. |
| No sound | Check your volume and that the browser tab isn't muted. The music only starts after you click on the second screen. |
| Images or text are missing | Make sure you started the server from the folder that contains `index.html`. |
| "Address already in use" | Another program is using port 8000. Run `python3 -m http.server 8001` and open `http://localhost:8001`. |

---

## Run the tests

The matcher has automated tests. You need **Node.js 18 or newer** (https://nodejs.org) and a `python3` command on your PATH. Check with `node --version` and `python3 --version`. The matcher test invokes `python3` to calculate reference scores, even on Windows.

From the project folder:

```bash
node tests/matcher.test.mjs
node tests/simulate_reading.mjs
```

- `matcher.test.mjs` checks that the JavaScript port of Python's `difflib.SequenceMatcher` gives the same scores as the original. To see the Python reference values, run `python3 tests/matcher_reference.py`.
- `simulate_reading.mjs` reads the whole story through the matcher as fake speech: clean reading, lines run together, a skipped line, misheard words and numbers written as digits.

---

## Regenerate the story data and images (optional)

You only need this if you want to change the story data or remake the images. The website already includes both.

### Story data

The exporter currently reads `../perform_visual_room_precued.py`, one directory above the repository. This original file exists in the development workspace, but a fresh clone does not contain it at that location. Before running the command below in a standalone clone, put a copy of `live-system/perform_visual_room_precued.py` at `../perform_visual_room_precued.py`. Do not overwrite a different file already there.

```bash
python3 tools/export_story.py
```

The script reads the 43 cues, scene prompts, chords, waveforms and envelopes from that parent-directory file without importing it, then writes `data/story.json`. It uses only the Python standard library.

### Images

Generating images needs a machine with a capable GPU: an Apple Silicon Mac (M1 or newer) or a PC with an NVIDIA GPU. The first run downloads the SD Turbo model, which is several gigabytes.

1. Create a separate Python environment (Python 3.11 or 3.12 is safest for PyTorch):

On macOS or Linux:

```bash
python3.12 -m venv .venv-images
source .venv-images/bin/activate
```

On Windows PowerShell, use `py -3.12 -m venv .venv-images`, then `.\.venv-images\Scripts\Activate.ps1`.

2. Install the image libraries:

```bash
pip install torch diffusers transformers accelerate numpy pillow
```

3. Generate all 27 scenes, with 3 variants each:

```bash
python tools/generate_images.py --overwrite
```

The included 81 images already exist, so `--overwrite` is needed to replace them. The default is one-step `txt2img` with the TAESD decoder, the setting selected after comparing five looks. The original noise-based `img2img` method remains available as an option.

Useful options:

| Option | What it does |
|---|---|
| `--scene scene-05` | Select one scene, add `--overwrite` to replace its existing images |
| `--variants 3` | Number of images per scene |
| `--seed-base N` | Change the starting seed, add `--overwrite` for existing images |
| `--mode img2img` or `--mode txt2img` | Start from grey noise or from text; `txt2img` is the default |
| `--strength 0.78` | Set the noise-to-prompt strength for `img2img` only, from 0.5 to 1.0 |
| `--fast-vae` | Use the TAESD decoder, which is already the default |
| `--full-vae` | Use the full SD Turbo VAE instead of TAESD |
| `--overwrite` | Replace existing images |

The seeds and settings used for every image are saved in `tools/seeds.json`. Open `tools/contact_sheet.html` in a browser to review the scene variants, or `tools/compare/compare.html` to see the five-setting comparison.

4. When you have finished, leave the environment with `deactivate`.

---

## Run the original live system (advanced)

The live performance code is in `live-system/`:

| File | What it is |
|---|---|
| `perform_visual_room_precued.py` | The version that ran at The Crypt. Each of the 43 lines has hand-composed mood values and a scene prompt, and a fuzzy matcher tracks which line the performer is reading. Built for reliability under live conditions. |
| `perform_visual_room.py` | The foundation the performance version grew from. A local language model (qwen3:1.7b through Ollama) reads each line and scores its mood live, so it can respond to any text. |

**Before you start:** this code needs `diffusion_utils.py` and the Dorothy library from the Performing Data course materials, which are not included (see Disclaimers). It was built and tested only on macOS with Apple Silicon.

In outline:

1. Install the system audio libraries with Homebrew: `brew install portaudio ffmpeg`.
2. Create a Python environment and install RealtimeSTT, torch, diffusers, transformers, accelerate, opencv-python, numpy and Pillow. Obtain Dorothy from the course materials. The earlier Ollama version also needs the Python `ollama` package.
3. Place `diffusion_utils.py` from the course materials next to the scripts.
4. For `perform_visual_room.py` only: install Ollama from https://ollama.com and run `ollama pull qwen3:1.7b`.
5. From the repository root, run `cd live-system`, then `python perform_visual_room_precued.py`. A window opens and the system starts listening. Read the story aloud. The full text is in the repository's `data/story.json`, or on the live site.

Full details are in `live-system/README.md`.

---

## Project history and key decisions

- **From live scoring to a composed score.** The project was built on a version where a local language model scored the mood of each spoken line live. It worked, but under performance conditions its timing and judgements were too unpredictable. For the show, the mood of every line was composed in advance, while the system still listened and followed the performer in real time. Machine agency against reliability was the central trade-off of the project. Both versions are kept.
- **The lag was kept on purpose.** In the live show, the delay of several seconds between speech and response read as the machine sitting with the words before answering.
- **One synth, not four.** Four simultaneous synths competed for the processor and slowed down transcription. A single 8-voice synth that switches chords solved it.
- **Fresh noise for every live image.** In the live show, feeding SD Turbo's output back in as its next input collapsed into the same repeating pattern. Starting each image from fresh random noise kept the scene prompt in control. The website's current image set uses the `txt2img` option described above.
- **From stage to browser.** For the website, the Python pipeline was rebuilt for the browser: built-in speech recognition instead of Whisper, Tone.js instead of Dorothy, and images generated in advance instead of live, so the site runs anywhere at no cost with nothing to install.

---

## Repository structure

```
index.html, style.css      the website
favicon.svg, favicon.png  black favicon and fallback
js/                        speech, matching, music, visuals and screen flow
data/story.json            the 43 lines, mood values, scenes and music settings
images/                    27 scenes x 3 images, generated with SD Turbo
vendor/                    Tone.js 15.1.22 and its MIT licence
tools/                     export, image generation, seeds and image review pages
tests/                     matcher, reading simulation and browser checks
live-system/               copies of the original performance code
BUILD_LOG.md               notes from building the website
.nojekyll                  GitHub Pages deployment marker
```

Special Elite is loaded from Google Fonts by `index.html`. This repository has no `fonts/` directory.

---

## Credits

- **Muhammad Ayan Achakzai:** technical foundation, pipeline architecture, model selection and benchmarking, and the website.
- **Maria Naqvi:** artistic direction, debugging, and the pre-cued performance version.

Made for **Performing Data**, MSc Applied Machine Learning for Creatives, UAL Creative Computing Institute, taught by Louis McCallum.

Built with: SD Turbo (Stability AI), Whisper (OpenAI), RealtimeSTT, Dorothy (Louis McCallum), Ollama with Qwen3, Tone.js, the Web Speech API, and the Special Elite typeface (Astigmatic, via Google Fonts).

---

## Licence

No open-source licence has been chosen for our original code, story, images or music design, so all rights are reserved by the authors. Please get in touch before reusing them. The bundled Tone.js library has its own [MIT licence](vendor/Tone.LICENSE.md), Special Elite is served by Google Fonts under Apache License 2.0, and SD Turbo has its own model licence.
