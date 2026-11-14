# LineOfSight
## Demo-first plan and detailed agent tasks

**Junction / 14 November 2026 / three people / about 24 hours**

**Build this:** capture a large printed receipt through the glasses, turn toward one of two screens, pinch to confirm, and show the same information as either an expense draft or JSON.

This revision replaces the earlier implementation plan. It keeps the useful interaction and removes production infrastructure. There is no application implementation to verify yet: the architecture and task dependencies have been reviewed; device behavior still needs a physical test.

### The six things to do, in order
1. **A: get a Display unit, Neural Band, and working companion phone.** With Amanda, prove camera streaming and a display-button selection callback together. Time limit: two hours.
2. **B: initialize the small hub and shared contract.** Use one process, memory only, a private hotspot, and HTTP/WebSockets.
3. **C: create BOTH destinations immediately.** `/expense` uses marker 10; `/json` uses marker 20. Both use one shared target component.
4. **Connect the flow with a fixture receipt.** Looking switches the target; confirmation changes only the selected draft. No AI is needed for this milestone.
5. **Replace fixture extraction with one real model call.** Capture the exact frame selected at pinch time. Extract once and map the record in ordinary code.
6. **Fix the short bug checklist and rehearse.** Show target switching, one transfer, and Undo. Record a real working run as backup.

### The scope boundary
**Keep:** two targets, native wristband input if supported, visible markers, one receipt schema, a stable target preview, duplicate protection, simple Undo, and clear connection feedback.

**Cut:** accounts, per-role secret tokens, certificate setup, databases, persistence, general app injection, SQL execution, advanced recovery, arbitrary documents, MediaPipe hand tracking, and a second phone platform.

### Three agents, three owners
| Agent | Main responsibility | Human responsibility |
| --- | --- | --- |
| A | Glasses, phone bridge, camera frames, wristband callback, display | Pair/install/test on the shared hardware. |
| B | Hub, target detection, workflow, in-memory drafts, integration | Own the shared contract and merge changes. |
| C | Both receiving pages, extraction adapter, demo feedback | Prepare receipts, test the visible experience, rehearse. |

**First useful demo:** the glasses select between two screens and transfer fixture data. **Finished demo:** the same flow extracts a real synthetic receipt from a live glasses image. Fixture mode must always be visible when used.

<!-- PAGE -->
# 01 / Big-picture check
## The simplified system fits together

```text
Glasses camera + Neural Band
        |
        v
One native phone app
  - sampled frames for target detection
  - frozen image on Capture
  - explicit button actions
        |
        v
One Python hub on a laptop
  - ArUco target selection
  - one receipt extraction request
  - authoritative workflow and drafts IN MEMORY
        |
        +---- /expense, marker 10
        +---- /json, marker 20
        +---- short state card back to the glasses
```

### Five corrections from the previous plan
1. **Two destinations are core.** Without a visible choice, head-directed selection adds little to the demonstration.
2. **The hub owns both drafts.** Browsers only render snapshots. A refresh receives the current snapshot; it does not replay a write. No database or browser reconciliation engine is required.
3. **Capture includes the image.** The phone freezes the frame at the gesture and uploads it with a capture ID. The server must not grab whichever streaming frame happens to arrive next.
4. **A preview has a stable ID.** Ordinary frame updates do not invalidate it. The ID changes only when the receipt or target changes, or the preview is canceled/lost.
5. **Stop is not rollback.** A completed draft update stays applied. Undo is a separate action. Canceling an extraction invalidates any later model response.

### What this architecture deliberately does not guarantee
- Restarting the hub clears all in-memory data and starts a new run. Say so and reset the demo; do not build restart recovery.
- Client role/query parameters are routing labels, not authentication. Use a controlled private network and synthetic data; do not describe this as secure public deployment.
- The camera center approximates head direction, not eye gaze. Marker visibility and a preview reduce mistakes but cannot prove exactly where the wearer is looking.
- Larger receipt text improves readability; it cannot guarantee correct extraction. Keep the total visible before confirmation.

### The remaining hard gate
The loaned glasses must support the camera and the chosen display input together. Public Meta guidance documents capability lifecycle and display callbacks, but the actual device/account combination still needs testing. A failed hardware check is a booth-support problem, not a reason to generate more app code. [S1]

