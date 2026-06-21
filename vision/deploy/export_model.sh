#!/usr/bin/env bash
#
# Export the YOLO model to NCNN for a real speedup on Raspberry Pi CPU.
# Run after install_pi.sh, with the venv active (or it activates it for you).
#
#   bash deploy/export_model.sh            # detect model (yolo11n)
#   bash deploy/export_model.sh pose       # pose model (yolo11n-pose)

set -euo pipefail

MODE="${1:-detect}"
if [ "${MODE}" = "pose" ]; then
  MODEL="yolo11n-pose.pt"
else
  MODEL="yolo11n.pt"
fi

if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

echo "==> Exporting ${MODEL} to NCNN"
yolo export "model=${MODEL}" format=ncnn

OUT="${MODEL%.pt}_ncnn_model"
echo "==> Done. Pass this to the runner:  --model ${OUT}"
echo "    NCNN runs noticeably faster than raw PyTorch on Pi CPU."
