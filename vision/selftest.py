#!/usr/bin/env python3
"""Dependency light self test for the CourtSense geometry and logic.

Runs with only numpy (no OpenCV, no model). Verifies the parts that are easy to
get subtly wrong: the homography round trips, the foot point rule, occlusion
bridging in the tracker, multi camera fusion, and occupancy classification.

    python selftest.py
"""

from __future__ import annotations

import numpy as np

from courtsense.homography import (
    compute_homography,
    image_to_world,
    world_to_image,
    foot_point_from_bbox,
)
from courtsense.tracker import OcclusionAwareTracker
from courtsense.fusion import fuse_world_detections
from courtsense.config import CourtConfig
from courtsense.court import CourtModel, CourtStatus


def _synthetic_homography():
    """A plausible perspective view of a 44x20 ft pickleball court.

    Four court corners (world feet) mapped to four image pixels that mimic a
    camera mounted high behind one baseline, so the far baseline is narrower in
    the image (perspective foreshortening).
    """

    world = [(0, 0), (44, 0), (44, 20), (0, 20)]
    image = [(300, 700), (980, 700), (760, 320), (520, 320)]
    H = compute_homography(image, world)
    return H, image, world


def test_homography_roundtrip():
    H, image, world = _synthetic_homography()
    # Image -> world recovers the calibration corners.
    w = image_to_world(H, image)
    err = np.sqrt(((w - np.array(world)) ** 2).sum(axis=1)).mean()
    assert err < 0.5, f"calibration reprojection too high: {err:.3f} ft"

    # world -> image -> world is identity.
    back = image_to_world(H, world_to_image(H, world))
    rt = np.sqrt(((back - np.array(world)) ** 2).sum(axis=1)).mean()
    assert rt < 1e-6, f"round trip drift: {rt}"
    print(f"  homography reprojection error  : {err:.4f} ft  (OK)")


def test_foot_point_rule():
    # Two people, one standing right behind the other in the image. Using the
    # box CENTER would collapse them; using the FOOT point keeps them apart.
    H, _img, _world = _synthetic_homography()
    front = (620, 480, 700, 700)  # nearer camera, lower in frame
    back = (628, 360, 690, 560)   # further, higher in frame, overlaps in x

    foot_front = foot_point_from_bbox(front)
    foot_back = foot_point_from_bbox(back)
    wf = image_to_world(H, [foot_front])[0]
    wb = image_to_world(H, [foot_back])[0]
    sep = float(np.linalg.norm(wf - wb))
    assert sep > 3.0, f"foot points should separate occluding players, got {sep:.2f} ft"
    print(f"  occluding players separated by : {sep:.2f} ft on court  (OK)")


def test_occlusion_bridging():
    # Player walks in a straight line; their detection drops out for 2 frames
    # (occluded), then returns. The track ID must survive.
    tracker = OcclusionAwareTracker(grace_frames=3, min_hits=1, max_match_distance_ft=4.0)
    path = [(10, 10), (12, 10), (14, 10)]
    ids = []
    for p in path:
        tracks = tracker.update([p])
        ids.append(tracks[0].track_id)

    # Occlusion: no detection for two frames.
    tracker.update([])
    tracker.update([])

    # Reappears where prediction expects (kept moving at +2 ft/frame).
    tracks = tracker.update([(20, 10)])
    reappear_id = tracks[0].track_id
    assert reappear_id == ids[0], (
        f"track ID changed across occlusion ({ids[0]} -> {reappear_id})"
    )
    print(f"  track ID {ids[0]} survived a 2 frame occlusion  (OK)")


def test_fusion_merges_views():
    # Same person seen by two cameras lands ~1 ft apart -> should merge to one.
    # A different person 10 ft away stays separate.
    dets = {
        "cam-a": [{"position": (22.0, 10.0), "confidence": 0.9},
                  {"position": (5.0, 5.0), "confidence": 0.8}],
        "cam-b": [{"position": (22.6, 10.3), "confidence": 0.85}],
    }
    fused = fuse_world_detections(dets, merge_radius_ft=2.5)
    assert len(fused) == 2, f"expected 2 unique people, got {len(fused)}"
    multi = [f for f in fused if f.num_views > 1]
    assert len(multi) == 1 and multi[0].num_views == 2, "two cameras should corroborate one person"
    print(f"  fusion merged 3 detections -> {len(fused)} people, 1 multiview  (OK)")


def test_occupancy_classification():
    cfg = CourtConfig(court_id="t", sport="pickleball", capacity=4, overcrowded_at=8)
    court = CourtModel(cfg)

    empty = court.classify([], timestamp=0.0)
    assert empty.status == CourtStatus.FREE

    active = court.classify([(10, 10), (30, 12)], timestamp=1.0)
    assert active.status == CourtStatus.ACTIVE

    busy = court.classify([(10, 10), (12, 8), (30, 12), (32, 9)], timestamp=2.0)
    assert busy.status == CourtStatus.BUSY

    crowd = court.classify([(i, 10) for i in range(2, 38, 4)], timestamp=3.0)
    assert crowd.status == CourtStatus.OVERCROWDED

    # A point far outside the court (a passerby) should not be counted.
    outside = court.classify([(200, 200)], timestamp=4.0)
    assert outside.people_on_court == 0
    print("  occupancy free/active/busy/overcrowded + boundary filter  (OK)")


def main() -> int:
    print("CourtSense self test")
    test_homography_roundtrip()
    test_foot_point_rule()
    test_occlusion_bridging()
    test_fusion_merges_views()
    test_occupancy_classification()
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
