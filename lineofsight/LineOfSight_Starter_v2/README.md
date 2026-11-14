# LineOfSight - start here

This is the simplified v2 hackathon plan. Use it instead of the earlier implementation tickets.

## Start in parallel

- Person A: give the coding agent Agent_A.md + contracts/protocol.md. Start A1 at the Meta booth.
- Person B: give the coding agent Agent_B.md + contracts/protocol.md. Start K0, then B1.
- Person C: give the coding agent Agent_C.md + contracts/protocol.md. Build C1 with fixtures as soon as K0 freezes names.

Give each model the common prompt and ONE task at a time. Read the card's dependencies and completion check. Do not ask it to implement the whole file at once.

## Contents

- Agent_A.md: five device/mobile tasks.
- Agent_B.md: K0 plus five hub/vision/integration tasks.
- Agent_C.md: five UI/extraction/demo tasks.
- contracts/protocol.md: exact shared routes, messages, state rules, and boundaries.
- fixtures/receipt_expected.json: the canonical synthetic record.
- fixtures/receipt_demo.html: open locally and print a large receipt; inspect a real camera frame before demo.
- tasks.json: subjects, owners, dependencies, and interface ownership.
- Audit_and_Checklist.md: actual planning checks and unrun implementation acceptance tests.

## No hidden implementation

This pack is a task plan and starter data, not an app. It does not include a working Meta integration, generated ArUco PNGs, frontend, or hub. Those are the assigned tasks. The initial target is a live selection between TWO screens using fixture data; then replace fixture extraction with one real camera/model call.

## Task subjects

| ID | Subject | Depends on |
| --- | --- | --- |
| K0 | Initialize the demo contract and reproducible fixtures | None |
| A1 | Prove camera and wristband selection together | None |
| A2 | Create the smallest native bridge and local-network setup | A1, K0 |
| A3 | Stream correctly oriented frames without a backlog | A2, B1 |
| A4 | Freeze the receipt image and send one deliberate action | A3 |
| A5 | Render simple cards and stop safely on interruption | A4, B3 |
| B1 | Build one in-memory hub and connect three clients | K0 |
| B2 | Detect the two markers and choose a stable target | B1 |
| B3 | Implement the receipt and preview state machine | B1, B2 |
| B4 | Apply once, broadcast, and provide one-level Undo | B3 |
| B5 | Connect all parts and run the short bug checklist | A5, B4, C2, C4 |
| C1 | Build Expenses and JSON from one target component | K0 |
| C2 | Add one clean socket and render server snapshots | C1, B1 |
| C3 | Implement one extraction interface with fixture and real modes | K0 |
| C4 | Validate the receipt and map it to both destinations | C3 |
| C5 | Add clear feedback and prepare the demo | C2, C4 |
