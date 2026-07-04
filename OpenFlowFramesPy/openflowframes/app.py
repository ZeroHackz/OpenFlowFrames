"""OpenFlowFrames - CustomTkinter GUI for RIFE video frame interpolation."""

import queue
import threading
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from . import engine

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

FACTORS = [2, 3, 4, 8]


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("OpenFlowFrames")
        self.geometry("720x560")
        self.minsize(640, 520)

        self.video: engine.VideoInfo | None = None
        self.job: engine.InterpolationJob | None = None
        self.models = engine.load_models()
        self._events: queue.Queue = queue.Queue()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        # --- Input row ---
        in_frame = ctk.CTkFrame(self)
        in_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        in_frame.grid_columnconfigure(0, weight=1)
        self.path_entry = ctk.CTkEntry(in_frame, placeholder_text="Select a video file...")
        self.path_entry.grid(row=0, column=0, sticky="ew", padx=(10, 6), pady=10)
        ctk.CTkButton(in_frame, text="Browse", width=90, command=self.browse).grid(
            row=0, column=1, padx=(0, 10), pady=10)

        self.info_label = ctk.CTkLabel(self, text="No video loaded", anchor="w",
                                       text_color="gray70")
        self.info_label.grid(row=1, column=0, sticky="ew", padx=22)

        # --- Options row ---
        opt = ctk.CTkFrame(self)
        opt.grid(row=2, column=0, sticky="ew", padx=12, pady=6)
        for c in range(4):
            opt.grid_columnconfigure(c, weight=1)

        ctk.CTkLabel(opt, text="AI Model").grid(row=0, column=0, sticky="w", padx=10, pady=(8, 0))
        self.model_menu = ctk.CTkOptionMenu(opt, values=[m["name"] for m in self.models])
        self.model_menu.set(engine.default_model(self.models)["name"])
        self.model_menu.grid(row=1, column=0, sticky="ew", padx=10, pady=(2, 10))

        ctk.CTkLabel(opt, text="Factor").grid(row=0, column=1, sticky="w", padx=10, pady=(8, 0))
        self.factor_menu = ctk.CTkOptionMenu(opt, values=[f"{f}x" for f in FACTORS],
                                             command=lambda _: self.update_info())
        self.factor_menu.set("2x")
        self.factor_menu.grid(row=1, column=1, sticky="ew", padx=10, pady=(2, 10))

        ctk.CTkLabel(opt, text="Quality (CRF)").grid(row=0, column=2, sticky="w", padx=10, pady=(8, 0))
        self.crf_slider = ctk.CTkSlider(opt, from_=10, to=30, number_of_steps=20,
                                        command=self._crf_changed)
        self.crf_slider.set(17)
        self.crf_slider.grid(row=1, column=2, sticky="ew", padx=10, pady=(2, 10))
        self.crf_label = ctk.CTkLabel(opt, text="17")
        self.crf_label.grid(row=1, column=3, sticky="w", padx=(0, 10))

        # --- Progress + actions ---
        act = ctk.CTkFrame(self)
        act.grid(row=3, column=0, sticky="ew", padx=12, pady=6)
        act.grid_columnconfigure(0, weight=1)
        self.progress = ctk.CTkProgressBar(act)
        self.progress.set(0)
        self.progress.grid(row=0, column=0, sticky="ew", padx=10, pady=12)
        self.run_btn = ctk.CTkButton(act, text="Interpolate", width=120, command=self.start)
        self.run_btn.grid(row=0, column=1, padx=(6, 4), pady=12)
        self.cancel_btn = ctk.CTkButton(act, text="Cancel", width=80, state="disabled",
                                        fg_color="gray30", command=self.cancel)
        self.cancel_btn.grid(row=0, column=2, padx=(0, 10), pady=12)

        # --- Log ---
        self.log_box = ctk.CTkTextbox(self, state="disabled", font=("Consolas", 12))
        self.log_box.grid(row=4, column=0, sticky="nsew", padx=12, pady=(6, 12))

        self.after(100, self._poll_events)

    # ---------- UI helpers ----------

    def log(self, msg: str):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _crf_changed(self, value):
        self.crf_label.configure(text=str(int(value)))

    def browse(self):
        path = filedialog.askopenfilename(filetypes=[
            ("Video files", "*.mp4 *.mkv *.mov *.avi *.webm *.gif"), ("All files", "*.*")])
        if path:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, path)
            self.load_video(Path(path))

    def load_video(self, path: Path):
        try:
            self.video = engine.probe(path)
        except Exception as e:
            self.video = None
            self.info_label.configure(text=f"Failed to read video: {e}", text_color="#e05555")
            return
        self.update_info()

    def update_info(self):
        if not self.video:
            return
        v = self.video
        factor = int(self.factor_menu.get().rstrip("x"))
        out_fps = v.fps_float * factor
        self.info_label.configure(
            text=f"{v.path.name}  —  {v.width}x{v.height}, {v.frame_count} frames @ "
                 f"{v.fps_float:.3f} fps  →  {out_fps:.3f} fps",
            text_color="gray70")

    # ---------- pipeline ----------

    def start(self):
        if self.job:
            return
        if not self.video:
            self.log("Select a video first.")
            return
        model = next(m for m in self.models if m["name"] == self.model_menu.get())
        factor = int(self.factor_menu.get().rstrip("x"))
        out_path = engine.make_out_path(self.video, factor)
        self.job = engine.InterpolationJob(self.video, model, factor, out_path,
                                           crf=int(self.crf_slider.get()))
        self.run_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.log(f"Starting: {self.video.path.name} -> {out_path.name} "
                 f"({model['name']}, {factor}x, CRF {int(self.crf_slider.get())})")
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        try:
            self.job.run(self._events.put)
        except engine.Cancelled:
            self._events.put(engine.Progress("Cancelled", 0.0, "Cancelled."))
        except Exception as e:
            self._events.put(engine.Progress("Error", 0.0, f"Error: {e}"))
        finally:
            self._events.put(None)  # sentinel: job finished

    def _poll_events(self):
        try:
            while True:
                ev = self._events.get_nowait()
                if ev is None:
                    self.job = None
                    self.run_btn.configure(state="normal")
                    self.cancel_btn.configure(state="disabled")
                else:
                    self.progress.set(ev.fraction)
                    if ev.message:
                        self.log(ev.message)
        except queue.Empty:
            pass
        self.after(100, self._poll_events)

    def cancel(self):
        if self.job:
            self.job.cancel()
            self.log("Cancelling...")


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
