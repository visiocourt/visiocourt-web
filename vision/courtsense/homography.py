"""Plane to plane geometry for CourtSense.

A homography maps one plane to another. For us that is the camera image plane
(pixels) to the court ground plane (real world feet, seen from straight above).

The single most important rule, and the most common mistake people make:

    A homography is ONLY valid for points that physically lie on the court
    surface. A person's head, torso, or bounding box center float above that
    plane, so projecting them gives the wrong court position. Always transform
    the foot contact point, where the player actually touches the ground.

Everything here works on the ground plane. It does not recover depth and it
cannot see through a full occlusion. What it gives you is an accurate bird's
eye occupancy map, which is what actually lets you reason about who is where.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np

try:  # OpenCV gives us a robust, RANSAC backed solver.
    import cv2

    _HAS_CV2 = True
except Exception:  # pragma: no cover - exercised only without OpenCV.
    cv2 = None  # type: ignore
    _HAS_CV2 = False


Point = Sequence[float]


def compute_homography(
    image_points: Sequence[Point],
    world_points: Sequence[Point],
    ransac_threshold: float = 3.0,
) -> "np.ndarray":
    """Solve for the 3x3 homography mapping image pixels to world feet.

    Parameters
    ----------
    image_points
        Pixel coordinates clicked on the court (x, y). At least four, and they
        must not all be collinear.
    world_points
        The real world court coordinates of those same points, in feet, in the
        court's own top down coordinate frame.
    ransac_threshold
        Reprojection error in pixels above which a correspondence is treated as
        an outlier. Only relevant when more than four points are supplied.

    Returns
    -------
    np.ndarray
        A 3x3 float64 matrix H such that ``world ~ H @ [x, y, 1]`` (after the
        homogeneous divide).
    """

    img = np.asarray(image_points, dtype=np.float64)
    wld = np.asarray(world_points, dtype=np.float64)

    if img.shape != wld.shape:
        raise ValueError(
            f"image_points {img.shape} and world_points {wld.shape} must match"
        )
    if img.shape[0] < 4:
        raise ValueError("Need at least 4 point correspondences for a homography")

    if _HAS_CV2:
        method = cv2.RANSAC if img.shape[0] > 4 else 0
        H, _mask = cv2.findHomography(img, wld, method, ransac_threshold)
        if H is None:
            raise RuntimeError(
                "findHomography failed. Points are likely collinear or degenerate."
            )
        return H.astype(np.float64)

    return _dlt_homography(img, wld)


def _dlt_homography(img: "np.ndarray", wld: "np.ndarray") -> "np.ndarray":
    """Direct Linear Transform fallback when OpenCV is unavailable.

    Uses a normalized DLT (Hartley normalization) and a least squares solve, so
    it behaves well even on a laptop with only numpy installed.
    """

    def normalize(pts: "np.ndarray"):
        centroid = pts.mean(axis=0)
        shifted = pts - centroid
        mean_dist = np.sqrt((shifted**2).sum(axis=1)).mean()
        if mean_dist < 1e-12:
            scale = 1.0
        else:
            scale = np.sqrt(2.0) / mean_dist
        T = np.array(
            [
                [scale, 0.0, -scale * centroid[0]],
                [0.0, scale, -scale * centroid[1]],
                [0.0, 0.0, 1.0],
            ]
        )
        homog = np.hstack([pts, np.ones((pts.shape[0], 1))])
        norm = (T @ homog.T).T
        return norm[:, :2], T

    src, T_src = normalize(img)
    dst, T_dst = normalize(wld)

    rows = []
    for (x, y), (u, v) in zip(src, dst):
        rows.append([-x, -y, -1, 0, 0, 0, u * x, u * y, u])
        rows.append([0, 0, 0, -x, -y, -1, v * x, v * y, v])
    A = np.asarray(rows, dtype=np.float64)

    _u, _s, vh = np.linalg.svd(A)
    H_norm = vh[-1].reshape(3, 3)

    H = np.linalg.inv(T_dst) @ H_norm @ T_src
    if abs(H[2, 2]) > 1e-12:
        H = H / H[2, 2]
    return H


def project_points(H: "np.ndarray", points: Sequence[Point]) -> "np.ndarray":
    """Apply a homography to an array of 2D points.

    Returns an (N, 2) array. Robust to the homogeneous divide blowing up for a
    point on the horizon (those rows come back as NaN rather than raising).
    """

    pts = np.asarray(points, dtype=np.float64).reshape(-1, 2)
    homog = np.hstack([pts, np.ones((pts.shape[0], 1))])
    projected = (H @ homog.T).T
    w = projected[:, 2:3]
    with np.errstate(divide="ignore", invalid="ignore"):
        out = projected[:, :2] / w
    out[np.abs(w[:, 0]) < 1e-9] = np.nan
    return out


def image_to_world(H: "np.ndarray", image_points: Sequence[Point]) -> "np.ndarray":
    """Map pixel coordinates to real world court feet."""
    return project_points(H, image_points)


def world_to_image(H: "np.ndarray", world_points: Sequence[Point]) -> "np.ndarray":
    """Map real world court feet back to pixel coordinates (inverse homography)."""
    return project_points(np.linalg.inv(H), world_points)


def foot_point_from_bbox(bbox: Sequence[float]) -> "tuple[float, float]":
    """Estimate the ground contact pixel of a person from their bounding box.

    The bottom center of an upright person's box is a good approximation of
    where their feet touch the floor, and crucially it lies on the court plane,
    which is the only place the homography is valid. Use pose ankle keypoints
    (see :mod:`courtsense.detector`) when you need more precision.
    """

    x1, _y1, x2, y2 = bbox
    return ((x1 + x2) / 2.0, float(y2))


@dataclass
class Homography:
    """Convenience wrapper bundling a matrix with its named usage.

    Keeps the ``image -> world`` direction explicit so call sites never have to
    remember which way the stored matrix points.
    """

    matrix: "np.ndarray"

    def __post_init__(self) -> None:
        self.matrix = np.asarray(self.matrix, dtype=np.float64).reshape(3, 3)
        self._inverse = np.linalg.inv(self.matrix)

    @classmethod
    def from_correspondences(
        cls,
        image_points: Sequence[Point],
        world_points: Sequence[Point],
        ransac_threshold: float = 3.0,
    ) -> "Homography":
        return cls(compute_homography(image_points, world_points, ransac_threshold))

    def to_world(self, image_points: Sequence[Point]) -> "np.ndarray":
        return project_points(self.matrix, image_points)

    def to_image(self, world_points: Sequence[Point]) -> "np.ndarray":
        return project_points(self._inverse, world_points)

    def reprojection_error(
        self,
        image_points: Sequence[Point],
        world_points: Sequence[Point],
    ) -> float:
        """Mean Euclidean error (in feet) of the calibration correspondences.

        A quick sanity number to print after calibration. Under roughly half a
        foot is excellent for a recreational court.
        """

        predicted = self.to_world(image_points)
        truth = np.asarray(world_points, dtype=np.float64).reshape(-1, 2)
        return float(np.sqrt(((predicted - truth) ** 2).sum(axis=1)).mean())

    def tolist(self) -> list:
        return self.matrix.tolist()
