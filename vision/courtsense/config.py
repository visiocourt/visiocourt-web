"""Calibration config for CourtSense cameras and courts.

A facility has one or more courts, and each court is watched by one or more
cameras. Each camera stores the homography that maps its pixels onto that
court's shared top down coordinate frame (feet). Because every camera writes
into the *same* world frame, fusing them later is just a matter of merging
points that land close together.

The config is plain JSON so it is easy to inspect, diff, and ship to the Pi.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

import numpy as np

# Standard court footprints in feet (length x width), playing area only.
# Handy defaults for the calibration tool and the top down renderer.
COURT_PRESETS = {
    "tennis": (78.0, 36.0),
    "pickleball": (44.0, 20.0),
    "basketball": (94.0, 50.0),
    "basketball_half": (47.0, 50.0),
    "volleyball": (59.0, 29.5),
    "multiuse": (60.0, 30.0),
}


@dataclass
class CameraConfig:
    """One camera's calibration against a court."""

    camera_id: str
    homography: list  # 3x3 row major, maps image pixels -> world feet
    source: str = "0"  # cv2.VideoCapture source: index, path, or RTSP URL
    image_size: Optional[list] = None  # [width, height] of the calibration frame
    reprojection_error_ft: Optional[float] = None
    notes: str = ""

    @property
    def homography_matrix(self) -> "np.ndarray":
        return np.asarray(self.homography, dtype=np.float64).reshape(3, 3)


@dataclass
class CourtConfig:
    """A court, its dimensions, and the cameras watching it."""

    court_id: str
    sport: str = "pickleball"
    # Court size in feet (length, width). Defaults to the sport preset.
    length_ft: float = 0.0
    width_ft: float = 0.0
    # Occupancy thresholds (number of people on the playing surface).
    capacity: int = 4
    overcrowded_at: int = 8
    cameras: list = field(default_factory=list)  # list[CameraConfig]

    def __post_init__(self) -> None:
        if (self.length_ft <= 0 or self.width_ft <= 0) and self.sport in COURT_PRESETS:
            self.length_ft, self.width_ft = COURT_PRESETS[self.sport]
        # Allow cameras to be passed as plain dicts (e.g. from JSON).
        self.cameras = [
            cam if isinstance(cam, CameraConfig) else CameraConfig(**cam)
            for cam in self.cameras
        ]

    def camera(self, camera_id: str) -> CameraConfig:
        for cam in self.cameras:
            if cam.camera_id == camera_id:
                return cam
        raise KeyError(f"No camera {camera_id!r} on court {self.court_id!r}")

    def to_dict(self) -> dict:
        data = asdict(self)
        return data


def save_config(court: CourtConfig, path: str | Path) -> None:
    """Persist a :class:`CourtConfig` to JSON."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(court.to_dict(), fh, indent=2)


def load_config(path: str | Path) -> CourtConfig:
    """Load a :class:`CourtConfig` from JSON written by :func:`save_config`."""
    with Path(path).open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    return CourtConfig(**data)
