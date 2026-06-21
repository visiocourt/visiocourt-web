# CourtSense Edge Vision

Pure computer vision court occupancy for a Raspberry Pi. No thermal sensors.
This turns one camera's angled view of a court into an accurate top down
occupancy map, and stays correct when one player steps behind another.

## The idea in one paragraph

A homography is a plane to plane mapping. We calibrate each camera once against
the court's flat ground plane, then for every detected person we project only
their foot contact point (where they touch the ground) into real world feet.
That gives a calibrated bird's eye map where two players who overlap in the
camera appear cleanly separated. A homography cannot see through a person and
cannot recover depth, so brief occlusions are bridged by tracking (predicting a
hidden player forward on their last velocity), and long or full occlusions are
resolved by adding a second camera at the opposite corner and fusing both maps.

## Why the foot point matters (the one rule to remember)

A homography is only valid for points that lie ON the court surface. A person's
head, torso, and bounding box center float above that plane, so projecting them
lands the player in the wrong spot, worst near the frame edges. We always
transform the foot contact point. With a pose model we use the ankle keypoints;
otherwise the bottom center of the bounding box.

## Layout

```
vision/
  courtsense/
    homography.py   image <-> world feet, foot point extraction
    config.py       per court / per camera calibration (JSON)
    detector.py     YOLO11 person + pose, with an offline mock fallback
    tracker.py      occlusion aware tracking (velocity bridging)
    court.py        occupancy status + wait time estimate
    fusion.py       merge multiple cameras into one world map
    visualize.py    camera overlay + top down court renderer
  homography_calibration.py   one time per camera calibration tool
  court_occupancy.py          single camera runtime
  multi_camera_fusion.py      multi camera runtime (full occlusion resolution)
  selftest.py                 numpy only checks for the core geometry/logic
  requirements.txt
```

## Install

```bash
cd vision
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

On 32 bit Raspberry Pi OS use the headless OpenCV wheel
(`pip install opencv-python-headless`) and export the YOLO model to NCNN.

## Try it with zero hardware

Everything degrades gracefully without a camera or a model. First create a demo
court config using the headless calibrator (these four points are a synthetic
pickleball court), then run the pipeline against the synthetic detector:

```bash
# 1. Build a demo calibration (no clicking, no camera).
python homography_calibration.py --headless \
  --point 300,700 0,0  --point 980,700 44,0 \
  --point 760,320 44,20  --point 520,320 0,20 \
  --court-id demo --sport pickleball --camera-id cam-a \
  --out courts/demo.json

# 2. Run occupancy on synthetic players (two cross + occlude each other).
python court_occupancy.py --config courts/demo.json --camera-id cam-a \
  --source mock --display          # drop --display on a headless Pi

# 3. Verify the math/logic with the numpy only self test.
python selftest.py
```

## Calibrate a real camera

Mount the camera high and angled steeply down (the single highest leverage fix
for occlusion), then run the interactive tool and click known court points,
typing each one's real world feet when prompted:

```bash
python homography_calibration.py --source 0 \
  --court-id court-1 --camera-id cam-a --sport pickleball \
  --out courts/court-1.json
```

Pick points flat on the court: the four corners, net post bases, service and
center line intersections. Four is the minimum; six to eight gives a better
fit. Aim for a reported reprojection error under about half a foot.

## Run on the court

Single camera (bridges brief occlusions):

```bash
python court_occupancy.py --config courts/court-1.json --camera-id cam-a \
  --mode pose --fps 2 --json-out readings.jsonl
```

Two cameras for full occlusion resolution (calibrate both into the same config,
then):

```bash
python multi_camera_fusion.py --config courts/court-1.json --fps 2 \
  --json-out readings.jsonl
