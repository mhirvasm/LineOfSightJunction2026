"""One background detector and one replaceable latest pending frame."""

import asyncio
from dataclasses import dataclass
from time import monotonic

from .detection import MarkerDetector
from .tracking import TargetTracker


@dataclass
class Frame:
    generation: int
    run_id: str
    stream_id: str
    owner: object
    sequence: int
    age_ms: int
    received_at: float
    data: bytes


class FrameRejected(ValueError):
    def __init__(self, message, status=409):
        super().__init__(message)
        self.status = status


class VisionService:
    def __init__(self, hub, detector=None):
        self.hub = hub
        self.detector = detector or MarkerDetector()
        self.tracker = TargetTracker()
        self.generation = 0
        self.worker = None
        self.pending = None
        self.timer = None
        self.invalidate()

    def start(self):
        self.timer = asyncio.create_task(self.expiry_loop())

    async def close(self):
        self.invalidate()
        for task in (self.worker, self.timer):
            if task:
                task.cancel()
        await asyncio.gather(*(task for task in (self.worker, self.timer) if task), return_exceptions=True)

    def invalidate(self):
        self.generation += 1
        self.pending = None
        self.last_sequence = -1
        self.processed_sequence = None
        self.received_at = None
        self.frame_age_ms = 0
        self.detected_id = None
        self.marker_ids = ()
        self.message = "No frames yet. Start the phone camera/photo test."
        self.tracker.clear()

    def signature(self):
        return (self.tracker.candidate_id, self.tracker.locked_id, self.detected_id, self.marker_ids, self.message)

    def snapshot(self):
        return {
            "candidate_id": self.tracker.candidate_id,
            "locked_target_id": self.tracker.locked_id,
            "detected_target_id": self.detected_id,
            "marker_ids": list(self.marker_ids), "frame_seq": self.processed_sequence,
            "frame_age_ms": None if self.received_at is None else int((monotonic() - self.received_at) * 1000 + self.frame_age_ms),
            "message": self.message, "stream_id": self.hub.active_stream_id,
            "input_source": self.hub.frame_source,
        }

    def guard(self, run_id, stream_id, sequence, age_ms, owner=None):
        mobile = self.hub.clients.get("mobile")
        if run_id != self.hub.run_id:
            raise FrameRejected("Old run. Wait for the current hub snapshot.")
        if mobile is None or (owner is not None and mobile is not owner):
            raise FrameRejected("The active phone connection is required.")
        if stream_id != self.hub.active_stream_id or not stream_id:
            raise FrameRejected("Announce the current stream over the active phone socket first.")
        if self.hub.state == "STOPPED":
            raise FrameRejected("Start the camera test before uploading frames.")
        if age_ms < 0 or age_ms > 300:
            raise FrameRejected("Frame local delivery age must be between 0 and 300 ms.", 422)
        if sequence < 0 or sequence <= self.last_sequence:
            raise FrameRejected("Frame sequence is old or out of order.")
        return mobile

    def submit(self, run_id, stream_id, sequence, age_ms, data, owner=None):
        mobile = self.guard(run_id, stream_id, sequence, age_ms, owner)
        self.last_sequence = sequence
        self.pending = Frame(self.generation, run_id, stream_id, mobile, sequence, age_ms, monotonic(), data)
        if self.worker is None or self.worker.done():
            self.worker = asyncio.create_task(self.process())

    def current(self, frame):
        return (frame.generation == self.generation and frame.run_id == self.hub.run_id
                and frame.stream_id == self.hub.active_stream_id
                and self.hub.clients.get("mobile") is frame.owner and self.hub.state != "STOPPED")

    def sync_target(self):
        target_id = self.tracker.locked_id
        if self.hub.target_id != target_id:
            self.hub.target_id = target_id
            self.hub.preview_id = None

    async def process(self):
        while self.pending is not None:
            frame, self.pending = self.pending, None
            try:
                result = await asyncio.to_thread(self.detector, frame.data)
                failure = None
            except Exception as error:
                result, failure = None, str(error)
            if not self.current(frame):
                continue
            now = monotonic()
            if (now - frame.received_at) * 1000 + frame.age_ms > 300:
                message = "Frame was too old after processing. Try a smaller fresh image."
                if self.message != message:
                    self.message = message
                    await self.hub.broadcast()
                continue
            before = self.signature()
            self.processed_sequence = frame.sequence
            self.received_at = frame.received_at
            self.frame_age_ms = frame.age_ms
            self.detected_id = result.target_id if result else None
            self.marker_ids = result.marker_ids if result else ()
            candidate = self.detected_id
            if candidate and f"target:{candidate}" not in self.hub.clients:
                candidate = None
                self.message = f"Recognized {self.detected_id}, but its receiving screen is disconnected."
            else:
                self.message = failure or result.message
            self.tracker.observe(candidate, now, unsafe=bool(failure or (result and result.unsafe)))
            if self.tracker.locked_id:
                self.message = f"Stable target: {self.tracker.locked_id}. Fresh frames are required to keep it selected."
            self.sync_target()
            if before != self.signature():
                await self.hub.broadcast()

    async def expiry_loop(self):
        while True:
            await asyncio.sleep(.1)
            before = self.signature()
            selected = self.tracker.locked_id or self.tracker.candidate_id
            if selected and f"target:{selected}" not in self.hub.clients:
                self.tracker.clear()
                self.message = "Receiving screen disconnected. No target selected."
            elif self.tracker.expire(monotonic()):
                self.message = "Target expired. Send fresh camera frames; a single photo is only a recognition check."
            self.sync_target()
            if before != self.signature():
                await self.hub.broadcast()
