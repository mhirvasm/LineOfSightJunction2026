# C4/A4/B4: text analysis and simulated Coffee

Issues: [#18](https://github.com/mhirvasm/LineOfSightJunction2026/issues/18) and
[#19](https://github.com/mhirvasm/LineOfSightJunction2026/issues/19).
Branch: `feat/text-analysis-coffee-demo`. Agent author: Codex. Responsible human:
`mhirvasm`. Review base: `feat/raw-text-grab`.

Previous verified source baseline: `e45f1ab34d69ee4a8b8bb4a67841313bce34c701`,
Android 0.3.0. Its APK is preserved at the ignored
`runtime/apk-archive/LineOfSight-0.3.0.apk`, outside Gradle output cleanup.
No main-branch merge or automatic merge is performed.

## Result and changed components

Android 0.4.0 keeps hold/aim/swipe without a content menu. Text-only captures get
a second text-only provider request for conservative correction and a short
summary. The original OCR remains visible on Text. Failed analysis keeps the
original with a fallback label; receipts bypass analysis. Semantic accuracy still
needs human review. See `services/hub/extraction/analysis.py`, the shared provider
transport, workflow and connections, and `contracts/protocol.md`.

Coffee at `/coffee` has marker 40. Aim there before holding; a right swipe confirms
the proposed on/off state. Looking or holding alone never toggles it. Release
before swipe cancels; repeated confirm cannot toggle twice. Coffee has no capture
upload or provider request. Stop/disconnect preserves its state; Undo restores the
previous action and Reset turns it off. Existing drafts remain intact. This is
a simulated appliance with SVG/CSS coffee and steam animation.

Changed UI: Android Protocol, HubClient, BridgeRuntime, MainActivity and MetaBridge;
React main/styles/PhotoTest plus CoffeeMachine; target configuration and marker PNG.
Fixtures and focused workflow, HTTP/WS, vision, native and foundation checks cover
the extensions. No dependency or SDK version upgrade.

## Verification performed

Python commands use `.venv/Scripts/python.exe` from the repository root.

| Command/check | Actual result |
| --- | --- |
| `scripts/verify_workflow.py` | 26 passed: analysis fallback/cancel/stale completion, text and receipt routing, coffee on/off/cancel/duplicate/Undo/reset and no extraction. |
| `scripts/verify_vision.py` | 10 passed, including decoding marker 40 from JPEG pixels. |
| `scripts/verify_hub.py` | 6 passed. |
| `scripts/verify_foundation.py` | 4 passed, including routes and marker assets. |
| `scripts/verify_hub_server.py` | Real connection/reset/reconnect/restart checks passed. |
| `scripts/verify_workflow_server.py` and `--text` | Full receipt and text fixture flows passed after Coffee integration. |
| `scripts/verify_coffee_server.py` | Real HTTP/WS marker look/hold/cancel/on/off, duplicate confirm, acknowledgement and unchanged drafts passed. |
| `scripts/verify_live_analysis.py` | Live Gemini grammar and negation/uncertainty cases passed in 4.2s and 4.7s. |
| `scripts/verify_live_receipts.py` | Live combined extraction read 24.80 and changed 31.90 with merchant/date/transcription checks, 6.5s and 4.7s. |
| `scripts/verify_workflow_server.py --live` and `--live --text` | Both passed with the new analysis phase; the text flow passed again after Coffee integration. |
| `node --test apps/web/src/connection/socket.test.js` | 4 passed. |
| `node apps/web/node_modules/vite/bin/vite.js build apps/web` | Passed with existing Vite 8.3.8. |

The initial live URL-preservation check rejected a sentence-ending period as part
of the URL. The validator now excludes trailing sentence punctuation; regression
and live retest passed. The initial Coffee socket check waited for an unnecessary
snapshot after unchanged fresh observations. It now uses the last received state;
the real on/off flow passed. Neither fix relaxes target freshness or confirmation.

Browser inspection on an isolated fixture hub showed corrected text, summary,
original OCR and the receipt amount. An actual Coffee browser client rendered
off/on/off and acknowledged both commits using:
`scripts/verify_coffee_server.py --port 8010 --browser --once` (twice).
Brewing streams/steam appeared while on and disappeared while off. Temporary
fixture server and tabs were closed. These are software checks with synthetic
inputs, not physical phone/glasses tests. Live extraction used Gemini; OpenAI
transport is covered by mocked request tests, not a new live OpenAI run.

Final native command:

```powershell
$env:JAVA_HOME = (Get-ChildItem '.tools/android-bootstrap/jdk' -Directory | Select-Object -First 1).FullName
$env:GRADLE_USER_HOME = Join-Path (Get-Location) '.tools/android-gradle-cache'
$env:ANDROID_USER_HOME = Join-Path (Get-Location) '.tools/android-user'
& .tools/android-bootstrap/gradle-8.13/bin/gradle.bat -p apps/mobile/android --offline --no-daemon --console=plain '-Pkotlin.incremental=false' assembleDebug testDebugUnitTest lintDebug
```

Passed in 1m47s; 25 JVM tests, zero failures; lint zero errors and 26 warnings.
DAT 1.0.1, Kotlin 2.2.21, AGP 8.11.1, Gradle 8.13, JDK 17 and API 36 unchanged.
APK `LineOfSight-0.4.0.apk`, version code 5, 41,279,475 bytes; APK v2 signature verified.
SHA-256: `f681ae4bfe978ba1935925144fce14e99879b03ea8c6b669f59597c2661481ff`.
Archived outside Gradle outputs in `runtime/apk-archive/` and copied to the served
APK directory after build. Do not rebuild during a phone download.

## Startup and human phone checks

Use one configured demo hub and a separate terminal for APK serving:

```powershell
.venv/Scripts/python.exe scripts/run_hub.py
.venv/Scripts/python.exe -m http.server 8001 --bind 0.0.0.0 --directory apps/mobile/android/app/build/outputs/apk/debug
```

The ignored `.env` selects live Gemini and stores its key. Never commit it.
Use `ipconfig` for the current Wi-Fi IPv4 address; network changes invalidate old
links. At handoff, health, Text, Coffee and APK returned HTTP 200 through the LAN IP.

1. Install `http://HUB-IP:8001/LineOfSight-0.4.0.apk`. If the browser download
   finishes without launching installation, open My Files > Downloads and tap
   the APK. Keep the existing app data and confirm version 0.4.0.
2. Enter `http://HUB-IP:8000`, Connect, Start camera test. Keep physical
   glasses/raw band unchecked for the S23 gesture simulation.
3. Open `/text` on a receiver. Aim at `/fixtures/text_analysis_demo.html` or a
   short note with grammar mistakes. Hold through reading and analysis. Compare
   corrected text and summary; aim at Text marker 30 and swipe right. Confirm
   original, correction and summary are visible separately.
4. Release during analysis: no paste or late revived preview. Repeat with a
   handwritten note and record actual OCR accuracy. Verify a receipt still sends
   its amount to Expenses and canonical receipt fields to JSON.
5. Open `/coffee` on a receiver and keep marker 40 visible. Aim until Coffee is
   selected. Hold then release: it remains off. Hold and swipe right: brewing
   begins. Release: it stays on. A fresh hold and swipe stops it.
6. With Coffee selected, aim away before swiping: no toggle. Aim held text at
   Coffee: no toggle. Undo restores the last action. Refresh Coffee: the current
   machine state remains. Operator Reset turns it off.
7. Test the same camera/target/HUD/raw-band sequence on actual glasses when
   available. Verify rightward input coordinates and release cancellation.

S23 installation/physical gestures, handwriting accuracy and glasses remain
pending. The responsible human reviews, performs these checks and decides on
merging the draft PR. This software verification does not close hardware scope.
