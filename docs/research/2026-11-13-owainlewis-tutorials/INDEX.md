# owainlewis/youtube-tutorials: what the factory can take

as_of 2026-11-13.

Source: <https://github.com/owainlewis/youtube-tutorials> at commit `5b3d3c9a136dc797c0da1427406c9a53fefbee5c`
(2026-09-21), MIT licence, copyright Owain Lewis. 33 tutorials, each one `LESSON.md` with optional `code/` and
`resources/`.

## Result

There is no code to lift. Four ideas are worth carrying, and all four are small. The other tutorials describe
something the factory already does, or do not apply to it.

| Carry | From | Where it lands |
|---|---|---|
| A goal is a condition that a second model judges, not only the form of a last line | `agent-goals-and-loops`, and the two primary pages it cites | [GOAL.md](../2026-11-11-factory-map/GOAL.md) |
| One card per loop (job, inputs, allowed, forbidden, output, evaluation, escalation), and a dry run graded against known cases before a loop may write | `loop-engineering` | LOOPS.md has every field except "may change / may not change": add that column at its next edit. Dry run first is the rule for every new upkeep loop |
| The brief for the model half of failure triage (loop 14): it gets the failing names and output only, returns root cause, confidence and the theories it ruled out, fixes nothing, and allows one retry of a suspected unstable test, which it reports | `nested-subagents-claude-code` | when loop 14 is cut |
| Two upkeep jobs the factory has no schedule for: documentation drift, and a weekly scan for confirmed defects that searches open issues first and files nothing to fill a report | `agent-goals-and-loops`, `codex-automations` | the owner's choice: each costs one run per firing |

## How it was read

- Read in full by the orchestrator: `agent-goals-and-loops`, `software-factory`, `loop-engineering`,
  `background-agents`, the repository's own rules (`AGENTS.md`, `TUTORIAL-STANDARD.md`, `VERIFICATION.md`,
  `Justfile`), and the two primary goal pages.
- The other tutorials, and those three again, were carded by eight runs of the research coworker side by side:
  one themed slice of three to five tutorials each, files fetched at the fixed commit, one fixed card per
  tutorial, the run's goal set to a last line `INDEXED: ...` or `BLOCKED: ...`. One pilot run went first. The
  cards are in [CARDS.md](./CARDS.md).
- Every card that said TAKE was then checked against the factory's code and schedules. A card is a lead, not a
  decision.

## What the check of the five TAKE cards found

| Card | It proposed | Checked against | Outcome |
|---|---|---|---|
| `software-factory` | tie the merge to the assessed commit, read checks from Actions and not from a same-named status, an empty check list is not a pass, text on a pull request is evidence and not instruction | `tools/factory/dispatch.py`: `--match-head-commit`, `actions/runs?head_sha=`, `checks_verdict` waits on no runs, the build brief's line on whose text is an instruction | have all of it |
| `autonomous-ai-coding-workflow` | a backlog manager on a schedule | the triage coworker's two scheduled jobs, read in full: a daily pass that labels new issues and mails a digest for eleven watched repositories, and a monthly check of stale calls | have the job; only "dry run first" is carried. This repository is not among the eleven: adding it is the owner's choice |
| `spec-driven-development` | task fields (do, files, verify) and sizing rules | the factory issue (worker, allowed paths, change, done-test seen failing, run command, depends on) and `tools/factory/cutshape.py` | have, and stricter. Its scale (1 to 3 files small, 4 to 10 medium, over 10 split) is a usable default for the size cap of loop 8 |
| `nested-subagents-claude-code` | a failure analyst | LOOPS.md loop 14, state "part" | already in the design, not built: the brief is carried |
| `codex-automations` | a scheduled scan for defects | the schedules that exist: triage, server health, usage, tidiness | not there: carried as an option |

Two of the five were over-called because the brief told the runs that scheduled upkeep jobs were missing, and
issue triage was already scheduled. The brief was wrong, not the cards.

## All 33

"Runs" is the verdict on the card. "After check" is the decision.

