# Android phone-first bridge

Task: [A2/A3, issue #6](https://github.com/mhirvasm/LineOfSightJunction2026/issues/6).
Branch: `feat/android-sdk-bridge`. Agent author: Codex. Responsible human: `mhirvasm`.
This is the separately requested Android implementation; iOS work stays on its
own branch. One controller and one hub remain the supported topology.

## What it does

- Connects the native app to `/v1/events?role=mobile` and renders shared hub state.
- Uses the real Meta SDK's MockDeviceKit with the handset's rear camera in
  explicitly labelled phone mode. The SDK display preview is interactive;
  its selection diagnostic counts callbacks without changing hub drafts.
- Sends JPEG pixels to `/v1/frames`, using a fresh stream UUID, increasing
  sequence, local delivery age, and the current run. Uploads have one request
  in flight and one replaceable newest pending frame. Old frames are dropped.
- Shows the last recognized screen separately from the current stable target.
  Looking at marker 10 chooses Expenses; marker 20 chooses JSON. No destination
  picker is used. Keep one whole marker inside the central outlined half.
- Stops camera/session work on Stop, Reset, disconnect, or backgrounding.
  Ordinary socket failures retry after 1.5 seconds, but camera/actions do not
  restart or replay. Duplicate-controller rejection requires a manual reconnect.
- Includes the real Display-glasses registration/permission/session path and
  one primary Capture/Confirm action. That path needs physical hardware testing.

The current B2 hub does not implement `/v1/captures` or receipt transfers. The
app checks the hub's OpenAPI paths and keeps Capture disabled when that endpoint
is absent. It never substitutes fixture output or reports a successful transfer.
The existing hub still reports receipt source `fixture`; camera source and
receipt source are shown independently. No receipt extraction is added here.

When the later hub implements the existing capture/confirmation protocol, the
bridge can upload an immutable copy of the current JPEG and confirm the exact
displayed run/preview. These client paths are not an implemented B3/B4 server.
The intended interaction remains face receipt, Capture, face screen, review
amount, Confirm. Setup and diagnostic controls are phone-only testing aids.

## Requirements and build

- Android Studio Narwhal (2025.1.1) or newer, with Android SDK API 36.
- JDK 17. The wrapper pins Gradle 8.13 and verifies its SHA-256 distribution hash.
- Android SDK Build-Tools 36.0.0 and Platform-Tools.
- Android 12/API 31 or newer; the Galaxy S23 is the intended first test handset.
- Meta DAT core/camera/display/mockdevice **1.0.1**, Kotlin **2.2.21**, Android
  Gradle Plugin **8.11.1**. Versions are explicit in the Gradle files.

Open this directory as a project in Android Studio and let it set the local
SDK location in ignored `local.properties`. No provider key or Meta app token
is needed for phone/mock mode. Optional real developer-mode metadata defaults
to the documented `0` placeholders. Other release channels need credentials
from the team's Meta project, outside tracked files:

```properties
mwdat_application_id=YOUR_APPLICATION_ID
mwdat_client_token=YOUR_CLIENT_TOKEN
```

From this directory on Windows:

```powershell
.\gradlew.bat assembleDebug testDebugUnitTest lintDebug
adb install -r app\build\outputs\apk\debug\app-debug.apk
adb shell am start -n fi.lineofsight.bridge/.MainActivity
```

On a Mac/Linux development machine with the Android SDK, use `./gradlew` for
the same tasks. Use the installed SDK's Platform-Tools `adb` if not on PATH.
Install and physical-camera behavior must be verified on the actual handset.
The APK is `app/build/outputs/apk/debug/app-debug.apk`; builds and local SDK
configuration are ignored by Git. Do not commit credentials, camera images,
device keys, or an APK.

The debug build permits the local HTTP/WS demo connection. The main/release
manifest disables cleartext traffic. This is a private-network prototype with
routing labels, not an authenticated public service.

## First phone test

1. Start the existing hub from the repository root:
   `python -m uvicorn services.hub.app:app --host 0.0.0.0 --port 8000`.
   Both phone and receiving laptops must reach it over the demo network.
2. Open `/expense` and `/json`, once each, on the receiving screens. Close
   `/fixture-mobile` and any other controller before using the Android app.
3. On the phone, leave physical glasses unchecked. Enter the actual hub origin,
   such as `http://YOUR-HUB-IP:8000`, and press Connect. Grant the requested camera
   and nearby-device permissions. The native app and Operator must say Connected
   and show the same hub run UUID. A phone cannot use the laptop's `127.0.0.1`.
4. Press Start camera test. The camera preview and SDK display preview should
   appear. Verify upright printed text and correct left/right. If the SDK feed
   arrives sideways, Stop, set the explicit rotation correction, and Start again.
   VideoFrame has no rotation field in this pinned API; do not guess orientation
   from width/height. Physical orientation is a required test, not assumed passed.
5. Face Expenses for at least a second, then JSON. Stable target should follow
   the fresh connected marker. A single still image is not replayed. Cover a
   marker or show an ambiguous central pair; the stable target must clear.
6. Press Show SDK selection test. Tap the primary action inside the SDK display
   preview ten times. Expect ten callbacks and no receipt/draft writes. This
   proves the mock SDK action path, not physical Neural Band input. Toggle the
   diagnostic again to return to marker feedback.
7. Reset from Operator. Preview and stream must clear; Start must create a new
   stream in the new run. Stop must release the camera without changing drafts.
8. Background/return, disconnect/reconnect, and temporarily lose network access.
   Camera and primary actions must stop; reconnect must not replay work. After
   foregrounding, press Connect and Start explicitly. No background operation
   or pocket-mode continuity is claimed for this first bridge.
9. Against the current hub, verify Receipt workflow unavailable remains disabled.
   No action in this marker test should fill either receiving draft.

Local upload age begins at SDK frame delivery, not sensor exposure. There is no
claim that it bounds end-to-end lag. JPEGs are limited to 2 MB/4 megapixels and
resized to a longest side of 1280 pixels. Frames are copied before asynchronous
conversion and never written to disk. Pixel conversion expects packed I420,
as in Meta's prior official uncompressed-camera sample; different layouts fail
visibly. Check actual orientation, colors, text readability, lag, and glare.

## Physical glasses later

Pair Display glasses and the band with the Meta AI app using the booth's known
working iPhone/Android account/device setup as appropriate. For this Android
bridge, verify that the loan supports the Android handset before relying on it.
Enable physical glasses setup, register the app, and grant glasses camera
permission. Phone/mock mode does not require the Meta AI companion app.

With the booth, prove changing real camera frames, actual display rendering,
and ten deliberate supported band selections together. The app attaches
capabilities only after session STARTED and uses the supported primary display
action; it does not depend on experimental raw-gesture access. Physical gesture
mapping, camera/display coexistence, firmware compatibility, and remove/re-wear
behavior remain hardware acceptance checks. Use the firmware/app update buttons
only when the real SDK reports a compatibility problem. Keep phone testing as
the honest fallback.

Actual verification and remaining checks are recorded in
[the task record](../../../docs/tasks/A2-A3-android-sdk-bridge.md).

## SDK evidence

- [Official Android SDK setup and lifecycle](https://github.com/meta/meta-wearables-dat-android/blob/main/AGENTS.md).
- [SDK release notes](https://github.com/meta/meta-wearables-dat-android/blob/main/CHANGELOG.md).
- [Official display/mock sample](https://github.com/meta/meta-wearables-dat-android/tree/main/samples/DisplayAccess).
- [Prior official I420 camera sample](https://github.com/meta/meta-wearables-dat-android/blob/4e56e1864a5e78194bababc3a68775c4196cbed0/samples/CameraAccess/app/src/main/java/com/meta/wearable/dat/externalsampleapps/cameraaccess/stream/StreamViewModel.kt).

Source inspected 14 November 2026. The app compiles against the published pinned
artifacts; SDK documentation or compilation does not pass physical-device checks.
