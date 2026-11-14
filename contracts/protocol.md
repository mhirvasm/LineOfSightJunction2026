# LineOfSight demo protocol v1 - streamlined task pack v2

This replaces the provisional protocol in the first planning report. It describes a local hackathon demo, not a production service. Read this file before any task. Agent B owns contract changes.

## Scope

- One wearer, one native phone app, one Python hub process, two receiving pages.
- No database, auth framework, TLS certificates, general OS clipboard, third-party app injection, or background task queue service.
- Plain HTTP/WS on a controlled private network using synthetic receipt data.
- Query parameters identify routes/roles; they do not authenticate callers.
- Hub memory is authoritative. Browser fields are read-only. A restart loses the run intentionally.
- Serve the built React app and API from the same origin on port 8000. During development, proxy /v1 and /health from the frontend dev server if needed.

## Target configuration

| target_id | Route | ArUco dictionary | Marker ID | Adapter |
| --- | --- | --- | --- | --- |
| expenses | /expense | DICT_4X4_50 | 10 | Read-only expense draft |
| json | /json | DICT_4X4_50 | 20 | Plain-text JSON viewer |

Generate the two marker PNGs with OpenCV. Do not style/crop their internal pattern. Put each in a large central tile with its destination name and a light outer margin. Do not put both IDs in the same physical target tile.

## Identifiers: only those needed for the demo

- `run_id`: random hub-issued UUID at process start or explicit Reset. All requests after connection carry it. A mismatched value is rejected without mutation.
- `stream_id`: random phone-issued UUID when a camera stream starts. `frame_seq` increases within that stream. The hub binds the currently active stream to the active mobile connection; it rejects previous-stream uploads after a replacement is established.
- `capture_id`: phone-issued UUID for one frozen receipt image. Duplicate upload of the same capture_id must not invoke the model again. Never reuse it for a different image.
- `preview_id`: hub-issued UUID that binds the current capture, selected target, and validated record. It does not change for repeated observations of the same unchanged target.
- `commit_id`: exactly the preview_id being confirmed. Use a set of applied commit IDs to deduplicate within this run. No cross-restart guarantee.

Keep capture/commit deduplication records for the demo run. If a small cap such as 1000 operations is reached, require an explicit Reset; do not silently evict records while accepting retries.

## ReceiptRecord

```json
{
  "merchant": "Demo Cafe",
  "date": "2026-11-14",
  "total_minor": 2480,
  "currency": "EUR",
  "tax_minor": null,
  "needs_review": []
}
```

`merchant` and `date` may be null during review, but both must be valid for confirmation. `currency` must be EUR; `total_minor` must be a nonnegative integer, not a boolean or silently truncated float. A missing tax value is null and is NOT a blocking review reason. `needs_review` lists ambiguous/missing required fields. There is no correction editor in scope: recapture instead. Display the amount before confirmation; schema validity does not prove the model read it correctly.

Only the extraction module produces this record; it never chooses a target or invokes an action. Escape receipt strings in the UI. Do not execute generated code/SQL. Use the same canonical fields for both destinations.

## Endpoints

### GET /health

Returns `{ "v": 1, "ok": true, "run_id": "..." }`.

### WS /v1/events

Clients use one of:

```text
/v1/events?role=mobile
/v1/events?role=target&id=expenses
/v1/events?role=target&id=json
/v1/events?role=operator
```

Allow only known role/target labels. One active mobile connection and one active connection per target; reject duplicates with a visible error. Remove the binding when that exact socket closes, not when an obsolete socket cleanup happens. The operator is read-only except for an explicit demo Reset control. Mobile is the normal control source. A fixture control harness may simulate mobile events only in clearly labeled fixture mode.

Send a full SNAPSHOT immediately on connection. Reconnecting clients render the current snapshot; they do not replay queued user actions. Operator Reset creates a new run_id, invalidates in-flight work, clears all drafts and IDs, and broadcasts a fresh snapshot.

### POST /v1/frames

Multipart form fields: `run_id`, `stream_id`, `frame_seq` (integer), `age_ms` (nonnegative local time from frame delivery to sending), and `image` (JPEG bytes). The active phone announces its stream_id over the socket using STREAM_STARTED before uploading frames. Only that stream is accepted.

