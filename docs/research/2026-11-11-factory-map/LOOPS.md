# Mechanisms of the factory: what Rerun has, what is missing (draft)

Rob, 2026-11-12: "We must also ultrathink on every single work loop we will create for every single workflow in rerun
harness. This will decide correctness, efficiency, code superiority and prevent code slop ... List every mechanisms that
rerun already uses, and all the missing mechanisms like loops, gates, consensus mechanisms, orchestration, decision
making by main LLM to rule over disputes and consensus options, and many other mechanisms needed to make automated
software factory described in north star"

Part 1 (what exists, with file and line) comes from a code read of `dev` and is added when that read is finished.
Part 2 below is the design: every loop the factory needs, each with the same six fields, so that none is left to a
prompt. A loop without an exit a script can check, a bound and an escalation is not a loop; it is a hope.

## The shape every loop has

| Field | Meaning |
|---|---|
| **Enters when** | the evidence that starts it |
| **Who works** | the coworker role and model tier inside the loop |
| **Exit check** | what a script reads to say "done"; never the coworker's own words |
| **Bound** | the most rounds or minutes before it stops by itself |
| **On fail** | where the job goes: back one stage, to an arbiter, or BLOCKED |
| **Removes** | the manual step or prompt section it replaces |

## The loops, in pipeline order

### Before any code
| # | Loop | Enters when | Who works | Exit check | Bound | On fail |
|---|---|---|---|---|---|---|
| 1 | **Intake** | the user tells the side bot what they want | side bot (small model) | a job issue exists with Goal and Done-tests; each done-test names something a script or CI can run | 3 questions to the user, on one card | back to the user with what is missing |
| 2 | **Facts** | job issue open | code reader (small model, read-only) | every stated fact carries path and line that exist at the named commit | 1 retry | back to Facts with the dead references listed |
| 3 | **Plan** | facts posted | planner (large model) | plan has outcome, done-tests, decision, rejected alternatives, risks; every claim about code points at a fact | 2 rounds | arbiter |
| 4 | **Plan review** | plan posted | Devils Advocate always, plus reviewers the plan's area calls for | every objection has a disposition (accepted and changed, or answered); the reviewers post the marker | 2 rounds | arbiter rules on the open objections |
| 5 | **User approval** | plan reviewed | nobody; a card through the side bot | the user's answer is recorded on the job | a per-job setting: wait, or proceed after N hours and inform | stays in planning; never proceeds on a "no" |
| 6 | **Breakdown** | plan approved | chunker (large model) | chunk list parses; every chunk has paths, one test file, dependencies, a size under the cap; the graph has no cycle; chunks that may run together share no path; every done-test of the job is covered by some chunk | 2 rounds | back to Plan (a plan that cannot be cut is wrong) |
| 7 | **Schedule** | breakdown accepted; then every tick | nobody; code | ready set = dependencies merged and no path overlap with a running chunk; started up to capacity | every tick | a chunk ready but not started for N ticks is reported (starvation) |

### Building
| # | Loop | Enters when | Who works | Exit check | Bound | On fail |
|---|---|---|---|---|---|---|
| 8 | **Build chunk** | scheduled | builder (small or mid model), fresh session, own worktree | a pushed commit on the chunk's branch; diff touches only the chunk's paths; under the size cap; no forbidden files (workflow files, secrets, generated folders); line endings and author correct | 1 session of about 30 minutes | counts as a failed attempt |
| 9 | **Red before green** | chunk pushed | nobody; CI | the chunk's test fails on the job branch without the change and passes with it | 1 run each | a test that passes before the change is rejected: it proves nothing |
| 10 | **Chunk test** | chunk pushed | nobody; CI single-file run plus type check | green | 1 run, plus one re-run alone for a test known to be unstable | Build again with the log tail in the packet, at most 2 times; then back to Breakdown with the reason |
| 11 | **Escalation ladder** | a chunk failed its attempts | nobody; code | the next attempt runs on the next model tier with the same packet | 1 step up | back to Breakdown |
| 12 | **Integrate** | chunk green | nobody; code | chunk merged into the job branch without conflict | 1 try | conflict: a resolver session gets both sides and the plan; then chunk test again |

