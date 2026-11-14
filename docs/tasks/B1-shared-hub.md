# B1: shared hub connection test

Issue: https://github.com/mhirvasm/LineOfSightJunction2026/issues/2.
Branch: `feat/b1-shared-hub`, based on `chore/k0-bootstrap` at `8f5254d`.
Agent author: Codex. Responsible human: `mhirvasm`.
Dependency: K0, issue #1; the human reported its local test working.

## Result and scope

One FastAPI process owns the run, empty destination drafts, transient
receipt/capture/preview/stream fields, and capture/commit records in memory.
`/v1/events` connects one mobile client, one Expenses target, one JSON
target, and operator clients. Every accepted client receives full snapshots.
Connection changes and explicit operator Reset broadcast to all clients.
Reset issues a new UUID and clears in-memory data and IDs. Mobile pause or
disconnect stops the interaction and clears transient fields while preserving
applied drafts. Only the exact currently bound socket can release its role.

React target pages now render hub snapshots. `/operator` shows connections
and an explicit Reset button. `/fixture-mobile` provides a clearly labeled
simulated phone socket, with no camera or wristband functionality. The old
standalone UI examples remain behind the explicit `?fixture=...` query and
never open a target socket. Each receiving page has at most one socket;
cleanup cancels reconnect timers, obsolete callbacks are ignored, and no
action queue is replayed. Duplicate connections show a visible rejection
and do not retry in a loop. A disconnected page clears stale server content.

The minimal target connection wiring overlaps the connection portion of C2.
DISPLAYED acknowledgements are deferred to C2/B4, when actual commits exist.
The operator/test-phone views support B1 verification; they do not implement
the full C5 presentation or the B3/B4 workflow.

## Protocol notes

Existing routes, role/target labels, receipt fields, and event names remain
unchanged from `contracts/protocol.md`. The snapshot adds one optional status
field for the connection check:

```json
{
  "connections": {
    "mobile": false,
    "targets": {"expenses": true, "json": true},
    "operators": 1
  }
}
```

This metadata is not authentication or physical-device detection. Clients
must not infer camera/SDK readiness from a connected socket. `source_mode`
remains `fixture`; no live extractor exists. No sample receipt is injected
into authoritative hub state.

Errors use an additive `ERROR` response with `v`, `type`, `run_id`, `error`,
and `message`. Unknown labels or duplicates receive a visible error before
the socket closes (4400 or 4409). Current-run RESET is operator-only.
STREAM_STARTED and DEVICE_PAUSED are mobile-only. Malformed, binary,
stale-run, unauthorized, and unsupported events cannot mutate drafts.
ACTION and DISPLAYED return `not_implemented` until their assigned tasks.
WebSocket queries route clients; they do not authenticate callers. Use the
controlled private network described in the original protocol.

## Acceptance and verification

Commands run on Windows from the root:

```powershell
.\.venv\Scripts\python.exe -m pip install websockets
.\.venv\Scripts\python.exe scripts/verify_hub.py
.\.venv\Scripts\python.exe scripts/verify_foundation.py
.\.venv\Scripts\python.exe scripts/verify_hub_server.py
.\.venv\Scripts\python.exe -m pip check
```

Bundled Node executable, assigned to `$nodePath`, is recorded in the K0
verification document. Equivalent actual frontend commands used:

```powershell
& $nodePath --test apps/web/src/connection/socket.test.js
& $nodePath apps/web/node_modules/vite/bin/vite.js build apps/web
```

- Six hub checks passed: shared/reset run, role/target/duplicate guards,
  mobile binding ownership, malformed/stale/unsupported input, disconnect
  state clearing with draft preservation, and stream/obsolete-cleanup guards.
- Four JavaScript checks passed: current-run state replacement, disconnect
  clearing and no replay, visible duplicate rejection without retry loops,
  and timer/callback cleanup.
- All four original foundation checks passed; original protocol and fixture
  contents and both marker IDs remain verified.
- Actual isolated Uvicorn/WebSocket smoke test passed, including three
  clients, Reset broadcast, duplicate rejection, stale-run rejection,
  mobile disconnect, and fresh empty state after a real process restart.
- Frontend build and `pip check` passed. Existing Starlette HTTPX TestClient
  deprecation warning remains non-failing.
- `websockets==17.4` is the only new Python dependency. Existing package
  versions remain unchanged.

Browser verification passed on the actual hub at port 8000:

- Expenses, JSON, simulated phone, and operator all connected.
- Operator Reset changed the run on every page from
  `660fc29f-905c-43e2-9182-4f7ad328b79c` to
  `1ae66fd2-ab5a-436a-9e30-023665409be7`, without page refreshes.
- A second JSON tab showed a visible duplicate-connection rejection.
- Closing the test phone was reflected as disconnected; reopening restored it.
- Refreshing the original JSON page reconnected to the current run.
- The separate fixture example still rendered APPLIED sample JSON and did
  not occupy a target socket. No operator-tab warning/error logs were observed.
- Temporary target/test-phone verification tabs were closed afterward so
  the human can open their own pages without duplicate connections.

The previous K0 server was stopped through its own execution session and
restarted with the same documented command on port 8000. An initial
PowerShell stop attempt failed; the first restart reported port in use.
After the old execution session was closed, the new hub started successfully.
No unrelated process was stopped. No Mac or cross-device network result is
claimed. The branch is prepared for publication and draft review, with no
main-branch merge or deployment.

## Human test

Open `/expense`, `/json`, `/fixture-mobile`, and `/operator` on the same
running hub. Operator must show three connected clients. Every page footer
must share a run number. Press Reset once: every page receives the same new
number without a refresh. Close and reopen the test-phone page; Operator
must show its disappearance/reappearance. A duplicate destination tab must
show a rejection while the original stays connected. Close the test phone
before future native-device work.

This proves shared communication. It does not prove camera capture,
Neural Band actions, image orientation, target detection from frames,
receipt reading, confirmation, transfer, Send Again, Undo, or DISPLAYED.
Next software task is B2; A1 remains the physical hardware gate. Human
review and integration are required; the agent must not merge this branch.
