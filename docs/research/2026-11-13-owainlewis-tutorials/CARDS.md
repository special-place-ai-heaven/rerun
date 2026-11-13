# The cards, as the runs returned them

as_of 2026-11-13. Source: <https://github.com/owainlewis/youtube-tutorials> at commit `5b3d3c9a136dc797c0da1427406c9a53fefbee5c`, MIT licence.

One run of the research coworker per slice. A verdict here is the run's own: TAKE means "the factory lacks this or does it worse", HAVE "the factory already has it", SKIP "does not apply". The decisions made after checking them are in [INDEX.md](./INDEX.md). Line numbers are the runs' own and were checked only for the five TAKE cards.

## Slice A: the factory itself

```text
=== CARD software-factory
What it is: A tutorial with two parts: a read-only-first Codex prompt that decides which open PRs may merge, and a GCP incident-triage agent (Python, Google ADK) that investigates an alert and recommends an action.
Artifacts: Prompt `tutorials/software-factory/resources/prompts.md` (the Assembler PR merge-policy prompt). Runnable Python code in `tutorials/software-factory/code/` (FastAPI app, ADK agent, deploy, cleanup, demo and tests). I did not read the code. It targets Cloud Run, Vertex AI, Pub/Sub and Firestore. I also did not read `walkthrough.md`, the diagrams, or `static/index.html`.
Maps to: 1, 6, 8, and the "scheduled upkeep jobs" gap
Verdict: TAKE
Why: Lift the merge-time re-verification from the prompt. Bind each risk assessment to the head SHA, re-check head, base, checks and reviews immediately before merging, and merge with `gh pr merge --match-head-commit`. The factory's merge step in `dispatch.py` could adopt the same guard, and its CI-provenance check (an Actions run, not a same-named status) and per-SHA audit comment too. The incident-triage code is a GCP product and does not apply.
Evidence: tutorials/software-factory/resources/prompts.md:48-52, tutorials/software-factory/resources/prompts.md:75-92, tutorials/software-factory/resources/prompts.md:102-115, tutorials/software-factory/LESSON.md:13
=== END

=== CARD loop-engineering
What it is: A prose lesson on designing a recurring agent job, with a manager that classifies GitHub issues, a worker that opens PRs from them, and a human who owns every merge.
Artifacts: Prose only. It has an inline dry-run prompt and an assessment template, but no files.
Maps to: 2, 4, 6, 10, and the "scheduled upkeep jobs" gap
Verdict: HAVE
Why: The factory already uses issues as the queue, an intake gate, a worker, review and checks, and it merges on review plus green checks rather than waiting for a human. The only extras are the dry-run-first mode for a triage job and the 7-field loop card (job, inputs, allowed, forbidden, output, evaluation, escalation). Both are small habits for later upkeep jobs, not something to lift now.
Evidence: tutorials/loop-engineering/LESSON.md:42-44, tutorials/loop-engineering/LESSON.md:133-147, tutorials/loop-engineering/LESSON.md:103-127, tutorials/loop-engineering/LESSON.md:183-191, tutorials/loop-engineering/LESSON.md:160-161
=== END

=== CARD background-agents
What it is: A lesson on the pull-based `agent-worker` (Bun, Linear): it polls a task manager, claims a ticket, runs pre-hooks (fetch, worktree), dispatches to an agent harness, then runs post-hooks (test, lint) and reports back.
Artifacts: Prose, plus an inline YAML config and hook examples (LESSON.md:234-294). The code is in a separate repository that I did not read.
Maps to: 1, 2, 5, 7
Verdict: HAVE
Why: The factory already polls GitHub issues, gives each job its own git worktree, runs deterministic checks after the agent, and has clocks, a ledger and reviewers. The factory also goes further, with dependencies and parking labels, retries, review gates and a merge step. The lesson's atomic claim for several workers is not needed because `dispatch.py` is a single delegator.
Evidence: tutorials/background-agents/LESSON.md:116-123, tutorials/background-agents/LESSON.md:234-252, tutorials/background-agents/LESSON.md:289-290, tutorials/background-agents/LESSON.md:375-379
=== END

INDEXED: 3 of 3 tutorials carded
```

## Slice B: autonomous work and the tracker as control