<!-- PAGE -->
# 02 / Order and ownership
## Run small tasks in parallel; integrate in stages

| Stage | A | B | C |
| --- | --- | --- | --- |
| Start | A1 hardware gate | K0 contract, then B1 hub | C1 two screens using fixtures |
| Connect | A2 shell, A3 frames | B2 marker detection | C2 socket connection |
| First flow | A4 capture/input, A5 display | B3 workflow, B4 apply/undo | C3 extraction adapter, C4 validation |
| Finish | Physical interruption test | B5 integration checks | C5 visible feedback and demo preparation |

K0 does not block the physical A1 check. C can sketch the two screens immediately; messages and marker assets must follow K0 before integration.

### Time limits from your actual start
- **Hour 2:** camera + display/button path either works or has a concrete fallback decision.
- **Hour 4:** two screens exist; their target labels can switch using fixture frames or the live stream.
- **Hour 6:** fixture receipt reaches either destination through the full control path.
- **Hour 8-10:** aim for one real glasses receipt extraction and transfer.
- **Hour 12:** finish the short fault checklist. Cut extra polish if the core is unstable.
- **Hour 16:** freeze features. Prepare slides, record a genuine run, and rehearse.
- **Final hours:** charge devices, confirm the loan slot, and keep a known-good build ready.

### Common prompt for every agent task
```text
Implement ONLY the task below. Read contracts/protocol.md
first. Stay inside your owned files. Use existing packages
and pinned SDK versions. Do not add production features.

Give a plan of at most five steps, implement it, and run
the task's checks. Do not guess Meta SDK API names: inspect
the official sample for the installed version.

Return changed files, exact commands run, passed/failed
checks, and anything still requiring physical hardware.
If blocked after two attempts, return the smallest failing
example and error. Do not silently replace live behavior
with fixture data. Stop when this task is complete.
```

### File ownership
A owns `apps/mobile/`. B owns `contracts/`, hub core, vision, and root dependency files. C owns `apps/web/`, `services/hub/extraction/`, and receipt fixtures. Ask B before changing shared messages. Only one agent edits a given file at a time.

**Handoff rule:** each task ends with one command or clear physical action that the next person can use to demonstrate the result. Run one working slice before adding another feature.

<!-- PAGE -->
# 03 / The shared contract
## Small enough for lighter models to follow

The starter pack contains the full `contracts/protocol.md` and `fixtures/receipt_expected.json`. These are proposed application interfaces, not Meta SDK names.

### Fixed demo configuration
| Item | Value |
| --- | --- |
| Hub | One Python process, port 8000, no auto-reload during demo. |
| Targets | `expenses` -> `/expense`, marker 10; `json` -> `/json`, marker 20. |
| Network | Private hotspot/router; UI and API on the same HTTP origin. |
| Socket | `/v1/events?role=mobile` or `?role=target&id=expenses` or `?role=target&id=json`. |
| Data | One active receipt, two in-memory drafts, one-level Undo. |
| Reset | New random `run_id`; clears drafts, receipt, previews, and deduplication set. |

### Minimal messages and endpoints
| Interface | Meaning |
| --- | --- |
| GET /health | Returns protocol version and current run_id. |
| POST /v1/frames | Sampled JPEG + run_id, stream_id, frame_seq, frame age. Latest frame wins. |
| POST /v1/captures | Frozen JPEG + run_id, capture_id, frame age. This exact image is extracted. |
| ACTION | START, CONFIRM, CANCEL, STOP, SEND_AGAIN, or UNDO. CONFIRM includes preview_id. |
| SNAPSHOT | Full state, receipt, selected target, preview_id, both drafts, last commit, feedback. |
| DISPLAYED | Target reports it rendered a particular commit_id. Does not perform a write. |

### The canonical receipt
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

Missing tax is allowed. Missing/ambiguous merchant, date, total, or currency blocks confirmation and prompts recapture. Do not treat model confidence as proof of correctness. Preview the total and destination for the wearer.

**Success semantics:** the hub updates a draft once, then broadcasts it. Show "Sent; waiting for screen" until the selected browser reports DISPLAYED. If the browser disconnects, show "Draft updated; screen not confirmed." Never repeat the mutation just to obtain an acknowledgement.

