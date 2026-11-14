# Agent A - LineOfSight demo tasks

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
