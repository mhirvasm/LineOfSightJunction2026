"""Paid live OCR checks on two generated printed notes; no handwriting claim."""

import asyncio
from pathlib import Path
import sys
from time import monotonic

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import scripts.run_hub
from services.hub.extraction.content import ContentReader

NOTE = 'Meet at the library at 14:30.\nBring the blue notebook.\nKiitos!'
CHANGED_NOTE = 'Meet at the library at 15:45.\nBring the red notebook.\n<b>plain text</b>'


def text_jpeg(text):
    lines = text.splitlines()
    image = np.full((160 + len(lines) * 60, 1000, 3), 255, dtype=np.uint8)
    for index, line in enumerate(lines):
        cv2.putText(image, line, (50, 110 + index * 60), cv2.FONT_HERSHEY_SIMPLEX, 1.25, (0, 0, 0), 2, cv2.LINE_AA)
    ok, jpeg = cv2.imencode('.jpg', image)
    assert ok
    return jpeg.tobytes()


async def main():
    reader = ContentReader('live')
    for label, expected in [('known note', NOTE), ('changed note with literal markup', CHANGED_NOTE)]:
        started = monotonic()
        result = await reader(text_jpeg(expected))
        assert result['receipt'] is None, 'A note was incorrectly classified as a receipt'
        assert result['text'].strip() == expected, f'Transcription mismatch for {label}: {result["text"]!r}'
        print(f'Live {label}: exact wording and line breaks passed in {monotonic() - started:.1f}s')


if __name__ == '__main__':
    asyncio.run(main())
