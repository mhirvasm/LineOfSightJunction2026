# Next phase: iOS bridge, phone tests, then glasses

Planning record: PLAN-IOS-1. Date: 14 November 2026, Europe/Helsinki.
Responsible human: `mhirvasm` (existing integration owner). Author: Codex.
Planning branch: `docs/ios-phone-first-plan`, from `60e7290` on
`feat/b2-target-selection`. This is a plan, not an implementation or test report.
This task publishes documentation only. Implementation issues and PRs will be
created separately; no application code or merge is included.

## Decisions and starting point

- Build one native Swift iOS bridge first. Android is deferred.
- Use one coding agent, one active implementation checkout, and one hub.
  A/B/C remain work areas. Mac/Xcode is required for the iOS build; the hub
  may continue on the current demo laptop. Other computers only open pages.
- First prove the complete flow with an actual iPhone camera and explicitly
  simulated band selection. Then validate and integrate real glasses/band.
- Keep Expenses and JSON. No destination menu, cursor, desktop automation,
  platform framework migration, database, or production infrastructure.
- The user's phone-first instruction changes the older A1-first ordering:
  mock SDK and phone development may proceed before A1. A1 remains mandatory
  before claiming hardware support or relying on glasses for the demonstration.

The current B2 branch contains shared sockets, both receiving pages, real
JPEG marker detection, stable-target rules, and a one-photo browser test.
[B2](tasks/B2-target-selection.md) records software checks and cross-device
HTTP/WebSocket reachability on the hotspot. Physical phone-photo readability
is still pending. No native app, receipt extractor, full workflow, transfers,
or Undo exists. Older K0 records describe their milestone, not current status.

Have `mhirvasm` review B2 and choose its accepted baseline before implementation.
Do not merge B2 automatically. `60e7290` is the current source reference, not a
known-good native or hardware build. Record each actually verified build later.

## Experience and implementation boundary

After setup and Start, the intended interaction is:

1. Face a receipt and activate Capture once.
2. Freeze that exact frame, read it, and show brief progress.
3. Face either registered receiving screen. Its marker selects the destination.
4. Show destination and amount, for example `Expenses / EUR 24.80 / Confirm`.
5. Activate Confirm once. Only that destination changes, and success follows
   the receiving page's acknowledgement.

Looking chooses the destination; it never commits. The prototype uses camera
direction and registered markers, not eye tracking. Target loss/change
invalidates the old preview. No confirmation is allowed while reading or
without a fresh connected target. A held/repeated activation cannot capture
and then confirm when an asynchronous result arrives.

On the iPhone, use large touch controls for Capture/Confirm and a visible
preview of the glasses content. Label input `PHONE BUTTON / BAND SIMULATED`.
These controls are test substitutes, not evidence of a wristband connection.
Setup, Stop, Cancel, Send Again, and Undo can remain accessible in the phone's
test controls; they are not a destination menu in the main flow. Reset remains
an explicit operator-page control, as required by the existing protocol.
Verify secondary hardware input mappings later rather than inventing gestures.

The iOS bridge owns camera/session/input/display adaptation and HTTP/WebSocket
transport. The hub remains authoritative for extraction, state, selection,
confirmation, deduplication, and Undo. Receiving browsers render snapshots.
Keep the existing [protocol](../contracts/protocol.md), routes, target IDs,
and canonical receipt record. Use small source adapters only where needed to
switch phone/mock camera and input to physical glasses; do not build a generic
cross-platform framework.

## Ordered deliverables

Each item below is a proposed meaningful implementation issue. Reuse the
existing task IDs noted in parentheses. Before starting each item, create or
link its real issue, name the responsible human, and branch from the baseline
chosen by `mhirvasm`. The default responsible human is `mhirvasm`; assign a
device tester before physical work.
Integration and agent-authored PR review/merge remain human-owned.

### IOS1: establish the iOS SDK mock bridge (A2 preparation, A5 preview)

