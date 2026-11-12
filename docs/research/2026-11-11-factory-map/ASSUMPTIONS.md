# Assumption register

Rob, 2026-11-12: "Assumptions are our enemy and we must attack each and every one of them. Research beforehand,
implement small chunks and test each, validate, move to the next until there are no assumptions left." and "Things that
require 100% proof, only 100% proof will do, nothing else, no assumption."

Rules:
- Three statuses only: **unproven**, **proven**, **refuted**.
- "Proven" needs evidence someone else can re-check: a file and line read on a named commit, or a probe that was run,
  with what it printed. A probe on one coworker proves it for that coworker's kind of session, not for all.
- A work order may rely only on proven rows. An unproven row it needs becomes that work order's first chunk.
- A refuted row sends the design that used it back to planning. It is not patched around in a build.
- A specification holds only proven facts and done-tests. Any other sentence is an open question and gets a row here.
- Rows are never deleted. A changed answer gets a new dated line in the row.

Code facts below were read on `dev` at `3011933` unless a row says otherwise. Probes ran on the server on 2026-11-12
with a scratch trigger on an idle coworker (switched off afterwards).

## A. How sessions start, run and end

| ID | Statement | Status | Evidence | Needed by |
|---|---|---|---|---|
| A1 | Firing a webhook trigger always creates a new session and returns the run id and session id | proven | code `apps/engine/src/runtime/trigger-runner.ts:19`, `http/routes/triggers.ts:76`; probe: 4 fires gave 4 sessions | starting a stage |
| A2 | A trigger can carry its own model and connection; its payload is cut at 65,536 bytes and appended to the instruction | proven (code) | `triggers/loader.ts:80-82`, `triggers/message.ts:6,22-24,46`; no size check on the raw request | model per stage, packets |
| A3 | Nothing caps the number of live runs of one coworker started by triggers | proven | code `trigger-runner.ts:12-39`; probe: two sessions ran side by side for 20 s and 50 s | clones |
| A4 | Each coworker has `data/system.db` with a `runs` table holding status, finish time, token counts, trigger source and slug | proven | code `db/systemDb.ts:58-68,172-183`, `db/schema.ts:34-54`; read on the server (row counts) | waiting at no token cost |
| A5 | A message to a session with a run in flight is refused with 409 `run_in_flight`; a message with no session id creates a session | proven (code) | `http/routes/chat.ts:17-22,42-47` | fresh session per stage |
| A6 | Token counts of a Claude or Codex run are empty until the turn ends | proven | code `runtime/loop.ts:304`; probe: no tokens shown while two runs were live | rerun#43 |
| A7 | When any run of a coworker ends, the engine sets that coworker's status column to idle | proven (code) | `runtime/loop.ts:348`, `db/repos/agents.ts:23-25` | never read the status column |
| A8 | The team status the app and tools show stays correct with two live sessions of one coworker | proven for one case | probe: "working, 1 running" until the second session ended | scheduling by live runs |
| A9 | On engine start, runs still marked running are set to error and nothing is resumed; triggers survive | proven (code), not tried live | `cli/commands/run.ts:28`, `runtime/reconcile.ts:17-28`, `db/repos/runs.ts:134-143` | restart safety |
| A10 | A coworker's starting context is about 26,500 input tokens, and every step re-reads the context | proven for one coworker | probe: 26,486 for a one-line answer, 53,162 with one tool call (Plugin Scout, small model) | rerun#40 |
| A11 | Delegated copies (`delegate_tasks`) get their own folder, four at a time, same model, but lose the tools to call others, ask the user, notify, use triggers and schedules | proven (code) | second reader, `tools/builtin/delegate.ts` | clones are sessions, not delegates |
| A12 | A called coworker's answer never returns to the caller unless the caller waits | proven (code) | `tools/builtin/call-agent.ts:152` | no waiting sessions |

## B. Stopping, access and the server

| ID | Statement | Status | Evidence | Needed by |
|---|---|---|---|---|
| B1 | The run cancel route is protected only by the engine key as a bearer token | proven (code) | `http/server.ts:41,73`, `http/auth.ts:4-11`, `http/routes/runs.ts:28-32` | stop control |
| B2 | A coworker on the server can cancel another coworker's run | **refuted for the key tried** | Box Janitor's key answered 401 as bearer and as `X-API-Key`; which key is valid is unknown | stop control |
| B3 | Coworkers run inside the engine's container as user `rerun`, with no Docker, no sudo, no cron and no user timers | proven | Box Janitor's read-only check, 2026-11-12 | where a runner can live |
| B4 | The engine answers on port 3000 inside the container; `GET /health` is 200 without a key | proven | same check | probes from the server |
| B5 | An engine change reaches the server by: merge into `dev`, image build of 11 to 13 minutes, `deploy/vps/update.sh` | proven (code and run history) | `.github/workflows/images.yml:10-13,47-50`, `docker-compose.yml:17,49`, last three image runs | development loop |
| B6 | A second engine instance can run on the same server with its own data folder and port, without disturbing the first | unproven | not tried | development engine |
| B7 | The shared GitHub account may merge pull requests, push branches and edit labels in every repo the factory works in | unproven | never tried from the server | merge stage |
| B8 | The server can dispatch a GitHub Actions workflow and read its result | unproven | `gh` is not installed for Box Janitor's shell and his token was rejected; builders push through the factory scripts | chunk test |

