#!/usr/bin/env python3
"""CourtSense multi camera runtime: full occlusion resolution.

Use this when one viewpoint is not enough, i.e. when players are fully (not
just briefly) hidden from a single camera for long stretches and you need an
accurate live person count anyway (overcrowding alerts, capacity enforcement).

Each camera is calibrated into the SAME world frame (feet) by the calibration
tool, so this runner:

    for each camera:  capture -> detect -> foot points
    project every camera's foot points through its own homography -> world feet
    fuse: merge points from different cameras that land on the same spot
    track the fused points -> classify occupancy -> render the single top down map

Mount the second camera at the diagonally opposite corner. It is very unlikely
the same court spot is blocked from both angles at once.

All cameras must already be in one court config JSON (run the calibration tool
once per camera, pointing --out at the same file).

    python multi_camera_fusion.py --config courts/court-1.json --display
    python multi_camera_fusion.py --config courts/court-1.json --source mock --display
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Dict, List

import numpy as np

from courtsense.capture import FrameSource
from courtsense.config import load_config
from courtsense.court import CourtModel
from courtsense.detector import PersonDetector
from courtsense.fusion import MultiCameraFuser
from courtsense.tracker import OcclusionAwareTracker
from courtsense.visualize import TopDownRenderer


def _parse_args(argv) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="CourtSense multi camera fusion")
    p.add_argument("--config", required=True)
    p.add_argument("--source", default=None, help="'mock' to synthesize all cameras")
    p.add_argument("--model", default="yolo11n.pt")
    p.add_argument("--mode", default="detect", choices=["detect", "pose"])
    p.add_argument("--device", default="cpu")
    p.add_argument("--fps", type=float, default=2.0)
    p.add_argument("--conf", type=float, default=0.35)
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--height", type=int, default=720)
    p.add_argument("--merge-radius-ft", type=float, default=2.5)
    p.add_argument("--grace-frames", type=int, default=3)
    p.add_argument("--display", action="store_true")
    p.add_argument("--json-out")
    p.add_argument("--max-frames", type=int, default=0)
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    court_cfg = load_config(args.config)
    if not court_cfg.cameras:
        raise SystemExit("Court config has no cameras. Run calibration first.")

    use_mock = args.source == "mock" or args.model == "mock"

    detectors: Dict[str, PersonDetector] = {}
    captures: Dict[str, object] = {}
    homographies: Dict[str, np.ndarray] = {}

    cv2 = None
    if not use_mock or args.display:
        try:
            import cv2 as _cv2

            cv2 = _cv2
        except Exception:
            if args.display:
                print("[warn] OpenCV missing; disabling --display.")
                args.display = False

    for cam in court_cfg.cameras:
        homographies[cam.camera_id] = cam.homography_matrix
        detectors[cam.camera_id] = PersonDetector(
            model_path="mock" if use_mock else args.model,
            conf=args.conf,
            mode=args.mode,
            device=args.device,
        )
        if not use_mock:
            try:
                captures[cam.camera_id] = FrameSource(
                    cam.source, args.width, args.height, fps=args.fps
                )
            except RuntimeError as exc:
                raise SystemExit(f"Camera {cam.camera_id}: {exc}")

    fuser = MultiCameraFuser(homographies, merge_radius_ft=args.merge_radius_ft)
    tracker = OcclusionAwareTracker(grace_frames=args.grace_frames)
    court = CourtModel(court_cfg)
    renderer = TopDownRenderer(court_cfg)

    json_fh = open(args.json_out, "a", encoding="utf-8") if args.json_out else None
    period = 1.0 / max(args.fps, 0.1)
    frame_idx = 0

    print(
        f"CourtSense fusion: court={court_cfg.court_id} "
        f"cameras={[c.camera_id for c in court_cfg.cameras]} "
        f"source={'mock' if use_mock else 'live'} fps={args.fps}"
    )

    try:
        while True:
            tick = time.time()
            foot_points_by_camera: Dict[str, List[tuple]] = {}
            conf_by_camera: Dict[str, List[float]] = {}

            for cam in court_cfg.cameras:
                if use_mock:
                    frame = np.full((args.height, args.width, 3), 235, dtype=np.uint8)
                else:
                    ok, frame = captures[cam.camera_id].read()
                    if not ok:
                        frame = np.full((args.height, args.width, 3), 235, dtype=np.uint8)
                dets = detectors[cam.camera_id].detect(frame)
                foot_points_by_camera[cam.camera_id] = [d.foot_point for d in dets]
                conf_by_camera[cam.camera_id] = [d.confidence for d in dets]

            fused = fuser.fuse(foot_points_by_camera, conf_by_camera)
            valid = [f.position for f in fused]
            tracks = tracker.update(valid)
            reading = court.classify([t.position for t in tracks], timestamp=tick)

            line = {
                "ts": round(tick, 2),
                "court_id": court_cfg.court_id,
                "status": reading.status.value,
                "people_on_court": reading.people_on_court,
                "estimated_wait_minutes": reading.estimated_wait_minutes,
                "fused": [
                    {"x": round(f.position[0], 2), "y": round(f.position[1], 2),
                     "views": f.num_views, "cameras": f.camera_ids}
                    for f in fused
                ],
            }
            if json_fh:
                json_fh.write(json.dumps(line) + "\n")
                json_fh.flush()
            else:
                multi = sum(1 for f in fused if f.num_views > 1)
                print(
                    f"[{frame_idx:05d}] {reading.status.value:11s} "
                    f"people={reading.people_on_court} "
                    f"fused={len(fused)} multiview={multi} "
                    f"wait={reading.estimated_wait_minutes}"
                )

            if args.display and cv2 is not None:
                top = renderer.render(
                    tracks=tracks,
                    fused=fused,
                    status=reading.status,
                    people=reading.people_on_court,
                    wait_minutes=reading.estimated_wait_minutes,
                )
                cv2.imshow("top down court (fused)", top)
                if (cv2.waitKey(1) & 0xFF) in (ord("q"), 27):
                    break

            frame_idx += 1
            if args.max_frames and frame_idx >= args.max_frames:
                break
            elapsed = time.time() - tick
            if elapsed < period:
                time.sleep(period - elapsed)
    finally:
        for cap in captures.values():
            cap.release()
        if cv2 is not None and args.display:
            cv2.destroyAllWindows()
        if json_fh:
            json_fh.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
