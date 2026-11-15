"""B2 pixel detection, target freshness, upload guards, and bounded work."""

import asyncio
from contextlib import ExitStack
from pathlib import Path
import sys
import threading
import time
import unittest
from uuid import uuid4

import cv2
import numpy as np
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from services.hub.app import create_app
from services.hub.connections import Hub
from services.hub.vision.detection import Detection, ImageTooLarge, MarkerDetector, validate_jpeg
from services.hub.vision.service import VisionService
from services.hub.vision.tracking import TargetTracker
from scripts.verify_hub import snapshot


def camera_frame(markers=((10, 360, 240),), size=(720, 960)):
    image = np.full(size, 255, dtype=np.uint8)
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    for marker_id, x, y in markers:
        marker = cv2.aruco.generateImageMarker(dictionary, marker_id, 240)
        image[y:y + 240, x:x + 240] = marker
    success, jpeg = cv2.imencode(".jpg", image)
    assert success
    return jpeg.tobytes()


def start_phone(client, stack):
    phone = stack.enter_context(client.websocket_connect("/v1/events?role=mobile"))
    current = snapshot(phone)
    phone.send_json({"v": 1, "type": "ACTION", "action": "START", "run_id": current["run_id"]})
    snapshot(phone, lambda value: value["state"] == "READY")
    stream = str(uuid4())
    phone.send_json({"v": 1, "type": "STREAM_STARTED", "run_id": current["run_id"], "stream_id": stream, "input_source": "fixture_frames"})
    snapshot(phone, lambda value: value["vision"]["stream_id"] == stream)
    return phone, {"run_id": current["run_id"], "stream_id": stream, "frame_seq": "1", "age_ms": "0"}


class PixelChecks(unittest.TestCase):
    def test_real_jpeg_pixels_choose_exact_ids_and_reject_ambiguous_unknown_offcentre(self):
        detect = MarkerDetector()
        self.assertEqual(detect(camera_frame()).target_id, "expenses")
        self.assertEqual(detect(camera_frame(((20, 360, 240),))).target_id, "json")
        self.assertEqual(detect(camera_frame(((30, 360, 240),))).target_id, "text")
        self.assertEqual(detect(camera_frame(((40, 360, 240),))).target_id, "coffee")
        self.assertIsNone(detect(camera_frame(((10, 10, 240),))).target_id)
        self.assertTrue(detect(camera_frame(((7, 360, 240),))).unsafe)
        ambiguous = detect(camera_frame(((10, 200, 240), (20, 540, 240))))
        self.assertTrue(ambiguous.unsafe)
        self.assertIsNone(ambiguous.target_id)
        self.assertIsNone(detect(camera_frame(())).target_id)

    def test_jpeg_byte_and_pixel_bounds_before_decode(self):
        self.assertEqual(validate_jpeg(camera_frame()), (960, 720))
        for invalid in (b"", b"not jpeg", b"\xff\xd8bad"):
            with self.assertRaises(ValueError):
                validate_jpeg(invalid)
        with self.assertRaises(ImageTooLarge):
            validate_jpeg(b"\xff\xd8" + b"x" * 2_000_000)
        oversized = bytearray(camera_frame())
        sof = oversized.index(b"\xff\xc0")
        oversized[sof + 5:sof + 9] = b"\x10\x00\x10\x00"
        with self.assertRaises(ImageTooLarge):
            validate_jpeg(oversized)

    def test_stability_switch_ambiguity_and_expiry(self):
        tracker = TargetTracker()
        tracker.observe("expenses", 0)
        tracker.observe("expenses", .349)
        self.assertIsNone(tracker.locked_id)
        tracker.observe("expenses", .351)
        self.assertEqual(tracker.locked_id, "expenses")
        for index in range(50):
            tracker.observe("expenses", .36 + index * .01)
            self.assertEqual(tracker.locked_id, "expenses")
        tracker.observe("json", .9)
        self.assertIsNone(tracker.locked_id)
        tracker.observe("json", 1.26)
        self.assertEqual(tracker.locked_id, "json")
        tracker.observe(None, 1.3, unsafe=True)
        self.assertIsNone(tracker.locked_id)
        tracker.observe("expenses", 2)
        tracker.observe("expenses", 2.4)
        self.assertFalse(tracker.expire(2.99))
        self.assertTrue(tracker.expire(3.01))
        self.assertIsNone(tracker.locked_id)

    def test_sparse_still_photos_cannot_form_a_fresh_stable_lock(self):
        tracker = TargetTracker()
        for timestamp in (0, 1, 2, 3):
            tracker.observe("expenses", timestamp)
            self.assertIsNone(tracker.locked_id)