```text
=== CARD autonomous-ai-coding-workflow
What it is: A two-loop workflow. A scheduled backlog manager labels issues and files evidence-backed maintenance tickets, and a run loop turns one low-risk issue into a draft PR.
Artifacts: Prompts, not runnable code. `resources/backlog-manager.md` has a dry-run prompt and an apply prompt. `resources/issue-to-pr-loop.md` has a one-issue prompt and a parallel variant. `resources/cron-wiring.md` has a cadence table and bash pseudocode, `agent run "$PROMPT"`. The skills `backlog-manager` and `codex-run-loop` live in another repo, owainlewis/agent-skills, which I did not read.
Maps to: 2, 4, and the "still weak" list (scheduled upkeep jobs, issue triage).
Verdict: TAKE
Why: Lift the backlog-manager job as a scheduled upkeep coworker. It runs dry-run first, then apply. It applies risk and type labels, flags stale issues whose PRs are already merged, and opens new issues only on cited evidence, with an explicit no-code, no-PR, no-merge boundary. This fills the factory's missing triage and drift jobs, and the risk label is a cheap gate on what enters the `factory` queue. The delegator, worktrees and PR loop are already covered, and its "human merges" rule is the opposite of the factory's merge on accepted review and green checks, so skip that part.
Evidence: autonomous-ai-coding-workflow/resources/backlog-manager.md:23-33 (what the dry run reports, evidence-only issues); backlog-manager.md:46-58 (allowed and forbidden actions in apply mode); LESSON.md:135-138 (12-hour backlog job, daily loop; README is 1-12 and LESSON starts at line 1 of its own file); LESSON.md:58-70 (selection by risk and agent labels, skip `needs:human` and `agent:blocked`); issue-to-pr-loop.md:46-47 (blocked issue gets a comment and a label, matching `factory-blocked`); cron-wiring.md:46 (never merge by default).
=== END

=== CARD linear-workflow
What it is: Using the Linear MCP server as the agent's control plane, with a lean CLAUDE.md for rules and a slash command for the playbook.
Artifacts: `resources/CLAUDE.md` (rules for branch, commit and PR format); `resources/examples/.claude/commands/create-tickets.md` (turns a spec into a parent issue and sub-issues, with an overlap check); `resources/examples/.claude/commands/implement.md` (ticket to PR, with a sub-agent self-review prompt); `resources/examples/settings.json` (Linear MCP config, 11 lines).
Maps to: 2, 6, 10.
Verdict: HAVE
Why: The factory's issues are already the queue. They name their files and dependencies, and `factory-blocked` parks a job. Review is done by independent reviewers at the head commit, which is stronger than the tutorial's self-review sub-agent. The rules-in-file, playbook-in-command split matches the factory's one rules file per repository plus per-coworker instructions and skills. Linear itself does not apply, because the tracker here is GitHub.
Evidence: linear-workflow/resources/examples/.claude/commands/create-tickets.md:14-16 (file overlap becomes `blockedBy`); linear-workflow/LESSON.md:225-231 (rules in CLAUDE.md, playbook in the command, via the "What Goes In A Slash Command" section; README is 1-12); linear-workflow/LESSON.md:313-324 (failure modes: parallel agents on the same files, vague tickets); implement.md:21-40 (sub-agent self-review prompt); CLAUDE.md:35-37 (stop and report on failure).
=== END

=== CARD github-ai-workflow
What it is: A walkthrough of GitHub as the control plane: spec to issues, issue to branch to PR with a fresh-context review, squash merge, then a tag-triggered release, shown on a Go CLI called shiplog.
Artifacts: `resources/prompts.md` (prompts for repo, board, spec, issues, implement, address-review, merge, release and commit message); `resources/github-cli.md` (a `gh` command list); the LESSON.md release workflow in YAML (GitHub Actions, building Go binaries and creating a release with `gh release create`).
Maps to: 1, 2, 6, and the "still weak" item on cutting a feature into chunks.
Verdict: HAVE
Why: The issue-to-PR-to-review-to-merge loop is what the delegator already does. It is stricter in the factory, where the merge is tied to the reviewed commit and the checks are read from that commit's runs. The spec-to-issues step is a bare prompt with no rule for how small a chunk is or in what order, so it adds nothing to the factory's open chunking question. The release workflow and the shiplog demo are outside the factory's scope.
Evidence: github-ai-workflow/LESSON.md:208-230 (spec to issues, titles and acceptance checklist only, no size or order rule); LESSON.md:263-287 (implement one issue with a fresh-context review); LESSON.md:357-360 (plain `gh pr merge --squash --delete-branch`, no commit pinning); LESSON.md:384-462 (release workflow); LESSON.md:497-511 (the fix is smaller work, not a bigger prompt); prompts.md:88-103 (address-review triage prompt).
=== END

INDEXED: 3 of 3 tutorials carded

Line numbers: my fetch printed README.md and LESSON.md of each tutorial as one continuous numbering, and likewise the resources of each tutorial. I converted every cited line to a per-file number. INDEXED: 3 of 3 tutorials carded
```

## Slice C: teams of agents

