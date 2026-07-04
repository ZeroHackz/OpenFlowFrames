# OpenFlowFrames - Video Frame Interpolation for Windows

This project is a fork of the original [Flowframes by n00mkrad](https://github.com/n00mkrad/flowframes). Huge thanks to him for creating and maintaining the powerful core of this application!

This fork is a **lean, fully free and open** reimagining: a modern Python GUI around the latest RIFE models — no Patreon tiers, no paid builds, no legacy codebase.

### Screenshot

*Main interface: pick a video or a folder of frames, choose a model and factor, interpolate.*

![Main interface](screenshots/MainInterface.png)

## ✨ Features

*   **Latest RIFE Models:** RIFE up to 4.26, downloaded and validated automatically on first use.
*   **Any GPU:** Runs on AMD, Intel, and NVIDIA via `rife-ncnn-vulkan` — no CUDA or PyTorch required.
*   **Modern GUI:** A clean CustomTkinter dark-mode interface — no install needed beyond Python.
*   **Video or Frame-Folder Input:** Interpolate a video file, or a directory of PNG/JPG/WebP frames with a custom input framerate.
*   **MP4 or PNG Output:** Encode to H.264 MP4 (audio preserved) or export the interpolated frames as a PNG sequence.
*   **Robust Frame Handling:** Mixed resolutions and alpha/16-bit PNGs (common in AI-generated frames) are normalized automatically.
*   **Portable Windows Executable:** Build a self-contained portable app with one script — no Python needed on the target machine.
*   **No Monetization:** Fully free; no Patreon/PayPal integrations.

## 💻 How to Use (Easy Way)

**Python GUI (recommended):**

1.  Clone this repository:
    ```bash
    git clone https://github.com/ZeroHackz/OpenFlowFrames.git
    ```
2.  Double-click `launcher-gui.bat` — it sets up a virtual environment on first run and launches the GUI.

**Portable build:**

Run `build-portable.bat`. The result in `dist/` is fully self-contained:

```
dist/
  OpenFlowFramesPortable.exe
  packages/av/           (ffmpeg)
  packages/rife-ncnn/    (interpolator; models download here on first use)
```

Copy the `dist` folder anywhere and double-click the exe.

## How It Works

1. `ffprobe` reads the input framerate and frame count (or you provide the FPS for a frame folder).
2. `ffmpeg` extracts frames (skipped for frame-folder input).
3. `rife-ncnn-vulkan` interpolates to `frames × factor`.
4. `ffmpeg` encodes H.264 at the multiplied framerate, copying the original audio — or the frames are exported as PNGs.

## Credits

- [Flowframes](https://github.com/n00mkrad/flowframes) by n00mkrad — the original application this fork is based on
- [RIFE](https://github.com/hzwer/Practical-RIFE) by hzwer
- [rife-ncnn-vulkan](https://github.com/nihui/rife-ncnn-vulkan) by nihui
- [FFmpeg](https://ffmpeg.org/)
