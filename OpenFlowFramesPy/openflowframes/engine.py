"""Core interpolation pipeline: probe -> extract -> interpolate (rife-ncnn-vulkan) -> encode.

No GUI code in here; everything reports through a callback so it can run headless.
"""

import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import urllib.request
import zlib
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

def _find_pkgs_dir() -> Path:
    """Locate the Pkgs folder: next to a frozen (PyInstaller) exe for portable
    builds, otherwise at the repo root two levels up from this file."""
    candidates = []
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent / "Pkgs")
    candidates.append(Path(__file__).resolve().parents[2] / "Pkgs")
    for c in candidates:
        if (c / "av").is_dir():
            return c
    return candidates[-1]


PKGS_DIR = _find_pkgs_dir()
AV_DIR = PKGS_DIR / "av"
RIFE_NCNN_DIR = PKGS_DIR / "rife-ncnn"

FFMPEG = AV_DIR / "ffmpeg.exe"
FFPROBE = AV_DIR / "ffprobe.exe"
RIFE_EXE = RIFE_NCNN_DIR / "rife-ncnn-vulkan.exe"

MODEL_SERVER = "https://dl.nmkd-hz.de/flowframes/mdl/rife-ncnn"

# Hide subprocess consoles on Windows
_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def _ff_crc32(data: bytes) -> str:
    """CRC32 in Flowframes' on-server format: standard CRC32, byte-swapped
    (the C# app reads Crc32.NET's big-endian digest with BitConverter.ToUInt32)."""
    crc = zlib.crc32(data) & 0xFFFFFFFF
    return str(struct.unpack("<I", struct.pack(">I", crc))[0])


@dataclass
class VideoInfo:
    path: Path
    width: int
    height: int
    fps: Fraction
    frame_count: int
    has_audio: bool
    is_frames: bool = False  # input is a directory of images instead of a video

    @property
    def fps_float(self) -> float:
        return float(self.fps)


IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def list_frames(path: Path) -> list[Path]:
    """Image files in a directory, naturally sorted (numeric filenames sort by value)."""
    import re
    def key(p: Path):
        return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", p.stem)]
    return sorted((p for p in path.iterdir() if p.suffix.lower() in IMG_EXTS), key=key)


@dataclass
class Progress:
    stage: str = ""        # human-readable stage name
    fraction: float = 0.0  # 0..1 within the whole job
    message: str = ""      # log line (optional)


class Cancelled(Exception):
    pass


def load_models() -> list[dict]:
    """Model list from the same models.json the C# app uses (tolerates trailing commas)."""
    raw = (RIFE_NCNN_DIR / "models.json").read_text(encoding="utf-8")
    import re
    raw = re.sub(r",\s*([}\]])", r"\1", raw)
    return json.loads(raw)


def default_model(models: list[dict]) -> dict:
    for m in models:
        if str(m.get("isDefault", "")).lower() == "true":
            return m
    return models[-1]


def model_is_downloaded(model: dict) -> bool:
    mdl_dir = RIFE_NCNN_DIR / model["dir"]
    files_json = mdl_dir / "files.json"
    if not files_json.is_file():
        return False
    try:
        for entry in json.loads(files_json.read_text(encoding="utf-8")):
            f = mdl_dir / entry["dir"].strip("\\/") / entry["filename"]
            if not f.is_file() or f.stat().st_size != int(entry["size"]):
                return False
    except (OSError, ValueError, KeyError):
        return False
    return True


