"""Occlusion aware tracking in world (court) coordinates.

The homography gives us each player's position in feet on the court. This
tracker assigns a stable ID to each player and, critically, keeps that ID
alive for a short grace window when a detection disappears, coasting on the
player's last known velocity.

That grace window is what bridges the occlusion you described: when player B
steps behind player A, B's detection vanishes for a few frames. Without
bridging, the system thinks B left the court and then re invents them as a new
ID when they reappear, which corrupts every count and analytic downstream. With
bridging, B's track is predicted forward and re associated when they emerge.

Why track in world feet rather than image pixels:
* The distance threshold ("same person if within ~3 ft") is physically
  meaningful and constant across the frame, instead of shrinking with
  perspective near the far baseline.
* It is the natural place to later fuse multiple cameras (see fusion.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence

import numpy as np


@dataclass
class Track:
    """A tracked player on the court."""

    track_id: int
    position: "np.ndarray"  # world feet (x, y)
    velocity: "np.ndarray"  # feet per frame
    hits: int = 1
    age: int = 1
    time_since_update: int = 0
    confidence: float = 1.0
    history: list = field(default_factory=list)

    @property
    def is_coasting(self) -> bool:
        """True when the track is currently bridging an occlusion."""
        return self.time_since_update > 0


class OcclusionAwareTracker:
    """Greedy nearest neighbour tracker with velocity based occlusion bridging.

    Parameters
    ----------
    max_match_distance_ft
        A detection is associated to a track only if it is within this distance
        of the track's predicted position. Roughly one player's stride.
    grace_frames
        How many frames a track survives without a matching detection before it
        is deleted. Set this from your sample rate: at 2 fps, ``grace_frames=2``
        bridges a one second occlusion. This is the occlusion bridge knob.
    min_hits
        A new track must be seen this many times before it is reported as
        confirmed, which suppresses one frame false positives.
    velocity_smoothing
        EMA factor for velocity. Higher means smoother but laggier prediction.
    """

    def __init__(
        self,
        max_match_distance_ft: float = 4.0,
        grace_frames: int = 3,
        min_hits: int = 2,
        velocity_smoothing: float = 0.5,
        max_speed_ft_per_frame: float = 8.0,
    ) -> None:
        self.max_match_distance = max_match_distance_ft
        self.grace_frames = grace_frames
        self.min_hits = min_hits
        self.velocity_smoothing = velocity_smoothing
        self.max_speed = max_speed_ft_per_frame
        self._tracks: List[Track] = []
        self._next_id = 1

    @property
    def tracks(self) -> List[Track]:
        return self._tracks

    def confirmed_tracks(self) -> List[Track]:
        """Tracks stable enough to count, including those currently coasting."""
        return [t for t in self._tracks if t.hits >= self.min_hits]

    def update(self, world_positions: Sequence[Sequence[float]]) -> List[Track]:
        """Advance the tracker one frame.

        Parameters
        ----------
        world_positions
            The court coordinates (feet) of every person detected this frame.
            Detections whose homography projection was NaN should be dropped by
            the caller before reaching here.

        Returns
        -------
        list[Track]
            The confirmed tracks after this update.
        """

        detections = np.asarray(world_positions, dtype=np.float64).reshape(-1, 2)

        # 1. Predict every existing track forward using its velocity.
        for track in self._tracks:
            track.position = track.position + track.velocity
            track.age += 1
            track.time_since_update += 1

        # 2. Associate detections to predicted tracks (greedy, nearest first).
        matches, unmatched_dets = self._associate(detections)

        # 3. Update matched tracks toward their detection.
        for track_idx, det_idx in matches:
            track = self._tracks[track_idx]
            measured = detections[det_idx]
            new_velocity = measured - (track.position - track.velocity)
            # Reject absurd jumps (likely an ID swap) by clamping speed.
            speed = float(np.linalg.norm(new_velocity))
            if speed > self.max_speed:
                new_velocity = new_velocity * (self.max_speed / speed)
            a = self.velocity_smoothing
            track.velocity = a * track.velocity + (1 - a) * new_velocity
            track.position = measured
            track.hits += 1
            track.time_since_update = 0
            track.history.append(tuple(measured))

        # 4. Spawn new tracks for detections that matched nothing.
        for det_idx in unmatched_dets:
            self._spawn(detections[det_idx])

        # 5. Retire tracks that have coasted past the grace window.
        self._tracks = [
            t for t in self._tracks if t.time_since_update <= self.grace_frames
        ]

        return self.confirmed_tracks()

    # --------------------------------------------------------------- internals
    def _associate(self, detections: "np.ndarray"):
        n_tracks = len(self._tracks)
        n_dets = len(detections)
        if n_tracks == 0 or n_dets == 0:
            return [], list(range(n_dets))

        track_pos = np.array([t.position for t in self._tracks])  # (T, 2)
        # Pairwise distances (T, D).
        diff = track_pos[:, None, :] - detections[None, :, :]
        dist = np.sqrt((diff**2).sum(axis=2))

        matches = []
        used_tracks: set = set()
        used_dets: set = set()

        # Greedy: repeatedly take the globally closest valid pair.
        flat_order = np.argsort(dist, axis=None)
        for flat in flat_order:
            ti, di = divmod(int(flat), n_dets)
            if ti in used_tracks or di in used_dets:
                continue
            if dist[ti, di] > self.max_match_distance:
                break  # everything further is also too far
            matches.append((ti, di))
            used_tracks.add(ti)
            used_dets.add(di)

        unmatched_dets = [d for d in range(n_dets) if d not in used_dets]
        return matches, unmatched_dets

    def _spawn(self, position: "np.ndarray") -> None:
        self._tracks.append(
            Track(
                track_id=self._next_id,
                position=position.astype(np.float64),
                velocity=np.zeros(2, dtype=np.float64),
                history=[tuple(position)],
            )
        )
        self._next_id += 1
