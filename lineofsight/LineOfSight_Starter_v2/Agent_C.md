# Agent C - LineOfSight demo tasks

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
