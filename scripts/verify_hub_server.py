"""Exercise real HTTP/WebSockets against an isolated Uvicorn process."""

import asyncio
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

from websockets.asyncio.client import connect

ROOT = Path(__file__).resolve().parents[1]


async def receive_until(connection, predicate, timeout=5):
    async with asyncio.timeout(timeout):
        while True:
            message = json.loads(await connection.recv())
            if predicate(message):
                return message


async def exercise(port):
    address = f"ws://127.0.0.1:{port}/v1/events"
    async with connect(address + "?role=target&id=expenses") as expenses, \
            connect(address + "?role=target&id=json") as json_target, \
            connect(address + "?role=mobile") as mobile, \
            connect(address + "?role=operator") as operator:
        ready = lambda value: value["type"] == "SNAPSHOT" and value["connections"] == {
            "mobile": True, "targets": {"expenses": True, "json": True, "text": False}, "operators": 1}
        sockets = [expenses, json_target, mobile, operator]
        values = await asyncio.gather(*(receive_until(client, ready) for client in sockets))
        assert len({value["run_id"] for value in values}) == 1
        initial = values[0]["run_id"]
        async with connect(address + "?role=target&id=json") as duplicate:
            error = json.loads(await duplicate.recv())
            assert error["error"] == "connection_rejected"
        await operator.send(json.dumps({"v": 1, "type": "RESET", "run_id": initial}))
        reset = await asyncio.gather(*(receive_until(client, lambda value: value["type"] == "SNAPSHOT" and value["run_id"] != initial) for client in sockets))
        assert len({value["run_id"] for value in reset}) == 1
        assert all(value["drafts"] == {"expenses": None, "json": None, "text": None} for value in reset)
        new_run = reset[0]["run_id"]
        await operator.send(json.dumps({"v": 1, "type": "RESET", "run_id": initial}))
        error = await receive_until(operator, lambda value: value["type"] == "ERROR")
        assert error["error"] == "stale_run"
        await mobile.close()
        disconnected = await receive_until(operator, lambda value: value["type"] == "SNAPSHOT" and not value["connections"]["mobile"])
        assert disconnected["state"] == "STOPPED"
        assert disconnected["run_id"] == new_run
        return new_run


def start(port, log):
    process = subprocess.Popen([sys.executable, "-m", "uvicorn", "services.hub.app:app", "--host", "127.0.0.1", "--port", str(port)], cwd=ROOT, stdout=log, stderr=log)
    for _ in range(80):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=.3) as response:
                return process, json.load(response)["run_id"]
        except OSError:
            if process.poll() is not None:
                raise RuntimeError("Uvicorn stopped; inspect tmp/b1-server-smoke.log")
            time.sleep(.1)
    stop(process)
    raise RuntimeError("Uvicorn did not become ready")


def stop(process):
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    (ROOT / "tmp").mkdir(exist_ok=True)
    with (ROOT / "tmp/b1-server-smoke.log").open("w", encoding="utf-8") as log:
        process, _ = start(port, log)
        try:
            reset_run = asyncio.run(exercise(port))
        finally:
            stop(process)
        process, restarted_run = start(port, log)
        try:
            assert restarted_run != reset_run
            async def check_empty():
                async with connect(f"ws://127.0.0.1:{port}/v1/events?role=operator") as operator:
                    current = json.loads(await asyncio.wait_for(operator.recv(), timeout=5))
                    assert current["drafts"] == {"expenses": None, "json": None, "text": None}
                    assert current["connections"]["mobile"] is False
            asyncio.run(check_empty())
        finally:
            stop(process)
    print("PASS: real Uvicorn clients share a run; Reset broadcasts; duplicates and stale events reject; disconnect and restart clear transient state.")


if __name__ == "__main__":
    main()
