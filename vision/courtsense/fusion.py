"""Multi camera fusion for full occlusion resolution.

Single camera homography bridges *brief* occlusions (one player stepping behind
another for a moment) via the tracker. But if a player is fully hidden from one
viewpoint for a long stretch there is simply no pixel to project, and no
geometry trick recovers it from that one camera.

The standard fix in sports analytics is a second camera at the diagonally
opposite corner. It is very unlikely that the same spot is blocked from both
angles at once. Because every camera was calibrated into the *same* world
coordinate frame (feet, see config.py), fusion is just clustering: points from
different cameras that land within a person's width of each other are the same
person and get merged.

This runs entirely in world coordinates, after each camera's detections have
been projected through its own homography.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence

import numpy as np


@dataclass
class FusedDetection:
    """One person on the court after merging across cameras."""

    position: tuple  # world feet (x, y), confidence weighted mean
    confidence: float
    camera_ids: List[str]  # which cameras saw this person
    num_views: int


def fuse_world_detections(
    detections_by_camera: Dict[str, Sequence[dict]],
    merge_radius_ft: float = 2.5,
) -> List[FusedDetection]:
    """Cluster per camera world detections into unique people.

    Parameters
    ----------
    detections_by_camera
        Mapping of ``camera_id -> list of {"position": (x, y), "confidence": c}``
        where ``position`` is already in world feet (projected through that
        camera's homography). NaN positions should be filtered out beforehand.
    merge_radius_ft
        Two detections from different cameras within this distance are treated
        as the same person. Roughly the width of a standing person.

    Returns
    -------
    list[FusedDetection]
        Merged, deduplicated people with how many cameras corroborated each.
    """

    # Flatten into a single list of (position, confidence, camera_id).
    flat: List[tuple] = []
    for cam_id, dets in detections_by_camera.items():
        for d in dets:
            pos = np.asarray(d["position"], dtype=np.float64)
            if pos.shape != (2,) or np.isnan(pos).any():
                continue
            flat.append((pos, float(d.get("confidence", 1.0)), cam_id))

    if not flat:
        return []

    n = len(flat)
    positions = np.stack([f[0] for f in flat])  # (n, 2)

    # Union find over points within merge_radius_ft.
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    diff = positions[:, None, :] - positions[None, :, :]
    dist = np.sqrt((diff**2).sum(axis=2))
    for i in range(n):
        for j in range(i + 1, n):
            # Only merge across different cameras; two blobs from one camera are
            # two people, never the same person.
            if flat[i][2] != flat[j][2] and dist[i, j] <= merge_radius_ft:
                union(i, j)

    clusters: Dict[int, List[int]] = {}
    for i in range(n):
        clusters.setdefault(find(i), []).append(i)

    fused: List[FusedDetection] = []
    for members in clusters.values():
        pts = np.stack([flat[m][0] for m in members])
        confs = np.array([flat[m][1] for m in members])
        cams = sorted({flat[m][2] for m in members})
        weight = confs.sum()
        mean_pos = (pts * confs[:, None]).sum(axis=0) / max(weight, 1e-9)
        fused.append(
            FusedDetection(
                position=(float(mean_pos[0]), float(mean_pos[1])),
                confidence=float(confs.max()),
                camera_ids=cams,
                num_views=len(cams),
            )
        )
    return fused


class MultiCameraFuser:
    """Convenience wrapper that projects then fuses several cameras.

    Each camera supplies its homography matrix and the foot point pixels of its
    detections; the fuser projects every camera into world feet and merges.
    """

    def __init__(self, homographies: Dict[str, "np.ndarray"], merge_radius_ft: float = 2.5):
        from .homography import image_to_world

        self._image_to_world = image_to_world
        self.homographies = {k: np.asarray(v, dtype=np.float64).reshape(3, 3) for k, v in homographies.items()}
        self.merge_radius_ft = merge_radius_ft

    def fuse(
        self,
        foot_points_by_camera: Dict[str, Sequence[Sequence[float]]],
        confidences_by_camera: Dict[str, Sequence[float]] | None = None,
    ) -> List[FusedDetection]:
        confidences_by_camera = confidences_by_camera or {}
        detections_by_camera: Dict[str, List[dict]] = {}
        for cam_id, feet in foot_points_by_camera.items():
            if cam_id not in self.homographies or len(feet) == 0:
                detections_by_camera[cam_id] = []
                continue
            world = self._image_to_world(self.homographies[cam_id], feet)
            confs = confidences_by_camera.get(cam_id, [1.0] * len(world))
            detections_by_camera[cam_id] = [
                {"position": (float(w[0]), float(w[1])), "confidence": float(c)}
                for w, c in zip(world, confs)
            ]
        return fuse_world_detections(detections_by_camera, self.merge_radius_ft)
