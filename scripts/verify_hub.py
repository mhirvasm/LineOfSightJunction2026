"""B1 socket ownership, reset, input guards, and disconnect checks."""

from contextlib import ExitStack
from pathlib import Path
import sys
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.hub.app import create_app
from services.hub.connections import Hub


def until(socket, predicate):
    for _ in range(30):
        message = socket.receive_json()
        if predicate(message):
            return message
    raise AssertionError("Expected socket message did not arrive")


def snapshot(socket, predicate=lambda value: True):
    return until(socket, lambda value: value["type"] == "SNAPSHOT" and predicate(value))


class HubChecks(unittest.TestCase):
    def test_three_clients_share_run_and_reset_broadcasts(self):
        application = create_app()
        with TestClient(application) as client, ExitStack() as stack:
            sockets = [stack.enter_context(client.websocket_connect(path)) for path in [
                "/v1/events?role=target&id=expenses", "/v1/events?role=target&id=json",
                "/v1/events?role=mobile", "/v1/events?role=operator",
            ]]
            complete = lambda value: value["connections"] == {
                "mobile": True, "targets": {"expenses": True, "json": True}, "operators": 1}
            initial = [snapshot(socket, complete) for socket in sockets]
            run_id = client.get("/health").json()["run_id"]
            self.assertEqual({item["run_id"] for item in initial}, {run_id})
            hub = application.state.hub
            hub.drafts["json"] = {"test": "previous applied record"}
            hub.capture_records["capture"] = "accepted"
            hub.applied_commit_ids.add("commit")
            hub.active_stream_id = str(uuid4())
            sockets[-1].send_json({"v": 1, "type": "RESET", "run_id": run_id})
            refreshed = [snapshot(socket, lambda value: value["run_id"] != run_id) for socket in sockets]
            self.assertEqual(len({item["run_id"] for item in refreshed}), 1)
            self.assertEqual(refreshed[0]["drafts"], {"expenses": None, "json": None})
            self.assertEqual(hub.capture_records, {})
            self.assertEqual(hub.applied_commit_ids, set())
            self.assertIsNone(hub.active_stream_id)
            self.assertEqual(client.get("/health").json()["run_id"], refreshed[0]["run_id"])

    def test_unknown_labels_and_duplicate_target_are_rejected(self):
        with TestClient(create_app()) as client:
            for path in ["?role=unknown", "?role=target&id=expense", "?role=operator&id=json"]:
                with client.websocket_connect("/v1/events" + path) as socket:
                    self.assertEqual(socket.receive_json()["error"], "connection_rejected")
            with client.websocket_connect("/v1/events?role=target&id=expenses") as original:
                first = snapshot(original)
                with client.websocket_connect("/v1/events?role=target&id=expenses") as duplicate:
                    self.assertIn("already active", duplicate.receive_json()["message"])
                original.send_json({"v": 1, "type": "RESET", "run_id": first["run_id"]})
                failure = until(original, lambda value: value["type"] == "ERROR")
                self.assertEqual(failure["error"], "forbidden")

    def test_duplicate_mobile_does_not_remove_original_binding(self):
        application = create_app()
        with TestClient(application) as client:
            with client.websocket_connect("/v1/events?role=mobile") as original:
                current = snapshot(original)
                with client.websocket_connect("/v1/events?role=mobile") as duplicate:
                    self.assertIn("already active", duplicate.receive_json()["message"])
                original.send_json({"v": 1, "type": "STREAM_STARTED", "run_id": current["run_id"], "stream_id": str(uuid4())})
                self.assertTrue(snapshot(original)["connections"]["mobile"])
            with client.websocket_connect("/v1/events?role=mobile") as replacement:
                self.assertTrue(snapshot(replacement)["connections"]["mobile"])

    def test_old_run_malformed_and_unsupported_inputs_do_not_mutate(self):
        with TestClient(create_app()) as client:
            with client.websocket_connect("/v1/events?role=operator") as operator:
                initial = snapshot(operator)
                bad = [({"v": 1, "type": "RESET", "run_id": "old-run"}, "stale_run"),
                       ({"v": True, "type": "RESET", "run_id": initial["run_id"]}, "invalid_event"),
                       ({"v": 1, "type": [], "run_id": initial["run_id"]}, "invalid_event"),
                       ({"v": 1, "type": "ACTION", "action": "CONFIRM", "run_id": initial["run_id"]}, "forbidden")]
                for event, code in bad:
                    operator.send_json(event)
                    self.assertEqual(operator.receive_json()["error"], code)
                    self.assertEqual(client.get("/health").json()["run_id"], initial["run_id"])
                for payload in ["not json", "[]", "null"]:
                    operator.send_text(payload)
                    self.assertEqual(operator.receive_json()["error"], "invalid_event")
                operator.send_bytes(b"binary")
                self.assertEqual(operator.receive_json()["error"], "invalid_event")

    def test_mobile_disconnect_clears_transient_state_and_preserves_drafts(self):
        application = create_app()
        with TestClient(application) as client:
            with client.websocket_connect("/v1/events?role=operator") as operator:
                snapshot(operator)
                with client.websocket_connect("/v1/events?role=mobile") as mobile:
                    snapshot(mobile)
                    snapshot(operator, lambda value: value["connections"]["mobile"])
                    hub = application.state.hub
                    hub.receipt = {"sample": True}
                    hub.capture_id = str(uuid4())
                    hub.preview_id = str(uuid4())
                    hub.target_id = "json"
                    hub.drafts["json"] = {"already": "applied"}
                stopped = snapshot(operator, lambda value: not value["connections"]["mobile"])
                self.assertEqual(stopped["state"], "STOPPED")
                for field in ("receipt", "capture_id", "preview_id", "target_id"):
                    self.assertIsNone(stopped[field])
                self.assertEqual(stopped["drafts"]["json"], {"already": "applied"})

    def test_stream_role_guards_and_identity_cleanup(self):
        hub = Hub()
        original, _ = hub.bind(object(), "mobile", None)
        self.assertTrue(hub.unbind(original))
        replacement, _ = hub.bind(object(), "mobile", None)
        self.assertFalse(hub.unbind(original))
        self.assertIs(hub.clients["mobile"], replacement)
        target, _ = hub.bind(object(), "target", "expenses")
        changed, error = hub.apply_event(target, {"v": 1, "type": "STREAM_STARTED", "run_id": hub.run_id, "stream_id": str(uuid4())})
        self.assertFalse(changed)
        self.assertEqual(error[0], "forbidden")
        changed, error = hub.apply_event(replacement, {"v": 1, "type": "STREAM_STARTED", "run_id": hub.run_id, "stream_id": []})
        self.assertFalse(changed)
        self.assertEqual(error[0], "invalid_stream")


if __name__ == "__main__":
    unittest.main(verbosity=2)