<!-- PAGE -->
# 04 / Agent A: prove and connect hardware
## A1-A3 / Keep the native app thin

### A1 - Prove camera and wristband selection together
**Depends on:** loan access. **Own:** `apps/mobile/`, `docs/device-check.md`. **Time box:** two hours, with booth help.

1. Ask Amanda for Display + Neural Band, companion phone, account setup, and a later rehearsal slot. Choose Android or iOS based on the working equipment; do not build both.
2. Build/install the official camera and display samples. Record SDK, firmware, phone OS, and the exact successful build command.
3. Obtain changing live frames. Put one focused action on the glasses and count ten deliberate band selections.
4. Run camera and display/input together. Remove/re-wear the glasses once and try starting again.

**Pass:** a human observes the real feed and callback together. Record each capability as PASS/FAIL/NOT TESTED. **Bugs:** assuming a simulator proves hardware; attaching capabilities before the session is ready; confusing physical controls with a documented app event. [S1]

### A2 - Create the smallest native bridge and local-network setup
**Depends on:** A1, K0. **Own:** native configuration and session wrapper. **Time box:** 45-60 minutes.

1. Keep the working official sample. Add one configurable hub URL and a connection status label.
2. For Android, allow local HTTP in the debug build's network-security configuration. Keep the release configuration unchanged. Use the matching platform's documented setup if using iOS.
3. Connect to the mobile socket; store the server-issued run_id. On a new run_id, discard pending local actions and captured uploads.
4. Put SDK observers and sockets under one lifecycle owner; clean them up before recreating a session.

**Pass:** the phone reaches /health and receives SNAPSHOT. Restarting the app creates one active callback subscription, not two. **Bugs:** wrong laptop IP, firewall/client isolation, cleartext blocked by Android, duplicate observers. [S2]

### A3 - Stream correctly oriented frames without a backlog
**Depends on:** A2, B1. **Own:** native frame conversion/uploader. **Time box:** 45-60 minutes.

1. Decode using the SDK's documented frame path. Copy frame data before a reusable camera buffer is released.
2. Normalize rotation once and preserve aspect ratio. Start near five uploaded frames per second; use actual supported resolution, not a hardcoded 640x480 assumption.
3. Allow one upload in flight and keep at most one newer pending frame. Drop old frames. Send stream_id, increasing frame_seq, and local frame age.
4. Give uploads a timeout. Stop sending when the camera/session is paused.

**Pass:** a printed word is upright, left/right are correct, and a ten-second network interruption does not create a delayed replay of old images. **Bugs:** double rotation, mirrored detection, recycled image buffers, unbounded tasks, comparing unrelated device clocks.

<!-- PAGE -->
# 05 / Agent A: capture and show state
## A4-A5 / Bind each gesture to what was shown

### A4 - Freeze the receipt image and send one deliberate action
**Depends on:** A3 and the K0 contract. **Own:** native input and capture adapter. **Time box:** 60 minutes.

1. Use the verified focused-button callback. Map its displayed action explicitly; do not use a generic "pinch advances whatever state is current" handler.
2. On Capture, copy the latest usable normalized frame immediately, assign capture_id, and upload that immutable JPEG to /v1/captures. Do not ask the hub to select its latest streaming frame.
3. If the last delivered camera frame is too old, show "Hold still and try again." Start with a 300 ms local-age limit and tune on hardware. This age measures local delivery, not guaranteed sensor exposure time.
4. Disable Capture while its upload/extraction is active. CONFIRM sends the preview_id that belonged to the visible button. A held/repeated callback must not become a second action.

**Pass:** point at receipt A, capture, then immediately look at receipt B: extraction receives the frozen A image. Ten deliberate pinches produce ten intended events, with no capture-plus-confirm from one gesture. **Bugs:** mutable image references, asynchronous latest-frame reads, stale button closures, callback duplication.

### A5 - Render simple cards and stop safely on interruption
**Depends on:** A4, B3. **Own:** native view rendering and pause/resume handling. **Time box:** 60 minutes.

