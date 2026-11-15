# A2/A3: Android phone-first SDK bridge

Issue: https://github.com/mhirvasm/LineOfSightJunction2026/issues/6.
Branch: `feat/android-sdk-bridge`, based on `chore/k0-bootstrap` at `366fb5b`.
Agent author: Codex. Responsible human: `mhirvasm`.
Dependencies: [K0 #1](https://github.com/mhirvasm/LineOfSightJunction2026/issues/1),
[B1 #2](https://github.com/mhirvasm/LineOfSightJunction2026/issues/2),
[B2 #4](https://github.com/mhirvasm/LineOfSightJunction2026/issues/4).

## Scope and result

The human explicitly requested a separate Android branch and implementation
after selecting iOS first. This task adds a native Kotlin Android bridge with
published Meta DAT 1.0.1 camera/display/mockdevice/core dependencies. It does
not alter the iOS branch, hub workflow, protocol, or receiving web pages.

`apps/mobile/android/` contains the pinned Gradle project/wrapper, manifests,
native UI, Meta session adapter, hub transport, action/stream guards, pixel
conversion, tests, and build/device runbook. The phone uses the rear camera
through MockDeviceKit and a labelled simulated-band display preview. The real
glasses path includes registration, camera permission, session/capability
lifecycle, and a primary display action; it is not physically verified yet.

Frame work is bounded at conversion and upload, with immutable copied buffers,
conflated pending slots, fresh run/stream/sequence metadata, and request timeouts.
Stop, Reset, disconnect, source replacement, and backgrounding release active
work. Socket recovery does not restart a camera or replay old actions. One
phone/controller and both receiving destinations remain the supported scope.

Capture is gated by the actual hub OpenAPI capture endpoint. B2 has none, so
Capture stays disabled. The future-compatible capture/confirm adapter freezes
the exact local JPEG and binds confirmation to the displayed run/preview;
receipt extraction, server state transitions, transfers, Send Again, and Undo
still require the separate B3/B4/C3/C4 work. The SDK selection diagnostic changes
only a local counter and cannot change receiving drafts.

## Acceptance and physical checks

- Native debug build, nine protocol/lifecycle tests, and lint: passed.
- Actual Galaxy S23 install/start/SDK mock camera: pending device connection.
- Phone-to-hub stable selection for Expenses and JSON: pending physical test.
- Ten SDK preview callbacks on handset: pending physical test.
- Phone rotation/readability, glare, latency, interruption and recovery: pending.
- Real glasses camera, display, band, and same-session coexistence: NOT TESTED.

The issue stays open until its acceptance criteria pass or the human records a
scope change. A draft PR is for review, not a claim of physical-device success.

## Verification record

Verified software build checkpoint: `132ecaf5f5162b8523ec8b60359f414d71873aca`.
This is the compiled/tested source commit, not a known-good hardware build.


Build environment prepared locally inside ignored `.tools/`: Azul OpenJDK
17.0.21, Gradle 8.13, Android command-line tools 19.0, API 36, Build-Tools 36.0.0.
The SDK/Gradle distributions were downloaded with certificate validation;
Gradle and Android command-line tools were checked against official distribution
checksums. No global Java/Android installation or dependency upgrade was needed.

Commands from the repository root (the standard project-local equivalent is
`apps/mobile/android/gradlew.bat assembleDebug testDebugUnitTest lintDebug`):

```powershell
$env:JAVA_HOME = (Get-ChildItem '.tools/android-bootstrap/jdk' -Directory | Select-Object -First 1).FullName
$env:GRADLE_USER_HOME = Join-Path (Get-Location) '.tools/android-gradle-cache'
$env:ANDROID_USER_HOME = Join-Path (Get-Location) '.tools/android-user'
& .tools/android-bootstrap/gradle-8.13/bin/gradle.bat -p apps/mobile/android --no-daemon --console=plain assembleDebug testDebugUnitTest lintDebug
.\.venv\Scripts\python.exe scripts/verify_vision.py
.\.venv\Scripts\python.exe scripts/verify_vision_server.py
```

- The debug APK compiled successfully. Output is ignored by Git.
- Nine native JVM tests passed: six protocol/action/pixel-layout checks and
  three real HTTP/WebSocket transport checks. Tests cover stale run/preview
  rejection, endpoint gating, frame age/size bounds, pixel plane conversion,
  one in-flight/newest-pending behavior, Reset cancellation, explicit restart,
  and duplicate-controller rejection without a reconnect loop.
- The first transport run exposed test-server cleanup calling a client-only
  cancel method on the mock server socket. Cleanup was corrected and all nine
  checks passed. This was a test harness failure, not a device test.
- Lint first found an incorrectly escaped drive separator in ignored local SDK
  configuration. The local property was corrected. Final lint passed with zero
  errors and 22 warnings, primarily version suggestions, English diagnostic
  strings, portrait-mode guidance, and backup configuration suggestions. Pinned
  dependencies were retained; no lint baseline or error suppression was added.
- All ten existing vision checks passed. The real hub HTTP/JPEG/WebSocket smoke
  test passed target acquisition/switching, ambiguity rejection, Stop, and no
  draft mutation. A pre-existing Starlette deprecation warning is non-failing.
- Local ADB 37.0.1 runs with the Windows USB backend (`ADB_LIBUSB=0`). An isolated
  test server on port 5038 listed no connected Android devices. Windows' filtered
  device query likewise showed no Galaxy/Android/ADB phone at that point. USB
  connection/debugging authorization is pending; no handset result is claimed.

## Install without USB

The debug APK can also be downloaded over the demo network. From the repository
root, the following command serves only the build output directory:

```sh
python -m http.server 8001 --bind 0.0.0.0 --directory apps/mobile/android/app/build/outputs/apk/debug
```

Open `http://YOUR-HUB-IP:8001/app-debug.apk` on the phone and install it manually.
The server was started for this test; HEAD requests to both localhost and the
laptop's Wi-Fi address returned HTTP 200 for the APK. The existing hub health
endpoint likewise returned HTTP 200 / ok true. This verifies laptop-side
serving only; phone download/install and camera behavior remain pending. Keep
the hotspot on, enter the hub origin on port 8000 in the app, and close other
mobile/controller tabs. Stop the temporary APK server after installation.

## Human handoff

Review the branch/issue, install the APK on the Galaxy S23, and follow the
[Android runbook](../../apps/mobile/android/README.md). Record actual phone
checks separately from JVM mocks and actual glasses checks. Close any browser
test controller before connecting the native app. Keep the reviewed source
baseline `366fb5b` available; it is not a verified native/hardware build.
