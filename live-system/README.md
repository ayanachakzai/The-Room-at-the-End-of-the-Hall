# Original live system

These are copies of the two original Python entry points used while making The Living Score. They are included for people who want to study or run the live-performance system rather than the static website.

## Files

- `perform_visual_room_precued.py` is the version that ran live at The Crypt. It matches recognised speech to fixed script cues, then applies authored emotion values, music settings, and image prompts.
- `perform_visual_room.py` is the earlier version. It asks a local Ollama model to score the emotional qualities of recognised text before driving the music and visuals.

## Requirements

These scripts were built for macOS on Apple Silicon and use the MPS device. Install the Python packages RealtimeSTT, torch, diffusers, transformers, accelerate, opencv-python, numpy and Pillow. Obtain Dorothy from the course materials. The earlier `perform_visual_room.py` also needs the Python `ollama` package, the Ollama application and its `qwen3:1.7b` model.

`diffusion_utils.py` and the Dorothy library come from the Performing Data course at UAL Creative Computing Institute, taught by Louis McCallum. They are not republished here and must be obtained separately through the course material.

## Run

Place the original `diffusion_utils.py` beside these scripts and install the required packages in an appropriate local Python environment. From the repository root, run:

```sh
cd live-system
python perform_visual_room_precued.py
```

or:

```sh
python perform_visual_room.py
```

For the earlier version, install and start Ollama first, then run `ollama pull qwen3:1.7b` before starting the Python script.

The scripts require microphone access, a working audio device, and a local setup compatible with the original course dependencies.