1. Render READY, READING, HOLDING, PREVIEW, and APPLIED from server snapshots. Show a short destination/total preview and an explicit Cancel/Stop path.
2. Do not rebuild the display on every unchanged camera observation. Stable content keeps the same preview_id.
3. On link loss, permission failure, or SDK pause, disable confirmation locally and show the actual problem. Stop local camera work promptly on Stop, even if the network is down.
4. After reconnect, accept the new server snapshot. Do not replay queued Capture or Confirm events. Require Start again after a device interruption.
5. Add a visible phone-button fallback using the same actions. Label it as fallback in the demo; do not present it as wristband input.

**Pass:** remove/re-wear and disconnect/reconnect once. No old gesture commits after recovery. Stopping after a successful transfer does not claim the transfer was undone.

### What A should bring to the next device slot
A known-good installed app, the correct hub URL, two visible target pages, large printed receipt fixtures, charging materials, and one concrete question to test. Do not spend the shared-device slot downloading build tools.

**If the hardware gate fails:** use Amanda's supported fallback path. A phone-camera or prerecorded feed may keep software development moving, but must be visibly labeled and does not prove the glasses integration.

<!-- PAGE -->
# 06 / Agent B: start the hub and targeting
## K0, B1, B2 / No infrastructure project

### K0 - Initialize the demo contract and reproducible fixtures
**Depends on:** nothing. **Own:** contracts, root setup, fixture manifest. **Time box:** 30-45 minutes.

1. Copy the starter protocol and expected receipt from this pack into the project. Keep target IDs, marker IDs, routes, and message names unchanged.
2. Create the minimal folder structure and actual run commands. Pin working packages; do not add Redis, Docker, a database, or an authentication framework.
3. Supply one valid receipt record, one invalid record, and example snapshots for all UI states. C can use these before the hub exists.
4. Assign file ownership. C owns the extraction module; B imports its agreed function without editing it concurrently.

**Pass:** A/B/C can explain the same Capture -> Preview -> Confirm flow and consume the same fixture. **Bugs:** field-name drift, expenses/expense ID confusion, differing marker dictionaries, silently changing contracts.

### B1 - Build one in-memory hub and connect three clients
**Depends on:** K0. **Own:** `services/hub/app.py`, connection/state containers. **Time box:** 45-60 minutes.

1. Add /health and the WebSocket route. Use role and target_id query parameters for routing on the controlled local network. Reject unknown labels; these checks are not authentication.
2. Store run_id, current receipt, two drafts, target connections, and deduplication IDs in memory. Serve the built web UI on the same origin when integrating.
3. Send a full SNAPSHOT on connect and meaningful state changes. Maintain one active mobile controller and one connection per target; reject a duplicate rather than silently mixing them.
4. Run one server worker. Disable auto-reload for the actual demonstration. Make a Reset operation create a new run_id and clear the demo state.

**Pass:** phone and two targets receive the same run_id; a server restart visibly clears the run. **Bugs:** independent state across multiple workers, stale sockets, wrong target routing, pretending query labels authenticate clients.

### B2 - Detect the two markers and choose a stable target
**Depends on:** B1. **Own:** `services/hub/vision/`, generated marker assets. **Time box:** 60 minutes.

1. Use one dictionary, DICT_4X4_50, with IDs 10 and 20. Generate PNG assets for C; preserve their normal pattern and border.
2. Detect actual captured pixels. Choose only a marker in the configured central region. Reject ambiguous views; no candidate is better than guessing.
3. Require roughly 350 ms of stable observations. Clear the lock after roughly 600 ms without evidence, or immediately when a different target wins.
4. Process a latest-frame buffer in bounded background work. Ignore old stream/sequence results; never block the control loop with image processing.

**Pass:** look left/right and see the correct name; unknown/covered/ambiguous markers cannot confirm. **Bugs:** using CSS pixels, stale worker results, glare, overlapping target regions. [S3, S5]

<!-- PAGE -->
# 07 / Agent B: connect the workflow
## B3-B5 / Protect the visible demo

### B3 - Implement the receipt and preview state machine
**Depends on:** B1, B2; use C's fixture adapter until C3/C4 are ready. **Own:** `services/hub/workflow.py`. **Time box:** 60 minutes.