class UploadChecks(unittest.TestCase):
    def test_multipart_guardrails_and_current_pixels(self):
        application = create_app()
        with TestClient(application) as client, ExitStack() as stack:
            target = stack.enter_context(client.websocket_connect("/v1/events?role=target&id=expenses"))
            snapshot(target)
            phone, fields = start_phone(client, stack)
            jpeg = camera_frame()
            for change, code in [({"run_id": "old"}, 409), ({"stream_id": str(uuid4())}, 409),
                                 ({"age_ms": "301"}, 422), ({"age_ms": "-1"}, 422),
                                 ({"frame_seq": "true"}, 422), ({"frame_seq": "-1"}, 409)]:
                response = client.post("/v1/frames", data=fields | change, files={"image": ("frame.jpg", jpeg, "image/jpeg")})
                self.assertEqual(response.status_code, code, response.text)
            malformed = client.post("/v1/frames", data=fields, files={"image": ("frame.jpg", b"not JPEG", "image/jpeg")})
            self.assertEqual(malformed.status_code, 400)
            oversized = client.post("/v1/frames", content=b"", headers={"content-length": "9000000"})
            self.assertEqual(oversized.status_code, 413)
            response = client.post("/v1/frames", data=fields, files={"image": ("frame.jpg", jpeg, "image/jpeg")})
            self.assertEqual(response.status_code, 202, response.text)
            detected = snapshot(phone, lambda value: value["vision"]["detected_target_id"] == "expenses")
            self.assertIsNone(detected["vision"]["locked_target_id"])
            duplicate = client.post("/v1/frames", data=fields, files={"image": ("frame.jpg", jpeg, "image/jpeg")})
            self.assertEqual(duplicate.status_code, 409)
            phone.send_json({"v": 1, "type": "ACTION", "action": "STOP", "run_id": fields["run_id"]})
            stopped = snapshot(phone, lambda value: value["state"] == "STOPPED")
            self.assertIsNone(stopped["target_id"])
            self.assertEqual(stopped["drafts"], {"expenses": None, "json": None, "text": None})
            response = client.post("/v1/frames", data=fields | {"frame_seq": "2"}, files={"image": ("frame.jpg", jpeg, "image/jpeg")})
            self.assertEqual(response.status_code, 409)

    def test_fresh_stream_locks_then_expires_without_changing_drafts(self):
        application = create_app()
        with TestClient(application) as client, ExitStack() as stack:
            target = stack.enter_context(client.websocket_connect("/v1/events?role=target&id=expenses"))
            snapshot(target)
            phone, fields = start_phone(client, stack)
            jpeg = camera_frame()
            for sequence in range(1, 5):
                response = client.post("/v1/frames", data=fields | {"frame_seq": str(sequence)}, files={"image": ("frame.jpg", jpeg, "image/jpeg")})
                self.assertEqual(response.status_code, 202)
                time.sleep(.14)
            locked = snapshot(phone, lambda value: value["vision"]["locked_target_id"] == "expenses")
            self.assertEqual(locked["target_id"], "expenses")
            self.assertFalse(locked["can_confirm"])
            expired = snapshot(phone, lambda value: "expired" in value["vision"]["message"])
            self.assertIsNone(expired["target_id"])
            self.assertEqual(expired["drafts"], {"expenses": None, "json": None, "text": None})

    def test_disconnected_receiving_screen_is_recognized_but_not_selected(self):
        with TestClient(create_app()) as client, ExitStack() as stack:
            phone, fields = start_phone(client, stack)
            response = client.post("/v1/frames", data=fields, files={"image": ("frame.jpg", camera_frame(), "image/jpeg")})
            self.assertEqual(response.status_code, 202)
            recognized = snapshot(phone, lambda value: value["vision"]["detected_target_id"] == "expenses")
            self.assertIsNone(recognized["vision"]["candidate_id"])
            self.assertIsNone(recognized["target_id"])
            self.assertIn("disconnected", recognized["vision"]["message"])


