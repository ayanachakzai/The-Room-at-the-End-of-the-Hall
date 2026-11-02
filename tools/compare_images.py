"""Render five SD Turbo settings for four scenes and measure their color."""

import html
import json
import statistics
import time
from pathlib import Path

from PIL import Image, ImageStat

from generate_images import (
    IMAGE_SIZE,
    MODEL_ID,
    WEBP_QUALITY,
    choose_device,
    generate_image,
    load_pipeline,
    load_story,
)


# These four prompts cover a warm room, a door, a dark hall, and morning light.
SCENE_IDS = ("scene-01", "scene-06", "scene-13", "scene-20")

# Each comparison uses the same seed that the original scene's first variant used.
SEED_BASE = 20260611

# These settings match the requested A through E comparison exactly.
SETTINGS = (
    ("A", "img2img", 0.78, False),
    ("B", "img2img", 0.78, True),
    ("C", "img2img", 0.9, True),
    ("D", "txt2img", None, False),
    ("E", "txt2img", None, True),
)

COMPARE_DIR = Path(__file__).resolve().parent / "compare"


# This measures the saved WebP, which is the exact image a visitor will see.
def image_metrics(path):
    with Image.open(path) as image:
        hsv = image.convert("RGB").convert("HSV")
        saturation = ImageStat.Stat(hsv.getchannel("S")).mean[0]
        contrast = ImageStat.Stat(hsv.getchannel("V")).stddev[0]
    return round(saturation, 2), round(contrast, 2)


# This makes a simple black review page with four rows and five labelled images.
def write_html(scenes, records):
    sections = []
    by_key = {(item["sceneId"], item["setting"]): item for item in records}

    for scene in scenes:
        cells = []
        for letter, mode, strength, fast_vae in SETTINGS:
            item = by_key[(scene["id"], letter)]
            label = f"{letter}: {mode}, {strength if strength is not None else '1 step'}, {'TAESD' if fast_vae else 'full VAE'}"
            cells.append(
                '<figure>'
                f'<img src="{item["file"]}" alt="{html.escape(scene["id"] + " setting " + letter)}">'
                f'<figcaption>{html.escape(label)}<br>S {item["meanS"]:.2f}, V SD {item["stdV"]:.2f}</figcaption>'
                '</figure>'
            )
        sections.append(
            f'<section><h2>{scene["id"]}</h2><div class="row">{"".join(cells)}</div>'
            f'<p>{html.escape(scene["prompt"])}</p></section>'
        )

    document = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>SD Turbo comparison</title><style>
body { margin: 0; padding: 2rem; background: #000; color: #e8e6e1; font: 14px monospace; }
section { margin-bottom: 3rem; } h2 { font-weight: normal; } p { color: #a8a6a1; line-height: 1.5; }
.row { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 1rem; }
figure { margin: 0; } img { display: block; width: 100%; aspect-ratio: 1; object-fit: cover; }
figcaption { padding-top: .6rem; line-height: 1.5; }
@media (max-width: 850px) { .row { overflow-x: auto; grid-template-columns: repeat(5, 180px); } }
</style></head><body><h1>SD Turbo comparison</h1>
""" + "\n".join(sections) + "\n</body></html>\n"
    (COMPARE_DIR / "compare.html").write_text(document, encoding="utf-8")


# This generates each setting, then writes the metric records and review page.
def main():
    story = load_story()
    scenes = [scene for scene in story["scenes"] if scene["id"] in SCENE_IDS]
    device = choose_device()
    COMPARE_DIR.mkdir(parents=True, exist_ok=True)
    records = []

    for letter, mode, strength, fast_vae in SETTINGS:
        print(f"Loading {letter}: {mode}, {'TAESD' if fast_vae else 'full VAE'}", flush=True)
        pipe = load_pipeline(device, mode, fast_vae)
        for scene in scenes:
            scene_number = int(scene["id"].split("-")[1])
            seed = SEED_BASE + (scene_number - 1) * 3
            path = COMPARE_DIR / f'{scene["id"]}-{letter}.webp'
            start = time.perf_counter()
            image = generate_image(pipe, scene["prompt"], seed, mode, strength or 0.78)
            image.save(path, "WEBP", quality=WEBP_QUALITY, method=6)
            mean_s, std_v = image_metrics(path)
            records.append({
                "setting": letter, "sceneId": scene["id"], "file": path.name,
                "seed": seed, "mode": mode, "strength": strength,
                "vae": "madebyollin/taesd" if fast_vae else "full SD Turbo VAE",
                "meanS": mean_s, "stdV": std_v,
            })
            print(f'{path.name}: S {mean_s:.2f}, V SD {std_v:.2f}, {time.perf_counter() - start:.1f}s', flush=True)
        del pipe

    summary = {}
    for letter, _, _, _ in SETTINGS:
        samples = [item for item in records if item["setting"] == letter]
        summary[letter] = {
            "meanS": round(statistics.mean(item["meanS"] for item in samples), 2),
            "stdV": round(statistics.mean(item["stdV"] for item in samples), 2),
        }
    (COMPARE_DIR / "metrics.json").write_text(
        json.dumps({"model": MODEL_ID, "device": device, "size": IMAGE_SIZE, "records": records, "summary": summary}, indent=2) + "\n",
        encoding="utf-8",
    )
    write_html(scenes, records)
    print(f"Summary: {summary}", flush=True)


if __name__ == "__main__":
    main()