1. Implement STOPPED -> READY -> READING -> HOLDING -> PREVIEW -> APPLIED. Capture is allowed only in READY. SEND_AGAIN returns APPLIED to HOLDING using the same receipt.
2. Accept the frozen capture image once. Start extraction outside the event loop and tag its result with run_id and capture_id.
3. On Cancel/Stop, invalidate the active capture. Ignore its late response. Failure goes back to READY with a recapture message, not fabricated fixture success.
4. Create preview_id only for a validated receipt and a fresh, connected target. Retain it while those facts remain unchanged. Target loss/change invalidates it.
5. Accept CONFIRM only for the exact current preview_id. Recheck target freshness and connection at that point.

**Pass:** late OCR after Cancel does nothing; 50 unchanged frame observations do not break confirmation; switching to JSON cannot send an old Expenses preview to JSON.

### B4 - Apply once, broadcast, and provide one-level Undo
**Depends on:** B3. **Own:** `services/hub/drafts.py`. **Time box:** 45-60 minutes.

1. Use commit_id = preview_id. In one synchronous section, check the deduplication set, copy the previous selected draft, update that draft, and add commit_id. Do not await between the check and mutation.
2. Broadcast the new snapshot. The other destination must remain unchanged. Repeated CONFIRM for the same preview returns the current result without another write.
3. Undo restores the last changed destination's previous snapshot and clears the one-level undo slot. Both target UIs are read-only for this demo, so there is no manual-edit conflict feature.
4. A target DISPLAYED message changes feedback only. Missing DISPLAYED never causes another draft mutation. On browser reconnect, send the current snapshot.

**Pass:** send the same confirmation three times; one update occurs. Undo once restores the previous draft; Undo twice has no extra effect. Stop after Apply leaves the draft intact. **Bugs:** check-then-await races, shallow snapshot copies, acknowledgement-triggered replays.

### B5 - Connect all parts and run the short bug checklist
**Depends on:** A5, B4, C2, C4. **Own:** integration checks and runbook; request module fixes from its owner. **Time box:** 60-90 minutes.

Run a fixture transfer to each target, then real capture to each. Check the scenarios on page 11. Record actual results and timings. Verify the two distinct screens, source mode label, and clean reset. Confirm that running a slow extraction does not freeze target/status updates.

**Pass:** three rehearsals from Start through transfer and Undo succeed. The final commands are in the runbook. No test result is claimed from hardware that was not used. Do not add persistence or recovery features after this task; fix only observed blockers.

<!-- PAGE -->
# 08 / Agent C: both screens and extraction
## C1-C3 / Make the idea visible early

### C1 - Build Expenses and JSON from one target component
**Depends on:** K0 fixtures; no live device required. **Own:** `apps/web/`. **Time box:** 45-60 minutes.

1. Create /expense and /json. Both render TargetShell with a large central marker, target name, connection status, preview area, and applied-data area.
2. Expenses uses target_id `expenses`, marker 10, and read-only form fields. JSON uses target_id `json`, marker 20, and a plain-text JSON view. Both consume the same ReceiptRecord.
3. Use B's generated marker assets; do not redraw, recolor, or crop the marker. Keep a light margin around it and test its size in actual camera frames.
4. Render fixture states before connecting to the server. Keep the two windows visible side by side or on two laptops, with clearly separated target tiles.

**Pass:** both destinations exist at the first UI milestone. An Expenses preview never changes its applied fields. Long merchant names and missing tax fit. **Bugs:** only one target built, the same ID reused twice, a marker hidden under an overlay, JSON output treated as executable HTML.

### C2 - Add one clean socket and render server snapshots
**Depends on:** C1, B1. **Own:** `apps/web/src/connection/`. **Time box:** 45 minutes.

1. Connect using role=target and the route's correct id. Keep one socket per mounted target. Clean up subscriptions and reconnect timers on unmount.
2. Render full snapshots; do not maintain an independent authoritative draft. Ignore events from an obsolete socket after reconnect.
3. Send DISPLAYED with the matching commit_id after the applied state is rendered in the active page. Do not send it from preview rendering or socket receipt alone.
4. On refresh, accept the current server snapshot. On a new run_id, clear all old local display state. Do not replay confirmations.

