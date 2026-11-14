# B2: marker recognition and phone-photo fallback

Issue: https://github.com/mhirvasm/LineOfSightJunction2026/issues/4.
Branch: `feat/b2-target-selection`.
Agent author: Codex. Responsible human: `mhirvasm`.
Dependency: B1, PR #3, merged into `chore/k0-bootstrap` at
`216801e23f51e94f627c733a7c8351372c99d96a`.

The human reported B1 working and explicitly requested its merge and
continuation. That specific instruction authorized execution of the B1
merge; the default human-review/merge policy remains in effect for later
work. B2 is prepared separately for review and must not be auto-merged.

## Result and ownership

OpenCV detects real JPEG pixels using DICT_4X4_50, with registered IDs 10
and 20. A marker's centre must lie in the central half of both image axes.
Multiple central markers or an unknown central ID are rejected. A known
marker without its receiving page connected is recognized for diagnostics
but is not selected. Stable acquisition starts at 350 ms, expiry at 600 ms.
Changing to a different candidate immediately clears the old lock.
Identical observations preserve the current target and preview identifier.

`/v1/frames` enforces the existing multipart protocol and current run/active
mobile/announced stream/increasing sequence guards. Sender delivery age is
0-300 ms. A JPEG is limited to 2,000,000 bytes and 4,000,000 decoded pixels.
The JPEG dimensions are checked before decoding. Known oversized HTTP
bodies are rejected before multipart parsing; only one file/four text
fields are accepted. The uploaded image is not written to project files or
logs. Background detection retains one in-flight frame and one replaceable
latest pending frame. Work tagged with an obsolete run, stream, generation,
or mobile socket cannot change current state. A processing result older
than the 300 ms starting bound is discarded with visible feedback.

The phone browser's `/fixture-mobile` page can now capture/choose an image,
normalize orientation, resize to a maximum 1280-pixel side, encode JPEG,
and upload it once. It displays the exact normalized JPEG sent. Reset,
disconnect, Stop, and unmount cancel local work and release preview URLs.
The page remains explicitly labeled as phone input, with no glasses claim.
It does not replay a still photo or implement a hidden fixture fallback.

This change touches hub/vision code, the frame endpoint and minimal camera
lifecycle, a phone photo component, marker status on the existing pages,
verification scripts, one pinned dependency, and the runbook. Native SDK
work, receipt capture/extraction, confirmation/transfers, Undo, and the
rest of B3/B4 are excluded.

## Protocol extensions and lifecycle

The original `contracts/protocol.md` is unchanged. The exact frame endpoint,
field names, IDs, and dictionary are preserved. The same existing ACTION
envelope now accepts mobile-only START/STOP for this camera test. START
enters READY from STOPPED without changing drafts. STOP clears transient
vision/stream state and preserves applied drafts. Other actions remain
unimplemented. This small lifecycle gate is needed for B2 uploads; it is
not the full receipt workflow.

STREAM_STARTED has an optional diagnostic `input_source` label:
`phone_photo`, `camera_stream`, `fixture_frames`, `native_camera`, or
`unspecified`. It is a caller declaration, not authentication or proof of
physical capture. The phone page uses `phone_photo`; automated tests use
`fixture_frames`. Snapshots add an optional `vision` object containing:

- `detected_target_id`: last image's recognized registered marker, retained
  after expiry for the still-photo diagnostic.
- `candidate_id`, `locked_target_id`: current fresh candidate/stable target.
- `marker_ids`, `frame_seq`, `frame_age_ms`: bounded diagnostic metadata.
- `message`, `stream_id`, `input_source`: readable status and current source.

Only the current stable lock is mirrored into `target_id`. It is never a
draft write and `can_confirm` remains false. Invalid/ambiguous observations,
expiry, receiving-screen loss, Reset, Stop, pause, stream replacement, and
mobile disconnect prevent stale target use. No unchanged camera observation
recreates a preview or triggers repeated identical broadcasts.

`source_mode` remains fixture because no live receipt extractor is connected.
Marker detection itself always inspects the uploaded pixels; it does not
invent the target from the input label or selected destination.

## Phone limitations

