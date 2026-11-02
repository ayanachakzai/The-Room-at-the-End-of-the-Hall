"""Generate fixed SD Turbo scene images for the static website."""

import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
from diffusers import AutoPipelineForImage2Image, AutoPipelineForText2Image, AutoencoderTiny
from PIL import Image


# SD Turbo was the model used by the live performance.
MODEL_ID = "stabilityai/sd-turbo"

# TAESD matches the VAE used by the live helper and gives the selected vivid look.
FAST_VAE_ID = "madebyollin/taesd"

# SD Turbo produces its best results at its native square resolution.
IMAGE_SIZE = 512

# Img2img remains available for comparison and needs at least one denoising step.
IMAGE_STEPS = 2

# This matches the live show's balance between the noise image and the prompt.
IMAGE_STRENGTH = 0.78

# SD Turbo does not need classifier-free guidance for these one or two step renders.
GUIDANCE_SCALE = 0.0

# WebP quality balances image quality with the website's page-weight target.
WEBP_QUALITY = 82

# These folders are relative to this script so the command works from any directory.
WEB_ROOT = Path(__file__).resolve().parents[1]
STORY_PATH = WEB_ROOT / "data" / "story.json"
IMAGE_DIR = WEB_ROOT / "images"
SEEDS_PATH = WEB_ROOT / "tools" / "seeds.json"
CONTACT_SHEET_PATH = WEB_ROOT / "tools" / "contact_sheet.html"


# Read the generated story data that defines every fixed scene prompt.
def load_story():
    return json.loads(STORY_PATH.read_text(encoding="utf-8"))


# Choose the Apple GPU when present, falling back to CUDA or CPU for portability.
def choose_device():
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


# Load an SD Turbo image-to-image or text-to-image pipeline with the selected VAE.
def load_pipeline(device, mode, fast_vae):
    pipeline_type = AutoPipelineForImage2Image if mode == "img2img" else AutoPipelineForText2Image
    dtype = torch.float16 if device != "cpu" else torch.float32
    options = {"torch_dtype": dtype}

    if device != "cpu":
        options["variant"] = "fp16"

    pipe = pipeline_type.from_pretrained(MODEL_ID, **options).to(device)

    if fast_vae:
        pipe.vae = AutoencoderTiny.from_pretrained(FAST_VAE_ID, torch_dtype=dtype).to(device)

    pipe.set_progress_bar_config(disable=True)
    return pipe


# Make the deterministic noise image used by the live system's img2img workflow.
def make_noise_image(seed):
    random = np.random.default_rng(seed)
    pixels = random.integers(70, 145, (IMAGE_SIZE, IMAGE_SIZE, 3), dtype=np.uint8)
    return Image.fromarray(pixels, mode="RGB")


# Return the letter suffix used by each scene variant file.
def variant_letter(index):
    return chr(ord("a") + index)


# Render one reproducible image using either the show-like img2img path or comparison txt2img.
def generate_image(pipe, prompt, seed, mode, strength=IMAGE_STRENGTH):
    generator = torch.Generator(device="cpu").manual_seed(seed)

    if mode == "img2img":
        return pipe(
            prompt=prompt,
            image=make_noise_image(seed),
            num_inference_steps=IMAGE_STEPS,
            strength=strength,
            guidance_scale=GUIDANCE_SCALE,
            generator=generator,
        ).images[0]

    return pipe(
        prompt=prompt,
        num_inference_steps=1,
        guidance_scale=GUIDANCE_SCALE,
        height=IMAGE_SIZE,
        width=IMAGE_SIZE,
        generator=generator,
    ).images[0]