**Pass:** React development remounting and a refresh do not create extra updates or duplicate active sockets. **Bugs:** effect cleanup missing, reconnection loops, stale closures, acknowledgement before rendering. [S4]

### C3 - Implement one extraction interface with fixture and real modes
**Depends on:** K0. **Own:** `services/hub/extraction/`, receipt fixtures. **Time box:** 45-60 minutes.

1. Expose `extract_receipt(image_bytes, mode)` with the same output in both modes. Fixture mode is explicit configuration and visibly labeled.
2. Use one provider with credentials already available. Send only the selected receipt image; credentials stay on the hub.
3. Request the declared fields and treat printed instructions as document content, not commands. Add an eight-second starting timeout and return a clear error on failure.
4. Do not call a model on every camera frame or destination switch. B handles background execution and discards canceled results.

**Pass:** one Capture creates one request. A network/provider failure returns an error, never an unannounced fixture record. **Bugs:** hidden fallback, exposed keys, blocking the event loop, model-selected destination.

<!-- PAGE -->
# 09 / Agent C: validate and present
## C4-C5 / Reliability the judges can see

### C4 - Validate the receipt and map it to both destinations
**Depends on:** C3. **Own:** `services/hub/extraction/validation.py`, shared fixture tests. **Time box:** 45 minutes.

1. Accept only the agreed fields. Merchant must be nonempty, date unambiguous and valid, currency EUR, and total_minor a nonnegative integer. Reject booleans as integers and do not silently truncate decimal values.
2. Missing tax is null and does not block the demo. Missing/uncertain required fields populate needs_review; confirmation stays disabled until recapture succeeds. Do not invent tax from the total.
3. Map the canonical record to expense labels and a JSON object deterministically. No second model call, generated code, or SQL execution.
4. Test the expected receipt, a changed amount, unreadable text, missing tax, ambiguous date, invalid JSON, and an instruction printed on the receipt.

**Pass:** the fixture yields 2480/EUR/2026-11-14, absent tax remains null, and both destinations use the same amount/date. **Bugs:** EUR 24.80 becoming 248000, locale comma mistakes, bool accepted as int, optional tax incorrectly blocking confirmation.

### C5 - Add clear feedback and prepare the demo
**Depends on:** C2, C4. **Own:** web feedback, printed receipt, demo notes. **Time box:** 60 minutes plus rehearsal.

1. Show candidate, locked, preview, sent, displayed, and disconnected with text as well as color. A green border means selection, not a completed write.
2. Prepare the large-print synthetic receipt from the starter pack. Start with roughly 18-point bold text and inspect an actual glasses capture. Move closer or increase text size if needed.
3. Add a small operator view showing current state, source mode, target name, last frame age, last error, and an explicit Reset Demo button. Keep it out of the normal user flow.
4. Write the 90-second script and capture a real backup video after the first successful integrated run. Save no unrelated camera footage.

**Pass:** a teammate can distinguish preview from applied data without explanation. The screen name and total agree with the glasses preview. Backup footage demonstrates actual implemented behavior, not a simulation presented as hardware.

### The simple 90-second script
1. Show the printed receipt and two different destination screens.
2. Capture once; show the extracted total.
3. Turn toward Expenses, then JSON, so the audience sees the target switch.
4. Confirm JSON; show it change while Expenses stays unchanged.
5. Choose Send Again, look at Expenses, and confirm the same receipt there.
6. Undo the last update. Explain that the prototype uses registered targets and one controlled document type.

**If time is short:** keep both target screens, fixture mode for development, and one working real extraction. Cut extra styling, spoken feedback, high-resolution still-photo modes, and every additional device category.

<!-- PAGE -->
# 10 / The bugs worth checking
## A short release checklist, not a production test suite