Preserve aspect ratio and normalize orientation once. Start near 5 uploads/second, with one request in flight and at most one pending latest frame. Use a request timeout; never accumulate an upload queue. Suggested starting limits: 2 MB per frame and 4 megapixels after decode. These are configurable demo limits, not device specifications.

The hub records its own receive time. Reject out-of-order sequences and obviously old sender age; start with age_ms <= 300. Do not compare phone and server monotonic clocks. Local age plus receive age does not guarantee true sensor exposure time or bound every network delay: test visible lag on the actual network. Stop confirming if the stream visibly falls behind.

Vision runs in bounded background work. Results carry stream_id and frame_seq; stale results cannot replace a newer target observation. An old worker finishing after Reset cannot change the new run.

### POST /v1/captures

Multipart fields: `run_id`, `capture_id`, `age_ms`, and `image` (JPEG bytes). The phone freezes/copies the exact frame at the Capture callback, before any async upload. Capture is allowed in READY or APPLIED. A fresh grab preserves both drafts and the Undo slot until another successful apply. Limit concurrent extraction to one. Apply the same bounded size/decode checks as frames.

Store the capture_id as accepted BEFORE starting extraction. A duplicate upload returns accepted/current status without another model call; a different capture_id while READING returns busy. Reject a reused capture_id with different image bytes. Return a clear response such as `{ "accepted": true, "capture_id": "..." }`; completion arrives in SNAPSHOT.

Do not select the hub's newest streaming frame as a substitute. Do not silently use fixture data if this request fails.

## Client events

All socket events contain `v:1`, `type`, and `run_id`.

```json
{"v":1,"type":"ACTION","run_id":"r1","action":"CONFIRM","preview_id":"p1"}
```

Actions: START, CONFIRM, CANCEL, STOP, SEND_AGAIN, UNDO. Capture is the HTTP upload, not a second ACTION. START begins a new active interaction after STOPPED. SEND_AGAIN reuses the last validated receipt after APPLIED and requires a new target preview/confirmation. The native button callback sends the action and preview_id shown when that button was rendered, not whichever action the app happens to consider current later.

Operator Reset uses `{ "v": 1, "type": "RESET", "run_id": "r1" }`. This is the only operator mutation and must be an explicit button press. It clears the demo rather than acting as a recovery algorithm.

```json
{"v":1,"type":"STREAM_STARTED","run_id":"r1","stream_id":"s1"}
```

```json
{"v":1,"type":"DEVICE_PAUSED","run_id":"r1","reason":"glasses_removed"}
```

On DEVICE_PAUSED or mobile disconnect, invalidate capture/preview, clear target lock, and enter STOPPED. Applied drafts remain. Require Start after reconnect. If disconnected locally, the phone disables actions immediately rather than waiting for hub detection.

```json
{"v":1,"type":"DISPLAYED","run_id":"r1","target_id":"expenses","commit_id":"p1"}
```

Accept DISPLAYED only from that target's current socket and only for the matching last commit. It changes feedback, not the draft. This is a software render acknowledgement, not proof a human saw it. A hidden tab should not report a new displayed result until visible.

## Server snapshot

```json
{
  "v": 1,
  "type": "SNAPSHOT",
  "run_id": "r1",
  "state": "PREVIEW",
  "source_mode": "live",
  "capture_id": "c1",
  "receipt": {"merchant":"Demo Cafe","date":"2026-11-14","total_minor":2480,"currency":"EUR","tax_minor":null,"needs_review":[]},
  "target_id": "expenses",
  "preview_id": "p1",
  "can_confirm": true,
  "drafts": {"expenses": null, "json": null},
  "last_commit": null,
  "feedback": "Expenses / EUR 24.80 / Confirm",
  "error": null
}
```

`last_commit`, when present, contains `commit_id`, `target_id`, and `display_status` (`waiting`, `displayed`, or `not_confirmed`). Broadcast on meaningful changes, not every identical camera observation. A late DISPLAYED for an earlier commit never changes feedback for a later commit.

## State rules

