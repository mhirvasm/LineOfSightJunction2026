"""Explicit, paid live check using two generated synthetic receipt images."""

import asyncio
from pathlib import Path
import sys
from time import monotonic

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import scripts.run_hub  # loads local configuration without printing it
from services.hub.extraction.receipt import ReceiptReader


def receipt_jpeg(amount):
    image = np.full((850, 700, 3), 255, dtype=np.uint8)
    for index, line in enumerate(["DEMO CAFE", "Receipt", "Date: 2026-11-14", "Coffee and lunch", f"TOTAL: EUR {amount}", "Thank you"]):
        cv2.putText(image, line, (40, 100 + index * 110), cv2.FONT_HERSHEY_SIMPLEX, 1.25, (0, 0, 0), 2, cv2.LINE_AA)
    ok, jpeg = cv2.imencode('.jpg', image)
    assert ok
    return jpeg.tobytes()


async def main():
    reader = ReceiptReader("live")
    for amount, minor in (("24.80", 2480), ("31.90", 3190)):
        jpeg = receipt_jpeg(amount)
        started = monotonic()
        record = await reader(jpeg)
        assert record['total_minor'] == minor, 'Changed total was not read correctly'
        assert record['date'] == '2026-11-14'
        assert record['merchant'].casefold() == 'demo cafe'
        print(f"Live synthetic receipt: EUR {amount}, merchant/date/validation passed in {monotonic() - started:.1f}s")


if __name__ == '__main__':
    asyncio.run(main())
