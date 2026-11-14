# What the planning skills of owainlewis/blueprint would give our cut (#281)
as_of 2026-11-14

Their side: `owainlewis/blueprint` at 9a73756a1f0dddd526aab89d2600e487ce6880ff (MIT, 66 files per the issue; not recounted),
every file fetched from raw.githubusercontent.com at that commit on 2026-11-14. Ours: worktree on dev 27db4ef.
Marks: **V** = verified (I read it), **I** = inference.
Short answer: their skills hold two rules our cut lacks (a size rule and "split by result, not by layer"); the rest we have.

## 1. What each planning skill produces (all V)

| Skill (path) | Artefact it writes | Fields of the artefact |
|---|---|---|
| requirements (`skills/requirements/SKILL.md`, template `skills/requirements/references/requirements.md`) | root `REQUIREMENTS.md`, the PRD of the whole product | Author, Status (Draft/Proposed/In Review/Approved), Date; Problem and users; User stories `REQ-n` with "Done when"; Business rules; Constraints; Out of scope; Success measures; Open decisions |
| spec (`skills/spec/SKILL.md`; its template `references/spec.md` was not read) | `docs/<feature-slug>/spec.md`, or the ticket text: "The spec is the ticket" | From the example `examples/consulting-crm/docs/capture-lead/spec.md`: header (Author, Status, Date); Problem; Goals; Non-goals; User journeys `J-n` (Given/When/Then, tied to `REQ-n`); Technical design with a diagram; Decisions table; Risks and rollout; Acceptance table `AC-n` (Done when, Proves, How to check); Open decisions |
| plan (`skills/plan/SKILL.md`) | an ordered list of tasks returned in chat; "Do not write a plan file"; tracker tickets only if asked | Per task, under "## Template": title; What are we building?; Why?; Done when (3 to 7 results, keeps AC/J/REQ ids); How to check (exact commands); Agent notes (Depends on, Source, decisions); Out of scope |
| review (`skills/review/SKILL.md`) | a findings list and a verdict block, nothing written to the repository | Findings: Must/Should/Could fix with Where, Problem, Proof, Trigger, Fix; verdict block VERDICT, SPEC, CHECKS_RUN, UNVERIFIED, REVIEWED_AT |
| codex-issue-coordinator (`skills/codex-issue-coordinator/SKILL.md`) | no planning artefact: it runs a batch of existing issues, one worker, worktree, branch and PR each | Reads the parent issue and dependencies; returns per issue worker, PR, gate state, blocker (heading "## Return") |

## 2. Their ticket beside our job (field by field)

Their ticket = the plan template (`skills/plan/SKILL.md`, "## Template") on top of the spec. Ours = the issue shape
read by `tools/factory/cutshape.py` and shown in issue #246 (text read via the packet tool, 2026-11-14).