### Proving and judging the whole job
| # | Loop | Enters when | Who works | Exit check | Bound | On fail |
|---|---|---|---|---|---|---|
| 13 | **Job CI** | all chunks merged | nobody; CI | full suite green on the job's pull request head | 1 run | failure triage (14) |
| 14 | **Failure triage** | any red CI | a script first: known signatures (unstable test, runner fault, timeout, pre-existing failure on the base). A model only when no signature matches | the failure is labelled: caused by the job, pre-existing, unstable, or infrastructure | 1 pass | caused by the job: fix build with the log. Otherwise: re-run or a separate small job; the job is not blamed |
| 15 | **Review** | job CI green | reviewers from the risk table (correctness always; security, data, contracts, interface by rule) | each required reviewer's verdict is bound to the head commit | 2 rounds; a re-review covers only the change since | third round goes to the arbiter, not back to the builder |
| 16 | **Consensus** | more than one reviewer | nobody; code | all required reviewers ACCEPT at the same head. Security and data reviewers hold a veto; others are by majority | — | a split verdict goes to the arbiter with both texts |
| 17 | **Dispute** | a builder or planner contests a rejection with evidence, or reviewers split, or a loop hit its bound | arbiter: the main model at its highest tier (Advisor), fresh session, sees only the plan, the diff, both positions and the evidence | a written ruling: who is right, what changes, and whether a rule should change so it does not recur | 1 ruling per dispute | "needs the owner" only for what is his alone: money, deleting data, product direction |
| 18 | **Acceptance** | review accepted | nobody; CI. For interface work also a rendered check: screenshots or measurements of the running product against the done-tests | the job's original done-tests pass on the integrated head | 1 run | back to Plan with what failed: the plan promised something the build did not deliver |
| 19 | **Merge** | accepted | nobody; code | green, accepted at this exact head, no open objection, branch up to date | — | waits; never merges on a stale verdict |
| 20 | **Deliver** | merged, for products with a deploy | nobody; code, per product procedure | backup taken, new version running, health check passes, a smoke check of the changed feature passes | 1 try | automatic rollback to the previous version, then a job for the cause |

### Around every job
| # | Loop | Runs | Exit or action |
|---|---|---|---|
| 21 | **Watchdog** | every tick | a run with no evidence after its time limit is stopped (needs the cancel control) and counted as a failed attempt; a job with no progress for N ticks is BLOCKED and the user is told once |
| 22 | **Budget** | every tick | a run over its token ceiling is stopped; a job over its ceiling pauses and asks the arbiter whether to continue, re-plan or stop |
| 23 | **Cleanup** | every tick and nightly | the session and worktree protocol: no session, no worktree; nothing removed before it is proven saved |
| 24 | **Runner self-check** | every tick | the runner writes a heartbeat; a second small timer alerts if it is missing; a tick that throws leaves the ledger unchanged |
| 25 | **After the merge** | for 7 days | a defect traced to a merged job is linked to it and counted against its quality; a regression reopens the job |
| 26 | **Close and measure** | job merged | the three numbers and the "why" report are written by a script: tokens by stage and model, time by stage, review rounds, attempts per chunk, largest run |
| 27 | **Learn** | job closed | a proposal (a rule, a skill, a packet change, a threshold) names the measured cause it targets; it is applied to the next jobs only; it stays if its number moved and is removed if not |
| 28 | **Knowledge delivery** | each stage start | the packet is assembled by label from rulings, repo rules and past outcomes; what was delivered and whether it was read is recorded |

## Gates (hard refusals by code, not requests in a prompt)

