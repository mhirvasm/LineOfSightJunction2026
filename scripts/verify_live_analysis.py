"""Paid text-only checks for grammar cleanup, summary and preserved source facts."""

import asyncio
import json
from pathlib import Path
import sys
from time import monotonic

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import scripts.run_hub
from services.hub.extraction.analysis import TextAnalyzer


async def main():
    analyzer = TextAnalyzer('live')
    cases = [
        ('grammar', 'The notes is ready.\nWe has a meeting at 14:30.'),
        ('negation and uncertainty', 'The delivery are not approved.\nDo not send EUR 31.90 to https://example.com/order/42.\nSigned: [unreadable].'),
    ]
    for label, source in cases:
        started = monotonic()
        result = await analyzer(source)
        if label == 'grammar':
            assert 'notes are ready' in result['corrected_text']
            assert 'We have a meeting' in result['corrected_text']
        else:
            assert 'not approved' in result['corrected_text'] and 'Do not send' in result['corrected_text']
            assert 'not' in result['summary'].lower() or "n't" in result['summary'].lower()
        print(json.dumps({'case': label, 'seconds': round(monotonic()-started, 1), **result}, ensure_ascii=True))


if __name__ == '__main__':
    asyncio.run(main())
