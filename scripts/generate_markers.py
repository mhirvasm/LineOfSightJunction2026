"""Generate exact OpenCV markers with a white quiet zone; no resampling."""

import json
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]


def generate():
    targets = json.loads((ROOT / "contracts/targets.json").read_text())
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    for target in targets.values():
        marker = cv2.aruco.generateImageMarker(dictionary, target["marker_id"], 480)
        image = cv2.copyMakeBorder(marker, 60, 60, 60, 60, cv2.BORDER_CONSTANT, value=255)
        output = ROOT / "apps/web/public" / target["marker_asset"].lstrip("/")
        output.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(output), image):
            raise RuntimeError(f"Could not write {output}")
        print(f"Generated {output.relative_to(ROOT)}")


if __name__ == "__main__":
    generate()
