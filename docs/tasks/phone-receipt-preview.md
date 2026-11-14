# A4/A5: visible phone receipt preview

Issue: [#14](https://github.com/mhirvasm/LineOfSightJunction2026/issues/14).
Branch: `fix/phone-receipt-preview`, based on `941f43b` (pre-glasses build).
Author: Codex (agent-authored). Responsible human: `mhirvasm`.

## Problem and change

The phone's hold surface and receipt feedback were separated by a long scrolling
page. Releasing to find the preview cancels the interaction. At investigation the
hub was connected to the phone and both receivers, with state READY and feedback
Canceled. That observation alone does not establish whether reading succeeded.

Android 0.2.1 keeps the live camera, parsed receipt, stable destination, hold
surface and concise status in one fixed panel. Setup and diagnostics scroll
separately below it. Amount, merchant and date are visible in HOLDING before a
destination is selected. Reading, capture-not-started and cancellation have
visible feedback near the finger. This is a parsed receipt preview; the camera
continues to show live pixels for aiming at a receiving marker.

A separate repeat-capture defect was found: a synchronous UI refresh during a
new capture could see the old APPLIED snapshot and consume the new hold. APPLIED
now consumes only the matching capture. Regression checks cover sending and
canceling a fresh hold while the previous applied snapshot is still visible.

The hub now distinguishes extraction timeouts in its feedback. No automatic
retry, provider switch, or fixture fallback is added.

## Verification

- Gemini recheck: the first request timed out; subsequent model access returned
  HTTP 200. Actual generated receipt images then passed at EUR 24.80 in 4.5 seconds
  and EUR 31.90 in 3.9 seconds, with correct merchant/date validation.
- The complete live HTTP/WebSocket capture flow passed with Gemini, both
  destinations, acknowledgement, duplicate confirmation, cancellation and Undo.
- Thirteen workflow/extraction checks passed, including visible timeout feedback
  with no draft mutation. The integration test now allows the actual extraction
  timeout while waiting for a receipt; other event waits keep their short limit.
- Android build/JVM/lint results and APK checksum are recorded after the final
  build below. A stale Kotlin test binary after a constructor change required
  recompiling tests without incremental compilation.
- Physical S23 visibility and hold behavior remain pending human verification.
  No emulator or desktop rendering is claimed as physical phone validation.

## Retest

Install the versioned 0.2.1 APK over the existing app. Confirm the version label
at the top. Use the current laptop IP for both APK and hub; it can change on Wi-Fi.
Connect and Start in the setup area below the fixed panel. Leave physical glasses
and raw band unchecked. Face the demo receipt, hold the green surface and keep
holding for the result. The amount, merchant and date should appear immediately
above the hold surface without scrolling or choosing a destination. Then aim at
Expenses or JSON and slide right. Release and repeat with a fresh hold. Also
release during Reading and check that it cancels without changing either draft.

Prior verified build: `941f43b251f039fbcd98e4dc3ca241a0f4b1caf4` (Android 0.2.0).
Its APK was preserved locally as `LineOfSight-0.2.0.apk` before rebuilding.

## Final build

Android assembleDebug, testDebugUnitTest and lintDebug passed after a complete
non-incremental compilation: 18 JVM checks, zero lint errors. The existing hub
connection smoke and complete fixture flow also passed after timeout-test changes.
APK: `LineOfSight-0.2.1.apk`. SHA-256: `aace0c40904729c9f8e709f88b0fec5b674852dcae88406135b2e1e31a3bfad1`.
S23 fixed-panel inspection remains pending; no device screenshot is claimed.
