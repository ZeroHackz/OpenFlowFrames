# OpenFlowFrames (Python UI)

Modern CustomTkinter frontend for RIFE video frame interpolation. Uses the bundled
`Pkgs/av/ffmpeg.exe` and `Pkgs/rife-ncnn/rife-ncnn-vulkan.exe` (works on any Vulkan GPU);
model weights are downloaded on first use from the Flowframes model server.

## Run

```
pip install customtkinter
cd OpenFlowFramesPy
python -m openflowframes
```

## Pipeline

1. `ffprobe` reads fps/frame count.
2. `ffmpeg` extracts frames to PNG.
3. `rife-ncnn-vulkan` interpolates to `frames * factor`.
4. `ffmpeg` encodes H.264 at the multiplied framerate, copying the original audio.