```text
=== CARD agent-teams
What it is: A lesson on Claude Code's experimental Agent Teams, where teammates message each other and share a task list, with a three-agent demo build (backend, frontend, reviewer).
Artifacts: Prompt `tutorials/agent-teams/resources/ai/prompts/build.md`; spec `tutorials/agent-teams/resources/ai/specs/content-repurposer.md` (a demo app spec, not read: the lesson uses it only as the demo input); settings JSON snippets in `LESSON.md`. No scripts and no code.
Maps to: 3, 6, 7
Verdict: HAVE
Why: The factory already splits builder and reviewer into separate coworkers, and the reviewer reports without editing. File ownership is in the issue's file list, and each job gets its own worktree. Peer-to-peer messaging between agents is an experimental Claude Code feature, and the factory routes everything through the delegator on purpose.
Evidence: agent-teams/resources/ai/prompts/build.md:28 (reviewer reports and does not edit; the lead assigns fixes to the owner); agent-teams/resources/ai/prompts/build.md:32 (clear ownership prevents stepping on each other); agent-teams/LESSON.md:3 (experimental, off by default); agent-teams/LESSON.md:240 (teammates are not isolated in worktrees, so split by files); agent-teams/resources/ai/prompts/build.md:9 (API contract defined upfront; the factory's issue-names-its-files rule is the equivalent)
=== END

=== CARD multi-agent-teams
What it is: Runbooks for a control plane (the Multica kanban) and remote Claude Code and Hermes workers on a VPS, each running a narrow skill and committing its output to a branch for human review.
Artifacts: Seven setup runbooks `tutorials/multi-agent-teams/resources/01-vps-setup/README.md` to `07-team-access/README.md` (shell commands); three skill files `resources/05-skills-and-agents/skills/ai-news-research/SKILL.md`, `linkedin-post/SKILL.md` and `youtube-description/SKILL.md`, plus `ai-news-research/references/sources.md`. I read `LESSON.md`, `README.md`, `04-multica` and `06-git-access` in full. I did not read the other runbooks or the three skill files. Each is one narrow content job (a news digest, a LinkedIn post, a YouTube description) and none is a coding or upkeep job.
Maps to: 1, 2, 3, 10
Verdict: HAVE
Why: This is the factory's own pattern: issues are the queue, the delegator routes them to typed workers, and output lands on a branch or pull request for review. The factory's merge gate (reviewed head commit plus green checks) is stricter than "inspect the branch, then mark done". The VPS, Multica and HTTPS setup is infrastructure the factory does not need.
Evidence: multi-agent-teams/LESSON.md:27 (control plane plus workers); multi-agent-teams/LESSON.md:69 (specialization sits at the worker, and the control plane only routes); multi-agent-teams/LESSON.md:155 (a branch name and file path per job is the output contract); multi-agent-teams/LESSON.md:197 (states todo, in_progress, in_review, done, blocked; "done" only after a human inspects); multi-agent-teams/LESSON.md:278 (agents own different output paths)
=== END

=== CARD nested-subagents-claude-code
What it is: A lesson on a three-level subagent tree (coordinator, workers, leaves) with independent review, exit-code-only check runners and failure triage that runs only when tests fail, ending in an issue-to-draft-PR prompt.
Artifacts: Five paste-ready prompts in `tutorials/nested-subagents-claude-code/LESSON.md` (nested verification at lines 108-119, independent review at 166-181, test triage at 200-210, full pipeline at 242-268, Codex pipeline at 297-391); a role and tool inventory table at lines 13-21 and a depth-test prompt at lines 411-423. No agent files, the lesson says so at line 7.
Maps to: 4, 6, 9 (and the "classes of failure" gap)
Verdict: TAKE
Why: Lift the failure-analyst idea: when a job's checks fail, a read-only coworker with clean context gets only the failing output and returns a root cause, a confidence level and ruled-out theories. Use that as the "class of failure" label that decides whether a retry is worth it. The one-retry-for-a-suspected-flake rule and the hard cap on repair loops with escalation to a human also give the retry policy a concrete default. The rest (independent review on issue plus diff only, exit codes as evidence, a human-gated merge) the factory already has.
Evidence: nested-subagents-claude-code/LESSON.md:187 (analyst gets only failing names and output and reports root cause, confidence, ruled-out theories; no fixing); nested-subagents-claude-code/LESSON.md:208 (one retry maximum for a suspected flake, and say so); nested-subagents-claude-code/LESSON.md:235 (maximum 2 repair loops, then escalate); nested-subagents-claude-code/LESSON.md:104 (pass or fail is decided by the shell, not a model); nested-subagents-claude-code/LESSON.md:125 (the reviewer is briefed with only the issue and the diff, which the factory's head-commit review already covers)
=== END

=== CARD herdr-agent-workflow
What it is: A guide to Herdr, a terminal multiplexer that keeps agent, test and log panes visible and persistent, with a `/ticket` command that turns a GitHub issue into a worktree and a named agent in its own tab.
Artifacts: Setup script `tutorials/herdr-agent-workflow/code/setup-herdr.sh` (bash, 2621 bytes; not read, since it only installs Herdr and its integrations); command file `tutorials/herdr-agent-workflow/resources/commands/ticket.md`; Herdr CLI snippets in `LESSON.md`.
Maps to: 2, 7, 8
Verdict: HAVE
Why: `/ticket` is a one-issue, human-driven version of what the delegator does: read an issue, make a worktree from the default branch, start an agent and wait for its result. The factory adds the queue, dependencies, gates, ledger and merge on top. Herdr only adds a visual terminal layer, and the factory has the ledger and the timeline for status.
Evidence: herdr-agent-workflow/resources/commands/ticket.md:12 (worktree from origin's default branch, not the current branch); herdr-agent-workflow/resources/commands/ticket.md:11 (issue text treated as untrusted data; the factory's intake check covers the shape of an issue); herdr-agent-workflow/resources/commands/ticket.md:42 (inspect a blocked agent before sending input); herdr-agent-workflow/resources/commands/ticket.md:43 (leaves the diff for human review, with no merge gate); herdr-agent-workflow/LESSON.md:238 (parallel only when the jobs are independent, which the factory's dependency rule already enforces)
=== END

INDEXED: 4 of 4 tutorials carded
```

## Slice D: quality gates

