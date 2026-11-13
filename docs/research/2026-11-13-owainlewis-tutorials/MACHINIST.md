# machinist: the author's factory, read against ours

as_of 2026-11-13.

`owainlewis/factory`, which the tutorials point to, is not public (GitHub answers 404). The author's public
factory is **machinist**: <https://github.com/owainlewis/machinist> at commit `4d7d776` (2026-10-29), MIT
licence, Go control plane with a React UI, about 20,000 lines of Go without tests. Nothing in it carries the
labels `factory-ready` or `factory-blocked`, so it is a different and larger program than the one in the lesson.

What was read: `ARCHITECTURE.md`, every operations page under `docs/`, the roadmap, the essay
`docs/coding-workflows-in-code.md`, the triage, spec and review prompts, the risk-gated merge example and the
names of its 80 scenario tests. The Go code itself was not read, so every statement about machinist below is
what its own documents say. Every statement about our factory was checked in our code and carries its path.

## What it is

One process (the "foreman") owns a private SQLite database and carries a job through Triage, an optional Spec
with human approval, Build, and an independent read-only Review, with at most three repair rounds on the same
pull request. A person merges; a narrow automatic merge exists for small documentation edits only. Agents are
the native Codex or Claude Code programs, started fresh for each stage. Work runs one job at a time per
credential.

## Where the two agree

| Rule | machinist | ours |
|---|---|---|
| Code moves the job, agents do the work | "The foreman is code that validates evidence and advances state" | `tools/factory/dispatch.py` |
| A transition is saved before anything is sent | "Transitions commit before dispatch" | `send()`: the intent row is written before `send_message` |
| Acceptance is tied to one commit | review bound to "the implementation attempt and published head" | review at `headRefOid`, merge with `--match-head-commit` |
| No checks is not a pass | "Missing checks are not passing checks" | `checks_verdict` waits on an empty list |
| Text on an issue or pull request is evidence, not instruction | `Task input (untrusted data)` in every prompt | the line on whose text is an instruction in `build_brief` |
| The repair budget survives a restart | "a restart must not silently reset the budget" | `attempt`, `round` and the retry counts are rows in the ledger (`store.py`) |
| A passing failure is retried, and stays on record | "a passed retry does not erase the earlier failure" | class `transient` with back-off; every change is a `transitions` row |
| One controller per job | "Never use two different controllers for the same active delivery" | one writer, by a lock on the ledger file (`store.py`) |

## What ours lacks or does worse

1. **A typed reason on every waiting job.** machinist gives each queued job `waiting_reasons`: no compatible
   worker, worker busy, global limit, repository limit, hold, and so on. Ours prints a state and, for a
   dependency, `waits on #n` (`tools/factory/timeline.py`); a job held back by a ceiling or a back-off shows no
   reason. Phase B adds queues per worker type and ceilings, which is where this is needed: one field per waiting
   job, from a fixed list.
2. **Measures of the factory, not of the queue.** Their list: accepted outcomes, human interventions per
   delivery, repair passes that changed nothing, defects missed, time and cost, recoveries, duplicate
   deliveries. Ours measures queue depth and waiting, occupancy, tokens per merged job and review time
   (`tools/factory/measures.py`). Missing are the two that say whether the factory is hands-off and whether its
   repairs are real: owner interventions per merged change, and fix rounds that pushed no new commit. Their token
   record also carries a flag for "usage incomplete", so a missing number is never read as zero.
3. **The check is run by code, not reported by the worker.** In their loop the program runs the test command,
   reads its exit code, and hands the output to the agent as data ("Python will rerun the checks"). In ours the
   builder runs the test and says so; the proof arrives later with GitHub's checks. This is the missing answer
   in [GOAL.md](../2026-11-11-factory-map/GOAL.md): see the note added there.
4. **The agent recommends, code applies.** Their upkeep agent gets a read-only checkout and suggests labels; the
   foreman adds them and "never removes human labels or changes routing labels". Our triage coworker posts its
   own labels with the shared token, and the same protection is a sentence in its instructions (added
   2026-11-13 when this repository joined its list). The pre-pass script that already runs before it is the
   place where the write could move behind code.
5. **A hold.** A held job is not dispatched and nothing is published for it; the hold survives retries and is
   lifted only by naming it. Ours stops a merge by setting the pull request to draft, which ends the job
   `factory-blocked` as a side effect.
6. **What a schedule does when its last run is not finished.** Theirs: a scheduled job waits for its own earlier
   run, skips an occurrence while busy, and after downtime runs once, not once per missed time. Not checked for
   the Rerun engine: to be read before any new upkeep job gets a schedule.
7. **A check before tokens are spent.** Theirs fails a job with a provisioning error before the agent starts
   when a tool is missing. Ours learns "no room" from the builder itself, after the run has started
   (`clocks.klass`, the `_ROOM` texts), and then retries.
8. **One builder conversation across build and fix.** They keep one session for the build and its repairs. Ours
   starts a fresh session for every step: `dispatch.py` never passes `sessionId`, though `send_message` takes
   one. Whether a continued session is cheaper here has to be measured: it saves re-reading the code and adds
   the whole earlier conversation to every step.

## Where ours is ahead

- Jobs that depend on each other, a check of an issue's shape at intake and a cycle check
  (`tools/factory/cutshape.py`). Theirs has no dependencies between jobs yet (roadmap, milestone 5).
- Several runs of one coworker at the same moment. Theirs is serial per credential by design.
- Merge without a person when review accepts and the checks of that commit are green. Theirs merges only small
  documentation edits on its own.
- A goal on every run, checked by the engine.

## A risk their design points at

machinist never runs two agents on one subscription at once, and says why: the credential is one stream. Ours
does, and the engine handles the reason it is dangerous: Anthropic revokes the old access token when a new one
is issued, so the engine refreshes "while no CLI is out on this connection", hours ahead, and forces a refresh
under live runs only in the last minutes (`apps/engine/src/connections/claude-token.ts`, the comment above
`IDLE_REFRESH_WINDOW_MS`). A factory that is busy around the clock has no idle moment. Then the forced refresh
arrives under every running coworker at once, and their runs end on a rejected credential, which the delegator
counts as a failed attempt, not as a passing failure (`clocks.klass`, `_ERR`). This is a prerequisite of phase
B to check before the ceiling of parallel runs is raised: either that error becomes class `transient`, or the
delegator leaves a gap for the refresh.

## Not taken

The Kubernetes runner, the GitHub App sign-in, the React UI, the artifact store and the spec approval step
solve problems this factory does not have.

## The two companions (README only)

- `owainlewis/software-factory` (Python): a Claude Code and Codex plugin that takes one ticket through triage,
  build, review and a browser review of pages. It stops and proposes a split when a ticket is too big for one
  pull request.
- `owainlewis/assembler` (TypeScript): a command-line runner for workflows written as code.

For the factory's weakest spot, cutting a feature into jobs, the author's planning skills are in a fourth
repository, `owainlewis/blueprint` (requirements, a spec per feature, a plan of small tickets). Not read.
