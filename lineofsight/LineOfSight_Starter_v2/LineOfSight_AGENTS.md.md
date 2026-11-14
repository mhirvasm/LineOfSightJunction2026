# LineOfSight: Agent Workflow and Git Policy

Save this file as `AGENTS.md` in the root of the LineOfSight implementation repository.

## 1. Purpose and priorities

Build a working hackathon demonstration: capture a receipt through Meta glasses, select between Expenses and JSON by looking toward a registered screen, and deliberately confirm the transfer.

Prioritize a working demo, understandable changes, and short verification cycles. Keep both destinations in scope. Do not add production infrastructure, unrelated features, or speculative abstractions.

This file replaces the agenTD-specific policy. Its single-agent default supersedes parallel-agent workflow suggestions in earlier LineOfSight planning documents; the existing task requirements and acceptance checks still apply.

## 2. Default setup: one coding agent, one integration machine

- Start with one active coding agent and one implementation checkout on the primary development machine.
- Choose a primary machine that supports the selected native phone platform. An iOS build requires a suitable Mac/Xcode environment.
- Run one hub process on the designated demo machine. Other laptops may show receiving pages without running additional hubs or coding agents.
- The A, B, and C labels in the task plan describe work areas. They do not require three agents running simultaneously.
- One human operates the coding agent and owns integration. The other teammates focus on hardware access, physical testing, receiving screens, receipts, and presentation.
- Do not spawn additional coding agents automatically. Add parallel coding only when the human explicitly requests it and a task can be isolated without delaying the working demo.

One agent reduces coordination and merge risk; it does not replace human testing or guarantee correct code.

## 3. Human responsibilities

| Role | Responsibility |
| --- | --- |
| Device owner | Coordinate with the Meta booth, install and test the phone app, verify camera/display/input on actual glasses. |
| Integration owner | Operate the coding agent, maintain the working branch/build, review PRs, run checks, and merge accepted changes. |
| Experience owner | Operate both receiving screens, verify visible results, prepare receipts, record rehearsals, and manage the pitch. |

Humans may rotate roles, but every active task and PR must have a named human owner. Only one person should direct edits in the active checkout at a time.

## 4. Task and issue policy

Use one issue per meaningful deliverable, such as camera transport, target selection, or the two receiving pages. Do not create separate issues for every file or minor adjustment.

Use the existing task ID where applicable, for example `B2: detect and select the two destination markers`.

Every implementation issue must contain:

1. **Background and rationale:** the problem and its role in the demo.
2. **Scope and ownership:** files/components to change and what is excluded.
3. **Technical approach:** relevant data fields, interfaces, state transitions, and parameters. Include formulas only when they matter.
4. **Acceptance criteria:** a short, complete checklist of observable outcomes.
5. **Verification:** exact commands or physical demo steps and their expected results.
6. **Dependencies:** links to prerequisite issues. State `None` when there are none.

Do not invent missing repository URLs, issue numbers, SDK methods, or test results. If issue tracking has not been configured, keep a local task record and explain what is missing. Link a real issue before opening its PR.

An issue is complete only when its acceptance criteria pass, or the human explicitly changes its scope and records the remaining work. Clearly separate simulated checks from physical-device checks.

## 5. Branch and integration policy

- Create a task branch from the current shared baseline before implementation. Example: `feat/b2-target-selection`.
- Do not commit directly to `main` or merge agent-authored code into `main`.
- Keep changes focused on the assigned issue. Preserve unrelated human and teammate changes.
- The integration owner decides when to update the baseline and integrate another branch. Do not switch branches over someone else's uncommitted work.
- Never discard changes, rewrite shared history, force-push, or perform destructive resets without explicit human authorization for that action.
- Keep a known-good commit available before every device test slot and before the final demonstration. Record its identifier in the runbook.

If a remote repository or PR workflow is not available yet, keep the work on a task branch for human review. Do not simulate a PR, invent an issue link, or treat missing infrastructure as permission to bypass the merge policy.