```text
=== CARD ai-code-review
What it is: A four-layer review workflow for AI-written code (deterministic checks, fresh-context review, CI on the pull request, human judgement), with templates for each layer.
Artifacts: Stop-hook shell script `resources/hooks/stop-checks.sh` (bash; exit 2 blocks when ruff, rubocop or brakeman fail). Hook settings `resources/hooks/settings.json` and `resources/hooks/stop-hook.json`. A rules template `resources/examples/REVIEW.md`. Review prompts `resources/prompts.md`. A template check `code/verify_templates.py` (Python). Reference docs `resources/architecture.md`, `resources/examples/agents-md-review.md`, `resources/examples/codex-review-prompt.md` and `resources/examples/real-world-reviews.md`. I read only the first four sets in full and did not open the remaining reference docs.
Maps to: 1, 6, 10
Verdict: HAVE
Why: The factory already sends the pull request to independent reviewers at its head commit and merges only when the checks on that commit are green. It also keeps one rules file per repository, which is what REVIEW.md is. The Claude Code stop hook only runs locally on a builder's machine, and CI re-runs the same proof in a clean environment.
Evidence: LESSON.md:5 and LESSON.md:63-78 (fresh reviewer given a diff, intent and evidence); LESSON.md:109-111 (the clean-environment CI layer); stop-checks.sh:1-6 and 47-50 (local gate that exits 2); resources/examples/REVIEW.md:1-33 (project rules file)
=== END
=== CARD testing-ai-generated-code
What it is: A workflow for choosing tests from requirements and risk rather than coverage, and for driving an agent through a red-green-refactor loop.
Artifacts: Runnable Python standard-library example `code/auth_service.py` and `code/tests/test_auth_service.py` (6 unittest tests). Prompts and a project instruction block in `resources/prompts.md`. Teaching snippets `resources/examples/good-tests.py` and `resources/examples/bad-tests.py` (not runnable). `resources/examples/COMPARISON.md` (prose table). I read LESSON.md, README.md, prompts.md and COMPARISON.md; I did not open the code or the example test files.
Maps to: 6, 10
Verdict: HAVE
Why: The factory's CI gate and independent review already decide whether tests prove the change. The useful lines ("confirm the test fails first", "do not delete or weaken tests") are builder instructions that fit in the existing per-coworker instructions and rules file. They need no new mechanism, and nothing in the tutorial detects a weakened test.
Evidence: LESSON.md:87 (the red step); resources/prompts.md:61-75 (the instruction block, with "do not delete or weaken tests" at line 72); LESSON.md:178 and LESSON.md:198-200 (a changed test is a review question for a person)
=== END
=== CARD spec-driven-development
What it is: A spec-first method in which a short spec file is cut into small tasks, each with files and a verify command, and each task runs in a fresh session and is committed on its own.
Artifacts: Command files `resources/commands/spec.md`, `task.md`, `review.md` and `commit.md`. Four example specs in `resources/examples/` (jwt-authentication, hybrid-search, streaming-chat, youtube). I read spec.md, task.md and review.md in full and the lesson's JWT example. I did not open commit.md or the four example files.
Maps to: 2, 9
Verdict: TAKE
Why: Lift the task-sizing rules into the factory's feature-cutting step, which is a named weak spot: split at commit boundaries, group changes that must ship together, split anything past a few files, and require a verify command on every chunk. Also lift the per-task shape (do, files, verify, depends on) as the template for a factory issue, with a size scale (1-3, 4-10 and 10+ files) to decide when a feature needs several specs.
Evidence: resources/commands/spec.md:80-83 (sizing), spec.md:53-64 (a task's fields), spec.md:100-104 (scale); LESSON.md:189-203 (task design rules, split past a few files, no task without a verify step); resources/commands/task.md:17-24 (only the listed files, no drive-by changes)
=== END
=== CARD stop-vibe-coding
What it is: A seven-stage lifecycle workflow (requirements, design, plan, build, review, deploy, monitor) with approval gates scaled to the risk of the change.
Artifacts: Prompts embedded in the lesson (work-breakdown, self-review, deployment gate). Slide deck `resources/slides/presentation.html` (skipped as HTML). Otherwise prose.
Maps to: 2, 6, 9
Verdict: HAVE
Why: Review, independent review, tests and human-approved merge are already covered by the factory's gates, and the breakdown prompt is a weaker version of the spec-driven tutorial's task rules. Its design stage and deploy and monitor stages are short prose with no artifact to lift, and the factory merges rather than deploys.
Evidence: LESSON.md:90-99 (the breakdown prompt, which waits for human approval); LESSON.md:129-141 (self-review is not independent evidence; independent review plus automated checks); LESSON.md:57 and LESSON.md:143-162 (design and deploy stages, prose and prompts only); LESSON.md:180-188 (risk-scaled process table)
=== END

INDEXED: 4 of 4 tutorials carded
```

## Slice E: git and Codex automations

