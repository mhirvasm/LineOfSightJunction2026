# LineOfSight

Junction prototype: capture a synthetic receipt through Meta Ray-Ban Display
glasses, look toward Expenses or JSON, preview the amount, and deliberately
confirm a transfer with a supported Neural Band/display action.

**Current milestone: K0 foundation, fixture UI only.** A real FastAPI server
provides `/health` and serves both React target pages. The marker PNGs are
generated with OpenCV. Receipt previews and applied-data examples are
predetermined fixtures. Camera input, wristband actions, extraction,
WebSockets, transfers, Reset, Send Again, and Undo are not implemented yet.
No provider key is needed to run this foundation.

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
git switch chore/k0-bootstrap
```

**The bootstrap branch must be uploaded to GitHub before another machine
can clone it.** Linking a local Git remote does not upload files. If
the repository is empty or `git switch` reports that the branch is missing,
stop and have the integration owner share the committed bootstrap branch. If it has
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
```

Expected: a successful Vite build and four passing checks covering the
health/run lifecycle, both routes/assets, marker decoding, and fixture
contract consistency. These checks require the web build from the preceding
command. They do not test glasses, extraction, or the network between devices.

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
**WebSocket not connected**. This is the expected K0 behavior. The fixture
selector changes local UI examples only; it never performs a transfer.

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
- **B1, next software task:** add the in-memory WebSocket hub and shared
  snapshots. This bootstrap includes health but does not complete B1.
- Continue the dependency order in [`contracts/task-plan.json`](contracts/task-plan.json).
  Keep both destinations throughout. Hardware integration and live extraction
  need their own verification before they can be presented as working.

K0 task scope and ownership are recorded in
[`docs/tasks/K0-bootstrap.md`](docs/tasks/K0-bootstrap.md) and
[`docs/ownership.md`](docs/ownership.md). Actual checks and outstanding Mac,
network, and hardware verification are in
[`docs/verification.md`](docs/verification.md).

Preserve these later workflow requirements: freeze the exact capture image;
keep unchanged previews stable; confirm the exact displayed preview; apply
each commit once; ignore late extraction after Cancel/Reset; keep Stop
separate from Undo; and allow missing optional tax. The full protocol is
the implementation contract. No live extraction setting or provider key
configuration exists yet; fixture examples cannot silently become live mode.
