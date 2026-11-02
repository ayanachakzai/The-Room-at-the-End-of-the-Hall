# The Room at the End of the Hall

This is a playable web version of The Living Score, a live performance system by Muhammad Ayan Achakzai and Maria Naqvi for the Performing Data module at UAL Creative Computing Institute. It was first performed at The Crypt on 11 June 2026. The live site is [ayanachakzai.github.io/The-Room-at-the-End-of-the-Hall](https://ayanachakzai.github.io/The-Room-at-the-End-of-the-Hall/).

## How it works

1. The browser listens as the visitor reads the fixed story aloud.
2. It matches recognised words against the current line and can recover when a line is skipped.
3. Each authored line supplies fixed emotion values and a scene prompt.
4. The emotion values shape slow chords, filtering, reverb, and tempo with Tone.js.
5. Pre-generated SD Turbo images change with the scene and crossfade between variants.

## Authored performance material

The story, emotion values, and images are hardcoded because they were authored for the live performance. This is a playable record of that work, not a system that generates a new performance from visitor data. The full live system is in this repository, including the [live-system/](live-system/) folder.

## Limitations and privacy

- Use Chrome, Edge, or Safari for speech recognition. Firefox, Opera, and Brave cannot listen in this experience.
- Chrome's speech recognition sends audio to Google's servers to turn it into text. This website records and stores nothing.
- Accents, background noise, and fast reading can make it lose its place. It recovers on the next line.
- Images were generated in advance with SD Turbo from the show's scene prompts. They are not generated live.
- The site is designed for laptops and desktop computers.

## Run locally

From this folder, run:

```sh
python3 -m http.server 8000
```

Then open [http://localhost:8000](http://localhost:8000). Microphone access works only on localhost or HTTPS.

## Regenerate data and images

The story exporter only uses Python's standard library:

```sh
python3 tools/export_story.py
```

The image generator requires a Python environment with Torch, Diffusers, Transformers, NumPy, and Pillow. On the original machine, the existing Conda base environment is used:

```sh
conda run -n base python tools/generate_images.py --overwrite
```

It makes three image variants for every scene by default. Use `--scene scene-05`, `--variants N`, `--seed-base N`, or `--overwrite` as needed. The selected default is one-step text-to-image with TAESD, which gave the most vivid result in the comparison. To compare the original noise-based image-to-image method, use `--mode img2img --strength 0.78`. Use `--full-vae` to compare the full SD Turbo VAE. The five-setting review is in [tools/compare/compare.html](tools/compare/compare.html).

## Deploy

### GitHub Pages

Push this folder as its own repository, then open Settings, Pages, and deploy from the `main` branch root. The included `.nojekyll` file is required for a plain static deployment.

### Netlify

Drag and drop this folder, or connect the repository. There is no build command. The publish directory is the repository root.

## Credits and licences

- Tone.js 15.1.22 is bundled in `vendor/tone.js` under the MIT License.
- Special Elite is by Astigmatic and is loaded from Google Fonts. It is licensed under Apache License 2.0.
- SD Turbo is loaded only by the optional offline image generator. See its Hugging Face model licence before redistributing generated material.

## Live system

The [live-system/](live-system/) folder contains the two original Python entry points from the performance project. It deliberately does not contain the course-provided `diffusion_utils.py` helper or the Dorothy library.
