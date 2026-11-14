"""Actual HTTP JPEG uploads and shared WebSocket marker results."""

import asyncio
import json
from pathlib import Path
import socket
import sys
from uuid import uuid4

import httpx
from websockets.asyncio.client import connect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_hub_server import receive_until, start, stop
from scripts.verify_vision import camera_frame


async def exercise(port):
    origin = f"http://127.0.0.1:{port}"
    address = f"ws://127.0.0.1:{port}/v1/events"
    async with connect(address + "?role=target&id=expenses") as expenses, \
            connect(address + "?role=target&id=json") as json_target, \
            connect(address + "?role=mobile") as mobile, \
            connect(address + "?role=operator") as operator, \
            httpx.AsyncClient(base_url=origin, timeout=5, trust_env=False) as http:
        current = await receive_until(mobile, lambda value: value["type"] == "SNAPSHOT")
        run_id = current["run_id"]
        await mobile.send(json.dumps({"v": 1, "type": "ACTION", "action": "START", "run_id": run_id}))
        await receive_until(mobile, lambda value: value["type"] == "SNAPSHOT" and value["state"] == "READY")
        stream = str(uuid4())
        await mobile.send(json.dumps({"v": 1, "type": "STREAM_STARTED", "run_id": run_id, "stream_id": stream, "input_source": "fixture_frames"}))
        await receive_until(mobile, lambda value: value["type"] == "SNAPSHOT" and value["vision"]["stream_id"] == stream)
        fields = {"run_id": run_id, "stream_id": stream, "age_ms": "0"}
        async def upload(sequence, pixels):
            response = await http.post("/v1/frames", data=fields | {"frame_seq": str(sequence)}, files={"image": ("synthetic-test-frame.jpg", pixels, "image/jpeg")})
            assert response.status_code == 202, response.text
        for sequence in range(1, 5):
            await upload(sequence, camera_frame())
            await asyncio.sleep(.14)
        for client in (mobile, operator, expenses, json_target):
            locked = await receive_until(client, lambda value: value["type"] == "SNAPSHOT" and value["vision"]["locked_target_id"] == "expenses")
            assert locked["target_id"] == "expenses"
            assert locked["can_confirm"] is False
            assert locked["drafts"] == {"expenses": None, "json": None}
        await upload(5, camera_frame(((20, 360, 240),)))
        switched = await receive_until(operator, lambda value: value["type"] == "SNAPSHOT" and value["vision"]["detected_target_id"] == "json")
        assert switched["target_id"] is None
        await upload(6, camera_frame(((10, 200, 240), (20, 540, 240))))
        ambiguous = await receive_until(operator, lambda value: value["type"] == "SNAPSHOT" and "Ambiguous" in value["vision"]["message"])
        assert ambiguous["target_id"] is None
        await mobile.send(json.dumps({"v": 1, "type": "ACTION", "action": "STOP", "run_id": run_id}))
        stopped = await receive_until(operator, lambda value: value["type"] == "SNAPSHOT" and value["state"] == "STOPPED")
        assert stopped["vision"]["detected_target_id"] is None
        assert stopped["target_id"] is None


def main():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    (ROOT / "tmp").mkdir(exist_ok=True)
    with (ROOT / "tmp/b2-server-smoke.log").open("w", encoding="utf-8") as log:
        process, _ = start(port, log)
        try:
            asyncio.run(exercise(port))
        finally:
            stop(process)
    print("PASS: real HTTP JPEG pixels produce shared stable marker selection, target switching, ambiguity rejection, and Stop clearing, without draft writes.")


if __name__ == "__main__":
    main()
