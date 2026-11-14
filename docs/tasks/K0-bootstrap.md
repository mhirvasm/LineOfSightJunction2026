# K0: runnable bootstrap foundation

Branch: `chore/k0-bootstrap`
Status: foundation verified locally; ready for human review. Mac, cross-device
network, and hardware checks are pending and are not claimed as passed.

Author: Codex (agent-authored). Responsible human/integration owner: `mhirvasm`.
Dependencies: None. Remote: https://github.com/mhirvasm/LineOfSightJunction2026.git.
Issue: https://github.com/mhirvasm/LineOfSightJunction2026/issues/1.
This task was initially tracked locally. The connected GitHub integration
now tracks it as issue #1, assigned to `mhirvasm`.

## Background and scope

The supplied v2 pack contains planning files and fixtures only. Create a
runnable starting point so the team can prepare both screens and check its
private network before device access. Scope: shared contract, generated
markers, fixture snapshots, a minimal FastAPI health endpoint, both React
target pages, pinned dependencies, and a Mac/Windows runbook.

## Approach

Preserve the original extracted pack and copy its single-agent policy to
root `AGENTS.md`. Keep protocol bytes and expected receipt unchanged. Use
`contracts/targets.json` for exact shared destination/marker configuration.
Generate marker PNGs with OpenCV and a white margin. Serve the built React
app and fixture files from one FastAPI process. Generate a new UUID at hub
startup. UI examples are static fixture snapshots; both in-memory hub drafts
start empty. No native platform, sockets, workflow, model calls, transfer
actions, deployment, or merge belong to this milestone.

## Acceptance criteria

- Root instructions, protocol, valid/invalid fixtures, and all six snapshot states exist.
- Expenses is `/expense`, target `expenses`, marker 10; JSON is `/json`, target `json`, marker 20.
- Both marker assets decode as DICT_4X4_50 and have a white quiet zone.
- `/health` returns protocol version 1, ok true, and a per-start run UUID.
- Both React pages distinguish fixture previews from applied sample data.
- Dependencies are pinned and install/build/start/verification commands are documented.
- Actual verification and untested hardware/platform checks are recorded honestly.

## Verification

Use README's install/build/start commands, then run
`python scripts/verify_foundation.py`, `python -m pip check`, and
`curl http://127.0.0.1:8000/health`. Open both routes and inspect labels,
markers, fixture status, and sample state controls. Record observed results
in `docs/verification.md`; Mac and physical network/device checks remain pending
until run on those machines.

Next software task: B1 (WebSocket hub); C1's initial fixture UI is included
here and must receive a later actual-camera size/readability check. A1 is
the next independent physical task. Stop after this foundation for human review.