| Check | Trigger | Required behavior |
| --- | --- | --- |
| Wrong capture frame | Capture receipt A, immediately look at B. | The uploaded immutable image is A; the server never substitutes a later stream frame. |
| Double pinch | Repeat callback/CONFIRM three times. | One draft update for that preview_id. |
| Stale preview | Look at Expenses, then JSON, then deliver the old confirmation. | Reject it; do not redirect it to JSON. |
| Constant frames | Keep looking at one target through 50 observations. | The unchanged preview_id stays valid. |
| Target loss | Cover the marker and wait past the configured freshness limit. | Confirmation is disabled/rejected. |
| Late AI result | Cancel while the model request is running. | The result cannot recreate a preview. |
| Optional field | Receipt has no tax line. | tax_minor is null; otherwise valid data can proceed. |
| UI reload | Refresh one receiving page. | It renders the current hub snapshot; no new write occurs. |
| Server restart | Restart the hub with an upload in flight. | New run_id; old request rejected; visibly start a new run. |
| Lost screen | Disconnect the selected browser after confirmation. | Draft is not applied twice; feedback does not claim the screen displayed it. |
| Stop after apply | Stop immediately after transfer. | Camera/input stop; draft remains. Undo is explicit. |
| Slow model | Delay extraction by several seconds. | Status/Cancel remain responsive. |
| Real readability | Inspect the exact glasses image used by the model. | The printed fields are readable enough; enlarge/move the receipt if needed. |

### What has and has not been checked in this planning work
The revised dependency graph, message ownership, and producer/consumer coverage can be mechanically checked from the included manifest. These checks find missing tasks and circular dependencies. They do not prove application correctness, model accuracy, or device compatibility.

The scenarios above are acceptance tests for the team to run after implementation. They are not reported as passed here. A documented hardware failure should remain a failure until a human retests it.

### Final decision rule
The demo is ready when both destinations work, the live capture path is truthful, three full rehearsals succeed, and the failure cases you actually encounter have clear feedback. Do not spend the final hours implementing persistence, general-purpose security, or recovery dialogs for hypothetical production use.

<!-- PAGE -->
# 11 / Setup notes and evidence
## Keep implementation decisions separate from verified facts

### Hardware questions for Amanda
- Which Display/Neural Band/phone combination should this team use, and when can it be borrowed again?
- Which official sample and SDK version are known to work on this loaned firmware?
- Can camera streaming and a focused display-button callback run together?
- If not, what supported fallback can be demonstrated today?

### Network setup for the demo
Use one private router/hotspot and verify phone-to-laptop and laptop-to-laptop traffic before debugging app logic. Serve React and the hub from the same origin for the integrated demo. Use plain HTTP/WS for this controlled development setup.

Android cleartext policy is configurable. Put the allowance in a debug-only resource/manifest setup and test it on the actual phone; do not promise that adding two lines fixes every build or network issue. This plan does not prescribe an unverified iOS exception. If the loan uses an iPhone, use its working official sample and ask the booth for the local-network setup. [S2]

### Primary sources
**[S1] Meta Android DAT integration guidance**  
[github.com/meta/meta-wearables-dat-android/blob/main/AGENTS.md](https://github.com/meta/meta-wearables-dat-android/blob/main/AGENTS.md)  
Use the sample/reference matching the installed SDK. Registration, session readiness, capability attachment, and display callbacks are distinct steps.

**[S2] Android network security configuration**  
[developer.android.com/privacy-and-security/security-config](https://developer.android.com/privacy-and-security/security-config)  
Cleartext policy and application network-security configuration.

**[S3] OpenCV ArUco detection tutorial**  
[docs.opencv.org/4.x/d5/dae/tutorial_aruco_detection.html](https://docs.opencv.org/4.x/d5/dae/tutorial_aruco_detection.html)  
Dictionary, marker generation, and detection behavior.

**[S4] React useEffect documentation**  
[react.dev/reference/react/useEffect](https://react.dev/reference/react/useEffect)  
Effect cleanup and development setup/cleanup cycles; relevant to duplicate sockets/subscriptions.

**[S5] Starlette thread pool documentation**  
[starlette.dev/threadpool/](https://starlette.dev/threadpool/)  
Blocking work must not stall the application event loop. Keep concurrency bounded for this prototype.

Sources reviewed 14 November 2026. The supplied challenge details, device inventory, and mentor name come from your messages. Task durations, thresholds, architecture, and scope cuts are proposed engineering choices, not verified performance results.

**Start with A1 + K0 + C1.** Give each coding agent the common prompt, the shared contract, and one task. Keep the first milestone small enough to run before the next shared-device slot.