```text
=== CARD ai-git-workflow
What it is: A set of Claude Code slash commands and a git-conventions config (branch names, conventional commits, PR template, safety rules) for interactive git work.
Artifacts: resources/CLAUDE.md (conventions), resources/commands/{branch,cleanup,commit,history,pr,squash,undo}.md (command prompts, all markdown, no scripts or code).
Maps to: 7, 10
Verdict: SKIP
Why: It targets a human typing slash commands. The factory already has worktrees with a sweep, a delegator that merges with `--match-head-commit`, and a per-repository rules file, which cover the branch, PR and merge parts. The only loose idea is the PR What/Why/How-to-test body, which is too small to count as a lift.
Evidence: tutorials/ai-git-workflow/LESSON.md:11-13 (commands copied for a person to type); resources/CLAUDE.md:18-31 (PR template), resources/CLAUDE.md:33-40 (hard rules, squash-and-merge); resources/commands/cleanup.md:3-9 (interactive branch deletion, needs confirmation); resources/commands/squash.md:1-6 (manual squash); LESSON.md:139 ("squash and merge if it's passing" is a natural-language prompt with no head-commit pinning)
=== END

=== CARD codex-automations
What it is: A guide to ChatGPT Scheduled tasks (web and desktop), with two example prompts: a read-only bug scan that files deduplicated GitHub issues, and a fix of one labelled issue that opens a PR and does not merge it.
Artifacts: resources/prompts.md has two paste-ready prompt templates, bug scan (lines 15-42) and bug fix (lines 49-76), plus a checklist of what a durable prompt defines (lines 78-90). No scripts or code.
Maps to: 2, 4, 7, and the missing scheduled upkeep jobs (issue triage, scans for errors)
Verdict: TAKE
Why: The factory lacks scheduled upkeep jobs. Lift the bug-scan prompt as the template for a researcher-type upkeep job: read-only, reports only a bug with a failing path, searches open issues before filing one so there are no duplicates, ends with "no bug found" instead of filing filler, and files into the `factory` queue. The stop-and-report rules (ambiguous, destructive, missing secrets) also fit the `BLOCKED: <reason>` goal.
Evidence: codex-automations/resources/prompts.md:15-42 (scan prompt: scope, dedupe, no filler issue); prompts.md:26-31 (search open issues before creating one); prompts.md:40-42 (clean "no bug found" exit); prompts.md:58-59 (stop conditions); LESSON.md:56-64 (one narrow job per task); LESSON.md:97-101 (review the first runs before raising frequency); LESSON.md:132-134 (the fix task opens a PR and leaves the merge to a human, where the factory merges after review and green checks)
=== END

=== CARD codex-skills-i-use
What it is: A description of seven kinds of Codex skills (design, plan, explain visually, clarify, address PR feedback, improve, architecture review), with example invocations and a rule for when not to make a skill.
Artifacts: prose only (inline example SKILL.md of three lines at LESSON.md:32-41, and mermaid diagrams, which are not copyable assets). The skill sources it links to are in another repository and were not read.
Maps to: 3, 10, and the missing design work before the build
Verdict: HAVE
Why: Per-coworker instructions and skills already exist (part 10), and the design-before-build ordering (clarify, design, architecture review, then plan) is only described, with no file to lift. The idea worth noting, an architecture review before implementation, is a gap in the factory, but this tutorial gives no skill text for it.
Evidence: codex-skills-i-use/LESSON.md:19-28 (skill = a directory with SKILL.md); LESSON.md:59 (one job and one artifact per skill); LESSON.md:91 (design first, plan second); LESSON.md:172-181 (architecture-review checklist, in prose); LESSON.md:213-223 (when not to create a skill); LESSON.md:229-230 (the real skill sources are external links)
=== END

=== CARD codex-for-developers
What it is: A general guide to OpenAI Codex for a developer (install, AGENTS.md, permissions, skills, plugins, worktrees), with templates for plans, a review checklist and a `justfile` of `codex exec` wrappers.
Artifacts: resources/04-skills/plan-skill/SKILL.md (plan skill with a lightweight and a full execution-plan mode); resources/execplan-template.md and resources/02-plans-and-specs/template.md (plan templates); resources/03-review/code_review.md (review checklist); resources/06-automation/justfile (five `just` recipes wrapping `codex exec`); resources/AGENTS.md (example repository rules file); config.toml and permissions files were not read, the lesson covers them.
Maps to: 2, 6, 10, and the missing cutting of a feature into chunks
Verdict: HAVE
Why: The factory already has a per-repository rules file, issue-based queue items with files and dependencies, independent code review and sequencing of dependent work. The one phrase worth passing to the cutting-into-chunks work is the plan skill's rule "if the plan is large because the task is really several tasks, split the work", but it gives no sizing or ordering method.
Evidence: codex-for-developers/LESSON.md:145 (merge A before starting B, which is the factory's dependency rule); LESSON.md:97 (keep commands in one executable source, not copied into AGENTS.md); resources/04-skills/plan-skill/SKILL.md:139 (split if the plan is really several tasks); resources/03-review/code_review.md:5-32 (generic review checklist); LESSON.md:229 ("a summary is not proof"); resources/06-automation/justfile:6-25 (thin `codex exec` wrappers with no gate or goal)
=== END

INDEXED: 4 of 4 tutorials carded
```

## Slice F: small agents and custom harnesses

