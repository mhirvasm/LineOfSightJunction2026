"""Serialized receipt transitions; asynchronous reading cannot revive old captures."""

import asyncio
from copy import deepcopy
from hashlib import sha256
from time import monotonic
from uuid import UUID, uuid4

import httpx

from .extraction.receipt import ProviderError
from .extraction.content import ContentReader, validate_content
from .extraction.analysis import TextAnalyzer, validate_analysis
from .vision.service import FrameRejected


class ReceiptWorkflow:
    def __init__(self, hub, reader=None, analyzer=None):
        self.hub = hub
        self.reader = reader or ContentReader()
        self.analyzer = analyzer or TextAnalyzer(mode=self.reader.mode, provider=self.reader.provider)
        self.task = None
        self.pending = set()
        self.sent_at = None

    def invalidate(self):
        if self.task:
            self.task.cancel()
            self.task = None

    async def close(self):
        self.invalidate()
        await asyncio.gather(*self.pending, return_exceptions=True)

    def clear(self, message="Canceled. Hold to capture again."):
        self.invalidate()
        h = self.hub
        h.capture_id = h.receipt = h.text = h.preview_id = None
        h.raw_text = h.summary = None
        h.text_status = "raw"
        h.interaction_kind = "content"
        h.coffee_desired = None
        if h.state != "STOPPED":
            h.state = "READY"
        h.feedback = message

    def fresh_target(self):
        h = self.hub
        vision = getattr(h, "vision", None)
        if not vision:
            return None
        vision.tracker.expire(monotonic())
        target = vision.tracker.locked_id
        return target if target and f"target:{target}" in h.clients else None

    def refresh(self):
        h = self.hub
        target = self.fresh_target()
        before = (h.state, h.preview_id, h.feedback, h.target_id)
        changed_target = target != h.target_id
        h.target_id = target
        if changed_target:
            h.preview_id = None
        if h.state in {"HOLDING", "PREVIEW"}:
            if not target:
                h.preview_id = None
                h.state = "HOLDING"
                h.feedback = "Held. Look at a screen; release to cancel."
            elif h.interaction_kind == "coffee" and target != "coffee":
                h.preview_id = None
                h.state = "HOLDING"
                h.feedback = "Coffee selected. Aim at its marker; release to cancel."
            elif h.interaction_kind != "coffee" and target == "coffee":
                h.preview_id = None
                h.state = "HOLDING"
                h.feedback = "Text cannot control Coffee. Release, then hold while aiming at Coffee."
            elif target == "expenses" and not h.receipt:
                h.preview_id = None
                h.state = "HOLDING"
                h.feedback = "Expenses needs a readable EUR receipt. Aim at Text or JSON; release to cancel."
            else:
                if changed_target or not h.preview_id:
                    h.preview_id = str(uuid4())
                h.state = "PREVIEW"
                if h.interaction_kind == "coffee":
                    h.feedback = f"Coffee / turn {'on' if h.coffee_desired else 'off'} / drag right to confirm"
                else:
                    summary = f"EUR {h.receipt['total_minor'] / 100:.2f}" if h.receipt and target != "text" else f"{len(h.text)} characters"
                    h.feedback = f"{target.title()} / {summary} / drag right to send"
            if h.text_status == "unavailable":
                h.feedback = "Cleanup unavailable; original text. " + h.feedback
        if h.last_commit and h.last_commit["display_status"] == "waiting":
            if (self.sent_at is not None and monotonic() - self.sent_at > 3) or f"target:{h.last_commit['target_id']}" not in h.clients:
                h.last_commit["display_status"] = "not_confirmed"
                if h.state == "APPLIED":
                    h.feedback = "Draft updated; screen not confirmed."
        return before != (h.state, h.preview_id, h.feedback, h.target_id)

    def accept(self, run, capture, age, image, owner):
        h = self.hub
        if run != h.run_id or owner is None or h.clients.get("mobile") is not owner:
            raise FrameRejected("Old run or phone connection.")
        try:
            UUID(capture)
        except (ValueError, TypeError, AttributeError):
            raise FrameRejected("capture_id must be a UUID.", 422)
        if not 0 <= age <= 300:
            raise FrameRejected("Capture age must be 0..300 ms.", 422)
        digest = sha256(image).hexdigest()
        previous = h.capture_records.get(capture)
        if previous:
            if previous["status"] == "canceled":
                raise FrameRejected("Capture canceled.")
            if previous["digest"] != digest:
                raise FrameRejected("Capture ID reused with different image bytes.")
            return
        if len(h.capture_records) >= 1000:
            raise FrameRejected("Capture limit reached. Reset explicitly.")
        if h.state not in {"READY", "APPLIED"} or not h.active_stream_id:
            raise FrameRejected("Finish or cancel the current capture first.")
        h.capture_records[capture] = {"digest": digest, "status": "reading"}
        h.capture_id, h.receipt, h.text, h.preview_id = capture, None, None, None
        h.raw_text = h.summary = None
        h.text_status = "raw"
        h.interaction_kind = "content"
        h.coffee_desired = None
        h.state, h.feedback = "READING", "Reading text. Keep holding; release to cancel."
        self.task = asyncio.create_task(self.read(run, capture, image, owner))
        self.pending.add(self.task)
        self.task.add_done_callback(self.pending.discard)

    async def read(self, run, capture, image, owner):
        h = self.hub
        try:
            record = validate_content(await asyncio.wait_for(self.reader(image), 25))
            failure = None
        except asyncio.CancelledError:
            return
        except ProviderError as error:
            record, failure = None, str(error)
        except (TimeoutError, httpx.TimeoutException):
            record, failure = None, "Text reading timed out. Check the hub internet connection, then capture again."
        except Exception:
            record, failure = None, "Could not read text. Capture a shorter, clearer block and check live configuration."
        if run != h.run_id or h.capture_id != capture or h.clients.get("mobile") is not owner or h.state != "READING":
            return
        if failure:
            self.task = None
            h.capture_records[capture]["status"] = "failed"
            self.clear(failure)
        else:
            h.receipt = record["receipt"]
            h.text = h.raw_text = record["text"]
            if h.receipt is None:
                h.text_status = "processing"
                h.feedback = "Text read. Correcting grammar and summarizing; keep holding."
                await h.broadcast()
                try:
                    analysis = validate_analysis(await asyncio.wait_for(self.analyzer(record["text"]), 25), record["text"])
                except asyncio.CancelledError:
                    return
                except Exception:
                    analysis = None
                if run != h.run_id or h.capture_id != capture or h.clients.get("mobile") is not owner or h.state != "READING":
                    return
                if analysis:
                    h.text, h.summary = analysis["corrected_text"], analysis["summary"]
                    h.text_status = "ready"
                else:
                    h.text_status = "unavailable"
            self.task = None
            h.capture_records[capture]["status"] = "read"
            h.state = "HOLDING"
            self.refresh()
        await h.broadcast()

    def event(self, client, event):
        h = self.hub
        if event["type"] == "DISPLAYED":
            last = h.last_commit
            if last and client.key == f"target:{last['target_id']}" and event.get("target_id") == last["target_id"] and event.get("commit_id") == last["commit_id"]:
                if last["display_status"] == "displayed":
                    return False, None
                last["display_status"] = "displayed"
                if h.state == "APPLIED":
                    h.feedback = f"Shown on {last['target_id'].title()}"
                return True, None
            return False, None
        if client.role != "mobile":
            return False, ("forbidden", "Only the active phone can change captures.")
        action = event.get("action")
        if action == "SELECT_COFFEE":
            capture = event.get("capture_id")
            try:
                UUID(capture)
            except (ValueError, TypeError, AttributeError):
                return False, ("invalid_capture", "Coffee selection requires a new interaction UUID.")
            previous = h.capture_records.get(capture)
            if previous:
                if previous.get("digest") == "coffee" and previous.get("status") != "canceled":
                    return False, None
                return False, ("invalid_capture", "Interaction already used or canceled.")
            if len(h.capture_records) >= 1000:
                return False, ("capacity", "Reset explicitly before more selections.")
            if h.state not in {"READY", "APPLIED"} or not h.active_stream_id or self.fresh_target() != "coffee":
                return False, ("unavailable", "Aim at a connected Coffee marker before holding.")
            self.clear()
            h.capture_records[capture] = {"digest": "coffee", "status": "selected"}
            h.capture_id, h.interaction_kind = capture, "coffee"
            h.coffee_desired = not h.coffee_on
            h.state = "HOLDING"
            self.refresh()
            return True, None
        if action == "CANCEL":
            capture = event.get("capture_id")
            try:
                UUID(capture)
            except (ValueError, TypeError, AttributeError):
                return False, ("invalid_capture", "Cancel requires its capture_id.")
            if capture not in h.capture_records and len(h.capture_records) >= 1000:
                return False, ("capacity", "Reset explicitly before more captures.")
            h.capture_records.setdefault(capture, {"digest": None})["status"] = "canceled"
            if capture == h.capture_id and h.state != "APPLIED":
                self.clear()
            return True, None
        if action == "CONFIRM":
            preview = event.get("preview_id")
            if not isinstance(preview, str):
                return False, ("invalid_preview", "Confirm requires preview_id.")
            if preview in h.applied_commit_ids:
                return False, None
            old_preview = h.preview_id
            self.refresh()
            if h.state != "PREVIEW" or preview != h.preview_id or (not h.text and h.interaction_kind != "coffee") or not h.target_id:
                if event.get("capture_id") == h.capture_id or preview == old_preview:
                    self.clear("Canceled: destination or preview expired.")
                    return True, None
                return False, ("stale_preview", "Preview expired. No draft changed.")
            if len(h.applied_commit_ids) >= 1000:
                return False, ("capacity", "Reset explicitly before more transfers.")
            target = h.target_id
            if h.interaction_kind == "coffee":
                h.previous_draft = ("coffee", h.coffee_on)
                h.coffee_on = h.coffee_desired
            else:
                h.previous_draft = (target, deepcopy(h.drafts[target]))
                h.drafts[target] = deepcopy(h.receipt) if target != "text" and h.receipt else {
                    "text": h.text, "raw_text": h.raw_text, "summary": h.summary, "text_status": h.text_status,
                }
            h.applied_commit_ids.add(preview)
            h.last_commit = {"commit_id": preview, "target_id": target, "display_status": "waiting"}
            self.sent_at = monotonic()
            h.preview_id, h.state = None, "APPLIED"
            h.feedback = "Sent; waiting for screen."
            return True, None
        if action == "UNDO" and h.previous_draft is not None and h.state in {"READY", "APPLIED"}:
            target, record = h.previous_draft
            if target == "coffee":
                h.coffee_on = record
            else:
                h.drafts[target] = record
            h.previous_draft = h.last_commit = None
            self.clear("Previous coffee state restored." if target == "coffee" else "Previous draft restored. Hold to capture again.")
            return True, None
        if action == "SEND_AGAIN" and h.state == "APPLIED" and h.text:
            h.state, h.preview_id = "HOLDING", None
            self.refresh()
            return True, None
        return False, ("invalid_action", "Action is unavailable in this state.")
