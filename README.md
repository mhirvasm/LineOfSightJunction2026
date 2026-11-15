# LineOfSight

## Current demo: text summaries, receipts and Coffee

Use Android 0.4.0 with the hub on the same network. Hold to capture text or a
receipt, face a registered destination, and drag right to paste; release cancels.
Open `/text` (marker 30) for corrected text, summary and original transcription,
`/expense` (10) for a validated EUR
receipt, or `/json` (20) for receipt fields or a text object. The destination
selects the output; no content-mode menu is needed. Text is pasted into the
receiving webpage. General OS clipboard and third-party app insertion are not
implemented. Text-only captures get a second AI pass; receipts bypass it. If the
second pass fails, the original text remains available with a clear label.

Open `/coffee` (marker 40) for the simulated coffee machine. Aim there before
holding, then swipe right to start brewing; a fresh hold/swipe stops it. Release
before swiping cancels. Looking alone does not toggle it. No image extraction or
real appliance connection is involved. Physical phone checks for this build,
handwriting and glasses checks are still pending.

Start the configured hub with `.venv/Scripts/python.exe scripts/run_hub.py` on
Windows, or `python scripts/run_hub.py` in the activated Mac environment. Copy
`.env.example` to the ignored `.env` and configure live mode/provider locally.
Never commit keys. Build web changes with `npm --prefix apps/web run build`.

See [text analysis and Coffee build](docs/tasks/text-analysis-coffee-demo.md) for exact checks,
startup commands and the prior verified build. Earlier sections below record the
foundation and original receipt-only setup; the current protocol takes precedence.

Junction prototype: capture a synthetic receipt through Meta Ray-Ban Display
glasses, look toward Expenses or JSON, preview the amount, and deliberately
confirm a transfer with a supported Neural Band/display action.

**Current milestone: B2 marker recognition and phone-photo test.** One
FastAPI server connects both React screens and the phone-test browser through
WebSockets. Real uploaded JPEG pixels are checked for markers 10 and 20.
A continuous sequence of fresh, central observations can select a stable
connected target; old/ambiguous results cannot select one. The phone page
can take or choose one photo to check recognition. It does not automatically
stream or replay that photo. Operator Reset clears the shared run and drafts.
Glasses input, receipt extraction, confirmation/transfers, Send Again, and
Undo are not implemented. No provider key is needed for these tests.