Plain HTTP on a remote phone generally cannot use `getUserMedia` live
streaming. The file input uses the phone's camera/photo-picker path without
TLS setup or browser-security bypasses. A single image proves recognition,
then expires; it cannot establish continuous fresh selection. Local age is
measured from browser-decoded frame delivery to sending, not true sensor
exposure, and an existing photo may be much older. The user is told this.

Actual phone/browser capture behavior, network reachability, image glare,
physical marker size, camera orientation, and glasses input remain human
checks. No native platform has been chosen. The human said glasses/band
access is still pending and requested phone testing first.

## Actual verification

Windows commands from the project root:

```powershell
.\.venv\Scripts\python.exe -m pip install python-multipart
.\.venv\Scripts\python.exe scripts/verify_vision.py
.\.venv\Scripts\python.exe scripts/verify_vision_server.py
.\.venv\Scripts\python.exe scripts/verify_foundation.py
.\.venv\Scripts\python.exe scripts/verify_hub.py
.\.venv\Scripts\python.exe scripts/verify_hub_server.py
.\.venv\Scripts\python.exe -m pip check
```

Bundled Node, assigned to `$nodePath` as in K0/B1, ran:

```powershell
& $nodePath apps/web/node_modules/vite/bin/vite.js build apps/web
& $nodePath --test apps/web/src/connection/socket.test.js
```

- Ten vision checks passed: exact JPEG pixel identities, centre filtering,
  ambiguity/unknown/blank rejection, pre-decode byte/pixel limits, stable
  acquisition/switch/expiry, sparse-photo non-locking, HTTP guardrails,
  connected-target requirement, bounded latest-frame work, old-worker Reset
  invalidation, unchanged preview preservation, and screen-loss clearing.
- The new real-server smoke test passed. HTTP multipart JPEG uploads led
  to shared stable selection, changed-target invalidation, ambiguity
  rejection, and Stop clearing across actual WebSocket clients, without
  any draft mutation.
- All four foundation checks, six hub checks, four JavaScript connection
  checks, the original real-server smoke test, frontend build, and pip check
  passed. The existing Starlette HTTPX deprecation warning is non-failing.
- `python-multipart==0.0.33` is the only new dependency in B2.
- Browser file uploads of explicitly synthetic Expenses and JSON JPEGs
  produced the correct last-recognized names on phone and operator pages.
  After operator Reset, the browser preview/result cleared and another
  photo worked in the new run with a new announced stream and sequence 1.
- The browser's JPEG preview showed the uploaded marker and centre guide.
  The phone tab had no observed warning/error logs. Its temporary test
  connection was closed afterward so a physical phone can connect.

These are software/synthetic-pixel checks, not a claim that an actual phone
camera, Mac, glasses, or Neural Band was tested. README contains the physical
phone instructions and expected one-photo expiry behavior. The working
server is left running on port 8000.

Next task after review and the phone marker check: B3, receipt/preview
workflow, with C3/C4 extraction work still required. A1 remains the separate
glasses camera/display/input concurrency gate.

## Hotspot connectivity follow-up

After switching to the Samsung Galaxy S23 hotspot, the laptop received a
new Wi-Fi address. The old address was no longer usable. Phone requests to
the new address still timed out while the server was running in the
restricted execution environment. Inspection confirmed the hub was bound
to all IPv4 interfaces and an enabled Windows Firewall rule already allowed
the actual Python executable on the active Public profile.

The hub was restarted with approved network-enabled execution using the
same command (`python -m uvicorn services.hub.app:app --host 0.0.0.0 --port 8000`).
Two other hotspot devices then received HTTP 200 from `/health`, and one
loaded `/fixture-mobile` and opened its mobile WebSocket. This verifies
cross-device HTTP and WebSocket reachability on the current hotspot.
No firewall rules or network-profile settings were changed. The restart
intentionally created a new run ID. Private client addresses are omitted.

For a manual launch, run the documented command from a normal Terminal on
the hub laptop with network access. A runner that permits only local
connections is insufficient for phone access. Actual physical photo
readability/orientation, live tracking, Mac, glasses, and band tests remain
pending; successful health requests do not pass those checks.
