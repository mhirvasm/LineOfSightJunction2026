# Agent B - LineOfSight demo tasks

Read contracts/protocol.md first. This pack supersedes the earlier implementation plan. Run one task at a time and use the owned paths in each card.

## Common prompt

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
