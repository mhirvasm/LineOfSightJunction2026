"""One in-memory run and socket ownership; receipt workflow comes later."""

import asyncio
from copy import deepcopy
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from fastapi import WebSocket, WebSocketDisconnect

TARGET_IDS = {"expenses", "json"}


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

    def reset(self):
        self.run_id = str(uuid4())
        self.state = "STOPPED"
        self.receipt = None
        self.capture_id = None
        self.target_id = None
        self.preview_id = None
        self.active_stream_id = None
        self.drafts = {"expenses": None, "json": None}
        self.capture_records = {}
        self.applied_commit_ids = set()
        self.previous_draft = None
        self.last_commit = None
        self.feedback = "Connection test ready. Camera capture and transfers are not connected yet."

    def snapshot(self):
        return deepcopy({
            "v": 1, "type": "SNAPSHOT", "run_id": self.run_id,
            "state": self.state, "source_mode": "fixture",
            "capture_id": self.capture_id, "receipt": self.receipt,
            "target_id": self.target_id, "preview_id": self.preview_id,
            "can_confirm": False, "drafts": self.drafts,
            "last_commit": self.last_commit, "feedback": self.feedback, "error": None,
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
        self.state = "STOPPED"
        self.receipt = None
        self.capture_id = None
        self.preview_id = None
        self.target_id = None
        self.active_stream_id = None
        self.feedback = "Controller paused or disconnected. A new Start will be required when workflow is implemented."

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
            self.active_stream_id = stream_id
            return changed, None
        return False, ("not_implemented", "This event belongs to a later workflow task; no draft was changed.")

    async def error(self, client, code, message):
        await client.send({"v": 1, "type": "ERROR", "run_id": self.run_id, "error": code, "message": message})