| Gate | Refuses when | State |
|---|---|---|
| Work order shape | the issue lacks Goal, Done-test, Limits, Chunks | exists (`job-open`) |
| Plan marker | no reviewed plan on the issue | exists (`wt new`); the marker does not prove who posted it |
| Builder capacity and memory | no slot, low memory, low disk | exists (`wt new`) |
| Nothing unsaved is deleted | unpushed commits, uncommitted changes | exists (`wt done`, `sweep`); salvage of uncommitted changes missing |
| Verdict bound to the head | the pull request moved since the review | exists (`review --sha`), used only when the reviewer passes it |
| Facts exist | a plan cites a path or line that is not there | missing |
| Plan reviewed by someone else | the author marks its own plan | missing (one shared account) |
| User approval | plan not approved | missing |
| Breakdown shape, cycles, overlaps, coverage | see loop 6 | missing |
| Chunk diff inside its paths and size | builder touched other files | missing |
| Forbidden files and secrets in a diff | workflow files, keys, generated folders | partly (`risk` stops on workflow files) |
| Red before green | the test never failed | missing |
| Required reviewers present | a risk label has no verdict | missing as a gate (`risk` only names them) |
| Merge conditions | not green, not accepted at head, stale | partly (`merge-dev` checks CI only) |
| Token ceiling per run and per job | over budget | missing (needs an engine change or the cancel control) |
| Deploy preconditions and rollback | no backup, a run in progress, failed health | exists as a procedure for testpilot, not as code |

## Decision rights (who rules when a loop cannot)

| Question | Decided by |
|---|---|
| Does the evidence satisfy the exit check? | code, always |
| Is the plan sound? Is the code correct? | reviewers; split or exhausted rounds go to the arbiter |
| Builder against reviewer, planner against challenger, reviewer against reviewer | the arbiter, once, in writing; the ruling becomes a precedent the packets carry |
| Continue, re-plan or stop a job over budget or out of rounds | the arbiter |
| What to build, whether a plan is what was wanted | the user, at the approval card |
| Money, deleting data that cannot be recreated, product direction | the user |

Boss is the orchestrator for what the runner does not drive: intake with the user, BLOCKED jobs, and work outside the
factory. He does not decide what happens next inside a job; the ledger does.

## Workflows (which loops a kind of job runs)

| Kind of job | Loops | Notes |
|---|---|---|
| New feature, behaviour change | all | the full line |
| Defect | 1, 2, then a reproduction test that fails (replaces 3 to 6 when the fix is one chunk), 8 to 20 | larger fixes take the full line |
| Refactor with no behaviour change | all, with loop 9 replaced by "every existing test still passes and no test was edited" | |
| Dependency upgrade | 1, a release-notes read (facts), 3 to 6, 8 to 20 | Rob's rule: the notes of important libraries are read and their changes handled |
| Small known fix | 1, 8, 10, 13, 15, 19 | the `SMALL FIX` path; counted, so its share can be watched |
| Documentation, research | 1, 3, 4, then a critic loop in place of 8 to 14 | no CI, so the exit check is the critic's dispositions |
| Release | 13, 19, 20 by the release automation | no model in the loop |
| Incident in production | reproduce, fix as a defect with priority over the schedule, deliver, then 25 and 27 | |
| A change to the factory itself | all, plus loop 27's keep-or-remove on the next jobs | the line corrects itself the same way it builds products |

## What makes this cheap instead of heavy

- Sixteen of the twenty-eight loops have nobody working in them: they are code reading evidence.
- A model appears only where judgement is needed, in a fresh session, with a packet, on the smallest tier that has
  passed that kind of chunk before.
- Every bound is a number in one config file, and every time a bound is hit it is counted. A bound that is hit often
  is the next thing to fix; one that is never hit can be tightened.
- Nothing here is built ahead of need: the order of building follows the measured failures, and each loop is added as
  the smallest check at a place work already passes through.
