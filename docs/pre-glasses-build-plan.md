# Pre-glasses build plan: hold, aim, drag right

Date: 14 November 2026. Task: pre-glasses planning.
Documentation branch: `docs/pre-glasses-build-plan`.
Responsible human/integration owner: `mhirvasm`. Plan author: Codex.
One coding agent, one checkout, one hub; A/B/C remain work-area IDs.

## Goal and current evidence

Complete a menu-free receipt transfer on the Galaxy S23 before the short glasses
slot: hold a pinch to capture, face a registered receiving screen, review the
amount, and drag the pinched hand right to send. Release before sending cancels.
Both Expenses and JSON remain required.

The user reports that the installed Android app works. This is an initial human
phone-test report, not a recorded pass for every device acceptance case.
The Android bridge has compiled, nine JVM checks and lint passed, and existing
vision checks passed. Real glasses camera/display/band coexistence is untested.
The current hub has screen detection but no receipt capture/extraction/apply flow.
The Android source has future capture/confirm adapters gated on that missing hub
endpoint. The existing display primary-action callback is not raw drag support.

Starting code: Android branch `feat/android-sdk-bridge` at
`57982e8f6a546799bf4d0729770f70ed36a43b62`; compiled native source checkpoint
`132ecaf5f5162b8523ec8b60359f414d71873aca`.
[Android issue #6](https://github.com/mhirvasm/LineOfSightJunction2026/issues/6)
and [draft PR #7](https://github.com/mhirvasm/LineOfSightJunction2026/pull/7)
remain subject to human acceptance/integration. This planning branch is based
on that Android checkpoint; it does not merge it into the shared baseline.
Before implementation, the integration owner selects the accepted baseline and
creates linked issues/task branches for the deliverables below.

## Agreed interaction

| Wearer action or condition | Required behavior |
| --- | --- |
| Face the receipt and begin an index-thumb hold | Freeze exactly one fresh local camera image; begin extraction once. |
| Keep holding while looking for a screen | Keep the captured receipt. A temporary lack of destination does not cancel by itself. |
| Face Expenses marker 10 or JSON marker 20 | Use the existing stable, fresh, connected target selection; show destination and amount. No destination menu. |
| Drag the whole pinched hand right after extraction and preview are ready | Confirm exactly that visible preview, once. Keep thumb and index touching during the movement. |
| Attempt the rightward paste after extraction, with no valid destination | Cancel the held receipt; change neither draft. Disconnected, ambiguous, or expired targets count as no destination. |
| Release before a commit | Cancel; late upload/extraction/input must not revive the capture. |
| Release after a commit | End the gesture; retain the applied draft. Release never means Undo. |
| Move right while extraction is still running | Do not queue a future paste. Require fresh movement after readiness. Release can still cancel. |
| Lose input/session/network, Stop, or Reset | Invalidate active capture/preview/input. Require explicit restart. Preserve applied drafts except on explicit Reset. |

A rightward drag is the preferred gesture, not a finger snap or thumb swipe that
breaks the hold. The actual band event mapping remains a hardware assumption.
After cancel/send, ignore further movement until release and a new hold.
Rebase movement when extraction becomes ready or the target/preview changes, so
old displacement cannot send to a newly selected screen. Use an adjustable
horizontal threshold and direction guard; calibrate against observed event units
instead of inventing pixel or physical-distance values.

For a paste/cancel race, the hub's serialized processing determines whether the
commit already happened. A later release cannot undo a completed commit.
If local target information looked valid but server freshness validation fails,
reject the send and clear the transient interaction without changing a draft.

## Architecture and deliberate boundaries

Our APK runs on the Android phone. It owns the Meta SDK session and sends camera
images to the single laptop hub; the hub owns extraction, target validation, and
draft writes. Display-capable glasses render the small SDK card supplied by the
phone. The band supplies input through the SDK. No separate custom glasses APK
is planned. Phone setup/permissions and operator diagnostics remain available;
the normal wearer flow uses status cards and gestures, without menus.

Use the same receipt and gesture logic in phone simulation and hardware modes.
The phone simulates hold/move/release on a touch pad while its rear camera supplies
real pixels. Injected SDK events test the adapter separately. Neither proves
physical band recognition.

Keep the existing receipt contract for both destinations. Handwritten receipts
can be evaluated with the real extractor, but handwriting is not a promised
capability until tested. General handwritten notes, arbitrary word selection,
system clipboard paste, and control of unrelated desktop apps require additional
scope and are not part of this build.

## Build sequence

These are proposed implementation deliverables, not already completed issues.
Each has `mhirvasm` as responsible human and Codex as proposed implementer.
Create one real issue per deliverable before its implementation PR. Use one task
branch at a time from the human-selected integration baseline.

### 1. B3 and C3/C4 fixture: frozen capture and cancellable workflow

**Background:** a working camera/marker path cannot yet hold a receipt or produce
a confirmable preview.

**Scope/ownership:** hub workflow, capture/extraction boundary, receipt validation,
protocol, and focused hub checks. Add only an explicit fixture extractor first.
Exclude real-provider setup and destination writes.

**Approach:** implement `POST /v1/captures` and READY -> READING -> HOLDING ->
PREVIEW using the exact frozen JPEG. Bind run/capture/preview identities; reject
duplicate captures with different bytes and avoid repeated extraction.
Extend the contract so cancellation identifies its capture, including a cancel
that arrives before its HTTP upload. Keep bounded cancellation/dedup records for
the run so late work cannot revive it or cancel a newer grab.
Document new-grab-after-APPLIED behavior for step 2. No silent fixture fallback.

**Acceptance:** fixture mode is visible; one frozen frame is used even when the
camera later faces a screen; release during upload or extraction cancels;
late results and old-capture cancels cannot affect a new grab; target changes
invalidate previews; invalid required fields request recapture.

**Verification:** extend and run `scripts/verify_hub.py` and
`scripts/verify_hub_server.py` with cancel-before-upload, late completion,
duplicate upload, stale run, and target-change cases. Inspect the resulting
snapshot sequence; drafts must remain unchanged.

**Dependencies:** [B1 #2](https://github.com/mhirvasm/LineOfSightJunction2026/issues/2),
[B2 #4](https://github.com/mhirvasm/LineOfSightJunction2026/issues/4), and the
accepted Android bridge [#6](https://github.com/mhirvasm/LineOfSightJunction2026/issues/6).
Fixture work covers only the prerequisite portion of C3/C4.

### 2. B4 and C2: apply once and show it on both receiving screens

**Background:** a preview needs an observable, duplicate-safe result.

**Scope/ownership:** hub apply/Undo, receiving React pages, render acknowledgements,
protocol clarification, and workflow/socket verification. Exclude arbitrary apps.

**Approach:** confirm the exact rendered preview only while its target is fresh
and connected. Atomically replace only that draft; use preview ID as commit ID.
Show waiting/displayed/not-confirmed feedback from matching DISPLAYED events.
Implement the existing one-level Undo and deliberate Send Again path.
Allow a fresh capture after APPLIED without erasing drafts or the existing Undo
slot; replace that slot only on the next successful apply. No automatic resend.

**Acceptance:** each destination renders the same canonical receipt; duplicates,
stale previews, target loss, reconnects, and release after send cannot write twice.
A new grab works after send. Undo restores the prior draft once. A hidden or
disconnected page does not falsely claim it displayed the result.

**Verification:** extend/run both hub scripts and the existing web socket tests;
build and visually inspect /expense and /json. Exercise duplicate confirm,
stale preview, reload, late DISPLAYED, Send Again, Undo, and a second fresh grab.

**Dependencies:** deliverable 1; existing receiving-page foundation.

### 3. A4: one hold/drag controller for phone and band adapters

**Background:** implement the agreed interaction before testing scarce hardware.

**Scope/ownership:** Android input controller, touch simulator, raw SDK Inputs
adapter, and native tests; add the pinned Inputs dependency only if required.
Update the protocol/client together with any missing cancellation correlation.

**Approach:** route phone DOWN/MOVE/UP and SDK DragAction events into the same
controller. Freeze on the initial hold, ignore pre-ready movement, bind the
displayed preview, and commit once on qualifying right movement. A paste attempt
without a valid target cancels. Exactly one input path controls the session.
Attach Inputs after the SDK session starts and handle approval/error/lifecycle
states. Keep diagnostics separate from mutations. Use an explicit operator-chosen
primary-action/tap fallback if raw Inputs is unavailable; never silently change
gesture modes during an interaction. Keep Undo off the release gesture.

**Acceptance:** touch simulation and injected SDK events cover the complete
gesture table, including jitter, repeated MOVE/UP, target changes, and interruption.
No target menu; no queued confirm; no old movement sending a new preview.

**Verification:** run Android `assembleDebug testDebugUnitTest lintDebug`;
add meaningful controller/adapter tests. On the S23, use rear-camera pixels and
the touch pad to capture, hold, face each screen, send, and cancel. Label injected
events as simulated. Raw band recognition remains pending.

**Dependencies:** deliverables 1 and 2; Android #6. Inputs capability approval is
a hardware-access prerequisite, not something a mock test proves.

### 4. C3/C4 live: extract and validate a real receipt

**Background:** fixture output proves routing but cannot prove camera-to-data.

**Scope/ownership:** one extraction provider, configuration placeholders,
canonical validation, known/changed-total receipt checks. Exclude provider
abstractions, arbitrary notes, and an editing interface.

**Approach:** select one available provider, keep credentials outside Git, send
only the frozen capture, and return the same canonical record for both targets.
Use timeouts and bounded work; cancel/discard stale results. Never replace an
error with a fixture success. Show amount and review failures before confirmation.
A missing optional tax does not block; missing/ambiguous required fields do.

**Acceptance:** live mode reads the known printed receipt and changed-total
receipt correctly, with visible mode labeling and no draft write on failure.
Document handwriting results separately; do not promise untested handwriting.

**Verification:** add focused extraction/validation checks and record their exact
command in the task runbook. Physically capture both printed receipts on S23,
compare visible amounts, and send to each destination. Exercise provider timeout
and cancellation while a real request is pending. Retain no camera image logs.

**Dependencies:** deliverables 1 and 2; available provider credentials/network.
This phase can follow the gesture implementation in the single-agent sequence.

### 5. A5, B5, C5: feedback, lifecycle, and rehearsal package

**Background:** minimize the glasses slot to hardware validation and calibration.

**Scope/ownership:** compact display cards, Android session ownership,
integration fixes, runbook, and demo fixtures. Device/experience operators must
be named by the integration owner before the slot.

**Approach:** show Reading, Held/look at screen, destination/amount/drag right,
Canceled, and Sent/waiting/Shown states. Move real-glasses session ownership out
of Activity-only lifetime into an appropriate foreground service with visible
notification/Stop, following the official SDK sample. Do not assume phone-camera
mock mode can run with its screen off; keep that path foreground-only if needed.
Pause/removal/capability loss cancels safely and requires restart; no input replay.
Keep the proven network setup, versions, receipt/marker assets, spare APK, and
exact startup commands. Do not depend on USB installation.

**Acceptance:** all software-readiness checks below pass; three consecutive full
phone rehearsals cover both destinations; record source commit/APK checksum,
mode, operators, results, and remaining physical-only checks. No silent automatic
restart or success claims after an unacknowledged screen update.

**Verification:** run the relevant complete checks below after integration;
inspect the compact UI on the SDK mock display and receiving pages. Exercise
phone interruptions/reconnects. Real glasses screen-lock and remove/re-wear
remain physical checks even if lifecycle unit tests pass.

**Dependencies:** deliverables 1-4. Real glasses/background behavior additionally
depends on physical device access.

## Software-readiness gate before the glasses slot

- [ ] Frozen receipt remains correct after pointing the camera at a destination.
- [ ] Release cancels before upload acceptance, during extraction, and in preview;
      late results/old cancels cannot revive or replace a new grab.
- [ ] Rightward paste with no fresh connected destination cancels without a write.
- [ ] Pre-ready/old-target movement is not queued; one hold can commit only once.
- [ ] Release after send retains the result; new holds work after send/cancel.
- [ ] Both Expenses and JSON render real extracted data and acknowledge display.
- [ ] Duplicate/stale actions, target refresh/loss, provider timeout, Reset,
      app interruption, and network recovery have their expected safe outcomes.
- [ ] Undo and Send Again follow the protocol; no automatic resends.
- [ ] Known and changed-total printed receipts pass in live extraction mode.
- [ ] Three consecutive physical-phone rehearsals pass; mock tests are labelled.
- [ ] Inputs access/device availability is checked with the Meta booth in advance.
- [ ] Known-good source/APK, startup commands, and rehearsal results are recorded.

Verification commands from the repository root (planned reruns, not new results):

```powershell
.\.venv\Scripts\python.exe scripts/verify_foundation.py
.\.venv\Scripts\python.exe scripts/verify_hub.py
.\.venv\Scripts\python.exe scripts/verify_hub_server.py
.\.venv\Scripts\python.exe scripts/verify_vision.py
.\.venv\Scripts\python.exe scripts/verify_vision_server.py
node --test apps/web/src/connection/socket.test.js
npm --prefix apps/web run build
```

Use the existing local JDK/Gradle environment and Android build command from
[the Android task record](tasks/A2-A3-android-sdk-bridge.md#verification-record):
`assembleDebug testDebugUnitTest lintDebug`. Extend existing checks for workflow
changes; record exact commands for any new extraction checks when implemented.
Start one hub using:
`.\.venv\Scripts\python.exe -m uvicorn services.hub.app:app --host 0.0.0.0 --port 8000`.
Receiving URLs are `http://HUB-IP:8000/expense` and
`http://HUB-IP:8000/json`. Use the actual current LAN IP; do not bake an old
hotspot address into the build.

## What still requires glasses

Passing the gate means software-ready for first physical glasses validation,
not a guarantee that the final hardware demonstration already works.

Before the slot, arrange compatible display glasses and band, Android/Meta AI
pairing, developer account/configuration, firmware, permissions, and Inputs
capability approval. Experimental Inputs access is a real dependency.
At the slot, use this order:

1. Confirm registration and camera/display/input capability status without writes.
2. Check camera orientation, receipt readability, central marker selection, and
   simultaneous camera + display + input on the same real session.
3. Observe real DOWN/MOVE/UP semantics, hold/release recognition, drag direction,
   units, and threshold. Calibrate briefly; do not assume injected events prove it.
4. Send one real receipt to each destination; test release cancel and no-target
   paste cancel. Confirm visible amount and receiving-page feedback.
5. Test phone screen lock, glasses removal/re-wear, input loss, and explicit
   recovery. Record exact versions, commit, results, and remaining failures.

If the band does not expose the required drag events or access is denied, use
the explicit primary-action fallback for a reduced demo and record the limitation.
Do not claim the agreed hold/drag interaction passed. Keep the known-good phone
demo available.

## Sources and task boundary

- [Meta Inputs lifecycle and approval guidance](https://github.com/meta/meta-wearables-dat-android/blob/main/.cursor/rules/inputs.mdc):
  experimental Inputs needs WDC approval and is unavailable for production apps.
- [Meta Android SDK changelog](https://github.com/meta/meta-wearables-dat-android/blob/main/CHANGELOG.md):
  Inputs and mock input/display support are SDK capabilities.
- [Official foreground camera service example](https://github.com/meta/meta-wearables-dat-android/blob/main/samples/CameraAccess/app/src/main/java/com/meta/wearable/dat/externalsampleapps/cameraaccess/stream/StreamingService.kt).
- [Local demo protocol](../contracts/protocol.md) and
  [Android runbook](../apps/mobile/android/README.md).

This task changes planning documentation only. It does not implement the five
deliverables or mark glasses/gesture acceptance complete. Review the plan, then
the integration owner chooses the first implementation issue and baseline.