## 6. Commit policy

Use this header:

```text
<type>(<scope>): <short imperative summary>
```

Suggested types: `feat`, `fix`, `refactor`, `test`, `docs`, and `chore`.

Suggested scopes: `mobile`, `camera`, `vision`, `workflow`, `hub`, `web`, `extraction`, `demo`, and `docs`.

For substantial changes, use the following concise body. Replace placeholders with facts about the actual change:

```text
Why:
<the problem or reason for this change>

Changes:
- <specific behavior or implementation change>
- <another relevant change, if needed>

Verification:
- <actual command or manual check and its result>
- <anything not tested and the reason, if applicable>
```

For a small documentation or formatting change, a clear header and short verification note are sufficient. Do not write an architectural essay for a trivial change. Never claim a successful build, test, or device run that was not performed.

## 7. Pull request policy

Every PR must:

- Link an existing issue, using a real reference such as `Closes #123`.
- Describe the resulting behavior and any relevant limitation.
- Identify whether the code was agent-authored or human-authored.
- Name the primary author and responsible human. Assign the author's account when assignable; otherwise assign the human operator and identify the agent in the description.
- Include actual verification results and pending physical checks.
- Remain focused enough for the human to review and run its acceptance checks during the hackathon.

**Agent-authored code must be reviewed, tested, and merged by a human.** The agent may prepare the branch and PR, explain changes, and address feedback. It must not merge the PR or enable automatic merging.

Human-authored code may be self-merged by its human author after the required checks. The human may request an agent review first. A PR containing agent-authored changes follows the agent-authored merge rule.

Before merging, the human confirms:

- [ ] The PR links the correct issue and stays within scope.
- [ ] The relevant build or test checks pass.
- [ ] The required visible behavior has been demonstrated, or the issue does not require a hardware check.
- [ ] No credentials, personal documents, or unrelated camera footage are included.
- [ ] The previous working demo flow still works after integration.

Templates document this process; they do not configure repository branch protection. Until repository settings enforce it, the integration owner is responsible for following it.

## 8. Verification proportional to the change

- UI change: build the web app and inspect the affected screens.
- Workflow or routing change: check the affected state transition and destination, including the relevant stale/duplicate action case.
- Extraction change: use the known receipt and the changed-total receipt; keep fixture mode explicit.
- Native device change: build the app and perform the relevant physical-device check. Simulator success is not hardware validation.
- Documentation-only change: review the diff and confirm names, commands, and links are accurate; unrelated application tests are not required.

Use the project's verified commands from its runbook. Do not invent test scripts or rebuild unrelated parts repeatedly. After fixing a failure, rerun that check and the relevant complete demo flow.

## 9. Rules if parallel coding becomes necessary

Use a separate branch and isolated checkout/worktree for each coding agent, even when they share a machine. Never have two agents edit the same checkout concurrently.

The human must assign non-overlapping files before work begins. One owner controls shared contracts and dependency lockfiles. Integration remains sequential through the human owner, with a smoke test after each merge.

Running agents on different machines is acceptable under these rules, but adds environment and integration work. Do not introduce it merely because spare machines are available.

## 10. Documentation, comments, and handoff

- Use clear, professional language. No emojis in commits, issues, PRs, or repository documentation.
- Keep source comments short and use simple lowercase prose. Do not add comments that only repeat the code.
- Mark temporary fixtures, mocked inputs, and untested hardware assumptions explicitly.
- Keep provider keys and device credentials outside tracked files. Supply example configuration with placeholders only.
- Record SDK/runtime versions and the exact working startup commands. Do not upgrade dependencies during the final rehearsal window without an observed blocker.

At the end of each task, the agent reports:

1. Issue/task ID and branch.
2. What changed and which files were touched.
3. Exact verification performed and the actual results.
4. Remaining limitations or physical checks.
5. The next human action needed to review or demonstrate the result.

The agent then stops at the task boundary. The integration owner chooses the next task according to dependencies and the time remaining.