- **Background:** test real SDK integration and display actions without waiting
  for glasses. A browser-only mock cannot prove that the native app builds.
- **Scope:** `apps/mobile/ios/`, mobile setup documentation, device/build record.
  Excludes Android and physical hardware claims.
- **Approach:** inspect the available Mac/Xcode/iPhone versions; choose an
  official released iOS sample/package combination that actually builds. Pin
  its exact SDK version and resolved dependencies. Add one configurable hub
  address, `/health`, and `/v1/events?role=mobile`. Use MockDeviceKit and the
  supported display preview/click path. Maintain one session, listener owner,
  and socket; discard pending actions when `run_id` changes. Keep credentials
  outside tracked files. Do not assume repository-main examples exist in every
  released binary package.
- **Acceptance:** app builds on the Mac; native mock display and one selection
  callback work; hub reports the iOS controller; Reset reaches the app; restarting
  it does not leave duplicate callbacks/connections.
- **Verification:** build/run the chosen official sample, then our actual iOS
  target; record exact workspace/project, scheme, destination, build command,
  signing requirements, and results. Run ten injected selections and observe ten
  intended callbacks. Check new-run handling and disconnect/reconnect.
- **Dependencies:** accepted K0/B1/B2 baseline; existing
  [K0 issue #1](https://github.com/mhirvasm/LineOfSightJunction2026/issues/1),
  [B1 issue #2](https://github.com/mhirvasm/LineOfSightJunction2026/issues/2),
  [B2 issue #4](https://github.com/mhirvasm/LineOfSightJunction2026/issues/4).

### IOS2: stream an actual iPhone camera to both targets (A3 phone path)

- **Background:** the current photo picker proves individual recognition;
  continuous fresh observations are needed for stable selection.
- **Scope:** iOS camera/uploader and phone feedback; preserve existing hub
  marker rules. No receipt transfer yet.
- **Approach:** first verify the pinned iOS MockCameraKit's phone-camera feed
  on an actual iPhone. If unavailable, use a small AVFoundation phone-camera
  source feeding the same uploader, and label it as phone-camera fallback.
  Announce `STREAM_STARTED`, upload normalized upright JPEG frames near five
  times per second, keep one request in flight and one replaceable newest frame.
  Use supported `camera_stream` input-source diagnostics for actual phone video;
  synthetic replay remains `fixture_frames`. Configure the required camera and
  local-network permissions/development transport settings narrowly. Stop or
  pause cleanly on app interruption. Do not promise background operation.
- **Acceptance:** facing Expenses acquires Expenses; turning to JSON invalidates
  the old target and acquires JSON. Blank/ambiguous views, screen disconnect,
  Stop, and old frames leave no actionable target. Portrait/landscape frames
  have correct orientation. No growing backlog or replay on recovery.
- **Verification:** on an actual iPhone over the demo network, point at both
  laptops, cover markers, show both centrally, rotate phone, disconnect a target,
  interrupt the app, and interrupt networking for ten seconds. Record observed
  lag and outcomes. Repeat existing vision checks after any hub change.
- **Dependencies:** IOS1 and accepted B2. Close `/fixture-mobile` first; only one
  controller connection is allowed.

### B3: capture and preview an explicit fixture receipt (C3/C4 fixture path)

- **Background:** establish exact-frame capture and the complete interaction
  states before adding a variable extraction provider.
- **Scope:** hub capture endpoint/state machine, extraction module/validation,
  iOS Capture and preview; both destination previews. No applied draft yet.
- **Approach:** implement `/v1/captures` with immutable JPEG and `capture_id`;
  duplicate captures do not reread. Implement READY, READING, HOLDING, PREVIEW,
  cancellation, and STOPPED. Fixture extraction returns the known canonical
  record only in explicitly selected fixture mode. Create `preview_id` from
  capture/target/record and invalidate it on target change/loss. Bind actions to
  their rendered intent and ID. Do not use a global gesture-to-next-state handler.
- **Acceptance:** the exact captured frame is preserved even when the camera
  immediately moves; both destinations show the same validated receipt; drafts
  remain empty before confirmation; stale extraction results cannot restore a
  canceled/reset preview. Missing optional tax is accepted; invalid required
  fields request recapture.
- **Verification:** capture receipt A then immediately face B; duplicate upload;
  cancel/reset while extraction is delayed; change/lose destination; validate
  known/invalid records and required field types. Label every receipt result as
  fixture; a changed-total photo must not be presented as live recognition here.
- **Dependencies:** IOS2; C3/C4 fixture validation is included in this deliverable.

### B4: apply once to either screen and Undo (C2 acknowledgement)

- **Background:** make the transfer visibly complete while preserving deliberate
  confirmation and the second destination.
- **Scope:** hub apply/Undo, receiving-page acknowledgements, iOS action feedback.
- **Approach:** Confirm includes the displayed `preview_id`. Atomically check
  freshness, current target, connection, validation, and commit deduplication;
  change only that target's draft. Implement DISPLAYED acknowledgement and
  distinguish sent/waiting/displayed. Add one-level Undo and Send Again using
  existing protocol rules. Each resend requires a fresh preview and confirmation.
- **Acceptance:** both Expenses and JSON receive a fixture receipt through the
  full phone interaction; repeated Confirm produces one update; stale Confirm
  cannot redirect to a newly selected screen; Undo restores only the last
  affected draft; reload/reconnect does not reapply a transfer.
- **Verification:** complete the flow separately for both destinations; repeat
  Confirm three times; switch targets then deliver old Confirm; lose a target;
  hide/reveal a receiving tab; reload; resend to the other screen; Undo; Reset.
  Inspect both affected pages after a web build.
- **Dependencies:** B3 fixture flow and existing receiving-page sockets.

### C3/C4: read actual phone-captured receipt pixels

- **Background:** replace predetermined fixture output with real extraction.
- **Scope:** one extractor/provider, canonical validation, visible mode/error
  feedback. No provider switching framework or receipt correction editor.
- **Approach:** select one available provider during implementation; document its
  configuration and keep the key on the hub outside Git. Submit only the frozen
  capture image. Keep fixture/live modes explicit and never silently fall back
  to fixture output after live failure. Validate EUR/minor-unit totals and the
  existing receipt fields before allowing confirmation.
- **Acceptance:** the known receipt and a receipt with a visibly changed total
  yield their respective values; unreadable required fields block confirmation;
  provider failure stays visible; both destinations receive identical canonical
  data from the same capture.
- **Verification:** run both receipt cases through actual extraction and through
  the phone transfer flow; inspect the exact captured image; test unreadable
  input, provider failure, and a late response after Cancel/Reset. Record actual
  provider/model configuration and outcomes without logging images or keys.
- **Dependencies:** B3 validation and B4 integrated fixture flow; a configured
  extraction provider/key is required for live verification.

### B5-PHONE: pass the complete phone rehearsal

- **Background:** establish a working fallback and baseline before the hardware slot.
- **Scope:** bug fixes in touched components, runbook, phone/receiving-screen checks.
- **Approach:** use one actual iPhone, one hub, and both receiving laptops.
  Start the session once; keep destination selection menu-free. Use labelled
  phone selection controls. Record receipt source and camera/input source
  independently so real camera footage does not imply real extraction or band input.
- **Acceptance:** three consecutive complete live receipt rehearsals succeed,
  exercising both destinations; preview-before-commit, exact-once apply, and
  Undo work. Disconnect, stale preview, and Reset cases have clear outcomes.
- **Verification:** run the full flow three times and the relevant failure cases
  from the [protocol](../contracts/protocol.md). Record exact startup commands,
  tested devices/OS/network, timings, results, and a known-good commit after human
  review. A fixture-only run remains a fixture milestone, not live completion.
- **Dependencies:** IOS1, IOS2, B3, B4, and C3/C4 live extraction.

### A1 then A2-A5: integrate physical glasses and band

- **Background:** replace the tested phone sources with physical hardware while
  keeping the same hub workflow and receiving screens.
- **Scope:** paired-device setup, real SDK camera/display/input, lifecycle fixes,
  and hardware record. No Android or general desktop control.
- **Approach:** with the Meta booth, verify the loaned Display glasses/band work
  with the chosen iPhone/account/firmware and pinned SDK. First prove changing
  camera frames, display content, and ten deliberate selection callbacks together.
  Then use the real camera and the supported primary-action callback for the
  existing Capture/Confirm intents. Keep phone test mode available. Validate
  Cancel/Stop and secondary actions using actual supported controls; do not
  promise arbitrary gesture recognition. Hardware incompatibility remains a
  documented blocker, not permission to silently change SDKs during rehearsal.
- **Acceptance:** exact receipt frame is captured; looking at either screen
  selects it; a deliberate second activation commits the shown preview; one
  held/repeated action cannot capture and confirm. Remove/re-wear and reconnect
  cannot replay actions. Camera, display, and input coexist on the actual device.
- **Verification:** A1 observed hardware gate first, then the same B5 phone cases
  on glasses, including both destinations, stale/duplicate actions, Stop,
  interruption, and three complete rehearsals. Record firmware, SDK, iPhone OS,
  build command, observed failures, and verified commit in the device/runbook
  records. Distinguish SDK simulation from actual band events.
- **Dependencies:** B5-PHONE for integrated glasses work; an A1 compatibility
  experiment can happen earlier if hardware becomes available. A1 must pass
  before relying on the real glasses bridge.

## Verification and task boundaries

Existing regression commands, from the repository root in an activated Python
environment, are documented in the runbook:

```sh
python scripts/verify_foundation.py
python scripts/verify_hub.py
python scripts/verify_hub_server.py
python scripts/verify_vision.py
python scripts/verify_vision_server.py
python -m pip check
node --test apps/web/src/connection/socket.test.js
npm --prefix apps/web run build
```

Use the relevant subset for each change, plus its complete affected flow. New
workflow/extraction/native checks must cover meaningful behavior above. Their
actual commands and iOS scheme/destination will be recorded when they exist;
this plan does not invent new test scripts or report new checks as passed.

The hub startup command remains:

```sh
python -m uvicorn services.hub.app:app --host 0.0.0.0 --port 8000
```

The planned phone-first order is IOS1 -> IOS2 -> B3 fixture -> B4 -> C3/C4 live
-> B5-PHONE -> A1/A2-A5 -> glasses rehearsal. Work is sequential, with one real
issue and reviewable task branch per deliverable. Each task ends with actual
verification, limitations, physical checks pending, and the next human action.
Do not auto-merge agent-authored PRs or start another task without the human's
direction. If hardware fails, demonstrate the phone fallback honestly; if live
extraction is incomplete, label the demonstration as fixture-based.

## SDK evidence and first human action

Sources inspected on 14 November 2026:

- [Official iOS SDK changelog](https://github.com/meta/meta-wearables-dat-ios/blob/main/CHANGELOG.md):
  1.0 adds mock display/click preview and mock inputs; primary display actions
  receive initial focus. Separate input APIs are experimental. Pin and verify
  package availability rather than assuming every main-branch feature is usable.
- [Official DisplayAccess sample](https://github.com/meta/meta-wearables-dat-ios/blob/main/samples/DisplayAccess/README.md):
  current source lists iOS 17.2+, Xcode 26.4+, Swift 6.3+ and documents a local
  XCFramework mock preview. The in-app preview is available without glasses;
  Chrome preview uses iOS Simulator and is not available on a physical iPhone.
  These are source requirements, not a claim that the team's Mac can run them.

First action: `mhirvasm` reviews this plan and B2, identifies the Mac/Xcode and
iPhone versions available, and chooses the accepted baseline. Start IOS1 with
a real linked issue and buildable official sample. No glasses are required
for that first deliverable.
