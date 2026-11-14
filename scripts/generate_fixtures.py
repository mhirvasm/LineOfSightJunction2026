"""Create deterministic K0 snapshots for UI work without hardware."""

import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def generate():
    receipt = json.loads((ROOT / "fixtures/receipt_expected.json").read_text())
    targets = json.loads((ROOT / "contracts/targets.json").read_text())
    base = {
        "v": 1, "type": "SNAPSHOT", "run_id": "00000000-0000-4000-8000-000000000001",
        "state": "STOPPED", "source_mode": "fixture", "capture_id": None,
        "receipt": None, "text": None, "target_id": None, "preview_id": None, "can_confirm": False,
        "drafts": {"expenses": None, "json": None, "text": None}, "last_commit": None,
        "feedback": "Fixture example: stopped. Start is not connected yet.", "error": None,
    }
    snapshots = {"STOPPED": deepcopy(base)}
    for state, feedback in [
        ("READY", "Ready to capture a receipt."), ("READING", "Reading the frozen receipt image."),
        ("HOLDING", "Receipt ready. Look toward a destination."),
    ]:
        item = deepcopy(base)
        item.update(state=state, feedback=feedback)
        if state in {"READING", "HOLDING"}:
            item["capture_id"] = "00000000-0000-4000-8000-000000000002"
        if state == "HOLDING":
            item["receipt"] = deepcopy(receipt)
            item["text"] = json.loads((ROOT / "fixtures/receipt_capture.json").read_text())["text"]
        snapshots[state] = item
    for target_id, preview_id in [("expenses", "00000000-0000-4000-8000-000000000010"),
                                   ("json", "00000000-0000-4000-8000-000000000020")]:
        item = deepcopy(snapshots["HOLDING"])
        item.update(state="PREVIEW", target_id=target_id, preview_id=preview_id, can_confirm=True,
                    feedback=f"{targets[target_id]['label']} / EUR 24.80 / Confirm (fixture example only)")
        snapshots[f"PREVIEW_{target_id}"] = item
    text_preview = deepcopy(snapshots["HOLDING"])
    text_preview.update(state="PREVIEW", receipt=None,
                        text=json.loads((ROOT / "fixtures/text_capture.json").read_text(encoding="utf-8"))["text"],
                        target_id="text", preview_id="00000000-0000-4000-8000-000000000030",
                        can_confirm=True, feedback="Text / drag right to paste (fixture example only)")
    snapshots["PREVIEW_text"] = text_preview
    text_applied = deepcopy(text_preview)
    text_applied.update(state="APPLIED", preview_id=None, can_confirm=False,
                        last_commit={"commit_id": text_preview["preview_id"], "target_id": "text", "display_status": "displayed"},
                        feedback="Shown on Text (fixture example only).")
    text_applied["drafts"]["text"] = {"text": text_preview["text"]}
    snapshots["APPLIED_text"] = text_applied
    applied = deepcopy(snapshots["PREVIEW_json"])
    applied.update(state="APPLIED", preview_id=None, can_confirm=False,
                   last_commit={"commit_id": applied["preview_id"], "target_id": "json", "display_status": "displayed"},
                   feedback="Shown on JSON (fixture example only).")
    applied["drafts"]["json"] = deepcopy(receipt)
    snapshots["APPLIED"] = applied
    invalid = deepcopy(snapshots["READY"])
    invalid.update(feedback="Required fields unreadable. Recapture the receipt.", error="invalid_receipt")
    snapshots["INVALID_RECEIPT"] = invalid
    (ROOT / "fixtures/snapshots.json").write_text(json.dumps(snapshots, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    generate()
