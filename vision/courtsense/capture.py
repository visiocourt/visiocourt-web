"""Unified frame capture for laptops and Raspberry Pi.

Why this exists: on current Raspberry Pi OS (Bookworm) the CSI ribbon camera
(Camera Module 3, HQ cam, etc.) is driven by libcamera and does NOT open through
``cv2.VideoCapture``. USB webcams and RTSP streams do. This class hides that
difference so the runtime code does not care what is plugged in.

Source strings understood:
    "0", "1", ...        USB / V4L2 camera index           (OpenCV)
    "picamera" / "csi"   Pi CSI camera via picamera2        (libcamera)
    "/path/file.mp4"     video file                         (OpenCV)
    "rtsp://..."         network stream                     (OpenCV)

All backends return BGR numpy frames, the convention OpenCV and Ultralytics
expect, so the rest of the pipeline is identical regardless of source.
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np

_CSI_ALIASES = {"picamera", "picamera2", "csi", "libcamera"}


class FrameSource:
    """A camera/video source with a uniform ``read`` / ``release`` interface."""

    def __init__(
        self,
        source: str,
        width: int = 1280,
        height: int = 720,
        fps: Optional[float] = None,
    ) -> None:
        self.source = str(source)
        self.width = width
        self.height = height
        self.fps = fps
        self.backend: str = ""
        self._cap = None
        self._picam = None

        if self.source.lower() in _CSI_ALIASES:
            self._open_csi()
        else:
            self._open_opencv()

    # --------------------------------------------------------------- backends
    def _open_csi(self) -> None:
        try:
            from picamera2 import Picamera2
        except Exception as exc:  # pragma: no cover - only on a real Pi
            raise RuntimeError(
                "picamera2 is required for the CSI camera. Install it with "
                "'sudo apt install -y python3-picamera2' and create your venv "
                "with '--system-site-packages'."
            ) from exc

        self._picam = Picamera2()
        # "RGB888" in picamera2 yields BGR-ordered bytes in the numpy array,
        # which is exactly what OpenCV/Ultralytics want, so no conversion needed.
        config = self._picam.create_video_configuration(
            main={"size": (self.width, self.height), "format": "RGB888"}
        )
        if self.fps:
            frame_us = int(1_000_000 / self.fps)
            config["controls"] = {"FrameDurationLimits": (frame_us, frame_us)}
        self._picam.configure(config)
        self._picam.start()
        self.backend = "picamera2"

    def _open_opencv(self) -> None:
        import cv2

        target = int(self.source) if self.source.isdigit() else self.source
        cap = cv2.VideoCapture(target)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        if self.fps:
            cap.set(cv2.CAP_PROP_FPS, self.fps)
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video source: {self.source!r}")
        self._cap = cap
        self.backend = "opencv"

    # ----------------------------------------------------------------- public
    def read(self) -> Tuple[bool, Optional["np.ndarray"]]:
        if self._picam is not None:
            frame = self._picam.capture_array()
            return frame is not None, frame
        ok, frame = self._cap.read()
        return ok, frame

    def release(self) -> None:
        if self._picam is not None:
            try:
                self._picam.stop()
            except Exception:
                pass
            self._picam = None
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def __enter__(self) -> "FrameSource":
        return self

    def __exit__(self, *_exc) -> None:
        self.release()
