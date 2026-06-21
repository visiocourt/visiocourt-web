#!/usr/bin/env python3
"""CourtSense single camera runtime pipeline.

Per frame flow:

    capture -> detect people -> take each person's FOOT point
            -> project foot point through the homography to world feet
            -> occlusion aware tracking (bridges brief occlusions)
            -> court occupancy classification (free/active/busy/overcrowded)
            -> render overlay + top down map, emit a status reading

The two design choices that matter most are baked in here:
1. We project the foot point only, never the box center, so people near the
   frame edges land in the right spot on the court.
2. We sample slowly (default ~2 fps). Court occupancy does not change frame to
   frame the way game action does, and slow sampling is what lets a Pi keep up.

Run with the mock detector (no model, no camera) to see it work immediately:
    python court_occupancy.py --config courts/court-1.json --camera-id cam-a \
        --source mock --display

Real camera with YOLO pose for accurate foot points:
    python court_occupancy.py --config courts/court-1.json --camera-id cam-a \
        --mode pose --display
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np

from courtsense.capture import FrameSource
from courtsense.config import load_config
from courtsense.court import CourtModel
from courtsense.detector import PersonDetector
from courtsense.homography import image_to_world
from courtsense.tracker import OcclusionAwareTracker
from courtsense.visualize import TopDownRenderer, draw_camera_overlay


def _mock_frame(width: int, height: int) -> "np.ndarray":
    img = np.full((height, width, 3), 235, dtype=np.uint8)
    return img


def _parse_args(argv) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="CourtSense single camera occupancy")
    p.add_argument("--config", required=True, help="court config JSON from calibration")
    p.add_argument("--camera-id", required=True)
    p.add_argument(
        "--source",
        default=None,
        help="override source: index (USB), 'picamera'/'csi' (Pi CSI cam), "
        "path, RTSP URL, or 'mock' for synthetic",
    )
    p.add_argument("--model", default="yolo11n.pt", help="YOLO weights or 'mock'")
    p.add_argument("--mode", default="detect", choices=["detect", "pose"])
    p.add_argument("--device", default="cpu")
    p.add_argument("--fps", type=float, default=2.0, help="sample rate (frames/sec)")
    p.add_argument("--conf", type=float, default=0.35)
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--height", type=int, default=720)
    p.add_argument("--grace-frames", type=int, default=3, help="occlusion bridge window")
    p.add_argument("--display", action="store_true", help="show overlay + top down windows")
    p.add_argument("--json-out", help="append status readings as JSON lines to this file")
    p.add_argument("--max-frames", type=int, default=0, help="stop after N frames (0=forever)")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    court_cfg = load_config(args.config)
    cam_cfg = court_cfg.camera(args.camera_id)
    H = cam_cfg.homography_matrix

    source = args.source or cam_cfg.source
    use_mock = source == "mock" or args.model == "mock"

    detector = PersonDetector(
        model_path="mock" if use_mock else args.model,
        conf=args.conf,
        mode=args.mode,
        device=args.device,
    )
    tracker = OcclusionAwareTracker(grace_frames=args.grace_frames)
    court = CourtModel(court_cfg)
    renderer = TopDownRenderer(court_cfg)

    cap = None
    cv2 = None
    if not use_mock or args.display:
        try:
            import cv2 as _cv2

            cv2 = _cv2
        except Exception:
            if args.display:
                print("[warn] OpenCV missing; disabling --display.")
                args.display = False
    if not use_mock:
        cap = FrameSource(source, args.width, args.height, fps=args.fps)
        print(f"Capture backend: {cap.backend}")

    json_fh = open(args.json_out, "a", encoding="utf-8") if args.json_out else None
    period = 1.0 / max(args.fps, 0.1)
    frame_idx = 0

    print(
        f"CourtSense running: court={court_cfg.court_id} camera={args.camera_id} "
        f"sport={court_cfg.sport} source={'mock' if use_mock else source} "
        f"mode={args.mode} fps={args.fps}"
    )

    try:
        while True:
            tick = time.time()

            if use_mock:
                frame = _mock_frame(args.width, args.height)
            else:
                ok, frame = cap.read()
                if not ok:
                    print("End of stream.")
                    break

            detections = detector.detect(frame)

            # Project FOOT points only (the homography is valid on the ground).
            foot_points = [d.foot_point for d in detections]
            if foot_points:
                world = image_to_world(H, foot_points)
                for det, w in zip(detections, world):
                    det.world_point = None if np.isnan(w).any() else (float(w[0]), float(w[1]))
            valid_world = [d.world_point for d in detections if d.world_point is not None]

            tracks = tracker.update(valid_world)
            reading = court.classify([t.position for t in tracks], timestamp=tick)

            line = {
                "ts": round(tick, 2),
                "court_id": court_cfg.court_id,
                "camera_id": args.camera_id,
                "status": reading.status.value,
                "people_on_court": reading.people_on_court,
                "capacity": reading.capacity,
                "estimated_wait_minutes": reading.estimated_wait_minutes,
                "tracks": [
                    {"id": t.track_id, "x": round(float(t.position[0]), 2),
                     "y": round(float(t.position[1]), 2), "coasting": t.is_coasting}
                    for t in tracks
                ],
            }
            if json_fh:
                json_fh.write(json.dumps(line) + "\n")
                json_fh.flush()
            else:
                print(
                    f"[{frame_idx:05d}] {reading.status.value:11s} "
                    f"people={reading.people_on_court} "
                    f"wait={reading.estimated_wait_minutes} "
                    f"tracks={[t.track_id for t in tracks]}"
                )

            if args.display and cv2 is not None:
                overlay = draw_camera_overlay(frame, detections, tracks)
                top = renderer.render(
                    tracks=tracks,
                    status=reading.status,
                    people=reading.people_on_court,
                    wait_minutes=reading.estimated_wait_minutes,
                )
                cv2.imshow("camera", overlay)
                cv2.imshow("top down court", top)
                if (cv2.waitKey(1) & 0xFF) in (ord("q"), 27):
                    break

            frame_idx += 1
            if args.max_frames and frame_idx >= args.max_frames:
                break

            # Pace to the target sample rate.
            elapsed = time.time() - tick
            if elapsed < period:
                time.sleep(period - elapsed)
    finally:
        if cap is not None:
            cap.release()
        if cv2 is not None and args.display:
            cv2.destroyAllWindows()
        if json_fh:
            json_fh.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