| Our field | Their field | Match |
|---|---|---|
| Worker (`WORKERS` in `cutshape.py`: coder, reviewer, researcher, designer) | none; the plan names no worker type. The coordinator names workers `#<issue> <short title>` ("## Coordinator workflow" step 3) | no equivalent. V |
| Files (allowed paths, "nothing else"; parsed, one backticked path per bullet in `cutshape.py`) | none. `skills/spec/SKILL.md` Rules: "Leave the code and the list of files to the agent that builds it." | opposite choice. V |
| Change | "What are we building?" (1 to 3 sentences) plus "Why?" | same job; ours is long and exact (#246 lists four functions), theirs short. V |
| Done-test seen failing | "Done when" (3 to 7 observable results) | theirs is a result, not a named test and not seen failing. Red-first appears only in `skills/review/SKILL.md` Part 2 step 4 ("Revert the code behind each main new test and confirm the test fails"). V |
| Run command | "How to check": "Exact commands, and any manual check" | same. Ours is not parsed by `cutshape.py` (no Run pattern in it); #246 states the exit code seen on dev. V |
| Waits on (`**Depends on**`, parsed; cycles checked in `cutshape.cycles`) | "Depends on: <task titles, or None>" under Agent notes | same; theirs by title, ours by issue number and machine-read. V |
| nothing | "Out of scope" (nearby work the task might absorb) | theirs only. In ours "Files ... nothing else" does part of it. V/I |
| nothing | "Source: link to the spec section", ids `AC-n`, `J-n`, `REQ-n` kept stable | theirs only; ours links by "Part of #198" prose. V |
| Test file (optional line, must be one of Files) | none | ours only. V |

`cutshape.parse` requires only the dependency line, a valid worker (default coder) and one path (V, code read); a Change, Run or done-test is not checked.

## 3. Width and size

- Width. `skills/codex-issue-coordinator/SKILL.md`, "## Coordinator workflow" step 4: "Independent issues may run together up to the worker limit." Step 5 of "## Preconditions": "Default to two active workers." Boundaries: "Never start dependent work from an unmerged pull request in this workflow." V
- Their files say nothing about two tickets that touch the same file (I found no such rule in the eight skill and guide files read). Ours names it as a gate not built: `docs/research/2026-11-11-factory-map/MACHINE.md` section 7, row "Cut shape" ("the shared-path rule is not built"). V
- Size. `skills/plan/SKILL.md`, "## Rules": "Aim for 250 to 500 words a task. If it needs more, split it." And its opening: "Split by result, never by layer". V
- For scale: the body of #246 is about 457 words by `wc -w` (V, includes headings and the Run block), inside their range.

## 4. Take (four)

**T1. Split by result, not by layer.**
- Theirs: `skills/plan/SKILL.md`, intro paragraph ("Split decided work into tasks that each deliver something that works, end to end"). Shipped skill text. V
- Ours: `docs/research/2026-11-11-factory-map/MACHINE.md` section 2a, the diagram cuts one feature into parts by layer (contract, storage, engine route, app client, screen) that join at a quality-control task; #246 itself is "the first half of job 1" (a module, `dispatch.py` untouched). V
- Would change: add a cut rule that every job leaves something a person can run, and that a layer-only job is allowed only when named as a shared contract (their "Keep shared contracts in one task", same skill, Steps 2). Whether this fits our joins is Holmes's call. I
**T2. A size rule on a job.**
- Theirs: `skills/plan/SKILL.md`, "## Rules" (quoted in part 3). Shipped skill text. V
- Ours: no size check in `tools/factory/cutshape.py` (code read; only dependency, worker, files, test file, cycles). V
- Would change: a word count or file count warning at intake for a job text, so an over-wide job goes back to the cut. The 250 to 500 range is theirs for human-and-agent readers; our #246 has 457. Number for ours not measured on other jobs. I
**T3. A readiness test before a job is cut.**
- Theirs: `skills/plan/SKILL.md`, "## Rules": "A task is ready when a fresh agent could finish it without asking a product or design question"; `skills/spec/SKILL.md` Process step 5, same idea. Shipped skill text. V
- Ours: `cutshape.py` checks shape only; the plan marker gate is posted by the delegator itself (`MACHINE.md` section 7, row "Plan marker": "it never refuses"). V
- Would change: before `PLAN READY`, a reader who did not cut it tries to name a missing decision; today no step does this. I
**T4. Out of scope, per job, and a source link.**
- Theirs: `skills/plan/SKILL.md`, template headings "### Out of scope" and "### Agent notes" (line "Source: link to the spec section"). Shipped skill text. V
- Ours: "Files (allowed paths; nothing else)" in #246 and `cutshape.parse`; the link to the parent is prose ("Part of #198"). V
- Would change: two optional lines in the cut text, "Out of scope" and "Proves" (the decision or journey id of the parent), so a reviewer can trace a job back. I

## Have (not taken)

- Dependencies by order, no stacking on unmerged work: `cutshape.py` (`Depends on`, `cycles`); MACHINE section 2a joins. V
- A fresh reviewer, read-only, verdict tied to a commit (`REVIEWED_AT`): "Verdict at this commit" gate, MACHINE section 7. V
- Red before green: `skills/review/SKILL.md` Part 2 step 4 vs `gate.py` and MACHINE section 7 row "Red before green" (live only in the hand tool). V
- Three failed attempts then pause: coordinator "Coordinator workflow" step 7 vs the retry classes, MACHINE section 9, row "Retry". V
- Worker cap: coordinator default of two vs `max_jobs` per type in `tools/factory/dispatch.json` (shape in #246). V
- Plan returned in chat, not written to a file, tickets only on request: ours cuts into issues by hand through Boss (MACHINE section 9, "Front of the line"). I

## 5. Not read

- Their `skills/spec/references/spec.md` (the spec template), `skills/architecture/`, `skills/task-to-pr/`, `skills/test/`, `skills/improve/`, `skills/architecture-review/`, `README.md` (including its "sample plan"), `examples/README.md`, `.github/pull_request_template.md`, and every other file of the 66.
- The commit history of their repository and any issue or PR there. Licence read from the issue text, not from `LICENSE`.
- Ours: MACHINE.md sections 1 to 6, 8 and 10; any job text other than #246; `readyq.py`, `evidence.py`, `gate.py` (named from MACHINE.md only, not opened).
- The issue text lists three files under `examples/consulting-crm/`; the tree at that commit has `ARCHITECTURE.md`, `REQUIREMENTS.md` and `docs/capture-lead/spec.md`, all read. Their examples are teaching examples with no code (their own text: "This is a teaching example").
