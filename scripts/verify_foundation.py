"""Verify the real foundation, generated markers, and protocol fixture invariants."""

import json
from pathlib import Path
import sys
import unittest
from uuid import UUID

import cv2
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from services.hub.app import create_app


class FoundationChecks(unittest.TestCase):
    def test_health_is_stable_and_new_lifespan_gets_new_run(self):
        application = create_app()
        with TestClient(application) as client:
            first = client.get("/health").json()
            self.assertEqual(first, client.get("/health").json())
            self.assertEqual(first["v"], 1)
            self.assertIs(first["ok"], True)
            UUID(first["run_id"])
            self.assertEqual(application.state.drafts, {"expenses": None, "json": None})
        with TestClient(application) as client:
            self.assertNotEqual(first["run_id"], client.get("/health").json()["run_id"])

    def test_both_routes_assets_and_fixtures_are_served(self):
        with TestClient(create_app()) as client:
            for route in ["/expense", "/json"]:
                response = client.get(route)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertIn('<div id="root">', response.text)
            index = client.get("/expense").text
            import re
            for asset in re.findall(r'(?:src|href)="(/assets/[^\"]+)"', index):
                self.assertEqual(client.get(asset).status_code, 200, asset)
            for marker_id in (10, 20):
                response = client.get(f"/markers/aruco-{marker_id}.png")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers["content-type"], "image/png")
            self.assertEqual(client.get("/fixtures/snapshots.json").status_code, 200)
            self.assertEqual(client.get("/v1/not-implemented").status_code, 404)
            self.assertEqual(client.get("/unknown-page").status_code, 404)

    def test_markers_decode_as_exact_target_ids(self):
        targets = json.loads((ROOT / "contracts/targets.json").read_text())
        dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        detector = cv2.aruco.ArucoDetector(dictionary)
        for target_id, marker_id, route in [("expenses", 10, "/expense"), ("json", 20, "/json")]:
            target = targets[target_id]
            self.assertEqual((target["route"], target["marker_id"], target["dictionary"]),
                             (route, marker_id, "DICT_4X4_50"))
            image = cv2.imread(str(ROOT / "apps/web/public" / target["marker_asset"].lstrip("/")), 0)
            self.assertIsNotNone(image)
            self.assertEqual(image.shape, (600, 600))
            self.assertTrue((image[:60] == 255).all())
            _, detected, _ = detector.detectMarkers(image)
            self.assertIsNotNone(detected)
            self.assertEqual(detected.flatten().tolist(), [marker_id])

    def test_fixtures_cover_all_states_without_target_or_field_drift(self):
        fixture_dir = ROOT / "fixtures"
        receipt = json.loads((fixture_dir / "receipt_expected.json").read_text())
        original = ROOT / "lineofsight/LineOfSight_Starter_v2"
        self.assertEqual(receipt, json.loads((original / "fixtures/receipt_expected.json").read_text()))
        self.assertEqual((ROOT / "contracts/protocol.md").read_bytes(), (original / "contracts/protocol.md").read_bytes())
        self.assertEqual(receipt["total_minor"], 2480)
        self.assertIsNone(receipt["tax_minor"])
        self.assertEqual(receipt["needs_review"], [])
        snapshots = json.loads((fixture_dir / "snapshots.json").read_text())
        self.assertEqual({s["state"] for s in snapshots.values()},
                         {"STOPPED", "READY", "READING", "HOLDING", "PREVIEW", "APPLIED"})
        for snapshot in snapshots.values():
            self.assertEqual(snapshot["source_mode"], "fixture")
            self.assertEqual(snapshot["type"], "SNAPSHOT")
            if snapshot["can_confirm"]:
                self.assertEqual(snapshot["state"], "PREVIEW")
                self.assertEqual(snapshot["receipt"], receipt)
                self.assertIsNotNone(snapshot["preview_id"])
                self.assertEqual(snapshot["drafts"], {"expenses": None, "json": None})
        self.assertNotEqual(snapshots["PREVIEW_expenses"]["preview_id"], snapshots["PREVIEW_json"]["preview_id"])
        self.assertEqual(snapshots["APPLIED"]["drafts"], {"expenses": None, "json": receipt})
        invalid = json.loads((fixture_dir / "receipt_invalid.json").read_text())
        self.assertIn("total_minor", invalid["needs_review"])
        self.assertNotIn("tax_minor", invalid["needs_review"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
