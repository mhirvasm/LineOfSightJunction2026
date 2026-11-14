"""Receipt lifecycle, cancellation ordering, destination writes, and provider checks."""

import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
from time import monotonic
import unittest
from unittest.mock import patch
from uuid import uuid4

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.hub.connections import Hub
from services.hub.extraction.receipt import ReceiptReader, validate_receipt
from services.hub.vision.service import VisionService, FrameRejected

RECORD = json.loads(Path('fixtures/receipt_expected.json').read_text())


class WorkflowChecks(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.h = Hub()
        self.h.vision = VisionService(self.h)
        self.phone, _ = self.h.bind(None, 'mobile', None)
        self.expenses, _ = self.h.bind(None, 'target', 'expenses')
        self.json, _ = self.h.bind(None, 'target', 'json')
        async def broadcast():
            pass
        self.h.broadcast = broadcast
        self.h.state = 'READY'
        self.h.active_stream_id = str(uuid4())
        self.calls = []
        self.gate = asyncio.Event()
        async def reader(image):
            self.calls.append(image)
            await self.gate.wait()
            return deepcopy(RECORD)
        self.h.workflow.reader = reader

    async def asyncTearDown(self):
        await self.h.workflow.close()

    def event(self, action, **kwargs):
        return self.h.apply_event(self.phone, dict(v=1, type='ACTION', run_id=self.h.run_id, action=action, **kwargs))

    def capture(self, id=None, image=b'frozen receipt'):
        id = id or str(uuid4())
        self.h.workflow.accept(self.h.run_id, id, 0, image, self.phone)
        return id

    def target(self, target):
        tracker = self.h.vision.tracker
        tracker.clear()
        if target:
            tracker.observe(target, monotonic() - .4)
            tracker.observe(target, monotonic())
        self.h.workflow.refresh()

    async def ready(self):
        capture = self.capture()
        self.gate.set()
        await self.h.workflow.task
        return capture

    async def test_cancel_before_upload(self):
        id = str(uuid4())
        self.event('CANCEL', capture_id=id)
        with self.assertRaises(FrameRejected): self.capture(id)
        self.assertEqual(self.calls, [])

    async def test_cancel_during_read_and_old_cancel_after_new_grab(self):
        old = self.capture()
        await asyncio.sleep(0)
        self.event('CANCEL', capture_id=old)
        new = self.capture()
        self.event('CANCEL', capture_id=old)
        self.gate.set()
        await self.h.workflow.task
        self.assertEqual(self.h.capture_id, new)
        self.assertEqual(self.h.state, 'HOLDING')

    async def test_duplicate_capture_and_changed_bytes(self):
        id = self.capture()
        self.capture(id)
        with self.assertRaises(FrameRejected): self.capture(id, b'other')
        self.gate.set()
        await self.h.workflow.task
        self.assertEqual(self.calls, [b'frozen receipt'])

    async def test_two_destinations_duplicate_release_undo_and_new_grab(self):
        for target in ('expenses', 'json'):
            capture = await self.ready()
            self.target(target)
            preview = self.h.preview_id
            self.event('CONFIRM', preview_id=preview, capture_id=capture)
            previous = deepcopy(self.h.previous_draft)
            self.event('CONFIRM', preview_id=preview)
            self.event('CANCEL', capture_id=capture)
            self.assertEqual(self.h.drafts[target], RECORD)
            self.assertEqual(self.h.previous_draft, previous)
        self.event('UNDO')
        self.assertIsNone(self.h.drafts['json'])
        self.assertEqual(self.h.drafts['expenses'], RECORD)

    async def test_stale_target_cancels_and_cannot_redirect(self):
        capture = await self.ready()
        self.target('expenses')
        old = self.h.preview_id
        self.target('json')
        self.event('CONFIRM', preview_id=old, capture_id=capture)
        self.assertEqual(self.h.drafts, dict(expenses=None, json=None))
        self.assertEqual(self.h.state, 'READY')

    async def test_expiry_rechecked_at_commit_without_timer(self):
        capture = await self.ready()
        self.target('expenses')
        old = self.h.preview_id
        self.h.vision.tracker.last_seen = monotonic() - 2
        self.event('CONFIRM', preview_id=old, capture_id=capture)
        self.assertIsNone(self.h.drafts['expenses'])
        self.assertEqual(self.h.state, 'READY')

    async def test_ack_and_send_again_new_preview(self):
        await self.ready()
        self.target('expenses')
        old = self.h.preview_id
        self.event('CONFIRM', preview_id=old)
        event = dict(v=1, type='DISPLAYED', run_id=self.h.run_id, target_id='expenses', commit_id=old)
        self.h.apply_event(self.json, event)
        self.assertEqual(self.h.last_commit['display_status'], 'waiting')
        self.h.apply_event(self.expenses, event)
        self.assertEqual(self.h.last_commit['display_status'], 'displayed')
        self.event('SEND_AGAIN')
        self.assertNotEqual(self.h.preview_id, old)

    async def test_reset_and_stop_discard_read(self):
        for reset in (False, True):
            self.h.state = 'READY'
            self.h.active_stream_id = str(uuid4())
            self.capture()
            if reset: self.h.reset()
            else: self.h.stop_interaction()
            self.gate.set()
            await asyncio.sleep(.01)
            self.assertIsNone(self.h.receipt)
            self.assertEqual(self.h.state, 'STOPPED')

    async def test_provider_timeout_is_visible_without_a_draft_write(self):
        async def slow_provider(image):
            raise httpx.ReadTimeout('test timeout')
        self.h.workflow.reader = slow_provider
        self.capture()
        await self.h.workflow.task
        self.assertEqual(self.h.state, 'READY')
        self.assertIsNone(self.h.receipt)
        self.assertIn('timed out', self.h.feedback)
        self.assertEqual(self.h.drafts, dict(expenses=None, json=None))


class ExtractionChecks(unittest.IsolatedAsyncioTestCase):
    async def test_validation(self):
        self.assertEqual(validate_receipt(RECORD), RECORD)
        for field, value in [('total_minor', True), ('total_minor', 24.8), ('date', 'bad'), ('merchant', None), ('currency', 'USD'), ('needs_review', ['total'])]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                validate_receipt(dict(RECORD, **{field: value}))

    async def test_live_request_contract_and_changed_total(self):
        record = dict(RECORD, total_minor=3190)
        def handler(request):
            body = json.loads(request.content)
            self.assertFalse(body['store'])
            self.assertTrue(body['input'][0]['content'][1]['image_url'].endswith('ZnJvemVu'))
            return httpx.Response(200, json={'status': 'completed', 'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(record)}]}]})
        with patch.dict(os.environ, OPENAI_API_KEY='test-only'):
            result = await ReceiptReader('live', httpx.MockTransport(handler), provider='openai')(b'frozen')
        self.assertEqual(result['total_minor'], 3190)

    async def test_provider_error_has_no_fixture_fallback(self):
        with patch.dict(os.environ, OPENAI_API_KEY='test-only'):
            with self.assertRaises(ValueError):
                await ReceiptReader('live', httpx.MockTransport(lambda _: httpx.Response(429)), provider='openai')(b'frozen')

    async def test_gemini_request_and_changed_total(self):
        record = dict(RECORD, total_minor=3190)
        def handler(request):
            body = json.loads(request.content)
            self.assertEqual(request.headers['x-goog-api-key'], 'test-only')
            self.assertEqual(body['contents'][0]['parts'][1]['inlineData']['data'], 'ZnJvemVu')
            self.assertEqual(body['generationConfig']['responseMimeType'], 'application/json')
            return httpx.Response(200, json={'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': json.dumps(record)}]}}]})
        with patch.dict(os.environ, GEMINI_API_KEY='test-only'):
            result = await ReceiptReader('live', httpx.MockTransport(handler), provider='gemini')(b'frozen')
        self.assertEqual(result['total_minor'], 3190)


if __name__ == '__main__':
    unittest.main(verbosity=2)