**Android bridge on this branch:** the native
[phone-first Android app](apps/mobile/android/README.md) adds continuous handset
camera streaming through Meta's mock SDK, shared marker status, and an SDK
selection diagnostic. Receipt actions remain disabled against the current B2
hub. Its physical phone/glasses checks are tracked separately in
[issue #6](https://github.com/mhirvasm/LineOfSightJunction2026/issues/6).

B1 was merged into `chore/k0-bootstrap` after the human tested it and
explicitly requested the merge. B2 is on `feat/b2-target-selection` for
review; it is not automatically merged.

## Test with a phone first

1. Keep the hub running on the laptop. Connect the phone to the same reachable
   Wi-Fi/hotspot. On the phone, open `http://YOUR-HUB-IP:8000/health`.
   It must show `ok: true`. Find the actual IP with `ipconfig` on Windows
   or the active connection's Network settings on Mac. A phone cannot use
   the laptop's `127.0.0.1` address.
2. On the laptop, open `/expense` and `/json` once each. Keep their two large
   markers visible. Close any old test-phone page on the laptop, because
   only one phone/controller connection is allowed.
3. On the phone, open `http://YOUR-HUB-IP:8000/fixture-mobile`. It should say
   **Connected** and **PHONE CAMERA FALLBACK**.
4. Tap **Take or choose a photo**. Use the camera option if offered. Point
   at the whole Expenses marker, near the centre of the photo, and submit it.
   The page shows the normalized JPEG actually sent to the hub.
5. Under **Marker recognition**, **Last image recognized** should become
   **Expenses**. Photograph the JSON marker next: it should become **JSON**.
   The laptop's Operator page should show the same recognition results.
6. Try photographing a blank area or both markers in the central part of
   the image. No target should be selected. **Stop camera test** and operator
   **Reset demo run** clear transient marker state without applying a draft.

**A single photo is a recognition test.** Its fresh candidate expires after
about 600 ms, so **Stable target: None** / **Target expired** is expected.
The last recognised name remains visible for comparison. A continuous camera
uploader must provide fresh observations for about 350 ms to acquire a target
and keep them coming to retain it. No receipt is transferred by this test.

The file picker may offer Camera, Photo Library, or a file chooser depending
on the phone/browser. Existing pictures are permitted for diagnostics and
are not evidence of a live stream. The browser normalizes orientation and
resizes the image to a JPEG with a longest side of 1280 pixels before upload.

Live `getUserMedia` camera streaming generally needs a secure context on a
remote phone. This plain-HTTP foundation uses the camera/photo picker and
does not add certificate setup or bypass browser security. References:
[MDN camera capture](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Attributes/capture),
[MDN getUserMedia](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia).
If the phone cannot open health, resolve network reachability first; changing
camera code will not fix it. A personal hotspot may be needed if the current
network isolates devices.

## Test it now

With the server running, open each link once in a separate tab/window:

1. [Expenses](http://127.0.0.1:8000/expense)
2. [JSON](http://127.0.0.1:8000/json)
3. [Test phone](http://127.0.0.1:8000/fixture-mobile) (phone-browser connection; the connection-only check can also run on the laptop)
4. [Operator](http://127.0.0.1:8000/operator)

On Operator, all three listed connections should say **Connected**. Find
the **Hub run** number at the bottom of each page: they must match. Press
**Reset demo run** on Operator. All four pages must show the same new run
number without refreshing. Close the test-phone tab: Operator should show
that the phone is no longer connected. Reopen it and the connection returns.

This proves real shared communication between the clients and server. It
does not yet prove receipt capture, screen selection, or a transfer. Both
drafts remain empty. The test phone does not use the camera or Neural Band.
Close that page before connecting a real native phone app.

Only one connected tab per destination is allowed. A duplicate tab shows
**Connection rejected**; close it. If you closed the original and want to
use the rejected tab, refresh it once. Ordinary network disconnections retry
after 1.5 seconds; old actions are never replayed.

The old standalone layout examples remain at
`/expense?fixture=PREVIEW_expenses` and `/json?fixture=PREVIEW_json`.
Those examples have no hub socket and cannot change shared state.

When testing from another device, replace `127.0.0.1` with the actual hub IP.

| Destination | URL | Target ID | ArUco marker |
| --- | --- | --- | --- |
| Expenses | `/expense` | `expenses` | DICT_4X4_50 / 10 |
| JSON | `/json` | `json` | DICT_4X4_50 / 20 |

The demo is planned for **15 November 2026 at 10:00, Europe/Helsinki**.
One coding agent works here; A/B/C identify workstreams. Assign one human
integration owner and record hardware/network results in
[`docs/device-check.md`](docs/device-check.md).

## Download and run on a Mac

Use these steps on the Mac that will run the hub. The other Mac can simply
open the hub's URLs in its browser; it does not need to install the project.
Have internet access and at least 2 GB of free space for dependencies.

### 1. Install the prerequisites

You need Git, **Python 3.12**, **Node.js 24**, and npm. The exact versions used
on the development machine are recorded in
[`docs/verification.md`](docs/verification.md). `.python-version` and `.nvmrc`
record its Python and Node versions; newer patch versions within 3.12/24
can be used but must be verified on your Mac.

In Terminal, install Apple's Command Line Tools if Git is missing:

```sh
xcode-select --install
```

Finish the installation dialog before continuing. If Homebrew is missing,
install it using the [official Homebrew instructions](https://brew.sh/),
including the `brew shellenv` step shown by its installer, then reopen
Terminal. Install the required runtimes:

```sh
brew install python@3.12 node@24
export PATH="$(brew --prefix node@24)/bin:$PATH"
git --version
python3.12 --version
node --version
npm --version
```

The PATH line selects Homebrew's versioned Node installation and works
with either Apple Silicon or Intel Homebrew prefixes. Repeat it in each
new Terminal, or add the same line to `~/.zshrc` if you want it to persist.
If Homebrew cannot supply a binary for your macOS/CPU, use the appropriate
Python 3.12 and Node 24 installers from [Python](https://www.python.org/downloads/macos/)
and [Node.js](https://nodejs.org/en/download) instead. With an existing nvm
installation, `nvm install` and `nvm use` in this repo select `.nvmrc`.

References: [Homebrew Python 3.12](https://formulae.brew.sh/formula/python@3.12),
[Homebrew Node 24](https://formulae.brew.sh/formula/node@24).
Full Xcode is not required for this Python/React foundation. Native iOS
development will need a separately verified Xcode/SDK setup after A1.

### 2. Clone the repository and select the bootstrap branch

Repository: [mhirvasm/LineOfSightJunction2026](https://github.com/mhirvasm/LineOfSightJunction2026).
Run from the folder where you keep projects:

```sh
git clone https://github.com/mhirvasm/LineOfSightJunction2026.git
cd LineOfSightJunction2026
git switch feat/b2-target-selection
```

The marker work is on `feat/b2-target-selection`, based on the merged
bootstrap. Linking a local Git remote does not upload files. If
the repository is empty or `git switch` reports that the branch is missing,
stop and have the integration owner share the committed task branch. If it has
already been reviewed and merged, use the branch containing this README.

For a private repository, sign in with an account that has access using
GitHub Desktop, GitHub CLI, or your configured Git credential manager.
GitHub HTTPS authentication uses a token/credential manager, not an account
password. Do not put tokens in commands, URLs, or tracked files.

### 3. Create a local Python environment and install dependencies

Run all remaining commands from the repository root:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python --version
python -m pip install -r requirements.txt
python -m pip check
npm --prefix apps/web ci
```

Do not copy a Windows `.venv` or `node_modules` folder to the Mac. Create
them on each machine. `npm ci` uses the committed `package-lock.json`;
do not delete the lockfile to work around an installation error.

### 4. Build and verify the foundation

```sh
npm --prefix apps/web run build
python scripts/verify_foundation.py
python scripts/verify_hub.py
python scripts/verify_hub_server.py
python scripts/verify_vision.py
python scripts/verify_vision_server.py
npm --prefix apps/web test
```

Expected: a successful Vite build, four foundation checks, six hub checks,
ten vision checks, four JavaScript connection checks, and both real-server
smoke tests. Each server smoke test starts and stops its own isolated temporary
hub; it does not reset the hub you are using. The foundation checks require
the web build. These tests use labeled synthetic image pixels and do not
verify physical phone photos, glasses, extraction, or cross-device networking.

Generated markers and fixture snapshots are committed, so generation is
not needed for a normal clone. If you intentionally need to regenerate them:

```sh
python scripts/generate_markers.py
python scripts/generate_fixtures.py
npm --prefix apps/web run build
python scripts/verify_foundation.py
```

### 5. Start the hub

Keep this Terminal open, with the virtual environment activated:

```sh
python -m uvicorn services.hub.app:app --host 0.0.0.0 --port 8000
```

Use one process, without `--reload` or multiple workers. In another Terminal:

```sh
curl http://127.0.0.1:8000/health
open http://127.0.0.1:8000/expense
open http://127.0.0.1:8000/json
```

Health returns `{"v":1,"ok":true,"run_id":"<UUID>"}`. Repeated requests
within one server run have the same UUID. A restart creates a new run.
Both pages must show **FIXTURE MODE**, the correct target name/marker, and
**Connected**. Their state starts at STOPPED with empty drafts. Follow
"Test it now" above to verify shared communication and Reset.

## Check the private network before the device slot

1. Connect the hub Mac, phone, and receiving computer to the same controlled
   private router/hotspot. Avoid guest networks that isolate devices.
2. On the hub Mac, find the active connection's local IP in System Settings
   > Network > Wi-Fi > Details > TCP/IP (or the active Ethernet service).
   It is not `127.0.0.1` and is not the router address. Record the real value.
3. With the hub running on `0.0.0.0`, open
   `http://YOUR-HUB-IP:8000/health` in the phone browser and on the second Mac.
   All devices must receive the same current `run_id`.
4. Open `http://YOUR-HUB-IP:8000/expense` on one receiving area and
   `http://YOUR-HUB-IP:8000/json` on the other. Keep both windows visible.
   Two hidden tabs do not provide two simultaneous physical targets.
5. If macOS asks about incoming connections, allow the known hub Python
   process on the trusted demo network. If local health works but another
   device cannot reach it, inspect the active IP, binding, firewall, and
   router client isolation. Keep the firewall enabled.

`YOUR-HUB-IP` is a placeholder to replace; do not type it literally. Do not
use `localhost` on the phone: that would point to the phone itself.
This foundation can verify browser reachability before a native app exists.
It cannot prove native local-network permissions or camera access.

## Start again later or update the checkout

In a new Mac Terminal:

```sh
cd /path/to/LineOfSightJunction2026
source .venv/bin/activate
python -m uvicorn services.hub.app:app --host 0.0.0.0 --port 8000
```

Stop the hub with Ctrl+C. Future applied drafts will live only in hub
memory and will intentionally be lost on restart. No database is used.
Before receiving updates, run `git status` and preserve any local work.
On the agreed shared branch, use `git pull --ff-only`; reinstall Python
packages if `requirements.txt` changed, run `npm --prefix apps/web ci` if
the dependency manifest/lockfile changed, and rebuild after web changes.
Never run another coding agent in the same checkout concurrently.

## Windows setup

With Git, Python 3.12, Node 24, and npm installed and on PATH, use PowerShell
from the repository root. No activation or execution-policy change is needed:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
npm --prefix apps/web ci
npm --prefix apps/web run build
.\.venv\Scripts\python.exe scripts/verify_foundation.py
.\.venv\Scripts\python.exe scripts/verify_hub.py
.\.venv\Scripts\python.exe scripts/verify_hub_server.py
.\.venv\Scripts\python.exe scripts/verify_vision.py
.\.venv\Scripts\python.exe scripts/verify_vision_server.py
npm --prefix apps/web test
.\.venv\Scripts\python.exe -m uvicorn services.hub.app:app --host 0.0.0.0 --port 8000
```

This development machine initially had Git and Node available only through
Codex's bundled runtime. See `docs/verification.md` for its actual commands.
Other machines should use their installed tools. Use `ipconfig` to find the
hub's active IPv4 address for the network check above.

## Common setup failures

| Symptom | Check / action |
| --- | --- |
| `brew`, `python3.12`, or `npm` not found | Finish prerequisite installation, reopen Terminal, and apply the Node PATH line. |
| Python package says incompatible version / no wheel | Confirm `python --version` is 3.12 and that the environment was created on this Mac. Record the exact error and macOS/CPU before changing pins. |
| `externally-managed-environment` | Activate `.venv`; install with its `python -m pip`. Do not use system-wide pip or `sudo pip`. |
| `npm ci` fails | Confirm Node is 24, internet works, and manifest/lockfile match. Keep the lockfile. |
| `/expense` or `/json` returns 503 | Run the web build from the repo root and retry. |
| Port 8000 already in use | Find the old hub Terminal and stop it with Ctrl+C; do not run two hubs. |
| Page loads but health is unavailable | Check the server Terminal and `/health` directly. The UI reports the error instead of simulating a connection. |
| Other device cannot reach health | Check the real LAN IP, same reachable network, `0.0.0.0` binding, and firewall/client isolation. |
| Marker looks small or glared | Enlarge the window/tile, improve the angle/light, and inspect an actual camera frame at A1/B2. |
| `No space left on device` | Free disk space before retrying dependency installation. |

## What to do next

The governing instructions are [`AGENTS.md`](AGENTS.md) and
[`contracts/protocol.md`](contracts/protocol.md). Original supplied planning
files remain under `lineofsight/`; older parallel-agent suggestions are
superseded by the root single-agent policy.

- **A1, human physical gate:** ask Amanda/the Meta booth which ready
  glasses/band/phone/account combination to use. Prove changing upright
  camera frames and ten deliberate supported display-button/band callbacks
  together on the actual hardware. Record separate results for camera,
  display, input, and simultaneous operation. The native platform is still
  undecided; the available iPhone/S23 and Macs/ThinkPad do not decide it.
- **B3, next software task:** build the receipt/preview workflow using the
  exact frozen capture image. B2 detects actual JPEG marker pixels, but
  physical phone/glasses targeting needs the team's camera check. Transfers
  still require B4 and the extraction tasks C3/C4.
- Continue the dependency order in [`contracts/task-plan.json`](contracts/task-plan.json).
  Keep both destinations throughout. Hardware integration and live extraction
  need their own verification before they can be presented as working.

K0 task scope and ownership are recorded in
[`docs/tasks/K0-bootstrap.md`](docs/tasks/K0-bootstrap.md) and
[`docs/ownership.md`](docs/ownership.md). Actual checks and outstanding Mac,
network, and hardware verification are in
[`docs/verification.md`](docs/verification.md).
B1 scope, optional connection-status metadata, actual checks, and limitations
are recorded in [`docs/tasks/B1-shared-hub.md`](docs/tasks/B1-shared-hub.md).
B2 upload limits, target selection, protocol extensions, actual checks, and
phone-test limitations are in [`docs/tasks/B2-target-selection.md`](docs/tasks/B2-target-selection.md).

Preserve these later workflow requirements: freeze the exact capture image;
keep unchanged previews stable; confirm the exact displayed preview; apply
each commit once; ignore late extraction after Cancel/Reset; keep Stop
separate from Undo; and allow missing optional tax. The full protocol is
the implementation contract. No live extraction setting or provider key
configuration exists yet; fixture examples cannot silently become live mode.
