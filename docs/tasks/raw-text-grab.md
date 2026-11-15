# A4/B4/C4: raw text grab and paste

Issue: [#16](https://github.com/mhirvasm/LineOfSightJunction2026/issues/16).
Branch: `feat/raw-text-grab`. Agent author: Codex. Responsible human: `mhirvasm`.
Baseline: `14f585d419d5ca7f09be9fdb784cfda0bdea90c0`, Android 0.2.1. This source
commit remains available for rebuilding; later Gradle output cleanup removed its
local versioned APK. Android 0.3.0 is now archived outside Gradle outputs at
`runtime/apk-archive/LineOfSight-0.3.0.apk`. No main-branch merge.

## Result and scope

Android 0.3.0 captures a whole visible block with the existing hold gesture.
One Gemini/OpenAI request returns literal text plus optional validated receipt
fields. The phone shows a text excerpt before a destination is selected. The
glasses HUD receives the same text, limited to a short excerpt. The receiving
page shows the full transcription. No content-mode menu is added.

- Text `/text`, marker 30: replace the previous pasted text with the transcription.
- JSON `/json`, marker 20: preserve receipt JSON when valid, otherwise `{text}`.
- Expenses `/expense`, marker 10: accept only a validated EUR receipt. A note
  leaves the hold active with an incompatibility message and no confirm action.

Keep holding while aiming, then drag right to apply exactly once. Release before
apply cancels. A paste attempt with no valid compatible destination cancels.
Acknowledgement, Undo, Send Again and a fresh capture after apply are preserved.
Line breaks and Unicode are data; HTML-looking text is rendered literally.
Text is bounded to 8000 characters. Empty/oversized/unreadable captures fail visibly.

No individual-word selection, automatic OS clipboard write, or insertion into
third-party applications is implemented. Handwriting recognition is requested
from the provider but remains unverified on actual handwriting. Review the OCR;
schema validation does not guarantee correct spelling or values.

## Changed components

`services/hub/extraction/content.py` adds the combined result and validation;
`receipt.py` shares the existing provider transport. Hub workflow/connections,
marker detection, `contracts/targets.json` and protocol add Text and route each
validated payload. Android Protocol/MainActivity/BridgeRuntime show text and the
third destination. React main/styles/PhotoTest render Text and retain receipts.
Synthetic note/receipt fixtures, marker 30, regression checks and run instructions
complete the change. No dependency or SDK version upgrade.

## Verification performed

Commands below use `.venv/Scripts/python.exe` from the repository root:

| Command | Actual result |
| --- | --- |
| `scripts/verify_workflow.py` | 18 passed: content bounds, literal Unicode/markup, provider contracts, text routing, incompatible Expenses, stale/duplicate operations, cancellation, acknowledgement, Undo and Send Again. |
| `scripts/verify_vision.py` | 10 passed, including actual marker 30 JPEG decoding. |
| `scripts/verify_hub.py` | 6 passed. |
| `scripts/verify_foundation.py` | 4 passed, including all three page routes and marker PNGs. |
| `scripts/verify_hub_server.py` | Real HTTP/WebSocket connection/reset/reconnect smoke passed. |
| `scripts/verify_workflow_server.py` and `--text` | Both full fixture flows passed. |
| `scripts/verify_workflow_server.py --live` and `--live --text` | Both full Gemini HTTP/WebSocket flows passed for all compatible destinations. |
| `scripts/verify_live_text.py` | Two live printed notes passed exact wording/line checks in 4.2s and 3.8s; the second changed time/color and included literal markup. |
| `scripts/verify_live_receipts.py` | New combined extraction read EUR 24.80 in 3.9s and EUR 31.90 in 4.4s, with merchant/date and transcription assertions. |
| `node --test apps/web/src/connection/socket.test.js` | 4 passed. |
| `node apps/web/node_modules/vite/bin/vite.js build apps/web` | Passed with existing Vite 8.3.8. Equivalent to the package build script. |

The first live note check returned extra blank lines. Instructions now request
one newline per visible line, and the synthetic image uses ordinary line spacing;
the exact-output retest passed. No output normalization hides provider errors.
These paid live checks use generated synthetic images, not physical camera input.

Browser inspection on an isolated fixture hub confirmed marker 30, held-text
preview, applied text with line breaks, Expenses amount preview, and applied JSON.
An actual browser Text client received a transfer and sent DISPLAYED. No browser
warnings/errors were observed. A first temporary tab disappeared before the check;
the check passed after reopening it. Temporary fixture server/tabs are closed
after inspection. This is not physical phone or glasses validation.

Android build command on this Windows checkout:

```powershell
$env:JAVA_HOME = (Get-ChildItem '.tools/android-bootstrap/jdk' -Directory | Select-Object -First 1).FullName
$env:GRADLE_USER_HOME = Join-Path (Get-Location) '.tools/android-gradle-cache'
$env:ANDROID_USER_HOME = Join-Path (Get-Location) '.tools/android-user'
& .tools/android-bootstrap/gradle-8.13/bin/gradle.bat -p apps/mobile/android --offline --no-daemon --console=plain '-Pkotlin.incremental=false' --rerun-tasks assembleDebug testDebugUnitTest lintDebug
```

Result: build passed, 21 JVM tests passed, lint zero errors and 26 warnings.
DAT 1.0.1, Kotlin 2.2.21, AGP 8.11.1, Gradle 8.13, JDK 17 and API 36 are unchanged.
APK: `LineOfSight-0.3.0.apk`, version code 4.
SHA-256: `1f47701a17c60c68f309900fba724a5d1e208b1ee3e79907301544609c272139`.

## Startup and physical retest

Use the current Wi-Fi IPv4 address from `ipconfig`; do not retain an old hotspot
address. On the hub laptop, use one configured demo hub:

```powershell
.venv/Scripts/python.exe scripts/run_hub.py
.venv/Scripts/python.exe -m http.server 8001 --bind 0.0.0.0 --directory apps/mobile/android/app/build/outputs/apk/debug
```

Run the APK server in a separate terminal. The ignored `.env` selects live Gemini
and holds its key. Fixture testing must be explicit: LOS_EXTRACTION_MODE=fixture
and LOS_FIXTURE_CONTENT=text or receipt. Live mode never uses those fixtures.

1. Install `http://HUB-IP:8001/LineOfSight-0.3.0.apk` over the old app. Verify 0.3.0.
2. Enter `http://HUB-IP:8000`, Connect, then Start camera test. Leave physical
   glasses/raw band unchecked for the S23 simulation.
3. Open `http://HUB-IP:8000/text` on a receiving computer and keep it visible.
   Close duplicate tabs for that target. Refresh older Expenses/JSON pages.
4. Aim at a short printed note (or `/fixtures/text_demo.html`). Hold the green
   area until the transcription appears. Keep holding and aim at Text marker 30.
5. After the destination says Text, slide the same finger right. Verify exact
   text/line breaks on only that page. Release; the pasted text should remain.
6. Repeat with changed wording and with a handwritten note. Record actual OCR
   accuracy separately. Test cancel while reading, paste with no target, and
   aiming a note at Expenses. No inappropriate draft should change.
7. Test Undo, a fresh hold after apply, and a receipt to Expenses and JSON.
8. On glasses, verify readable camera pixels, HUD excerpt, raw band direction,
   cancellation and target selection together. Hardware access remains pending.

Human S23 checks, handwriting checks and glasses checks remain open on issue #16.
The responsible human reviews and merges after the applicable acceptance checks.