```text
=== CARD nano-agent
What it is: A small Python terminal coding agent (Anthropic API, seven tools, event listeners, turn limit) built to show the core agent loop.
Artifacts: Runnable Python under tutorials/nano-agent/code/src/nano_agent/ (agent.py, tools/, listeners/, providers/), config nano-agent.example.yml, and pytest tests under code/tests/. The rest is prose in resources/architecture.md and requirements.md. I read only README and LESSON, so I did not open the code files.
Maps to: 4, 10
Verdict: HAVE
Why: The per-run turn limit and the allowed stop forms are already covered by the factory's goal per run (a turn limit and an engine check on the last line). The lesson itself says it leaves out retries, sandboxing, token and cost tracking and saved sessions, which are the gaps the factory still has, so it offers nothing for them.
Evidence: tutorials/nano-agent/LESSON.md:146-174 (turn limit is a safety boundary, default 20); tutorials/nano-agent/LESSON.md:231-243 (omits retries, sandbox, cost tracking); tutorials/nano-agent/LESSON.md:189-191 (approval as a listener, a child agent auto-approves after the parent approves the spawn).
=== END

=== CARD micro-agents-demo
What it is: A pattern of an AGENTS.md instruction file plus a roughly 1,000-line Python command-line tool (YouTube research), with offline tests.
Artifacts: AGENTS.md (resources/AGENTS.md), CLAUDE.md, context guides (resources/context/*.md), spec and design docs (resources/docs/), Python tool code/tools/youtube.py, offline tests code/tests/test_youtube.py and tests/run.sh, and .env.example. I read only README and LESSON, so I did not open these files.
Maps to: 10
Verdict: SKIP
Why: The topic is a YouTube research agent, which has no link to the factory's issue-to-merge flow. The lesson's useful point, testing tools offline with fakes, is a general habit and adds no factory part. The lesson also says the pattern does not suit durable queues, concurrent workers or unattended writes, which is exactly what the factory does.
Evidence: tutorials/micro-agents-demo/LESSON.md:240-257 (pattern unsuitable for durable queues, concurrent workers, unattended writes); tutorials/micro-agents-demo/LESSON.md:175-185 (offline test boundaries); tutorials/micro-agents-demo/LESSON.md:28-37 (AGENTS.md plus tools/ is the whole agent interface).
=== END

=== CARD micro-neo
What it is: A one-file Go coding agent (OpenRouter, three tools, serial loop, in-memory transcript, events) with tests, an architecture guide and live-build prompts.
Artifacts: Runnable Go code/main.go with main_test.go and a demo project in testdata/demo/. Prose and prompts in docs/ARCHITECTURE.md, resources/architecture-guide.md and resources/prompts.md, plus slides in HTML (skipped). I read only README and LESSON, so I did not open the code or prompts.
Maps to: 4, 6
Verdict: HAVE
Why: "Put preferences in the prompt, put guarantees in code" is the factory's own design: the engine checks the run's last line, and CI and review gates run outside the model. The lesson says the same of its own tools, which reject ambiguous edits and return failures as results. It lists no approval gate, no subagents and no compaction.
Evidence: tutorials/micro-neo/LESSON.md:315-328 (guarantees in code, not the prompt); tutorials/micro-neo/LESSON.md:267-298 (every tool call gets a result, even on failure); tutorials/micro-neo/LESSON.md:433-442 (tradeoffs, no approval gate).
=== END

=== CARD pi-agent-workflow
What it is: A roughly 300-line Python teaching harness (nano-harness.py) with a lesson on turning an agent loop into a Pi workflow that takes a GitHub issue through branch, plan, implement, check, evaluate, review and pull request.
Artifacts: Runnable Python code/nano-harness.py with unit tests code/tests/test_nano_harness.py, .env.example, code/README.md, and a long technical reference (resources/docs/harness-engineering-reference.md). The Pi extension it describes lives in another repository (pi-extensions/pbe-harness) and is not here. I read only README and LESSON, not the code or the reference.
Maps to: 1, 4, 6, 8
Verdict: HAVE
Why: The state machine from issue to pull request, separate evaluation, a check that each transition leaves an observable result (a branch, an exit code, a PR URL), and completion decided by the harness all match the factory's delegator, independent review, artifact check and goal per run. Its advice to pass the exact failure evidence into the next loop is a good idea. It is not a failure-class or retry scheme, which the factory lacks, and the lesson lists retry, tracing and token accounting as left out.
Evidence: tutorials/pi-agent-workflow/LESSON.md:214-230 (workflow state machine, each transition observable); tutorials/pi-agent-workflow/LESSON.md:245-259 (keep evaluation separate, feed back exact evidence); tutorials/pi-agent-workflow/LESSON.md:286-289 (completion is a harness decision); tutorials/pi-agent-workflow/LESSON.md:176-189 (leaves out retry, subagents, tracing, token accounting).
=== END

=== CARD pi-coding-agent-guide
What it is: A course on installing and using the Pi coding agent, adding AGENTS.md, skills, extensions and custom models only as needed.
Artifacts: Skill resources/04-skills/code-review/SKILL.md, TypeScript extensions resources/03-extensions/permission-gate.ts and slash-command.ts, config (02-configuration/APPEND_SYSTEM.md, models.json, settings.json), an AGENTS.md example (resources/pi/AGENTS.md), and the checker code/verify.mjs (Node). I read only README and LESSON, so I did not open these files.
Maps to: 10
Verdict: HAVE
Why: Per-repository instruction files, skills and a table of when to use each are already covered by the factory's per-coworker instructions and skills and its one rules file per repository. The cost lesson says Pi's displayed cost is only an estimate and tells you to check provider billing, so it gives no method for cost per merged change.
Evidence: tutorials/pi-coding-agent-guide/LESSON.md:197-209 (customisation table: AGENTS.md, skill, extension); tutorials/pi-coding-agent-guide/LESSON.md:165-175 (project instruction files); tutorials/pi-coding-agent-guide/LESSON.md:298-322 (cost display is an estimate, use the provider's billing).
=== END

I read only README.md and LESSON.md of each tutorial, because the lessons did not point to any prompt, hook or script as the thing to copy. I did not use SymForge, Terminal Commander or other models, since none of them is in my toolset and I ran one fetch pass myself.

INDEXED: 5 of 5 tutorials carded
```

