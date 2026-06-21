"""Rendering for CourtSense: camera overlay and the top down court map.

The top down map is the "3D feeling" view you asked for. It is not literal
depth, it is a calibrated bird's eye projection of the court, which is exactly
what makes two players who overlap in the camera appear cleanly separated.

All drawing degrades to no ops if OpenCV is missing, so importing this module
never breaks a headless analytics only deployment.
"""

from __future__ import annotations

from typing import List, Optional, Sequence

import numpy as np

try:
    import cv2

    _HAS_CV2 = True
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore
    _HAS_CV2 = False

from .config import CourtConfig
from .court import CourtStatus

# BGR colors.
_STATUS_COLOR = {
    CourtStatus.FREE: (96, 200, 96),
    CourtStatus.ACTIVE: (96, 200, 230),
    CourtStatus.BUSY: (64, 140, 240),
    CourtStatus.OVERCROWDED: (64, 64, 230),
    CourtStatus.MAINTENANCE: (160, 160, 160),
    CourtStatus.UNKNOWN: (180, 180, 180),
}


def draw_camera_overlay(
    frame: "np.ndarray",
    detections,
    tracks=None,
) -> "np.ndarray":
    """Annotate the raw camera frame with boxes, foot points, and track IDs."""
    if not _HAS_CV2:
        return frame
    out = frame.copy()
    for det in detections:
        x1, y1, x2, y2 = (int(v) for v in det.bbox)
        cv2.rectangle(out, (x1, y1), (x2, y2), (90, 90, 90), 1)
        fx, fy = (int(det.foot_point[0]), int(det.foot_point[1]))
        # The foot point is the only pixel the homography trusts; mark it.
        cv2.circle(out, (fx, fy), 5, (40, 220, 40), -1)
        cv2.line(out, (fx - 8, fy), (fx + 8, fy), (40, 220, 40), 1)
        if det.keypoints is not None:
            for kp in det.keypoints:
                if kp[2] >= 0.3:
                    cv2.circle(out, (int(kp[0]), int(kp[1])), 2, (0, 180, 255), -1)
    return out


class TopDownRenderer:
    """Renders the court rectangle and players from a bird's eye view."""

    def __init__(
        self,
        court: CourtConfig,
        pixels_per_foot: float = 10.0,
        padding_ft: float = 6.0,
    ) -> None:
        self.court = court
        self.ppf = pixels_per_foot
        self.pad = padding_ft
        self.width_px = int((court.length_ft + 2 * padding_ft) * pixels_per_foot)
        self.height_px = int((court.width_ft + 2 * padding_ft) * pixels_per_foot)

    def _to_px(self, x_ft: float, y_ft: float) -> tuple:
        px = int((x_ft + self.pad) * self.ppf)
        py = int((y_ft + self.pad) * self.ppf)
        return px, py

    def render(
        self,
        tracks=None,
        fused=None,
        status: Optional[CourtStatus] = None,
        people: Optional[int] = None,
        wait_minutes: Optional[float] = None,
    ) -> "np.ndarray":
        if not _HAS_CV2:
            # Return a blank array so callers can still save/inspect shape.
            return np.zeros((self.height_px, self.width_px, 3), dtype=np.uint8)

        img = np.full((self.height_px, self.width_px, 3), 250, dtype=np.uint8)

        # Court rectangle and center line.
        tl = self._to_px(0, 0)
        br = self._to_px(self.court.length_ft, self.court.width_ft)
        border = _STATUS_COLOR.get(status or CourtStatus.UNKNOWN, (120, 120, 120))
        cv2.rectangle(img, tl, br, (60, 60, 60), 2)
        mid_x = self._to_px(self.court.length_ft / 2, 0)
        mid_x2 = self._to_px(self.court.length_ft / 2, self.court.width_ft)
        cv2.line(img, mid_x, mid_x2, (200, 200, 200), 1)

        # Players. Coasting (occlusion bridged) tracks are drawn hollow so you
        # can see the bridge happening.
        for trk in tracks or []:
            px, py = self._to_px(trk.position[0], trk.position[1])
            if getattr(trk, "is_coasting", False):
                cv2.circle(img, (px, py), 9, (0, 140, 255), 2)
            else:
                cv2.circle(img, (px, py), 9, (40, 120, 220), -1)
            cv2.putText(
                img, str(trk.track_id), (px + 11, py + 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (30, 30, 30), 1, cv2.LINE_AA,
            )

        for fd in fused or []:
            px, py = self._to_px(fd.position[0], fd.position[1])
            # Brighter when corroborated by more than one camera.
            color = (40, 180, 60) if fd.num_views > 1 else (40, 120, 220)
            cv2.circle(img, (px, py), 9, color, -1)
            cv2.putText(
                img, f"{fd.num_views}cam", (px + 11, py + 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (30, 30, 30), 1, cv2.LINE_AA,
            )

        self._draw_banner(img, status, people, wait_minutes, border)
        return img

    def _draw_banner(self, img, status, people, wait_minutes, color) -> None:
        if status is None:
            return
        label = status.value.upper()
        if people is not None:
            label += f"  {people} on court"
        if wait_minutes:
            label += f"  ~{wait_minutes:.0f} min wait"
        cv2.rectangle(img, (0, 0), (self.width_px, 26), color, -1)
        cv2.putText(
            img, label, (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
            (255, 255, 255), 1, cv2.LINE_AA,
        )
