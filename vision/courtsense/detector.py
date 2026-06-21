"""Person detection for CourtSense.

Wraps Ultralytics YOLO11 with two modes:

* ``detect``  - bounding boxes. Foot point is the box bottom center.
* ``pose``    - 17 keypoint COCO pose. Foot point is the mean of the two
                ankle keypoints, which sits much closer to true ground contact
                than the box bottom (the box bottom drifts when a player
                lunges, jumps, or the box is clipped by another body).

If Ultralytics is not installed (e.g. you are developing the geometry on a
laptop) the detector falls back to a deterministic mock so the rest of the
pipeline still runs. Set ``model_path="mock"`` to force that path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence

import numpy as np

from .homography import foot_point_from_bbox

# COCO pose keypoint indices for the ankles.
LEFT_ANKLE = 15
RIGHT_ANKLE = 16
LEFT_KNEE = 13
RIGHT_KNEE = 14


@dataclass
class Detection:
    """A single detected person in image (pixel) space."""

    bbox: tuple  # (x1, y1, x2, y2)
    confidence: float
    foot_point: tuple  # (x, y) ground contact pixel
    keypoints: Optional["np.ndarray"] = None  # (17, 3) x,y,conf when pose is used
    world_point: Optional[tuple] = field(default=None)  # filled in after homography

    @property
    def center(self) -> tuple:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def _foot_from_keypoints(
    keypoints: "np.ndarray",
    bbox: Sequence[float],
    min_conf: float = 0.3,
) -> tuple:
    """Best available ground contact point from a COCO pose.

    Prefers the average of confident ankle keypoints, falls back to knees, then
    to the bounding box bottom center if nothing reliable is visible (e.g. legs
    occluded by the net or another player).
    """

    for a, b in ((LEFT_ANKLE, RIGHT_ANKLE), (LEFT_KNEE, RIGHT_KNEE)):
        pts = []
        for idx in (a, b):
            if idx < len(keypoints) and keypoints[idx, 2] >= min_conf:
                pts.append(keypoints[idx, :2])
        if pts:
            mean = np.mean(pts, axis=0)
            return (float(mean[0]), float(mean[1]))
    return foot_point_from_bbox(bbox)


class PersonDetector:
    """YOLO person detector with an offline mock fallback."""

    def __init__(
        self,
        model_path: str = "yolo11n.pt",
        conf: float = 0.35,
        mode: str = "detect",  # "detect" or "pose"
        device: str = "cpu",
        imgsz: int = 640,
    ) -> None:
        self.conf = conf
        self.mode = mode
        self.device = device
        self.imgsz = imgsz
        self._model = None
        self._is_mock = model_path == "mock"

        if not self._is_mock:
            try:
                from ultralytics import YOLO

                # A pose model is only needed for pose mode; otherwise the
                # plain detector is lighter on the Pi.
                if mode == "pose" and "pose" not in model_path:
                    model_path = "yolo11n-pose.pt"
                self._model = YOLO(model_path)
            except Exception as exc:  # ultralytics missing or model download failed
                print(
                    f"[detector] Ultralytics unavailable ({exc}). "
                    "Falling back to mock detector."
                )
                self._is_mock = True

    # ------------------------------------------------------------------ public
    def detect(self, frame: "np.ndarray") -> List[Detection]:
        """Return the list of people detected in ``frame``."""
        if self._is_mock:
            return self._mock_detect(frame)
        return self._yolo_detect(frame)

    # ------------------------------------------------------------------ YOLO
    def _yolo_detect(self, frame: "np.ndarray") -> List[Detection]:
        results = self._model.predict(
            frame,
            conf=self.conf,
            classes=[0],  # person only
            device=self.device,
            imgsz=self.imgsz,
            verbose=False,
        )
        detections: List[Detection] = []
        if not results:
            return detections

        result = results[0]
        boxes = getattr(result, "boxes", None)
        if boxes is None or boxes.xyxy is None:
            return detections

        xyxy = boxes.xyxy.cpu().numpy()
        confs = boxes.conf.cpu().numpy()

        kpts_all = None
        if self.mode == "pose" and getattr(result, "keypoints", None) is not None:
            # (N, 17, 3) -> x, y, conf
            kpts_all = result.keypoints.data.cpu().numpy()

        for i, (box, conf) in enumerate(zip(xyxy, confs)):
            bbox = tuple(float(v) for v in box[:4])
            if kpts_all is not None and i < len(kpts_all):
                kp = kpts_all[i]
                foot = _foot_from_keypoints(kp, bbox)
                detections.append(Detection(bbox, float(conf), foot, kp))
            else:
                detections.append(
                    Detection(bbox, float(conf), foot_point_from_bbox(bbox))
                )
        return detections

    # ------------------------------------------------------------------ mock
    def _mock_detect(self, frame: "np.ndarray") -> List[Detection]:
        """Deterministic synthetic people that drift across the frame.

        Lets you exercise calibration, tracking, occlusion bridging, and the
        top down renderer without a model or a real camera. The motion is a
        function of a frame counter so two players periodically cross and
        occlude each other.
        """

        h, w = frame.shape[:2]
        t = getattr(self, "_mock_t", 0)
        self._mock_t = t + 1

        people = []
        # Two players that sweep horizontally in opposite directions and cross
        # near the middle, producing a deliberate occlusion event.
        phase = (t % 120) / 120.0
        ax = int(w * (0.15 + 0.6 * phase))
        bx = int(w * (0.85 - 0.6 * phase))
        for cx, conf in ((ax, 0.92), (bx, 0.88)):
            cy = int(h * 0.55)
            bw, bh = int(w * 0.06), int(h * 0.32)
            bbox = (cx - bw, cy - bh, cx + bw, cy + bh)
            people.append(
                Detection(bbox, conf, foot_point_from_bbox(bbox))
            )
        return people