## C. Reaching the user

| ID | Statement | Status | Evidence | Needed by |
|---|---|---|---|---|
| C1 | A session started by a trigger can show an ask-the-user card, and an answer sent into that session continues it | proven for an ordinary coworker | probe: card shown, turn ended, answer "Blue" sent into the session, reply `ANSWER Blue` | plan approval |
| C2 | While such a session waits, Rerun shows the coworker as waiting for a person | **refuted** | probe: status idle, nothing listed as waiting | the runner must remember the session |
| C3 | The user sees such a card where he works (the side bot) | unproven | not tried; he uses the side bot, the probe used another coworker | plan approval |
| C4 | The side bot can be started from code | unproven | code: only `POST /agents/foreman/chat` with the engine key, no trigger (`http/foreman-guard.ts`); the account tools answer "Coworker not found" | intake |
| C5 | `notify` works in a trigger-started run and marks the conversation as pending for the user | proven (code) | second reader: sets the session to `awaiting_ack` | BLOCKED notices |

## D. Shared state

| ID | Statement | Status | Evidence | Needed by |
|---|---|---|---|---|
| D1 | The shared database is separate per space | unproven | code shows one `shared.db` per engine data folder and no space key; whether spaces are separated another way was not settled | a local index for the runner |
| D2 | A handoff file in the shared folder can be overwritten by any session | proven | it happened on 2026-11-11 (`projects/terminal-commander/HANDOFF.md`) | ledger as the only record |

## E. Factory scripts and CI

| ID | Statement | Status | Evidence | Needed by |
|---|---|---|---|---|
| E1 | The sweep removes a worktree only when its pull request is merged or closed at the same head; a clean worktree whose tip is on the default branch is kept | proven | code `tools/factory/factory.py` (`sweep_verdict`); seen on the server (`189-1`) | cleanup |
| E2 | The plan check in `wt new` passes on any line that begins with the marker words | proven | rerun#52's first line passed it by accident | plan gate |
| E3 | A pushed chunk branch in this repo gets a "Factory tools tests" run | **refuted** | `.github/workflows/factory-tools.yml:3-8` runs on pull requests and on `dev` only | chunk test for factory chunks |
| E4 | Only testpilot has a workflow that runs one named test file | proven | `one.yml` exists there (three trials, 3 to 5 minutes); not in rerun, terminal-commander or symforge | chunk test in other repos |
| E5 | `factory.api(paginate=True)` returns every page | **refuted** | it keeps the first page only (`factory.py:62-64`); checked with a two-page string | reading issue comments |
| E6 | `job-cost` finds every run of a job | **refuted** | it matched 30 of 66 runs of testpilot#189 (it looks for the short repo name) | cost per job |
| E7 | The engine writes timestamps with milliseconds and GitHub without, so comparing them as text is wrong | proven | found while building `limits.py`; covered by a test | every time comparison |

## F. Cost and behaviour (measured, not assumed)

| ID | Statement | Status | Evidence |
|---|---|---|---|
| F1 | 96.5% of a job's input tokens are re-read context | proven for testpilot#189 | run records: 110.1M of 114.0M |
| F2 | Planning costs a few percent of a job; building most of it | proven for testpilot#189 | planning under 3M of about 115-120M; two builders 95M |
| F3 | A fresh Boss session costs about a tenth of his long one per message | unproven | the long session read 344,112 and 439,910; the fresh one has not reported yet |
| F4 | A builder with no local test run needs more attempts than one with a local check | unproven | not measured |

## G. Open questions with no statement yet

