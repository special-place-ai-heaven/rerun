# machinist: the author's factory, read against ours

as_of 2026-11-13.

`owainlewis/factory`, which the tutorials point to, is not public (GitHub answers 404). The author's public
factory is **machinist**: <https://github.com/owainlewis/machinist> at commit `4d7d776` (2026-10-29), MIT
licence, Go control plane with a React UI, about 20,000 lines of Go without tests. Nothing in it carries the
labels `factory-ready` or `factory-blocked`, so it is a different and larger program than the one in the lesson.

What was read in full: `ARCHITECTURE.md`; under `docs/` the pages `workflows.md`, `artifacts.md`,
`task-artifact-model.md`, `agent-workflow.md`, `local-factory/spec.md`, `local-factory/automations.md` and
`local-factory/github-followups.md`; the triage, spec and review prompts; the README and the classify prompt
of the risk-gated merge example. Read in part: the capacity section of `configuration.md`, sections 3, 4, 5
(milestones 3 to 6) and 7 of `workflow-roadmap.md`, the second half of the essay
`coding-workflows-in-code.md`, the first 60 lines of the example's `gate.py`, and the names of the tests of the
optional script `agent.py`. Not opened: `SECURITY.md`, `native-agents.md`, the setup, Kubernetes and deployment
pages, and all Go code.

So every statement about machinist below is what its documents say, and each point carries one of three marks:
**shipped** (the architecture or an operations page describes it as working), **proposed** (the roadmap), or
**example** (the essay or the optional script). Every statement about our factory was checked in our code and
carries its path.

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

1. **A typed reason on every waiting job** (shipped). machinist gives each queued job `waiting_reasons`: no compatible
   worker, worker busy, global limit, repository limit, hold, and so on. Ours prints a state and, for a
   dependency, `waits on #n` (`tools/factory/timeline.py`); a job held back by a ceiling or a back-off shows no
   reason. Phase B adds queues per worker type and ceilings, which is where this is needed: one field per waiting
   job, from a fixed list.
2. **Measures of the factory, not of the queue** (proposed; the two counters are in the example script). The
   roadmap's list: accepted outcomes, human interventions per delivery, repair passes that changed nothing,
   defects missed, time and cost, recoveries, duplicate deliveries. Ours measures queue depth and waiting,
   occupancy, tokens per merged job and review time (`tools/factory/measures.py`). Missing are the two that say
   whether the factory is hands-off and whether its repairs are real: owner interventions per merged change, and
   fix rounds that pushed no new commit. The optional script `agent.py` already counts repairs with and without
   a new commit, and marks a token record "usage incomplete" so a missing number is never read as zero.
3. **The check is run by code, not reported by the worker** (example, and proposed). In the essay's sample loop
   the program runs the test command, reads its exit code, and hands the output to the agent as data ("Python
   will rerun the checks"); the roadmap proposes the same for the product. What is shipped is narrower: the
   foreman checks Git and GitHub evidence against the claim, and the reviewer is given the exact diff and the
   check results. In ours the builder runs the test and says so; the proof arrives later with GitHub's checks.
   This bears on the open point of [GOAL.md](../2026-11-11-factory-map/GOAL.md): see the note added there.
4. **The agent recommends, code applies** (shipped). Their upkeep agent gets a read-only checkout and suggests labels; the
   foreman adds them and "never removes human labels or changes routing labels". Our triage coworker posts its
   own labels with the shared token, and the same protection is a sentence in its instructions (added
   2026-11-13 when this repository joined its list). The pre-pass script that already runs before it is the
   place where the write could move behind code.
5. **A hold** (shipped). A held job is not dispatched and nothing is published for it; the hold survives retries and is
   lifted only by naming it. Ours stops a merge by setting the pull request to draft, which ends the job
   `factory-blocked` as a side effect.
6. **What a schedule does when its last run is not finished** (shipped). Theirs: a scheduled job waits for its own earlier
   run, skips an occurrence while busy, and after downtime runs once, not once per missed time. Not checked for
   the Rerun engine: to be read before any new upkeep job gets a schedule.
7. **A check before tokens are spent** (example). The optional script fails a job with a provisioning error
   before the agent starts when a tool is missing. Ours learns "no room" from the builder itself, after the run
   has started (`clocks.klass`, the `_ROOM` texts), and then retries.
8. **One builder conversation across build and fix** (proposed). The roadmap wants one session for the build
   and its repairs "when the harness supports it"; the shipped product starts a fresh process for every stage,
   as ours does (`dispatch.py` never passes `sessionId`, though `send_message` takes one). So neither has it.
   Whether a continued session is cheaper here has to be measured: it saves re-reading the code and adds the
   whole earlier conversation to every step.

## Where ours is ahead

- Jobs that depend on each other, a check of an issue's shape at intake and a cycle check
  (`tools/factory/cutshape.py`). Theirs has no dependencies between jobs yet (roadmap, milestone 5).
- Several runs of one coworker at the same moment. Theirs is serial per credential by design.
- Merge without a person when review accepts and the checks of that commit are green. Theirs merges only small
  documentation edits on its own.
- A goal on every run, checked by the engine.

## A risk their design points at

machinist never runs two agents on one subscription at once, and says why: the credential is one stream. Ours
does. What our engine does about it, read in `apps/engine/src/connections/claude-token.ts`:

- A connection whose token has no refresh token or expiry is "static" and is never refreshed. Then none of
  this applies. The live connection is not of that kind: of 967 finished runs read on 2026-11-13, one (on
  2026-11-11) ended with the engine's own text for a sign-in renewed during the run.
- Otherwise the old access token is revoked when a new one is issued (the comment above
  `IDLE_REFRESH_WINDOW_MS`), and a running program keeps the token it started with. So
  `ensureFreshClaudeToken` refreshes from four hours before expiry, but only while no run is out on the
  connection; with runs out it defers, and in the last five minutes it refreshes regardless.
- A run whose token was swapped under it is told apart (`claudeTokenOutlived`). It ends in error with the text
  `interrupted: Claude sign-in renewed during the run` (`settle` in `apps/engine/src/runtime/loop.ts`); nothing
  picks it up again.

The question for phase B follows from the second point. A factory that is busy around the clock has no moment
without a run, so the refresh arrives under every running coworker at once, and each of those runs ends in
error. Settled on 2026-11-13, after the first version of this page:

- The delegator counted such an end as a failed attempt (`clocks.klass`; `_ERR` listed only overload and rate
  limits). It becomes class `transient` in #241: sent again after a back-off, and no attempt is spent.
- That saves the job, not the work: every run in flight at that moment is still lost and paid for again.

Open, for the cut of phase B:

- How long a sign-in lasts. The engine logs `expiresIn` at each renewal; it was not read. It decides how often
  the cut happens.
- Whether the delegator makes the idle moment itself: when a renewal is due it holds new sends, the runs in
  flight finish, the engine renews with no run out, and sending goes on. That costs a pause of minutes once per
  sign-in instead of every run in flight. The engine knows when a renewal is due and is deferred (it logs
  "refresh deferred"), but no account tool reports it, so this needs one field on the engine's side first.
  Runs outside the factory (a chat, a schedule) hold the same connection and cannot be held back; they are
  short.

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
