# Pre-glasses implementation and rehearsal

Branch: `feat/pre-glasses-workflow`, based on the Android planning checkpoint
`f9503e567eb15874d7c178f998e30dc0ba00afb8`.
Primary author: Codex (agent-authored). Responsible human: `mhirvasm`.
Tasks: [B3 #8](https://github.com/mhirvasm/LineOfSightJunction2026/issues/8),
[B4/C2 #9](https://github.com/mhirvasm/LineOfSightJunction2026/issues/9),
[A4 #10](https://github.com/mhirvasm/LineOfSightJunction2026/issues/10),
[C3/C4 #11](https://github.com/mhirvasm/LineOfSightJunction2026/issues/11),
[A5/B5/C5 #12](https://github.com/mhirvasm/LineOfSightJunction2026/issues/12).
The user authorized building the entire phase together. Review/integration stays
with the human; no agent merge or automatic merge is authorized.

## Result

- The hub accepts one frozen capture, reads and validates a receipt, previews the
  fresh connected destination, applies once, acknowledges screen rendering, and
  supports one-level Undo. Capture-correlated cancellation protects against an
  upload arriving after release and late extraction after Stop/Reset.
- Expenses and JSON receive the same canonical record. Previewing never writes.
  Hidden pages defer DISPLAYED until visible; reload never repeats a transfer.
- Android 0.2.0 adds a hold/drag/release touch surface and shared controller,
  a pinned Meta DAT 1.0.1 Inputs adapter, compact display feedback, and a real-device
  foreground service with Stop notification. Phone-camera mock mode stays foreground.
- Live extraction explicitly selects Gemini or OpenAI. The user requested Gemini
  after OpenAI returned HTTP 429 / credit_balance_exhausted. Gemini 2.5 Flash
  returned not available to new users; the provider-directed replacement,
  `gemini-3.8-flash`, successfully read the known and changed-total synthetic receipts.
  There is no automatic provider or fixture fallback. Credentials are only in
  ignored local `.env`; no key is compiled into the APK.

Main changed areas: `services/hub/workflow.py`, `extraction/receipt.py`, hub/vision
integration, Android input/runtime/service classes and MainActivity, React
receiving-page acknowledgement, protocol, startup and verification scripts.

## Startup and installation

From the repository root on the demo Windows laptop:

```powershell
.\.venv\Scripts\python.exe scripts/run_hub.py
```

`scripts/run_hub.py` reads `.env`; environment variables override file values.
Copy `.env.example` to `.env` only when configuring a new checkout; do not overwrite
existing local credentials. For live Gemini set `LOS_EXTRACTION_MODE=live`,
`LOS_EXTRACTION_PROVIDER=gemini`, `GEMINI_API_KEY`, and
`LOS_GEMINI_MODEL=gemini-3.8-flash`. Keep secrets out of terminals, screenshots,
issues, and Git. Only the frozen receipt goes to the selected cloud provider.

For a deliberate fixture rehearsal in a separate terminal:

```powershell
$env:LOS_EXTRACTION_MODE = 'fixture'
.\.venv\Scripts\python.exe scripts/run_hub.py
```

Run only one demo hub. Stop it before changing modes. Remove that environment
override to return to `.env` mode. Fixtures always return the labelled Demo Cafe
EUR 24.80 record; they do not read the image.

Serve the APK without USB:

```powershell
.\.venv\Scripts\python.exe -m http.server 8001 --bind 0.0.0.0 --directory apps/mobile/android/app/build/outputs/apk/debug
```

Install `http://HUB-IP:8001/app-debug.apk` over the existing app, then set its hub
origin to `http://HUB-IP:8000`. Open `/expense` and `/json` on the receiving screens.
The LAN IP can change; read the current Wi-Fi IPv4 address. Close extra receiver
tabs and `/fixture-mobile` before testing. Keep the laptop awake and on the same
reachable network as the phone.

## Phone rehearsal

1. Leave physical glasses unchecked, Connect, then Start camera test. Check the
   source label, upright receipt text, and fresh preview; correct rotation while stopped.
2. Face a receipt and press/hold the green PHONE SIMULATION surface. The rear
   camera supplies real pixels; the touch surface simulates the band.
3. Keep holding while extraction completes, then face one destination marker.
   Check destination and amount. Move the same finger right at least 80 dp.
4. Confirm that only that receiving page changes and reports the result. Release:
   the applied draft must remain. Repeat on the other destination with a fresh hold.
5. Hold/release during reading; try a rightward paste while no screen is selected.
   Both cancel without changing drafts. Movement while Reading never queues a send.
6. Test Undo, another fresh grab, target loss, hub Reset and reconnect. Phone
   backgrounding stops mock camera mode; Connect/Start explicitly after returning.
7. Repeat the complete two-destination flow three times and record actual phone
   results. These rehearsals are pending until the human performs them.

Tap Capture/Confirm remains an explicit diagnostic fallback. It is disabled while
the touch hold owns the interaction and when raw band mode is active. Send Again
uses a new preview and tap confirmation; it is not mapped to an unverified gesture.

## Glasses slot

Before access, arrange compatible Display glasses/band, Meta AI pairing,
registration, camera permission, and WDC Inputs capability approval. Raw Inputs is
experimental. Check physical-glasses mode and raw band mode before Start; enter a
positive drag threshold in device units. Initial 80 is only a calibration value,
not a verified physical distance. Read the diagnostic DOWN/MOVE/UP coordinates,
confirm rightward direction, and calibrate before attempting a transfer.

Verify camera/display/input together, whole-receipt readability, each destination,
release cancel, no-target paste cancel, screen lock, remove/re-wear, and restart.
Hardware recognition and background behavior remain untested. If raw Inputs is
unavailable, explicitly stop and switch to primary-action tap fallback; report
that reduced interaction. No silent fallback occurs.

## Verification record

Software checks on 14 November 2026:

- `scripts/verify_hub.py`: six checks passed.
- `scripts/verify_hub_server.py`: real HTTP/WebSocket connection smoke passed.
- `scripts/verify_vision.py`: ten checks passed after correcting target-loss
  preview invalidation exposed by the original regression test.
- `scripts/verify_vision_server.py`: real JPEG/HTTP/WebSocket marker smoke passed.
- `scripts/verify_foundation.py`: four checks passed.
- `scripts/verify_workflow.py`: twelve checks passed, including both provider
  request contracts, strict validation, cancellation ordering, stale/duplicate
  operations, both destinations, acknowledgement, Undo and Send Again.
- `scripts/verify_workflow_server.py`: complete fixture HTTP/WebSocket flow passed.
- `scripts/verify_workflow_server.py --live`: complete real Gemini HTTP/WebSocket
  flow passed, including both destinations, cancellation and Undo.
- `scripts/verify_live_receipts.py`: actual Gemini calls read generated EUR 24.80
  and EUR 31.90 receipts correctly, including merchant/date. This is live model
  validation with synthetic images, not physical-camera OCR validation.
- `node --test apps/web/src/connection/socket.test.js`: four checks passed.
- `npm --prefix apps/web run build`: passed; both receiving pages visually
  inspected. Both actual browser clients rendered the fixture record and sent
  DISPLAYED acknowledgements during an HTTP/JPEG/WS rehearsal.
- Android `assembleDebug testDebugUnitTest lintDebug`: build passed; fifteen JVM
  checks passed, including injected real SDK Drag event types. Lint: zero errors,
  25 warnings (mainly existing UI localization/version suggestions).

Build uses the local JDK/Gradle command in the Android bridge task record, DAT
1.0.1 (now including Inputs), Kotlin 2.2.21, AGP 8.11.1, Gradle 8.13, JDK 17,
API 36. Sandbox-only daemon/network restrictions required the existing approved
build execution path; versions were not upgraded.

The earlier Android source checkpoint `132ecaf5f5162b8523ec8b60359f414d71873aca`
remains the prior build baseline. The human reported the earlier APK working.
This new build requires S23 rehearsal and physical glasses checks; issues remain
open until acceptance. Record the accepted commit and APK SHA-256 before the slot.

References: [Meta Inputs](https://github.com/meta/meta-wearables-dat-android/blob/main/.cursor/rules/inputs.mdc),
[foreground service example](https://github.com/meta/meta-wearables-dat-android/blob/main/samples/CameraAccess/app/src/main/java/com/meta/wearable/dat/externalsampleapps/cameraaccess/stream/StreamingService.kt),
[OpenAI image input](https://developers.openai.com/api/docs/guides/images-vision),
[Gemini generation API](https://ai.google.dev/api/generate-content).

Verified APK SHA-256: `64c40727d2475b7a7143f64c531706c59f9e6e86576657b38c234616c2a9c06e`.