- Where the weekly allowance percentage can be read from (rerun#40).
- What uses `/data/work/e2e/mainsrc` and `/data/work/review/linus-191` on the server.
- How the worktree `terminal-commander/296-1` disappeared on 2026-11-11.
- What else on the server, outside the factory, uses disk.
- What a Boss run that has been live for over an hour is waiting on, and how to tell from outside.

## H. Engine-inside design and its challenge (2026-11-12)

Rows N1 to N18 come from the Advisor's design (issue #42, comment 6818876939), read on `dev` at `ee15f5a`. Rows X1 to X4 come from the Devils Advocate's challenge (comment 6819228687); every code line in them had one reader. Milestone 1 (issue #56) is built to settle B6, B2, N2, N3, N4, N5, N8 and X3.

| ID | Statement | Status | Evidence |
|---|---|---|---|
| N1 | Every engine data path resolves under `RERUN_DATA_DIR` (default `~/.rerun`; `/data` in the image) | proven (code, one reader) | `config/paths.ts:5-77`, `config/env.ts:6`, `apps/engine/Dockerfile:33`, `ee15f5a` |
| N2 | With no hub URL or no key, `sendNotification` returns without a request | proven (code, one reader) | `runtime/notify.ts:57-58`, `ee15f5a` |
| N3 | `update.sh` runs `docker compose pull` and `docker compose up -d` with no project flag and no `--remove-orphans`, so it does not touch another compose project. Since 2026-11-12 it ends with `docker image prune -f`, which removes untagged images that no container uses, of any project; tagged images, containers and volumes are not touched | code proven, effect unproven | `deploy/vps/update.sh:21,34,38`; P7 |
| N4 | A non-privileged container with only its own volume and no docker socket cannot write the live engine's data | unproven | P1 |
| N5 | The engine boots and serves with no hub and no model connection | unproven | P5 |
| N6 | The engine builds from source inside the engine image (corepack present; native modules unknown) | partly proven (code: `Dockerfile:5-7`), the build unproven | T2 |
| N7 | A dev rebuild takes under 15 minutes on the server | unproven | T2 |
| N8 | A coworker and a trigger can be created through engine HTTP with no hub | unproven | P5 |
| N9 | Live coworkers reach a container on the live network by service name | unproven | P2 |
| N10 | An in-process abort ends a Claude or Codex CLI run within the 15 s teardown | unproven | M4 |
| N11 | The engine process can call GitHub with the shared account's credentials | unproven | M3 |
| N12 | python3 stays present in the engine container for `factory.py` and `gate.py` | proven today, not guaranteed | probe 2026-11-12: `/usr/bin/python3` → 3.13 in the live container; the Dockerfile does not list it (`Dockerfile:20-21`), so it comes in as a side effect of another install. M3 declares it explicitly |
| N13 | A new built-in side-bot tool works without a change to the hub allow-list | unproven | M5 |
| N14 | Claude and Codex runs write one step per turn, so live ceilings need an adapter change | unproven (INVENTORY: inferred from a comment) | M4 |
| N15 | Copying a delegate's run rows before its folder is deleted keeps its cost | unproven | M7 |
| N16 | Memory and CPU limits on the dev container stop it from starving the live engine | unproven | P6 |
| N17 | Fixed temp paths (`rerun-desktop`) and screen ports from 5900 would collide for two engines in one container | proven (code, one reader) | `desktop/session.ts:15-16,131`, `tools/builtin/computer.ts:172`, `ee15f5a` |
| N18 | Line numbers from `3011933` still hold on `ee15f5a` | unproven | a second reader before M2 is planned |
| X1 | `settle` is the single end of every run, so one event from it is enough to wait on | **refuted (one reader)** | the cancel route with no live loop (`http/routes/runs.ts:33-35`, `db/repos/runs.ts:139-142`) and boot reconcile (`runtime/reconcile.ts:25`) close run rows without it; the runs table is the truth, an event only a hint |
| X2 | A process beside the engine cannot stop a run | unproven | the cancel route calls `abortRun` (`runs.ts:28-33`); B2 was refuted for one coworker's key only; probe P6 of #56 tries the engine key |
| X3 | A fault in runner code inside the engine cannot end the engine process | unproven, likely false | no process-wide handler for unhandled rejections in the engine source; probe P5 of #56 |
| X4 | A stage that is fired again after an engine restart does no harm | unproven | a builder that already pushed or opened a pull request is not repeatable; A9 was never tried live |

Open again after the challenge: whether the runner lives inside the engine process or beside it. It is decided after P5 and P6 of #56 are read.

## I. Milestone 1 results (2026-11-12, issue #56)

The status script was run on the server by Rob; its output is on issue #42. Earlier rows keep their text; these lines are their new answers.

| Row | New status | From |
|---|---|---|
| B6 a second engine runs on the same server without disturbing the first | **proven** | P0 to P7; live engine start time and restart count unchanged |
| B2 the cancel route refuses a caller on the server | **proven accepted for the engine key** (was refuted for one coworker's key only) | P6: 404 for a run that does not exist, not 401 |
| X2 a process beside the engine cannot stop a run | **refuted** | P6 |
| X3 a stray rejected promise cannot end the engine process | **refuted for the Node in the engine image** | P5: exit code 1 |
| N4 own volume, not privileged, no socket | proven | P1 |
| N5 the engine boots and serves with no hub and no model | proven | P3, P4 |
| N8 a coworker and a trigger can be created over HTTP with no hub | proven | P4 (the run ends in `error` for the missing model, as expected) |
| N2 no hub configuration reaches the development engine | supported | P1, P2 |


Still open: N3 (the development engine survives the next normal live update) and one deliberate remove and start again.
