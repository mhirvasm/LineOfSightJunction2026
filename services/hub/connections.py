"""One in-memory run, socket ownership, and serialized receipt actions."""

import asyncio
from copy import deepcopy
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from fastapi import WebSocket, WebSocketDisconnect

TARGET_IDS = {"expenses", "json", "text", "coffee"}


@dataclass(eq=False)
class Client:
    socket: WebSocket
    key: str
    role: str
    send_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def send(self, message):
        async def write():
            async with self.send_lock:
                await self.socket.send_json(message)
        try:
            await asyncio.wait_for(write(), timeout=1)
            return True
        except (TimeoutError, RuntimeError, OSError, WebSocketDisconnect):
            return False


class Hub:
    def __init__(self):
        self.clients = {}
        self.broadcast_lock = asyncio.Lock()
        self.reset()
        from .workflow import ReceiptWorkflow
        self.workflow = ReceiptWorkflow(self)

    def reset(self):
        if getattr(self, "workflow", None):
            self.workflow.invalidate()
        if getattr(self, "vision", None):
            self.vision.invalidate()
        self.run_id = str(uuid4())
        self.state = "STOPPED"
        self.receipt = None
        self.text = None
        self.raw_text = self.summary = None
        self.text_status = "raw"
        self.capture_id = None
        self.target_id = None
        self.preview_id = None
        self.active_stream_id = None
        self.frame_source = None
        self.drafts = {target: None for target in ("expenses", "json", "text")}
        self.coffee_on = False
        self.coffee_desired = None
        self.interaction_kind = "content"
        self.capture_records = {}
        self.applied_commit_ids = set()
        self.previous_draft = None
        self.last_commit = None
        self.feedback = "Ready. Start the camera and hold to capture text or a receipt."

    def snapshot(self):
        return deepcopy({
            "v": 1, "type": "SNAPSHOT", "run_id": self.run_id,
            "state": self.state, "source_mode": self.workflow.reader.mode,
            "extraction_provider": self.workflow.reader.provider,
            "capture_id": self.capture_id, "receipt": self.receipt, "text": self.text,
            "raw_text": self.raw_text, "summary": self.summary, "text_status": self.text_status,
            "interaction_kind": self.interaction_kind, "coffee_on": self.coffee_on,
            "coffee_desired": self.coffee_desired,
            "can_select_coffee": self.state in {"READY", "APPLIED"} and self.active_stream_id is not None and self.workflow.fresh_target() == "coffee",
            "target_id": self.target_id, "preview_id": self.preview_id,
            "can_confirm": self.state == "PREVIEW" and self.preview_id is not None and self.workflow.fresh_target() == self.target_id, "drafts": self.drafts,
            "last_commit": self.last_commit, "feedback": self.feedback, "error": None,
            "vision": self.vision.snapshot() if getattr(self, "vision", None) else None,
            "connections": {
                "mobile": "mobile" in self.clients,
                "targets": {target: f"target:{target}" in self.clients for target in sorted(TARGET_IDS)},
                "operators": sum(client.role == "operator" for client in self.clients.values()),
            },
        })

    def bind(self, socket, role, target_id):
        if role not in {"mobile", "target", "operator"}:
            return None, "Unknown role. Use mobile, target, or operator."
        if (role == "target" and target_id not in TARGET_IDS) or (role != "target" and target_id is not None):
            return None, "Invalid target label for this role."
        key = f"target:{target_id}" if role == "target" else role
        if role == "operator":
            key = f"operator:{uuid4()}"
        if key in self.clients:
            return None, f"A {key} connection is already active. Close the other page first."
        client = Client(socket, key, role)
        self.clients[key] = client
        return client, None

    def stop_interaction(self):
        self.workflow.invalidate()
        if getattr(self, "vision", None):
            self.vision.invalidate()
        self.state = "STOPPED"
        self.receipt = None
        self.text = None
        self.raw_text = self.summary = None
        self.text_status = "raw"
        self.interaction_kind = "content"
        self.coffee_desired = None
        self.capture_id = None
        self.preview_id = None
        self.target_id = None
        self.active_stream_id = None
        self.frame_source = None
        self.feedback = "Paused. Press Start to resume; applied drafts remain."

    def unbind(self, client):
        if self.clients.get(client.key) is not client:
            return False
        del self.clients[client.key]
        if client.role == "mobile":
            self.stop_interaction()
        return True

    async def broadcast(self):
        async with self.broadcast_lock:
            while self.clients:
                clients = list(self.clients.values())
                results = await asyncio.gather(*(client.send(self.snapshot()) for client in clients))
                failed = [client for client, sent in zip(clients, results) if not sent]
                if not failed:
                    break
                for client in failed:
                    self.unbind(client)
                    try:
                        await asyncio.wait_for(client.socket.close(code=1011), timeout=1)
                    except (TimeoutError, RuntimeError, OSError):
                        pass

    def apply_event(self, client, event):
        if self.clients.get(client.key) is not client:
            return False, ("obsolete_connection", "This connection no longer owns its role.")
        if not isinstance(event, dict) or type(event.get("v")) is not int or event["v"] != 1:
            return False, ("invalid_event", "Send a JSON object with v: 1.")
        if event.get("run_id") != self.run_id:
            return False, ("stale_run", "The run changed. Use the current snapshot; do not replay the old action.")
        kind = event.get("type")
        if not isinstance(kind, str):
            return False, ("invalid_event", "type must be an event name string.")
        if kind == "RESET":
            if client.role != "operator":
                return False, ("forbidden", "Only an operator can reset the demo.")
            self.reset()
            return True, None
        action = event.get("action")
        if kind == "ACTION" and isinstance(action, str) and action in {"START", "STOP"}:
            if client.role != "mobile":
                return False, ("forbidden", "Only the active phone can start or stop its camera test.")
            if action == "STOP":
                self.stop_interaction()
                return True, None
            if self.state != "STOPPED":
                return False, None
            self.stop_interaction()
            self.state = "READY"
            self.feedback = "Ready. Hold to capture text or a receipt."
            return True, None
        if kind in {"STREAM_STARTED", "DEVICE_PAUSED"}:
            if client.role != "mobile":
                return False, ("forbidden", "Only the active mobile controller can send this event.")
            if kind == "DEVICE_PAUSED":
                self.stop_interaction()
                return True, None
            stream_id = event.get("stream_id")
            try:
                if not isinstance(stream_id, str):
                    raise ValueError
                UUID(stream_id)
            except ValueError:
                return False, ("invalid_stream", "stream_id must be a UUID string.")
            changed = stream_id != self.active_stream_id
            source = event.get("input_source", "unspecified")
            if not isinstance(source, str) or source not in {"unspecified", "phone_photo", "camera_stream", "fixture_frames", "native_camera"}:
                return False, ("invalid_event", "Unknown frame input source label.")
            if changed and getattr(self, "vision", None):
                self.vision.invalidate()
                self.target_id = None
                self.preview_id = None
            self.active_stream_id = stream_id
            self.frame_source = source
            if changed:
                self.workflow.clear("Camera changed. Hold to capture again.")
            return changed, None
        if kind in {"ACTION", "DISPLAYED"}:
            return self.workflow.event(client, event)
        return False, ("invalid_event", "Unknown event.")

    async def error(self, client, code, message):
        await client.send({"v": 1, "type": "ERROR", "run_id": self.run_id, "error": code, "message": message})
