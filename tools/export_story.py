"""Export the fixed performance cues into browser-friendly JSON."""

import ast
import json
from pathlib import Path


# These names are the literal values needed by the static website.
REQUIRED_NAMES = {"SCRIPT_CUES", "VISUAL_STYLE", "CHORDS", "WAVE", "ADSR"}

# This is the original source file confirmed for the website export.
SOURCE_PATH = Path(__file__).resolve().parents[2] / "perform_visual_room_precued.py"

# This is the generated data file used by the browser code.
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "story.json"


# Read selected top-level literal assignments without importing performance dependencies.
def read_literals(source_path):
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    values = {}

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue

        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in REQUIRED_NAMES:
                values[target.id] = ast.literal_eval(node.value)

    missing = REQUIRED_NAMES - values.keys()
    if missing:
        names = ", ".join(sorted(missing))
        raise ValueError(f"Missing literal assignments: {names}")

    return values


# Build stable scene ids in the order scenes first appear in the performance.
def build_story(values):
    scene_ids = {}
    scenes = []
    lines = []

    for index, cue in enumerate(values["SCRIPT_CUES"]):
        scene_text = cue["scene"]

        if scene_text not in scene_ids:
            scene_id = f"scene-{len(scene_ids) + 1:02d}"
            scene_ids[scene_text] = scene_id
            scenes.append(
                {
                    "id": scene_id,
                    "prompt": f"{values['VISUAL_STYLE']}, {scene_text}",
                    "short": " ".join(scene_text.split()[:6]),
                }
            )

        lines.append(
            {
                "index": index,
                "text": cue["text"],
                "corner": cue["corner"],
                "e": cue["e"],
                "t": cue["t"],
                "v": cue["v"],
                "p": cue["p"],
                "sceneId": scene_ids[scene_text],
            }
        )

    return {
        "title": "The Room at the End of the Hall",
        "authors": ["Muhammad Ayan Achakzai", "Maria Naqvi"],
        "visualStyle": values["VISUAL_STYLE"],
        "scenes": scenes,
        "lines": lines,
        "music": {
            "chords": values["CHORDS"],
            "wave": values["WAVE"],
            "adsr": values["ADSR"],
        },
    }


# Print the scene mapping so each exported line can be checked against the source.
def print_summary(story):
    print(f"Lines: {len(story['lines'])}")
    print(f"Scenes: {len(story['scenes'])}")

    for scene in story["scenes"]:
        line_numbers = [
            str(line["index"] + 1)
            for line in story["lines"]
            if line["sceneId"] == scene["id"]
        ]
        print(f"{scene['id']}: lines {', '.join(line_numbers)}")


# Export the story data and show the generated scene mapping.
def main():
    values = read_literals(SOURCE_PATH)
    story = build_story(values)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(story, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print_summary(story)


if __name__ == "__main__":
    main()
