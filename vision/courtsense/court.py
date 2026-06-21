"""Court occupancy model: from world positions to a CourtSense status.

Given the tracked players' positions in feet, this decides whether the court
is free, active, busy, or overcrowded, counts how many people are actually on
the playing surface (a margin around it absorbs benches and people walking by),
and produces a rough wait time estimate from a rolling history of occupancy.

The wait estimate here is intentionally simple and transparent. It is a
heuristic placeholder for the real predictive model that lives in the cloud
analytics layer; on the edge we just need a believable live number.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Deque, List, Optional, Sequence

import numpy as np

from .config import CourtConfig


class CourtStatus(str, Enum):
    FREE = "free"
    ACTIVE = "active"
    BUSY = "busy"
    OVERCROWDED = "overcrowded"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"


@dataclass
class OccupancyReading:
    status: CourtStatus
    people_on_court: int
    capacity: int
    estimated_wait_minutes: Optional[float]
    timestamp: float


class CourtModel:
    """Stateful occupancy classifier for one court.

    Parameters
    ----------
    config
        The court's calibration, dimensions, and thresholds.
    boundary_margin_ft
        People within this margin of the court rectangle still count as "on
        court". A small positive margin avoids dropping a player who steps just
        over the baseline to return a serve.
    history_seconds
        Window of occupancy samples kept for the wait time heuristic.
    typical_session_minutes
        Expected length of one group's play, used to project a wait time when
        the court is at or over capacity.
    """

    def __init__(
        self,
        config: CourtConfig,
        boundary_margin_ft: float = 4.0,
        history_seconds: float = 600.0,
        typical_session_minutes: float = 30.0,
    ) -> None:
        self.config = config
        self.margin = boundary_margin_ft
        self.typical_session_minutes = typical_session_minutes
        self._history_seconds = history_seconds
        self._history: Deque[tuple] = deque()  # (timestamp, people_on_court)
        self._maintenance = False

    def set_maintenance(self, on: bool) -> None:
        """Manually flag the court out of service (overrides occupancy)."""
        self._maintenance = on

    def on_court(self, world_positions: Sequence[Sequence[float]]) -> int:
        """Count positions that fall inside the court plus margin."""
        if len(world_positions) == 0:
            return 0
        pts = np.asarray(world_positions, dtype=np.float64).reshape(-1, 2)
        pts = pts[~np.isnan(pts).any(axis=1)]
        if len(pts) == 0:
            return 0
        m = self.margin
        inside = (
            (pts[:, 0] >= -m)
            & (pts[:, 0] <= self.config.length_ft + m)
            & (pts[:, 1] >= -m)
            & (pts[:, 1] <= self.config.width_ft + m)
        )
        return int(inside.sum())

    def classify(
        self,
        world_positions: Sequence[Sequence[float]],
        timestamp: float,
    ) -> OccupancyReading:
        """Produce the current occupancy reading and update history."""
        people = self.on_court(world_positions)
        self._record(timestamp, people)

        if self._maintenance:
            status = CourtStatus.MAINTENANCE
        elif people == 0:
            status = CourtStatus.FREE
        elif people >= self.config.overcrowded_at:
            status = CourtStatus.OVERCROWDED
        elif people >= self.config.capacity:
            status = CourtStatus.BUSY
        else:
            status = CourtStatus.ACTIVE

        wait = self._estimate_wait(people, status)
        return OccupancyReading(
            status=status,
            people_on_court=people,
            capacity=self.config.capacity,
            estimated_wait_minutes=wait,
            timestamp=timestamp,
        )

    # --------------------------------------------------------------- internals
    def _record(self, timestamp: float, people: int) -> None:
        self._history.append((timestamp, people))
        cutoff = timestamp - self._history_seconds
        while self._history and self._history[0][0] < cutoff:
            self._history.popleft()

    def _estimate_wait(self, people: int, status: CourtStatus) -> Optional[float]:
        """Heuristic wait time in minutes.

        Free or active courts have no wait. Once at or over capacity, estimate
        how long until a spot opens from how full and how long the court has
        been continuously occupied, capped at one typical session.
        """

        if status in (CourtStatus.FREE, CourtStatus.ACTIVE, CourtStatus.MAINTENANCE):
            return 0.0 if status != CourtStatus.MAINTENANCE else None

        # How long has the court been continuously at/over capacity?
        occupied_streak_minutes = self._occupied_streak_minutes()
        remaining = max(0.0, self.typical_session_minutes - occupied_streak_minutes)

        # Overcrowding implies a queue, so scale by how far over capacity we are.
        overflow = max(0, people - self.config.capacity)
        queue_factor = 1.0 + 0.5 * overflow
        return round(remaining * queue_factor, 1)

    def _occupied_streak_minutes(self) -> float:
        if not self._history:
            return 0.0
        latest_t = self._history[-1][0]
        streak_start = latest_t
        for ts, ppl in reversed(self._history):
            if ppl >= self.config.capacity:
                streak_start = ts
            else:
                break
        return (latest_t - streak_start) / 60.0
