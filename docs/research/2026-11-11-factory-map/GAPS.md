# Gaps to close for the golden form (the negatives, 2026-11-12)

Rob: "make a list of all gaps we must close for the golden vision. Anything missing, anything lacking, anything
underutilized, detrimental, with a negative impact and ready to cut out.. all the negatives."

Each row names the evidence. "Measured" and "proven" mean seen on 2026-11-11/12; "code" means read in `dev`.
Order inside each group is by how much it costs today.

## 1. Missing: the factory cannot run without a person

| # | Gap | Evidence | Closes with |
|---|---|---|---|
| M1 | Nothing drives a job from stage to stage. A person dispatches, waits, reads CI, decides, dispatches | measured: 12 h 42 min of hand orchestration on testpilot#189; the team idled an hour when the orchestrator was slow | runner v1 (rerun#53) |
| M2 | No ledger of jobs, stages and chunks that code can read | Boss's board and handoff files are prose; one was overwritten | the ledger comment on the job issue (#53) |
| M3 | No breakdown into chunks a small model can finish | one job ran as two sessions of 20-25M tokens each | Breakdown stage and chunk format (#53) |
| M4 | No scheduling: nothing decides what runs side by side | builders blocked twice by a limit that counted finished folders | Schedule stage (#53 chunk 10) |
| M5 | No way to stop a run, and no alarm when one stalls | a session looped 2.5 h; cancel refused with 401; found by Rob | rerun#52 |
| M6 | Nothing wakes the next step when CI finishes or a run ends | every wait was a watcher on one PC that dies with the session | the runner's tick |
| M7 | Plan approval by the user has no mechanism | proven possible today with the ask-the-user card; not built | approval stage (#53) |
| M8 | Intake through the side bot does not create a job | code: the side bot can be started only with the engine key; no path from it to a factory job | intake stage; probe from the server first |
| M9 | No dispute ruling: split reviewers or exhausted rounds have nowhere to go | on #189 the third rejection was handled by a person | arbiter loop |
| M10 | No acceptance stage: nothing checks the job's original done-tests on the merged result, and nothing looks at the running product | #189 deployed without anyone seeing it in a browser | acceptance loop with a rendered check |
| M11 | No delivery loop with automatic rollback | deploys are a hand procedure; two parties deployed the same stack on one evening | deliver loop per product |
| M12 | No learning loop: outcomes are not recorded, changes to rules are not measured | the change log has "pending" in every result cell | close-and-measure, then keep-or-remove |

## 2. Lacking: exists, but too weak to rely on

| # | Gap | Evidence | Closes with |
|---|---|---|---|
| L1 | Runs cannot be judged while they run: no tokens until the turn ends | proven live | rerun#43 |
| L2 | Cost cannot be attributed: no job, branch or initiator on a run; the cost script matches text and missed half the runs | measured: 30 of 66 runs found | rerun#44, #45; fix `job-cost` matching |
| L3 | Verdicts and plan markers do not prove who wrote them | all coworkers post from one account | separate identities or a signed verdict record |
| L4 | `merge-dev` checks CI only; required reviewers are named, not enforced | code | merge gate in the runner |
| L5 | The plan marker passes on any line that starts with the words | my own issue text passed it by accident | tighter matcher |
| L6 | The sweep keeps a clean folder whose work is already on the default branch | code and measured (`189-1`) | one rule in the sweep |
| L7 | Uncommitted leftovers of a crashed session have no salvage | code | salvage step in the removal sequence |
| L8 | Model and thinking level are fixed per provider, not set per coworker or per stage | code; builders on the large model cost 4 to 10 times the mid one per round | rerun#46; model on each trigger |
| L9 | A dead tool connection is invisible and needs a manual reconnect | observed after every tool update | rerun#41, terminal-commander#294 |
| L10 | CI: 39% of runs end green; red arrives after 17 minutes; two heavy runners are the queue | measured | CI plan changes 2 to 7; carry to every repo |
| L11 | Only testpilot can run one test file on demand | rerun, terminal-commander, symforge have no such workflow | CI standard for all repos |
| L12 | The server cannot run anything on a timer, reach Docker, or deploy | measured | one install by Rob in a terminal on the server |
| L13 | The server has Node 22; testpilot needs 24; builders cannot run a single spec locally | measured | Node 24 under the tools folder, or CI only by rule |
| L14 | Coworkers cannot be told anything while they run | code: 409 on a busy session | fresh short sessions make it unnecessary; delivery into a live session later |
| L15 | The handoff file has no protection against being overwritten | happened | append through a script, or drop it for factory jobs |
| L16 | Testpilot's layout tests are unstable under load and 12 files fail on main | measured; issue #195 | fix at the cause |

## 3. Underutilized: already in Rerun, not used for this

| # | What | Evidence | Use |
|---|---|---|---|
| U1 | Webhook triggers: fresh session, own model, payload, parallel | proven live; the team has none | every stage start |
| U2 | Ask-the-user cards and `notify` | proven live in a trigger session | plan approval and BLOCKED notices |
| U3 | The per-coworker run records | code and measured | zero-token waiting, cost per stage |
| U4 | The engine-wide shared database | code | the runner's local index later |
| U5 | The brain and its proposal and approval flow | 10 corrections approved once; nobody is made to read it | packets by label; rulings as precedents |
| U6 | The small and mid models | planning on the large model cost 2.5% of a job; builders cost 80% | builders on the mid tier, checks on the small one, large for plan, review, arbiter |
| U7 | Planning coworkers | "0 planning, direct task delegation only" until 2026-11-11; the Planning department is approved and not formed | Code Mapper and Planner, Scope Shaper as chunker |
| U8 | 38 coworkers, about 12 did the work | team status | retire or merge the rest as mechanisms take their duties |
| U9 | Rob's 10 light runners | they idle while two heavy ones queue | fit backend tests to a light runner |
| U10 | The factory scripts' own checks (`risk`, `repo-check`, `gate`) | used by hand, results not enforced | called by the runner as gates |

## 4. Detrimental: actively costing tokens, time or safety

| # | What | Evidence | Fix |
|---|---|---|---|
| D1 | Long-lived sessions that re-read themselves | measured: 96.5% of input is re-read context; two runs were a third of a job | one stage, one fresh session |
| D2 | A session waiting on CI or on another coworker | measured: a 19.8M-token run was mostly four CI rounds | the runner waits |
| D3 | One Boss conversation for the whole day | measured: 344,000 to 440,000 input tokens per message | a new job, a new session |
| D4 | The starting context of every coworker | measured: 26,487 tokens before any work, doubled by the first tool call | take it apart (rerun#40) |
| D5 | Readers cloning whole repos | measured: 43 clones, 8.5 GB, one per review or plan | one shared checkout per repo |
| D6 | Dependency folders and code indexes per worktree | measured: up to 0.9 GB and 179 MB each | source-only worktrees; one index per repo |
| D7 | Building before planning | measured: about 49M tokens for a rejected branch | plan gate (in place) and approval |
| D8 | Rules written in prompts | planning rules stood in Boss's instructions and never ran | each becomes a check in code, then leaves the prompt |
| D9 | Pull requests aimed at side branches, so no CI runs | three times in one day | the runner opens the job's pull request |
| D10 | Many small pull requests | six CI pull requests in one evening, each a full run | one pull request per job |
| D11 | Two teams deploying one stack without telling each other; a deploy that ran a migration unnoticed | 2026-11-11 evening | one delivery loop per product, migrations named before deploy |
| D12 | Tests that depend on the clock or on load | found: a list 74 px shorter after midnight UTC; a half-loaded baseline | deterministic test data; waits on the thing, not on time |
| D13 | Folders and branches that vanish or pile up | a worktree disappeared and nobody knows how; six leftover branches from one job | the removal sequence as the only deleter; branch rules |
| D14 | Scratch commands and messages built inline in a shell | backticks in a message started a program on Rob's PC | messages built in files |
| D15 | Secrets handling by convention | trigger addresses are secrets and have no agreed place on the server | one root-only env file, written once by Rob |

## 5. Ready to cut

| # | What | Why |
|---|---|---|
| C1 | Most of Boss's 27,000-character instructions | procedure the runner will own: playbook, waves, loops between coworkers, "on every event" |
| C2 | "Waiting on CI and fixing a red run" in every builder's instructions | the runner does it |
| C3 | Builders creating, sharing and removing worktrees | the runner does it |
| C4 | The handoff files for factory jobs | the ledger is the record |
| C5 | Coworkers with no remaining duty | after each mechanism lands; 26 of 38 did not run on the busiest day |
| C6 | The `job/<issue>` branch as a pull request target for single-chunk fixes | caused the missing-CI cases |
| C7 | The known-failing list for layout tests | once #195 is fixed; a list of accepted failures is a debt, not a feature |
| C8 | Coding-supervisor on the server | done: nothing used it |
| C9 | Mac builds | done |
| C10 | My own watchers on this PC | when the runner's tick exists |
| C11 | The hand-made folders `/data/work/e2e` and `/data/work/review`, the 43 clones | after the shared checkout exists and their use is known |

## 6. Not known yet (a gap in knowledge is a gap)

- Which key the server's coworkers hold, and why the cancel route refused it.
- Whether the side bot can be driven from the server, and how a request there becomes a job.
- The weekly allowance reading: where the percentage comes from (rerun#40).
- What uses `/data/work/e2e/mainsrc` and `/data/work/review/linus-191`.
- How `terminal-commander/296-1` disappeared.
- Whether the shared account may merge and push everywhere the runner needs.
- What else on the server, outside the factory, uses disk.
- Whether a blind builder (no local test run) needs more attempts than one with a local check.
