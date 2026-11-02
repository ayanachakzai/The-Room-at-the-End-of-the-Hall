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
- Published commit `8c2d57b` to the public GitHub repository. GitHub Pages is enabled from `main` and `/`, and the first Pages build completed successfully.
- Verified the published home page, story data, scene image, Tone.js, Google Font CSS, and font file all returned HTTP 200 over HTTPS with no browser console errors.

## Fixes round 1

- Compared the raw scene-01 image with the website. The image was grey in the source file. The resting image layer uses opacity 1 and has no filter or blend mode.
- Rendered scenes 01, 06, 13, and 20 with five settings. The four-scene average saturation and value contrast were: A 17.85 and 10.65, B 27.55 and 18.82, C 27.55 and 18.82, D 88.30 and 47.63, E 95.11 and 52.03. Values use the 0 to 255 HSV scale. B and C are identical because two inference steps produce one effective img2img denoising step at either strength.
- Chose setting E, one-step text-to-image with TAESD, for vivid color, higher contrast, and a warm painterly appearance in the sample rooms. Regenerated 81 images and kept all comparison images and measurements in `tools/compare/`.
- Added browser and address checks, a four-second recognition start watchdog, arrow hints, smoothed music values, and black SVG and PNG favicons.
- Restored both copied live-system scripts byte for byte from their originals, including historical comments and title.
- The Special Elite font file has no U+2192 glyph, so the arrow hint uses the typed characters `->` in that font. The arrow is static when reduced motion is preferred.
- The first browser check found that a pending line render could repaint the story after microphone denial. Clearing that timer fixed the failure screen.
- Re-tested the 16 Python matcher parity pairs and all simulated reading scenarios. Both Node tests passed.
- Browser checks passed for Brave, Opera, a recognition start timeout, network failure before start, immediate and delayed microphone denial, a local file URL, and music value layout at 1280 by 720, 1440 by 900, 1920 by 1080, and 680 by 900.
