# OpenFlowFrames (Python UI)

Modern CustomTkinter frontend for RIFE video frame interpolation. Uses the bundled
`Pkgs/av/ffmpeg.exe` and `Pkgs/rife-ncnn/rife-ncnn-vulkan.exe` (works on any Vulkan GPU);
model weights are downloaded on first use from the Flowframes model server.

## Run (from source)

```
pip install customtkinter
cd OpenFlowFramesPy
python -m openflowframes
```

## Portable build

Run `build.bat` — it creates a venv, installs dependencies, builds a single-file
exe with PyInstaller, and copies the runtime packages (ffmpeg + rife-ncnn-vulkan)
next to it. The result in `dist/` is self-contained:

```
dist/
  OpenFlowFramesPortable.exe
  Pkgs/av/...
  Pkgs/rife-ncnn/...
```

Copy the `dist` folder anywhere and double-click the exe. Model weights are
downloaded on first use into `Pkgs/rife-ncnn/`.

## Pipeline

1. `ffprobe` reads fps/frame count.
2. `ffmpeg` extracts frames to PNG.
3. `rife-ncnn-vulkan` interpolates to `frames * factor`.
4. `ffmpeg` encodes H.264 at the multiplied framerate, copying the original audio.