class WorkerChecks(unittest.IsolatedAsyncioTestCase):
    async def make_service(self, detector):
        hub = Hub()
        owner, _ = hub.bind(object(), "mobile", None)
        hub.bind(object(), "target", "expenses")
        hub.bind(object(), "target", "json")
        hub.state = "READY"
        hub.active_stream_id = str(uuid4())
        async def broadcast():
            pass
        hub.broadcast = broadcast
        service = VisionService(hub, detector)
        hub.vision = service
        return hub, owner, service

    async def test_one_inflight_frame_and_only_latest_pending_survives(self):
        entered, release = threading.Event(), threading.Event()
        calls = []
        def detect(data):
            calls.append(data)
            if data == b"first":
                entered.set()
                release.wait(2)
            return Detection("expenses", "Recognized expenses.")
        hub, owner, service = await self.make_service(detect)
        service.submit(hub.run_id, hub.active_stream_id, 1, 0, b"first", owner)
        self.assertTrue(await asyncio.to_thread(entered.wait, 1))
        try:
            for sequence in range(2, 21):
                service.submit(hub.run_id, hub.active_stream_id, sequence, 0, str(sequence).encode(), owner)
            self.assertEqual(calls, [b"first"])
            self.assertEqual(service.pending.sequence, 20)
        finally:
            release.set()
        await asyncio.wait_for(service.worker, 2)
        self.assertEqual(calls, [b"first", b"20"])
        self.assertIsNone(service.pending)

    async def test_reset_invalidates_old_worker_and_preserves_single_worker_for_new_run(self):
        entered, release = threading.Event(), threading.Event()
        def detect(data):
            if data == b"old":
                entered.set()
                release.wait(2)
            return Detection("expenses" if data == b"old" else "json", "Recognized marker.")
        hub, owner, service = await self.make_service(detect)
        service.submit(hub.run_id, hub.active_stream_id, 1, 0, b"old", owner)
        self.assertTrue(await asyncio.to_thread(entered.wait, 1))
        old_worker = service.worker
        try:
            hub.reset()
            hub.state = "READY"
            hub.active_stream_id = str(uuid4())
            service.submit(hub.run_id, hub.active_stream_id, 1, 0, b"new", owner)
            self.assertIs(service.worker, old_worker)
        finally:
            release.set()
        await asyncio.wait_for(service.worker, 2)
        self.assertEqual(service.detected_id, "json")
        self.assertIsNone(hub.target_id)
        self.assertEqual(hub.drafts, {"expenses": None, "json": None, "text": None})

    async def test_unchanged_selection_keeps_preview_id_and_screen_loss_clears_it(self):
        hub, owner, service = await self.make_service(lambda data: Detection("expenses", "Recognized."))
        service.tracker.observe("expenses", time.monotonic() - .4)
        service.tracker.observe("expenses", time.monotonic())
        service.sync_target()
        hub.preview_id = "unchanged-preview"
        service.sync_target()
        self.assertEqual(hub.preview_id, "unchanged-preview")
        service.start()
        try:
            hub.unbind(hub.clients["target:expenses"])
            await asyncio.sleep(.15)
            self.assertIsNone(hub.target_id)
            self.assertIsNone(hub.preview_id)
        finally:
            await service.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