| State | Allowed main behavior |
| --- | --- |
| STOPPED | START; camera locally stopped/paused. Applied drafts remain until Reset. |
| READY | Capture upload, CANCEL/STOP. A capture cannot confirm anything. |
| READING | CANCEL/STOP; ignore new captures and confirms. |
| HOLDING | Select a connected target using fresh vision; CANCEL/STOP. |
| PREVIEW | CONFIRM for exact preview_id, CANCEL/STOP. Loss/change of target invalidates preview. |
| APPLIED | New capture, SEND_AGAIN, UNDO, CANCEL/STOP. A repeated old CONFIRM is a no-op. |

Extraction success enters HOLDING only if run_id/capture_id are still active. Failure or invalid required fields returns READY with a recapture message. CANCEL invalidates the receipt/preview and returns READY during an active camera session; STOP enters STOPPED. Neither reverses an applied draft. A new START clears the active receipt/preview but does not erase either destination's previous draft.

Target acquisition starts around 350 ms stable observation in a central region; expire around 600 ms after the last usable observation. Reject ambiguous/unknown targets. A fresh observation is needed at CONFIRM. These are adjustable starting points. There is no eye tracking, secure physical-device recognition, or guarantee of zero false selections.

## Applying and Undo

The hub is the only writer. CONFIRM first checks the current run. If its preview_id is an already-applied commit_id, return an already-applied result without changing the current state or feedback, even if a newer operation now exists. Otherwise check state, current preview_id, required fields, target freshness, and target connection. Then, without an await between check and mutation:

1. Recheck that commit_id has not already been applied if a lock was needed between earlier validation and mutation.
2. Deep-copy the selected draft into one global previous-draft slot with its target ID.
3. Replace only that target's draft with a copy of the canonical record.
4. Record commit_id, invalidate the actionable preview, enter APPLIED.

Broadcast afterward. Feedback starts as `Sent; waiting for screen`. After a matching DISPLAYED, say `Shown on Expenses/JSON`. After a short timeout or target disconnect, say `Draft updated; screen not confirmed`. Do not retry the mutation. Reconnecting targets receive the current snapshot and may acknowledge it.

UNDO is available in READY/APPLIED. It restores the previous-draft slot once, clears that slot, invalidates the current capture/preview/last-commit feedback, and returns to READY. There is no manual form editing and no conflict resolution. SEND_AGAIN creates a new preview_id even for the same target. It must never reuse the prior commit_id.

Duplicate checks, draft mutation, and state transition run in one event-loop turn or under one hub lock. Do not await image/model work while holding that lock. Run one server worker. Keep slow work outside the event loop; completion returns tagged data to the workflow.

## Minimal checks before demo

Wrong frame at capture; duplicate confirmation; stale target preview; repeated unchanged observations; late extraction after Cancel; missing tax; target refresh; server restart; target disconnect after send; Stop after Apply; slow provider; real receipt readability. See B5 and the revised PDF for exact expected outcomes.

## Privacy/demo constraints

Use synthetic receipts and a consenting wearer. Do not log camera images or provider keys. Release active image buffers after extraction/cancel/stop. Cloud extraction sends the selected image to the configured provider; make that boundary clear. Final receipt data remains in demo memory until Reset/restart. No public deployment claim is made.


## Hold/drag build clarification (issues #8-#12)

CANCEL carries capture_id. It records a cancellation even if that capture upload
has not arrived yet. A cancel for an old capture cannot cancel a newer one. A
release after APPLIED never undoes a draft. Clients include capture_id with
CONFIRM to let a failed freshness check cancel only that same interaction.
Capture cancellation records and image digests remain bounded for the run; images
do not. Only accepted capture IDs invoke extraction, at most once.

The band mapping is DOWN -> freeze, fresh rightward MOVE after HOLDING/PREVIEW ->
confirm exact preview (or CANCEL if no destination), UP before commit -> CANCEL.
Rebase displacement on readiness or preview/target change. Pre-ready movement is
never queued. Ignore movement after send/cancel until release. No target while
looking between screens is allowed; an attempted paste without a target cancels.

Snapshots add extraction_provider (gemini/openai). source_mode remains fixture/live.
LOS_EXTRACTION_MODE explicitly selects the mode; LOS_EXTRACTION_PROVIDER selects
one provider. There is no provider or fixture fallback. scripts/run_hub.py loads
only recognized keys from ignored .env without printing them.