## Slice G: sandboxes, deploys and the rest

```text
=== CARD docker-sandboxes-for-developers
What it is: A guide to running Claude Code and Codex in Docker `sbx` microVMs, covering direct versus clone mode, secret proxying, network policy, port publishing and cleanup.
Artifacts: Shell command sequences in `LESSON.md`. Runnable code in Python: `code/server.py`, `code/test_server.py`. Prompts in `resources/prompts.md`: two task prompts and one diff-review prompt (lines 43-48). No hooks or skill files.
Maps to: 7, 6
Verdict: SKIP
Why: It sandboxes the Claude Code and Codex command-line tools on a Mac, Windows or KVM host. The factory runs Rerun coworkers in git worktrees and already has an independent security review at the PR head commit, so there is no sbx layer to plug into. The notes that a mounted worktree cannot use git (line 379) and that clone mode suits parallel agents (lines 365, 376) are worth knowing only if the factory later moves to CLI agents.
Evidence: LESSON.md:11, LESSON.md:365, LESSON.md:376, LESSON.md:379, LESSON.md:303, resources/prompts.md:43-48
=== END

=== CARD deepseek-harness-setup
What it is: A setup walkthrough for the DeepSeek Harness (`dsh`, version rc.8), including a Linear MCP connection and a prompt to build a "DS Kanban" browser plugin that groups coordinator and worker sessions into batches.
Artifacts: Profile patch in YAML, `resources/cordis.patch.yml`. Build prompt in `resources/prompts.md`. Plugin code in JavaScript, `code/dsh-client-ui-ds-kanban/lib/client.js` (39835 bytes) and `lib/index.js`, plus `package.json`. I did not read the plugin code, because the build prompt already specifies its model. No hooks or skill files.
Maps to: 8, 3
Verdict: HAVE
Why: The batch model has state per session (blocked outranks running), batch state as the worst of its members, and a blocked-first board. The factory already covers this with the per-job ledger rows and the timeline of every job's status (part 8). `factory-blocked` parks a job with its reason (part 2). The prompt is tied to the harness plugin API and cannot be reused.
Evidence: resources/prompts.md:141-159, resources/prompts.md:184-186, resources/prompts.md:80-84, LESSON.md:144-149
=== END

=== CARD deploy-ai-on-gcp
What it is: A guide to deploying a scheduled Gmail classifier as a Cloud Run Job on Google Cloud with Terraform. The flow is validate locally, review, plan, human approval, then apply.
Artifacts: Python Cloud Run job in `code/email-classifier/main.py`, with `tests/test_main.py`, `Dockerfile` and `requirements.txt`. Terraform in HCL in `code/terraform/main.tf`, `variables.tf`, `outputs.tf`, `dashboard.json.tftpl`, plus `validate.sh`. Two prompt assets in `code/proposal-generator/backend/app/prompts/`. Design documents in `resources/`: `AGENTS.md`, `architecture.md`, `checklist.md`, `spec.md`. I read only `README.md` and `LESSON.md`; the lesson points to the Terraform and sample as GCP-specific material.
Maps to: 6, 10
Verdict: SKIP
Why: The content is GCP infrastructure for a specific sample, and the factory deploys nothing to Google Cloud. The one general idea is a read-only, no-apply first agent pass followed by human approval (lines 50-60, 167-182). The factory's review gates and merge-on-green already cover that, and the dry-run-first, paused-scheduler default (line 157) is not something the factory is missing.
Evidence: LESSON.md:17, LESSON.md:50-60, LESSON.md:157, LESSON.md:167-182
=== END

=== CARD mcp-airtable
What it is: A guide to connecting Claude Code or Codex to Airtable's hosted MCP server with OAuth, plus a read-before-write workflow and one example skill.
Artifacts: Skill file `resources/claude/skills/research/SKILL.md`. Config commands in `LESSON.md`: `claude mcp add`, `codex mcp add`, and plugin install lines.
Maps to: 6, 10
Verdict: HAVE
Why: The skill's pattern is preview the write, wait for approval, write once, then read the result back from the source and return the stored values. The factory already does this: it merges tied to the reviewed head commit, and a check confirms the artifacts a coworker claims really exist. Treating web content as untrusted data (SKILL.md:23) is already standard practice here.
Evidence: SKILL.md:27-30, SKILL.md:23, LESSON.md:154, LESSON.md:187
=== END

=== CARD how-id-learn-software-engineering
What it is: A learning roadmap for software engineering with eight areas, guides for four of them and three worked system-design questions.
Artifacts: The only config-like file is an example project rules file, `resources/ai-tools/CLAUDE.md`. The rest is prose in `README.md` files and `resources/system-design/questions/*.md`, plus the HTML mind map I skipped. No prompts, hooks or scripts. I read the lesson and the example CLAUDE.md only, because the other guides are learner exercises.
Maps to: 10
Verdict: SKIP
Why: It is educational material for a human learner and does not touch the delegator, queue, gates or clocks. The example CLAUDE.md (project context, conventions, commands, rules) is the same thing as the factory's one rules file per repository.
Evidence: LESSON.md:3, LESSON.md:49-58, resources/ai-tools/CLAUDE.md:1-40
=== END

INDEXED: 5 of 5 tutorials carded
```

## Slice H: memory and retrieval

```text
=== CARD ai-agent-memory
What it is: A lesson on agent memory as saved context loaded back into the prompt, with four Python demos: no memory, static AGENTS.md/MEMORY.md files, SQLite session search, and Mem0.
Artifacts: Runnable Python demos in code/01_no_memory.py, 02_static_memory.py, 03_session_search.py and 04_mem0_memory.py. Also code/memory_utils.py, code/tests/test_memory_utils.py, code/reset_demo.py, memory fixtures code/memory/AGENTS.md and MEMORY.md, config code/pyproject.toml, and resources/prompts.md. I read only the prose, per the brief.
Maps to: 10
Verdict: HAVE
Why: The factory already has the static-file layer (per-coworker instructions, skills and one rules file per repository) and a shared memory store. Both match the lesson's recommended "start boring" order, and the Mem0 and SQLite session-search demos add nothing the factory needs.
Evidence: LESSON.md:203-205 and 254 (AGENTS.md as startup memory); LESSON.md:554-567 (decision order, static files first); LESSON.md:473 (use files when memory is stable and small). Factory part 10 is in the brief.
=== END

=== CARD 6-types-of-rag
What it is: A lesson on six retrieval strategies (full documents, full-text, vector, hybrid, SQL, agentic) against a small shop dataset using PostgreSQL, pgvector and OpenAI.
Artifacts: Runnable Python in code/src/01_document_loading.py through 06_agentic_rag.py, with config.py and seed.py. Also code/sql/schema.sql, code/docker-compose.yml, code/pyproject.toml, code/tests/test_strategies.py, code/data/faq.md and refund-policy.md, resources/architecture.md, resources/walkthrough.md and resources/slides/slides.html. I read only the prose, per the brief.
Maps to: 10
Verdict: SKIP
Why: It teaches retrieval over a product catalogue and policy documents, and the factory has no retrieval corpus to serve. The factory's shared memory and per-repository rules file are small and stable, so the lesson's own "load complete files" advice already covers them.
Evidence: LESSON.md:34-40 (shop dataset, Postgres, pgvector, OpenAI); LESSON.md:73-79 (load whole files when the corpus is small and stable); LESSON.md:55 (strategies are choices, not maturity levels).
=== END

=== CARD intent-based-classification
What it is: A lesson on classifying a query into one of five intents with a typed model output, then routing it with ordinary code to a retrieval strategy.
Artifacts: Runnable Python in code/intents.py, intent_classifier.py, routing.py, retrieval.py, router.py and example.py. Offline tests in code/test_offline.py, config in code/pyproject.toml and .python-version, and resources/evaluation-checklist.md. I read only the prose, per the brief.
Maps to: 3, 4
Verdict: SKIP
Why: It routes user questions to retrieval backends, which the factory does not do. The factory's dispatcher already routes issues to worker types by label and dependency. The one reusable idea is a labelled test set to score a classifier, and no factory classifier is described.
Evidence: LESSON.md:8-14 and 50-56 (user-query intents mapped to search routes); LESSON.md:112-138 (routing is a match statement over retrieval functions); LESSON.md:219-239 (labelled test cases to measure accuracy).
=== END

=== CARD postgresql-only-database-ai
What it is: A lesson on building a small RAG app on PostgreSQL with pgvector, full-text search and a hybrid search function using Reciprocal Rank Fusion, served by FastAPI.
Artifacts: SQL in code/sql/01_setup.sql through 05_seed_data.sql. Python in code/src/main.py, code/src/seed.py and code/verify_offline.py. Shell in code/start.sh and code/verify_database.sh. Config in code/docker-compose.yml, .env.example and pyproject.toml, plus a frontend in code/src/static/index.html. resources/prompts.md holds a retrieval-evaluation prompt. I read only the prose and resources/prompts.md, per the brief.
Maps to: 8, 10
Verdict: SKIP
Why: It is a document-retrieval app on Postgres, and the factory's ledger is SQLite, so it has no need for vector or hybrid search. The evaluation prompt compares retrieved against expected sources for RAG and does not apply to factory jobs.
Evidence: LESSON.md:3-5 (Postgres, pgvector, FastAPI, OpenAI RAG app); LESSON.md:228-237 (hybrid search function using RRF); resources/prompts.md:5-13 (prompt judges retrieval against expected source IDs). The SQLite ledger is in the brief, part 8.
=== END

INDEXED: 4 of 4 tutorials carded
```
