# Plan audit - demo-first v2

## Corrections made

1. Both destinations are required from the first UI task.
2. Remove per-role tokens, certificate work, databases, persistence, and edit-conflict/reconciliation dialogs.
3. One in-memory hub owns drafts; browsers render full snapshots.
4. Freeze the exact image at Capture, instead of reading a later streaming frame.
5. Keep preview_id stable across unchanged observations; bind confirmation to the displayed preview.
6. Ignore late extraction results after Cancel, Reset, or device interruption.
7. Deduplicate the commit before mutation; do not await between validation/check and mutation.
8. Missing optional tax is permitted; malformed required fields require recapture.
9. Stop does not undo applied data; one-level Undo is explicit.
10. Server restart resets the run intentionally. Old run_id requests cannot modify the new run.

## Mechanical checks performed

- 16 unique task cards match the machine-readable manifest.
- Every hard dependency refers to an existing task.
- Dependency graph is acyclic.
- 12 declared interfaces/data handoffs have an owner and at least one consumer.
- Receipt fixture parses as JSON and matches the displayed EUR 24.80 total.
- PDF contains 12 pages with no extra overflow pages.

These are checks of the written plan and its metadata, not application tests. Producer/consumer coverage does not prove semantic correctness. C1 can build with fixture marker placeholders while B2 generates final assets; live integration must use those exact final assets. B3 injects a test fixture extractor until C3/C4 are ready; B5 requires the real validated path.

## Device and acceptance status

NOT TESTED in this planning task: camera/display/input concurrency, true camera delay, wristband mapping, receipt readability, model accuracy, network reliability, or any working end-to-end application. A1 and B5 own these checks. Follow the acceptance checklist below without treating it as passed.

# 10 / The bugs worth checking
## A short release checklist, not a production test suite

| Check | Trigger | Required behavior |
| --- | --- | --- |
| Wrong capture frame | Capture receipt A, immediately look at B. | The uploaded immutable image is A; the server never substitutes a later stream frame. |
| Double pinch | Repeat callback/CONFIRM three times. | One draft update for that preview_id. |
| Stale preview | Look at Expenses, then JSON, then deliver the old confirmation. | Reject it; do not redirect it to JSON. |
| Constant frames | Keep looking at one target through 50 observations. | The unchanged preview_id stays valid. |
| Target loss | Cover the marker and wait past the configured freshness limit. | Confirmation is disabled/rejected. |
| Late AI result | Cancel while the model request is running. | The result cannot recreate a preview. |
| Optional field | Receipt has no tax line. | tax_minor is null; otherwise valid data can proceed. |
| UI reload | Refresh one receiving page. | It renders the current hub snapshot; no new write occurs. |
| Server restart | Restart the hub with an upload in flight. | New run_id; old request rejected; visibly start a new run. |
| Lost screen | Disconnect the selected browser after confirmation. | Draft is not applied twice; feedback does not claim the screen displayed it. |
| Stop after apply | Stop immediately after transfer. | Camera/input stop; draft remains. Undo is explicit. |
| Slow model | Delay extraction by several seconds. | Status/Cancel remain responsive. |
| Real readability | Inspect the exact glasses image used by the model. | The printed fields are readable enough; enlarge/move the receipt if needed. |

### What has and has not been checked in this planning work
The revised dependency graph, message ownership, and producer/consumer coverage can be mechanically checked from the included manifest. These checks find missing tasks and circular dependencies. They do not prove application correctness, model accuracy, or device compatibility.

The scenarios above are acceptance tests for the team to run after implementation. They are not reported as passed here. A documented hardware failure should remain a failure until a human retests it.

### Final decision rule
The demo is ready when both destinations work, the live capture path is truthful, three full rehearsals succeed, and the failure cases you actually encounter have clear feedback. Do not spend the final hours implementing persistence, general-purpose security, or recovery dialogs for hypothetical production use.