# Create a plain local review page containing every generated variant and its prompt.
def write_contact_sheet(story, variants):
    cards = []

    for scene in story["scenes"]:
        images = "".join(
            f'<img src="../images/{scene["id"]}-{variant_letter(index)}.webp" alt="{scene["short"]}">'
            for index in range(variants)
        )
        cards.append(
            "<section>"
            f"<h2>{scene['id']}</h2>"
            f'<div class="variants">{images}</div>'
            f"<p>{scene['prompt']}</p>"
            "</section>"
        )

    page = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>The Living Score image review</title>
  <style>
    body { margin: 0; padding: 2rem; background: #000; color: #e8e6e1; font: 16px monospace; }
    section { margin: 0 0 3rem; }
    h2 { font-size: 1rem; font-weight: 400; }
    .variants { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; }
    img { width: 100%; aspect-ratio: 1; object-fit: cover; background: #0d0d0d; }
    p { max-width: 72rem; color: #a8a6a1; line-height: 1.5; }
  </style>
</head>
<body>
  <h1>The Living Score, image review</h1>
""" + "\n".join(cards) + "\n</body>\n</html>\n"
    CONTACT_SHEET_PATH.write_text(page, encoding="utf-8")


# Parse the supported command-line options for repeatable scene generation.
def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", help="Generate one scene id, for example scene-05")
    parser.add_argument("--variants", type=int, default=3, help="Variants per scene, default: 3")
    parser.add_argument("--seed-base", type=int, default=20260611, help="First reproducible seed")
    parser.add_argument("--mode", choices=("img2img", "txt2img"), default="txt2img")
    parser.add_argument("--strength", type=float, default=IMAGE_STRENGTH, help="Img2img strength, default: 0.78")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing image files")
    vae = parser.add_mutually_exclusive_group()
    vae.add_argument("--fast-vae", action="store_true", dest="fast_vae", help="Use TAESD, the selected default")
    vae.add_argument("--full-vae", action="store_false", dest="fast_vae", help="Compare with the full SD Turbo VAE")
    parser.set_defaults(fast_vae=True)
    return parser.parse_args()


# Generate selected scenes, record their settings, and update the review sheet.
def main():
    arguments = parse_arguments()
    story = load_story()
    scenes = story["scenes"]

    if arguments.variants < 1 or arguments.variants > 26:
        raise ValueError("--variants must be between 1 and 26")
    if arguments.mode == "img2img" and not 0.5 <= arguments.strength <= 1.0:
        raise ValueError("--strength must be from 0.5 to 1.0 with two inference steps")

    if arguments.scene:
        scenes = [scene for scene in scenes if scene["id"] == arguments.scene]
        if not scenes:
            raise ValueError(f"Unknown scene: {arguments.scene}")

    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    device = choose_device()
    print(f"Using {device} with {'TAESD' if arguments.fast_vae else 'the full SD Turbo VAE'}.")
    pipe = load_pipeline(device, arguments.mode, arguments.fast_vae)
    started = time.perf_counter()
    existing_records = {}
    if SEEDS_PATH.exists():
        previous = json.loads(SEEDS_PATH.read_text(encoding="utf-8"))
        existing_records = {item["file"]: item for item in previous.get("images", [])}
    records = dict(existing_records)
    processed = 0

    for scene in scenes:
        scene_number = int(scene["id"].split("-")[1])

        for variant_index in range(arguments.variants):
            suffix = variant_letter(variant_index)
            output_path = IMAGE_DIR / f"{scene['id']}-{suffix}.webp"
            seed = arguments.seed_base + (scene_number - 1) * arguments.variants + variant_index
            record = {
                "file": output_path.name,
                "sceneId": scene["id"],
                "seed": seed,
                "mode": arguments.mode,
                "size": IMAGE_SIZE,
                "numInferenceSteps": IMAGE_STEPS if arguments.mode == "img2img" else 1,
                "strength": arguments.strength if arguments.mode == "img2img" else None,
                "guidanceScale": GUIDANCE_SCALE,
                "vae": FAST_VAE_ID if arguments.fast_vae else "full SD Turbo VAE",
            }

            if output_path.exists() and not arguments.overwrite:
                if output_path.name not in existing_records:
                    raise ValueError(f"No saved seed for {output_path.name}; use --overwrite")
                print(f"Keeping {output_path.name}")
                processed += 1
                continue

            image_started = time.perf_counter()
            image = generate_image(pipe, scene["prompt"], seed, arguments.mode, arguments.strength)
            image.save(output_path, "WEBP", quality=WEBP_QUALITY, method=6)
            seconds = time.perf_counter() - image_started
            record["seconds"] = round(seconds, 2)
            records[output_path.name] = record
            processed += 1
            print(f"Generated {output_path.name} in {seconds:.2f}s")

    all_images_use_e = all(
        item.get("mode") == "txt2img" and item.get("vae") == FAST_VAE_ID
        for item in records.values()
    )
    seeds = {
        "model": MODEL_ID,
        "device": device,
        "selectedComparisonSetting": "E" if all_images_use_e else "mixed or custom",
        "images": [records[name] for name in sorted(records)],
    }
    SEEDS_PATH.write_text(json.dumps(seeds, indent=2) + "\n", encoding="utf-8")
    write_contact_sheet(story, arguments.variants)
    total = time.perf_counter() - started
    print(f"Processed {processed} images with {len(records)} seed records in {total:.2f}s")


if __name__ == "__main__":
    main()