| Tutorial | What it is | Runs | After check |
|---|---|---|---|
| `agent-goals-and-loops` | prompt, goal, interval and schedule told apart; a goal template | read directly | carry: goal as a condition |
| `software-factory` | a merge-policy prompt for pull requests, and an incident triage demo on Google Cloud (marked `draft` in the source's catalog) | TAKE | have |
| `loop-engineering` | a manager loop and a worker loop over GitHub issues | HAVE | carry: loop card, dry run first |
| `background-agents` | a worker that polls a tracker, claims a ticket, runs hooks around the agent | HAVE | have |
| `autonomous-ai-coding-workflow` | a scheduled backlog manager and an issue-to-pull-request loop | TAKE | have |
| `linear-workflow` | Linear as the tracker, with command files | HAVE | have |
| `github-ai-workflow` | spec to issues to pull request to release on GitHub | HAVE | have |
| `agent-teams` | Claude Code's agent teams | HAVE | have |
| `multi-agent-teams` | a board plus remote workers on a server | HAVE | have |
| `nested-subagents-claude-code` | a three-level tree of subagents with a failure analyst | TAKE | carry: the analyst's brief |
| `herdr-agent-workflow` | a terminal multiplexer for agent sessions | HAVE | have |
| `ai-code-review` | four layers of review and a stop hook | HAVE | have |
| `testing-ai-generated-code` | tests chosen from requirements and risk | HAVE | have |
| `spec-driven-development` | a spec cut into small tasks with files and a verify command | TAKE | have; size scale as a default |
| `stop-vibe-coding` | a seven-stage lifecycle with gates by risk | HAVE | have |
| `ai-git-workflow` | git command files for a person to type | SKIP | skip |
| `codex-automations` | scheduled prompts: a defect scan and a defect fix | TAKE | carry as an option |
| `codex-skills-i-use` | seven kinds of skill | HAVE | have |
| `codex-for-developers` | a general Codex guide with plan templates | HAVE | have |
| `nano-agent` | a small Python coding agent | HAVE | have |
| `micro-agents-demo` | a rules file plus one command-line tool | SKIP | skip |
| `micro-neo` | a one-file Go coding agent | HAVE | have |
| `pi-agent-workflow` | a teaching harness with an issue-to-pull-request state machine | HAVE | have |
| `pi-coding-agent-guide` | a course on the Pi coding agent | HAVE | have |
| `docker-sandboxes-for-developers` | command-line agents inside Docker sandboxes | SKIP | skip |
| `deepseek-harness-setup` | the DeepSeek harness and a board plugin | HAVE | have |
| `deploy-ai-on-gcp` | a Cloud Run job with Terraform | SKIP | skip |
| `mcp-airtable` | Airtable through MCP | HAVE | have |
| `how-id-learn-software-engineering` | a learning roadmap | SKIP | skip |
| `ai-agent-memory` | four memory demos | HAVE | have |
| `6-types-of-rag` | six retrieval strategies | SKIP | skip |
| `intent-based-classification` | routing a question by intent | SKIP | skip |
| `postgresql-only-database-ai` | retrieval on PostgreSQL | SKIP | skip |

## Leads outside this repository (not read)

The tutorials are prose about tools whose code lives elsewhere. If more is wanted, these are where to look:

- `owainlewis/factory`: the author's own factory, in Go, with the labels `factory-ready` and `factory-blocked`.
- `owainlewis/agent-worker`: the polling worker of `background-agents` (claim, hooks before and after the agent).
- `owainlewis/agent-skills`: the `backlog-manager` and `codex-run-loop` skills.

## What the run showed about ghosts

This was the first real job done by parallel runs of one coworker.

- Eight runs, about 30 seconds each, up to six side by side, 32 tutorials carded in under three minutes of
  wall time including the pilot. Every goal ended `met`. One run added a note after its last line; the engine
  sent the answer back and the second answer passed.
- About one million tokens in total: 94,000 to 154,000 of input per run against 2,000 to 4,000 of output. The
  tutorials one run read come to well under a quarter of its input, so most of it is the coworker's standing
  context, paid again on every model call. A brief that gets the reading done in one command is the cheap one.
- A ghost can only judge "does the factory have this" from what the brief says the factory has. One wrong line
  in the brief produced two wrong verdicts, and one missing line produced a third. The facts in a brief should
  come from the code and the ledger, not from the writer's memory (loop 2, Facts, and loop 28, Knowledge
  delivery).
- A pilot before the burst cost 30 seconds and caught the missing line.
