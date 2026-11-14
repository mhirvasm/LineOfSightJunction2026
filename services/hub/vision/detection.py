"""Detect registered markers from JPEG pixels, without choosing an action."""

from dataclasses import dataclass

import cv2
import numpy as np

MAX_BYTES = 2_000_000
MAX_PIXELS = 4_000_000
TARGETS = {10: "expenses", 20: "json", 30: "text"}


class ImageTooLarge(ValueError):
    pass


def validate_jpeg(data):
    if not data:
        raise ValueError("JPEG must be nonempty.")
    if len(data) > MAX_BYTES:
        raise ImageTooLarge("JPEG must be at most 2 MB.")
    if data[:2] != b"\xff\xd8":
        raise ValueError("Send a JPEG image.")
    offset = 2
    while offset + 3 < len(data):
        if data[offset] != 255:
            break
        while offset < len(data) and data[offset] == 255:
            offset += 1
        if offset >= len(data):
            break
        marker = data[offset]
        offset += 1
        if marker in {0xD9, 0xDA}:
            break
        if marker == 0x01 or 0xD0 <= marker <= 0xD8:
            continue
        if offset + 2 > len(data):
            break
        length = int.from_bytes(data[offset:offset + 2], "big")
        if length < 2 or offset + length > len(data):
            break
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            if length < 8:
                break
            height = int.from_bytes(data[offset + 3:offset + 5], "big")
            width = int.from_bytes(data[offset + 5:offset + 7], "big")
            if width <= 0 or height <= 0 or width * height > MAX_PIXELS:
                raise ImageTooLarge("Decoded image must be at most 4 megapixels.")
            return width, height
        offset += length
    raise ValueError("JPEG header is invalid or incomplete.")


@dataclass(frozen=True)
class Detection:
    target_id: str | None
    message: str
    marker_ids: tuple = ()
    unsafe: bool = False


class MarkerDetector:
    def __init__(self):
        dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        self.detector = cv2.aruco.ArucoDetector(dictionary)

    def __call__(self, data):
        validate_jpeg(data)
        image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION)
        if image is None:
            raise ValueError("JPEG pixels could not be decoded.")
        height, width = image.shape[:2]
        if width * height > MAX_PIXELS:
            raise ValueError("Decoded image must be at most 4 megapixels.")
        corners, ids, _ = self.detector.detectMarkers(image)
        if ids is None:
            return Detection(None, "No marker found. Move closer, reduce glare, and keep the whole square visible.")
        found = tuple(int(value) for value in ids.flatten())
        central = []
        for box, marker_id in zip(corners, found):
            x, y = box.reshape(4, 2).mean(axis=0)
            if .25 <= x / width <= .75 and .25 <= y / height <= .75:
                central.append(marker_id)
        if len(central) > 1:
            return Detection(None, "Ambiguous view: more than one central marker. Aim at one screen.", found, True)
        if not central:
            return Detection(None, "Marker is outside the central half of the image. Aim at the middle of one screen.", found)
        marker_id = central[0]
        if marker_id not in TARGETS:
            return Detection(None, f"Unknown central marker {marker_id}; only 10, 20 and 30 are registered.", found, True)
        return Detection(TARGETS[marker_id], f"Recognized marker {marker_id}: {TARGETS[marker_id]}.", found)
