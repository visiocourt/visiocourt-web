#!/usr/bin/env python3
"""CourtSense camera calibration tool.

Run this ONCE per camera after it is mounted (and again only if the camera
moves). You click known court reference points in a snapshot and type their
real world court coordinates in feet. It solves the homography mapping that
camera's pixels onto the shared top down court frame and writes it into a
court config JSON.

Pick reference points that lie flat ON the court surface and are easy to locate
precisely: the four court corners, the net post bases, and line intersections
(service line / center line crossings). Four is the minimum; six to eight
spread across the whole court gives a noticeably more accurate, more robust fit.

Court coordinate frame
----------------------
Use one corner of the playing area as the origin (0, 0). X runs along the
length, Y along the width, in feet. For a pickleball court (44 x 20 ft) the
four corners are (0,0), (44,0), (44,20), (0,20).

Usage
-----
Interactive (GUI, needs a desktop / VNC):
    python homography_calibration.py --source 0 --court-id court-1 \
        --sport pickleball --camera-id cam-a --out courts/court-1.json

From a still image:
    python homography_calibration.py --image snapshot.jpg --court-id court-1 \
        --sport pickleball --camera-id cam-a --out courts/court-1.json

Headless (no GUI): pass correspondences directly, no clicking required:
    python homography_calibration.py --headless \
        --point 320,540 0,0  --point 1180,520 44,0 \
        --point 1210,300 44,20 --point 300,310 0,20 \
        --court-id court-1 --sport pickleball --camera-id cam-a \
        --out courts/court-1.json

Controls (interactive):
    left click   add a point, then type its world X Y in the terminal
    u            undo last point
    r            reset all points
    enter        solve and save (needs >= 4 points)
    q / esc      quit without saving
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

from courtsense.config import (
    COURT_PRESETS,
    CameraConfig,
    CourtConfig,
    load_config,
    save_config,
)
from courtsense.homography import Homography


def _grab_frame(source: str, image: Optional[str]) -> "np.ndarray":
    import cv2

    if image:
        frame = cv2.imread(image)
        if frame is None:
            raise SystemExit(f"Could not read image: {image}")
        return frame

    cap = cv2.VideoCapture(int(source) if source.isdigit() else source)
    if not cap.isOpened():
        raise SystemExit(f"Could not open video source: {source}")
    print("Warming up camera, press SPACE to freeze a snapshot, q to abort...")
    frame = None
    while True:
        ok, live = cap.read()
        if not ok:
            cap.release()
            raise SystemExit("Failed to read from camera.")
        cv2.imshow("calibration - press SPACE to capture", live)
        key = cv2.waitKey(30) & 0xFF
        if key == ord(" "):
            frame = live.copy()
            break
        if key in (ord("q"), 27):
            cap.release()
            cv2.destroyAllWindows()
            raise SystemExit("Aborted.")
    cap.release()
    cv2.destroyWindow("calibration - press SPACE to capture")
    return frame


def _interactive(frame: "np.ndarray") -> Tuple[List[tuple], List[tuple]]:
    import cv2

    image_points: List[tuple] = []
    world_points: List[tuple] = []
    window = "CourtSense calibration"

    def redraw():
        disp = frame.copy()
        for i, (px, py) in enumerate(image_points):
            cv2.circle(disp, (int(px), int(py)), 6, (40, 220, 40), -1)
            wx, wy = world_points[i]
            cv2.putText(
                disp, f"{i+1}:({wx:.0f},{wy:.0f})", (int(px) + 8, int(py)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (40, 220, 40), 1, cv2.LINE_AA,
            )
        cv2.putText(
            disp, "click point, then enter world X Y in terminal. ENTER=save q=quit",
            (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2, cv2.LINE_AA,
        )
        cv2.imshow(window, disp)

    def on_mouse(event, x, y, _flags, _param):
        if event == cv2.EVENT_LBUTTONDOWN:
            print(f"Clicked pixel ({x}, {y}).")
            try:
                raw = input("  Real world court X Y in feet (e.g. 44 0): ").strip()
                wx, wy = (float(v) for v in raw.replace(",", " ").split()[:2])
            except (ValueError, IndexError):
                print("  Skipped (could not parse two numbers).")
                return
            image_points.append((float(x), float(y)))
            world_points.append((wx, wy))
            redraw()

    cv2.namedWindow(window)
    cv2.setMouseCallback(window, on_mouse)
    redraw()

    while True:
        key = cv2.waitKey(50) & 0xFF
        if key in (ord("q"), 27):
            cv2.destroyAllWindows()
            raise SystemExit("Aborted without saving.")
        if key == ord("u") and image_points:
            image_points.pop()
            world_points.pop()
            redraw()
        if key == ord("r"):
            image_points.clear()
            world_points.clear()
            redraw()
        if key in (13, 10):  # enter
            if len(image_points) >= 4:
                break
            print(f"Need at least 4 points, have {len(image_points)}.")
    cv2.destroyAllWindows()
    return image_points, world_points


def _parse_args(argv) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="CourtSense homography calibration")
    p.add_argument("--source", default="0", help="camera index or RTSP URL")
    p.add_argument("--image", help="use a still image instead of a live camera")
    p.add_argument("--court-id", required=True)
    p.add_argument("--camera-id", required=True)
    p.add_argument("--sport", default="pickleball", choices=sorted(COURT_PRESETS))
    p.add_argument("--length-ft", type=float, default=0.0)
    p.add_argument("--width-ft", type=float, default=0.0)
    p.add_argument("--capacity", type=int, default=4)
    p.add_argument("--overcrowded-at", type=int, default=8)
    p.add_argument("--out", required=True, help="path to court config JSON")
    p.add_argument(
        "--headless",
        action="store_true",
        help="no GUI; supply correspondences via --point",
    )
    p.add_argument(
        "--point",
        nargs=2,
        action="append",
        metavar=("PX,PY", "WX,WY"),
        help="a pixel,world correspondence, e.g. --point 320,540 0,0",
    )
    return p.parse_args(argv)


def _points_from_args(args) -> Tuple[List[tuple], List[tuple]]:
    image_points, world_points = [], []
    for pixel, world in args.point or []:
        px, py = (float(v) for v in pixel.split(","))
        wx, wy = (float(v) for v in world.split(","))
        image_points.append((px, py))
        world_points.append((wx, wy))
    return image_points, world_points


def main(argv=None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    image_size = None
    if args.headless:
        image_points, world_points = _points_from_args(args)
        if len(image_points) < 4:
            raise SystemExit("Headless mode needs at least 4 --point correspondences.")
    else:
        frame = _grab_frame(args.source, args.image)
        image_size = [int(frame.shape[1]), int(frame.shape[0])]
        image_points, world_points = _interactive(frame)

    homography = Homography.from_correspondences(image_points, world_points)
    error = homography.reprojection_error(image_points, world_points)
    print(f"\nSolved homography. Mean reprojection error: {error:.3f} ft")
    if error > 1.0:
        print("  Warning: error over 1 ft. Re check your clicked points / world coords.")

    camera = CameraConfig(
        camera_id=args.camera_id,
        homography=homography.tolist(),
        source=args.source,
        image_size=image_size,
        reprojection_error_ft=round(error, 4),
    )

    out_path = Path(args.out)
    if out_path.exists():
        court = load_config(out_path)
        court.cameras = [c for c in court.cameras if c.camera_id != args.camera_id]
        court.cameras.append(camera)
        print(f"Updated existing court config, camera {args.camera_id!r}.")
    else:
        court = CourtConfig(
            court_id=args.court_id,
            sport=args.sport,
            length_ft=args.length_ft,
            width_ft=args.width_ft,
            capacity=args.capacity,
            overcrowded_at=args.overcrowded_at,
            cameras=[camera],
        )

    save_config(court, out_path)
    print(f"Saved {out_path}")
    print(f"Court {court.court_id}: {court.sport} {court.length_ft}x{court.width_ft} ft, "
          f"{len(court.cameras)} camera(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
