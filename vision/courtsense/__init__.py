"""CourtSense edge vision package.

Turns a single Raspberry Pi camera's perspective view of a court into a
calibrated top down occupancy map, with occlusion aware tracking so that a
player who briefly steps behind another is not lost.

Modules
-------
homography   Plane to plane geometry. Image pixels <-> real world court feet.
config       Load and save the per camera calibration produced by the
             calibration tool.
detector     Person detection and pose, wrapping Ultralytics YOLO with a
             dependency free mock fallback for development.
tracker      Occlusion aware multi object tracker (velocity bridging).
court        Court model: zones, occupancy classification, wait estimates.
fusion       Fuse top down detections from several cameras into one map.
visualize    Render the camera overlay and the top down court view.
"""

from .homography import (
    Homography,
    compute_homography,
    image_to_world,
    world_to_image,
    foot_point_from_bbox,
)
from .config import CameraConfig, CourtConfig, load_config, save_config
from .detector import Detection, PersonDetector
from .tracker import Track, OcclusionAwareTracker
from .court import CourtModel, CourtStatus
from .fusion import fuse_world_detections, MultiCameraFuser

__all__ = [
    "Homography",
    "compute_homography",
    "image_to_world",
    "world_to_image",
    "foot_point_from_bbox",
    "CameraConfig",
    "CourtConfig",
    "load_config",
    "save_config",
    "Detection",
    "PersonDetector",
    "Track",
    "OcclusionAwareTracker",
    "CourtModel",
    "CourtStatus",
    "fuse_world_detections",
    "MultiCameraFuser",
]

__version__ = "0.1.0"