```

Each reading emitted (stdout or JSON lines) carries the court status
(`free` / `active` / `busy` / `overcrowded`), the count of people on the
surface, an estimated wait, and per player world positions. That is exactly the
payload the CourtSense cloud dashboards and the public availability app consume.

## Running on a Raspberry Pi (full walkthrough)

Hardware: a Pi 4 or Pi 5 (Pi 5 strongly preferred), a camera, a microSD card,
and power. Either camera type works:

- USB webcam: simplest, opens as `--source 0`.
- Pi CSI camera (Camera Module 3 / HQ): use `--source picamera`. On current Pi
  OS the CSI camera is driven by libcamera and will NOT open through OpenCV,
  which is exactly why the pipeline uses `picamera2` for it under the hood.

Use the 64-bit Raspberry Pi OS (Bookworm). Check with `uname -m`, you want
`aarch64`. PyTorch/Ultralytics ship 64-bit Arm wheels but not 32-bit ones.

### 1. Get the code onto the Pi

```bash
git clone <your repo> ~/visiocourt-web
cd ~/visiocourt-web/vision
```

### 2. Install

```bash
bash deploy/install_pi.sh
```

This installs `python3-picamera2` from apt, creates a `--system-site-packages`
virtualenv (so the venv can see picamera2), and pip installs numpy, headless
OpenCV, and Ultralytics. Then sanity check with `python selftest.py`.

### 3. Speed up inference (recommended)

```bash
bash deploy/export_model.sh          # or: bash deploy/export_model.sh pose
```

This exports YOLO11 to NCNN, which is meaningfully faster than raw PyTorch on
Pi CPU. Pass the result to the runner with `--model yolo11n_ncnn_model`.

### 4. Calibrate the mounted camera

Calibration needs to see the frame. Two options:

- With a screen/VNC on the Pi, run the interactive tool (`--source picamera`).
- Headless: capture one still, copy it to a laptop, click points there, or pass
  the pixel/world correspondences directly with `--headless --point ...`.

```bash
# Grab one snapshot from the CSI camera to calibrate against:
python -c "from courtsense.capture import FrameSource; import cv2; \
c=FrameSource('picamera'); ok,f=c.read(); cv2.imwrite('snap.jpg',f); c.release()"
```

Save the homography into `courts/court-1.json` (see the calibration section
above).

### 5. Run it

```bash
source .venv/bin/activate
python court_occupancy.py --config courts/court-1.json --camera-id cam-a \
  --source picamera --model yolo11n_ncnn_model --fps 2 \
  --json-out readings.jsonl
```

No display is needed: it writes one JSON line per sample to `readings.jsonl`.
Drop the AI HAT or a second USB camera in and use `multi_camera_fusion.py` the
same way for full occlusion resolution.

### 6. Run on boot as a service

```bash
sudo mkdir -p /var/log/courtsense
sudo cp deploy/courtsense.service /etc/systemd/system/courtsense.service
# edit the paths/args inside the unit to match your install, then:
sudo systemctl daemon-reload
sudo systemctl enable --now courtsense.service
journalctl -u courtsense -f
```

The service restarts automatically on failure and starts at boot, so a power
blip at the facility brings the court back online unattended.

## Tuning for the Pi

- `--fps 2` is the big one. Court occupancy does not change frame to frame the
  way game action does; sampling at 1 to 2 fps cuts compute ~10 to 15x.
- Export the detector: `yolo export model=yolo11n.pt format=ncnn` (or int8
  TFLite) for a real speedup on Pi CPU.
- A Pi 5 + Hailo 8L AI HAT gives real time headroom if you later need higher
  rates (ball tracking, fast sports).
- Centralize inference: cheap camera only Pis can stream a JPEG every 1 to 2 s
  to one stronger box per facility that runs all detection.

## What this does and does not do

- Does: accurate live occupancy, who is where, counts robust to brief
  occlusion, multi camera fusion for hard occlusion, status + wait estimates.
- Does not: recover depth from one camera, or see a player who is fully hidden
  from every camera. Those are physical limits of monocular vision, handled by
  camera placement and adding viewpoints, not by math on one image.
```
