# K0 verification record

Date: 14 November 2026 (Europe/Helsinki). Development machine: Windows.
Task branch: `chore/k0-bootstrap`, prepared for human review. `origin` is
`https://github.com/mhirvasm/LineOfSightJunction2026.git`; remote inspection
initially returned no branches/commits. GitHub issue #1 now tracks this
milestone and is assigned to `mhirvasm`. No merge or deployment was performed.
There is no existing `main` baseline against which to open a PR.

## Commit and upload status

Verified foundation commit: `02ff158a933b90ddda9064c53258909e0608b301`
(`chore(demo): initialize the K0 fixture foundation`). It includes the root
`.gitignore`. No ignored dependencies, builds, temporary screenshots, or
secret configuration files are tracked.

The initial command-line push failed because Git Credential Manager had no
stored GitHub login. The human then signed in to GitHub Desktop and explicitly
authorized a trust exception for this checkout only. Desktop added that
exception and successfully published `chore/k0-bootstrap` to the existing
`mhirvasm/LineOfSightJunction2026` repository.

Published application/documentation head: `145691d` (includes foundation
commit `02ff158`). GitHub branch listing and fetching the remote `.gitignore`
confirmed publication. The bootstrap branch is now available for the Mac clone
steps in README. No `main` commit, merge, deployment, or PR was created.

## Runtime and locked dependencies

- Python 3.12.14, Node 24.22.1, npm 11.6.2, Git 2.56.0.windows.4.
- FastAPI 0.162.7, Uvicorn 0.54.0, OpenCV headless 5.0.0.93, NumPy 2.5.4.
- React / React DOM 19.3.1; Vite 8.3.8.
- Every resolved Python dependency is pinned in `requirements.txt`.
- Exact web direct versions and resolved dependencies are in
  `apps/web/package.json` and `apps/web/package-lock.json`.

Git, Node, and Python were located through Codex's bundled workspace
dependencies, because Git/Node were absent from the normal PATH. No
system-wide software installation was performed. Git's sandbox ownership
check initially used per-command `safe.directory`; GitHub Desktop later added
a repository-specific trust exception at the human's explicit request.

## Actual commands and observed results

These are the commands used on this Windows machine (from the repository
root), including the bundled-tool paths needed here:

```powershell
$runtime = 'C:\Program Files\WindowsApps\OpenAI.CodexPrimaryRuntime.v26-1112-737-0_26.1112.737.0_x64__3k8sg7r9htsxt\dependencies'
$env:PATH = "$runtime\node\bin;" + $env:PATH
& "$runtime\python\python.exe" -m venv .venv
& "$runtime\native\git\cmd\git.exe" init -b chore/k0-bootstrap .
& "$runtime\native\git\cmd\git.exe" -c safe.directory=C:/Users/uusi123/Documents/LineOfSight remote add origin https://github.com/mhirvasm/LineOfSightJunction2026.git
& "$runtime\native\git\cmd\git.exe" -c safe.directory=C:/Users/uusi123/Documents/LineOfSight ls-remote origin
.\.venv\Scripts\python.exe -m pip install --no-cache-dir fastapi uvicorn opencv-python-headless httpx
.\.venv\Scripts\python.exe -m pip freeze | Set-Content -LiteralPath requirements.txt -Encoding ascii
.\.venv\Scripts\python.exe scripts/generate_markers.py
.\.venv\Scripts\python.exe scripts/generate_fixtures.py
& "$runtime\bin\fallback\pnpm.cmd" --package=npm@11.6.2 dlx npm --prefix apps/web install --save-exact react react-dom
& "$runtime\bin\fallback\pnpm.cmd" --package=npm@11.6.2 dlx npm --prefix apps/web install --save-dev --save-exact vite
& "$runtime\bin\fallback\pnpm.cmd" --package=npm@11.6.2 dlx npm --prefix apps/web ci
& "$runtime\bin\fallback\pnpm.cmd" --package=npm@11.6.2 dlx npm --prefix apps/web run build
.\.venv\Scripts\python.exe scripts/verify_foundation.py
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m compileall -q services scripts
.\.venv\Scripts\python.exe -m uvicorn services.hub.app:app --host 0.0.0.0 --port 8000
```

| Check | Observed result |
| --- | --- |
| `npm ci` from the generated lockfile | Passed; 20 packages installed, npm reported 0 vulnerabilities. |
| `npm run build` | Passed with Vite 8.3.8; HTML, CSS, and JS emitted in `apps/web/dist`. |
| `python scripts/verify_foundation.py` | All 4 checks passed. |
| Health lifecycle | Same UUID for repeated requests; new UUID after a new app lifespan. |
| Both page routes and referenced built assets | HTTP 200 in the FastAPI checks. Unknown API/page routes remain 404. |
| Exact original protocol and valid fixture | Match the preserved supplied pack. |
| OpenCV marker round-trip | Both 600x600 PNGs decode as their exact IDs, 10 and 20, from DICT_4X4_50. |
| Fixture consistency | All six states present; distinct destination previews; only JSON populated in the applied example; absent tax is nonblocking. |
| `pip check` | No broken requirements. |
| Python compilation | Passed. |
| Actual Uvicorn process | Started successfully on `0.0.0.0:8000`. |
| Actual HTTP requests to the running hub | `/health`, `/expense`, `/json`, both marker PNGs, and `/fixtures/snapshots.json` all returned 200 via Python `urllib.request.urlopen`. |
| Expenses browser inspection | Correct label, marker 10, fixture warning, EUR 24.80 preview, empty applied draft, hub reachable. |
| JSON browser inspection | Correct label, marker 20; applied sample displays the canonical JSON including null tax. |
| Fixture selector in browser | APPLIED renders sample JSON; invalid receipt returns READY with recapture feedback and empty draft. |
| Browser warnings/errors | None observed in the inspected tab. |
| README local links and ignore rules | All local README targets exist; `git check-ignore --no-index -q` passed all 24 cases (12 ignored and 12 trackable), including nested secrets, example configs, marker PNGs, lockfiles, and Gradle wrappers. |

The verification script currently receives a non-failing Starlette warning
that its HTTPX TestClient integration is deprecated in favor of HTTPX2.
The four assertions still pass; no runtime behavior depends on the test client.

Initial attempts exposed and recovered from three environment limitations:
network-restricted dependency downloads required tool approval; C: initially
had approximately 75 MB free and installation failed with no space left;
and writing `.git/config` required tool approval. After the human freed
space (approximately 29 GB available), dependency installation succeeded.
No personal files were deleted by the agent.

## Not verified / not implemented

Mac commands are documented against the same project files and official
Homebrew/GitHub instructions but have **not been executed on a Mac**.
Apple Silicon/Intel wheel availability and the actual macOS versions still
need the team's install/build check. No phone-to-hub or second-Mac network
test has been performed. Firewall settings were not changed.

There is no actual camera input, Neural Band callback, native phone app,
receipt extraction, WebSocket connection, marker targeting of real frames,
workflow mutation, confirmation, Send Again, Undo, Reset, or operator page.
Synthetic UI snapshots do not prove any of these features. The actual
hub drafts start empty; sample JSON is not an applied server transfer.

## Human handoff

1. `mhirvasm` reviews the published task branch and issue #1. Clone the
   `chore/k0-bootstrap` branch on the hub Mac; no main-branch merge has occurred.
2. Run README's Mac setup and private-network check, recording the actual
   hub IP and matching run_id seen from the phone/other computer.
3. At the Meta booth, run A1: actual camera + display + ten supported input
   callbacks together; choose the native platform based on that result.
4. Next software task: B1, the in-memory WebSocket hub. K0 is the stop point.