def download_model(model: dict, report) -> None:
    """Fetch model files from the Flowframes model server (files.json index + files)."""
    mdl_dir = RIFE_NCNN_DIR / model["dir"]
    mdl_dir.mkdir(parents=True, exist_ok=True)
    base = f"{MODEL_SERVER}/{model['dir']}"
    report(Progress("Downloading model", 0.0, f"Downloading '{model['name']}' from {base}"))
    with urllib.request.urlopen(f"{base}/files.json", timeout=30) as r:
        index = json.loads(r.read().decode("utf-8"))
    (mdl_dir / "files.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    for i, entry in enumerate(index):
        rel = Path(entry["dir"].strip("\\/")) / entry["filename"]
        dest = mdl_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        url = f"{base}/{str(rel).replace(os.sep, '/')}"
        with urllib.request.urlopen(url, timeout=60) as r:
            data = r.read()
        if len(data) != int(entry["size"]) or _ff_crc32(data) != str(entry["crc32"]).strip():
            raise RuntimeError(f"Downloaded file {entry['filename']} failed validation")
        dest.write_bytes(data)
        report(Progress("Downloading model", (i + 1) / len(index), f"Downloaded {entry['filename']}"))


def probe(path: Path) -> VideoInfo:
    cmd = [str(FFPROBE), "-v", "error", "-show_entries",
           "stream=index,codec_type,width,height,r_frame_rate,nb_frames",
           "-count_packets", "-show_entries", "stream=nb_read_packets",
           "-of", "json", str(path)]
    out = subprocess.run(cmd, capture_output=True, text=True, creationflags=_CREATE_NO_WINDOW).stdout
    data = json.loads(out)
    video = next(s for s in data["streams"] if s.get("codec_type") == "video")
    has_audio = any(s.get("codec_type") == "audio" for s in data["streams"])
    fps = Fraction(video["r_frame_rate"])
    frames = int(video.get("nb_frames") or video.get("nb_read_packets") or 0)
    return VideoInfo(path, int(video["width"]), int(video["height"]), fps, frames, has_audio)


def probe_image_dir(path: Path, fps: float) -> VideoInfo:
    """Treat a directory of images as an input clip at the given framerate."""
    frames = list_frames(path)
    if not frames:
        raise ValueError(f"No image files ({', '.join(sorted(IMG_EXTS))}) found in {path}")
    first = probe(frames[0])  # ffprobe reads image dimensions too
    return VideoInfo(path, first.width, first.height, Fraction(fps).limit_denominator(10000),
                     len(frames), has_audio=False, is_frames=True)


@dataclass
class InterpolationJob:
    video: VideoInfo
    model: dict
    factor: int
    out_path: Path
    crf: int = 17
    out_mode: str = "mp4"  # "mp4" or "png" (folder of interpolated frames)
    _cancel: threading.Event = field(default_factory=threading.Event)

    def cancel(self):
        self._cancel.set()

    def _check_cancel(self, proc=None):
        if self._cancel.is_set():
            if proc is not None:
                proc.kill()
            raise Cancelled()

    def _run_process(self, cmd, report, stage, span, total_frames, watch_dir=None):
        """Run a subprocess; if watch_dir given, report progress by counting files in it."""
        start, end = span
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                creationflags=_CREATE_NO_WINDOW)
        while proc.poll() is None:
            self._check_cancel(proc)
            if watch_dir is not None and total_frames:
                done = len(os.listdir(watch_dir))
                frac = start + (end - start) * min(1.0, done / total_frames)
                report(Progress(stage, frac))
            threading.Event().wait(0.5)
        if proc.returncode != 0:
            raise RuntimeError(f"{stage} failed (exit code {proc.returncode}): {' '.join(map(str, cmd))}")

    def run(self, report) -> Path:
        v = self.video
        out_frames_expected = v.frame_count * self.factor
        with tempfile.TemporaryDirectory(prefix="openflowframes-") as tmp:
            out_dir = Path(tmp) / "out"
            out_dir.mkdir()

            if not model_is_downloaded(self.model):
                download_model(self.model, report)

            if v.is_frames:
                in_dir = v.path  # use the image directory as-is
                report(Progress("Interpolating", 0.05, f"Using {v.frame_count} frames from {v.path.name}/"))
            else:
                in_dir = Path(tmp) / "in"
                in_dir.mkdir()
                report(Progress("Extracting frames", 0.05, f"Extracting {v.frame_count} frames..."))
                self._run_process(
                    [str(FFMPEG), "-y", "-i", str(v.path), "-fps_mode", "passthrough",
                     "-pix_fmt", "rgb24", str(in_dir / "%08d.png")],
                    report, "Extracting frames", (0.05, 0.25), v.frame_count, watch_dir=in_dir)

            in_count = len(list_frames(in_dir))
            target = in_count * self.factor
            report(Progress("Interpolating", 0.25, f"Interpolating {in_count} -> {target} frames ({self.model['name']})..."))
            self._run_process(
                [str(RIFE_EXE), "-i", str(in_dir), "-o", str(out_dir), "-n", str(target),
                 "-m", str(RIFE_NCNN_DIR / self.model["dir"]), "-f", "%08d.png"],
                report, "Interpolating", (0.25, 0.85), target, watch_dir=out_dir)

            if self.out_mode == "png":
                report(Progress("Exporting frames", 0.85, f"Moving {target} frames to {self.out_path}..."))
                self.out_path.mkdir(parents=True, exist_ok=True)
                for f in out_dir.iterdir():
                    shutil.move(str(f), str(self.out_path / f.name))
            else:
                new_fps = v.fps * self.factor
                report(Progress("Encoding", 0.85, f"Encoding at {float(new_fps):.3f} fps..."))
                cmd = [str(FFMPEG), "-y",
                       "-framerate", f"{new_fps.numerator}/{new_fps.denominator}",
                       "-i", str(out_dir / "%08d.png")]
                if v.has_audio:
                    cmd += ["-i", str(v.path), "-map", "0:v", "-map", "1:a?", "-c:a", "copy"]
                cmd += ["-c:v", "libx264", "-crf", str(self.crf), "-pix_fmt", "yuv420p",
                        str(self.out_path)]
                self._run_process(cmd, report, "Encoding", (0.85, 1.0), out_frames_expected)

        report(Progress("Done", 1.0, f"Saved: {self.out_path}"))
        return self.out_path


def make_out_path(video: VideoInfo, factor: int, out_mode: str = "mp4") -> Path:
    p = video.path
    stem = p.stem if not video.is_frames else p.name
    if out_mode == "png":
        return p.with_name(f"{stem}-{factor}x-frames")
    return p.with_name(f"{stem}-{factor}x.mp4")
