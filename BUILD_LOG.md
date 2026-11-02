# Build log

## Phase 1

- Exported `data/story.json` from the confirmed root `perform_visual_room_precued.py` with `ast.parse` and `ast.literal_eval`.
- Verified 43 lines, 27 unique scenes, exact source text, and the expected music tables.

## Phase 2

- Checked Conda environments before image work. The existing `base` environment contains Torch 2.11.0, Diffusers 0.38.0, Transformers 4.57.6, NumPy 1.26.4, and Pillow 12.3.0.
- Used that existing environment unchanged on the MPS device.
- Wrote `tools/generate_images.py` with full SD Turbo VAE as the default and an optional `--fast-vae` TAESD comparison mode.
- Generated 27 scenes with three deterministic img2img variants each at 512 by 512, WebP quality 82. Wrote `tools/seeds.json` and `tools/contact_sheet.html`.

## Phase 3

- Built the three-screen static interface with the specified Special Elite type, black palette, placeholder support, keyboard access, responsive layout, and reduced-motion fallback.

## Phase 4

- Ported the live text normalisation, weighted matching, and difflib autojunk behaviour to JavaScript.
- Added word-level matching, skipped-line recovery, microphone restart handling, debug mode, Python parity tests, and simulated readings.

## Phase 5

- Bundled Tone.js 15.1.22 and recreated the PolySynth, low-pass filter, reverb, transport, emotion smoothing, and chord-change throttle.

## Phase 6

- Added two-layer image crossfades, scene preloading, variant cycling, placeholder fallback, and the six-second end sequence.

## Phase 7

- Added this README, local run and deployment instructions, privacy notes, licences, and acceptance checks.
- Automated checks passed: `node tests/matcher.test.mjs` for 16 Python parity pairs, `node tests/simulate_reading.mjs` for clean, joined, skipped, noisy, and numeric readings, Python JSON validation, and local Chrome visual checks.

## Phase 8

- Copied the two original Python entry points into `live-system/` and did not copy the course-provided `diffusion_utils.py` helper.
- Replaced em dashes only in comments and the copied precued window title to respect the website publication rule. Runtime matching, prompt, image, and audio code was not changed.
