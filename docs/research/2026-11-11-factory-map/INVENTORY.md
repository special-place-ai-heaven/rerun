<!-- Read-only code inventory of dev at 3011933, made 2026-11-12 by a reader agent for Rob's local Claude. Paths: engine/ = apps/engine/src/, ui/ = apps/ui/, contracts/ = packages/contracts/src/. Facts with locations, no recommendations. The rows used by ASSUMPTIONS.md were checked by a second reader; the others were not. -->

# Rerun: existing mechanisms for AI coworker runs (inventory, branch `dev`)

## 1. Starting a run

| Mechanism | What it does | Where | Limits or gaps seen in code |
|---|---|---|---|
| Engine chat route `POST /agents/:id/chat` | Starts a run on an existing session or a new one, and streams it back. | engine/http/routes/chat.ts:25-67 | Creates a new session when no `sessionId` is sent (chat.ts:17-23). One live run per session: a second one gets 409 `run_in_flight` (chat.ts:42-48; run-control.ts:33-39). Records `trigger_source='chat'` (chat.ts:55 → loop.ts:421). Returns a resumable SSE stream plus `x-session-id`/`x-run-id` headers (chat.ts:53-66). Checks `enabled` (chat.ts:28). Install claim returns 409 `install_in_flight` (chat.ts:32-33). No per-coworker or per-engine cap. No budget-latch check on this path. |
| Hub web chat → engine | The web app forwards a typed message to the engine. | ui/app/api/chat/route.ts:117 | A queued message retries on 409 with delays from 250 ms to 4 s, 10 tries (ui/lib/chat/start-chat.ts:9-19). Otherwise 409 `run_in_flight` is returned (route.ts:141-146). Other hub pre-checks not determined (route body not read in full). |
| Foreman chat | The hub sends the foreman a message plus a brief and a signed hub token. | ui/app/api/chat/foreman/engine/route.ts:73; engine/http/routes/chat.ts:30 | Same engine route and session claim as any chat. The brief exists only for that run (engine/agents/types.ts:29-31). |
| Kickoff on coworker creation | The hub sends a new coworker its first message. | ui/app/api/_services/kickoff.service.ts:32-33 | Source `dashboard`. Goes through the normal chat route. |
| Setup hand-off | The hub starts the guided install in a coworker. | ui/lib/foreman/setup-handoff.ts:72-76 | Source `api`, with `install` flag. |
| Account MCP `send_message` | An external MCP client or the foreman messages a coworker and polls for the result. | ui/app/api/_services/mcp-account.service.ts:789-814 | Source `api`. Waits 120 s by default, 600 s max (mcp-account.service.ts:198-199), polling `get_run` (:245-253). Returns run projection, output, or a "still working" note. |
| `call_agent` tool | One coworker starts a run in another coworker. | engine/tools/builtin/call-agent.ts:58-170 | **New session every call** (`source='agent'`, origin recorded, :92-97). Runs with `trigger_source='chat'` and no author (:126). `MAX_PARALLEL_CALLS=4` (:34), but the gate is built once per run (:56) and is released immediately when `wait:false` (:147-148). No depth limit: the callee keeps `callAgent`, only self is excluded (:18). Callee has `selfImprovement` forced off (:88-90). Checks the target's `enabled` (:87). |
| `delegate_tasks` tool | Spawns temporary sub-coworkers for subtasks and returns their answers. | engine/tools/builtin/delegate.ts:33-134 | New temp agent and new session per task (`source='delegate'`, :88, :91). `runAgent` is called without a trigger, so it defaults to `'chat'` (:93; loop.ts:210). Returns concatenated `## Task N` text (:132). `MAX_CONCURRENCY=4` per call (:27, :127). No cap on the number of tasks (`.min(1)` only, :37-46). Depth 1 (`delegate=false`, :62). |
| Scheduler tick | Every 30 s, fires due schedules of every enabled coworker. | engine/runtime/scheduler.ts:21, 93-134 | New session per fire (`source='schedule'`, :46). `trigger_source='schedule'` plus slug (:57). In-flight dedupe per agent+slug (:23-28, :65-69). Returns `{runId, sessionId}`. Skips when: coworker disabled (:31, :110); a live run exists **and** the coworker has a screen (:35); budget latch, Rerun provider only (:40); plan-limit latch (:41). Stamps `markFired` before launch, so at-most-once (:42-45). One coworker's schedules fire one after another (:119-126). |
| Cron due logic | Decides whether a schedule is due. | engine/schedules/cron.ts:43-53 | Baseline is `lastRunAt`, so after downtime a missed recurring schedule fires once, not once per missed slot. A one-shot `runAt` fires once (:45-47). No minimum interval (schedule_create only validates syntax: tools/builtin/schedule.ts:62-66). |
| Manual schedule run | Fires a schedule now from the HTTP route. | engine/http/routes/schedules.ts:77-90 | `manual:true` bypasses the busy check and both latches (scheduler.ts:35, :40, :41). `markFired:false`. Refused while setup is pending and the schedule is disabled (:85). Account MCP `run_schedule_now` calls it (mcp-account.service.ts:689-692). |
| Public webhook trigger | An external HTTP call to the trigger URL starts a run. | ui/app/api/t/[agentId]/[slug]/[token]/route.ts:27-40 → engine/http/routes/triggers.ts:64-77 → engine/runtime/trigger-runner.ts:14-40 | UI drops passive visits (route.ts:27) and caps the body at 1 MiB (ui/lib/triggers/webhook.ts:3). Engine compares the token timing-safe and answers 404 on any reject, 405 on a wrong method (triggers.ts:11-15, :71-72). New session every fire, no dedupe (trigger-runner.ts:12-13, :19). Checks the budget latch only, **no plan-limit latch** (:18). `trigger_source='trigger'` (:31). Returns 202 `{runId, sessionId, triggerSlug}`. Payload is truncated to 64 KiB (engine/triggers/message.ts:5). No rate limit found. |
| Account MCP `test_trigger` | Fires a trigger with a test payload. | ui/app/api/_services/mcp-account.service.ts:741-770 | Checks method and enabled first. Same engine path as the public webhook. |
| Headless run wrapper | Runs that no HTTP client streams (schedule, trigger, `call_agent`) still publish their stream. | engine/runtime/headless-run.ts:12-40 | Inserts the run row before running. Delegates do **not** use it (delegate.ts:93 calls `runAgent` directly), so no stream is registered for them. |
| Engine boot | Startup rewrites the foreman, reconciles runs, starts the scheduler. | engine/cli/commands/run.ts:27-28, 42 | No CLI subcommand starts a run (engine/cli/bin.ts:43-82). |
| Model calls outside the run system | Curator, compaction summary and skill drafting call models without a run row. | engine/runtime/curator.ts:37-63; engine/runtime/compaction/compact.ts:71-90; engine/skills/apply-proposal.ts:70-92 | Not in telemetry: `insertRunStep`/`insertToolCall` are only called from loop.ts:170 and :193. |

## 2. The run loop

| Mechanism | What it does | Where | Limits or gaps seen in code |
|---|---|---|---|
| `runAgent` / `runTurn` | Single entry point for every run. | engine/runtime/loop.ts:210-221 | The run row and abort controller exist before any preparation step (:222-226). |
| `settle` | The one terminal path: writes the row, frees the session, tells the hub. | loop.ts:279-388 | Guarded against a second call (:280-281). |
| Stop condition | The turn ends only when a HITL card ends it or the model stops calling tools. | loop.ts:489; tools/builtin/hitl.ts:88-91 | **No step-count cap** (grep `stepCountIs\|maxSteps\|maxTurns` in engine: only a provider error mapping at provider-errors.ts:61). |
| Tool-choice rule | Forces `toolChoice:'none'` for one step when a HITL card was sent without a message. | loop.ts:493-500; hitl.ts:81-83 | Non-CLI providers only. A `ToolChoiceViolationError` is swallowed (loop.ts:516-518). |
| Failed-finish handling | A provider "finish" that is really a failure becomes an error. | loop.ts:540-549; runtime/provider-errors.ts:66-76 | `length` (max-tokens truncation) counts as success (provider-errors.ts:72-73). |
| Drain fallback | A stream that ends without any callback is settled as an error. | loop.ts:557-573 | Error code `provider_stream_incomplete`. |
| Teardown timeout | Provider teardown is capped. | loop.ts:67, 256-266 | 15 s. |
| Stream retry | Replays a step whose stream was cut before it produced output. | agents/openrouter-stream-retry.ts:11, 21-26, 46; wired at agents/providers.ts:509, 515 and agents/opencode.ts:167 | 2 retries (2 s, 8 s). Only the OpenRouter-based, custom and OpenCode providers. No run-level retry. `maxRetries` not set in `streamText` (loop.ts:481-552). |
| Tool-call repair | Fixes nulls in tool input and CLI-style tool names. | runtime/tool-repair.ts:42-50 | No model round-trip. |
| Compaction | Summarises older history when it is long. | loop.ts:447; runtime/compaction/compact.ts:105-148; config.ts:1-9 | Runs **only at run start**, never mid-turn. Trigger: 75% of the context window, capped at 150k tokens for API providers (compact.ts:100-103). Keeps a 20k-token tail. Summary max 12k tokens. Tool outputs over 2,000 chars are pruned (prune.ts). 15-min timeout (compact.ts:30). On failure, continues uncompacted (:143-147). Skipped when the window is unknown (:118). Claude CLI's own auto-compact is off (providers.ts:65-67). |
| Coworker status flag | Engine sets `busy` at start and `idle` at settle. | loop.ts:434, 348; db/repos/agents.ts:23-25 | Only two values exist in the engine. **Set to idle when ANY run of the coworker ends**, even if another run is still live. |
| HITL pause | A run that ends on a card stays "awaiting" by sending no terminal event. | loop.ts:298, 359-361 | Engine run row is `done` (:304) and the agent is `idle` (:348). The waiting state exists only on the hub. |
| Cancel route | Stops a run and closes its row. | engine/http/routes/runs.ts:28-53; runtime/run-control.ts:65-75 | If no live loop exists but the row is `running`, it sets `cancelled` and emits a cancelled terminal event (:34-50). |
| Partial results on cancel | Saves what sub-coworkers already returned when the parent is stopped. | loop.ts:316; runtime/partial-results.ts | Only for delegate results pushed to `partialResults` (delegate.ts:98). |
| Error side effects | Errors arm latches and record bad credentials. | loop.ts:329-340 | Budget latch, plan-limit latch, rejected credential, refused Codex model. Partial messages are kept (:343). |
| Reconcile on restart | Marks interrupted runs failed and tells the hub. | runtime/reconcile.ts:17-50; db/repos/runs.ts:134-143 | `running` → `error 'interrupted: engine restarted'`. Skill proposals failed, busy agents reset to idle. Hub notified for at most 20 runs from the last 24 h (reconcile.ts:12-13). Includes the foreman (:22). **No resume.** |
| Shutdown | SIGTERM stops the scheduler and MCP servers, then exits. | cli/commands/run.ts:52-58 | Live runs are not aborted; they are reconciled at next boot. |
| Curator after a run | Writes or updates a memory after a successful turn. | loop.ts:383-385; runtime/curator.ts:37-63 | Only when `selfImprovement.enabled` and `autoMemory`. 10-min timeout. |
| Memory recall per turn | Injects recalled memories into the turn. | loop.ts:407, 449-450 | Never rejects; a failure means no memories that turn. |

## 3. Between coworkers

| Mechanism | What it does | Where | Limits or gaps seen in code |
|---|---|---|---|
| `call_agent` dispatch (`wait:false`, default) | Starts the callee and returns a fixed sentence. | call-agent.ts:147-153 | The answer is never returned to the caller. |
| `call_agent` wait (`wait:true`) | Streams the callee run and returns its final text. | call-agent.ts:155-160 | Idle timeout 15 min, no total timeout (sub-run-watch.ts:7). CLI bridge tool timeout is 3,600 s (agents/providers.ts:57). |
| Call targets | Decides which coworkers a run may call. | call-agent.ts:16-19; loop.ts:416, 423 | Excludes self and names ending in `' delegate'`. Narrowed by `callableAgentIds`, which only chat runs carry (loop.ts:416), so schedule and trigger runs can call **every** coworker. The hub computes the list from Box access (ui/app/api/_auth/access.ts:178-186). The foreman is not in the agent index, so it can't be called (agents/foreman.ts:48-49). |
| Target resolution | Finds the callee by id or by name. | call-agent.ts:21-30 | Name match is case-insensitive. Ambiguous names return an error. |
| Hub mirror of a called session | Tells the hub the callee session exists. | call-agent.ts:102-112 | `agent.session.created` with `originAgentId`. |
| Delegate creation | Builds a temporary agent for each subtask. | delegate.ts:59-88; agents/factory.ts:18-36 | Inherits a clone of the config (tools, MCP servers), soul, keys, and the pinned connection/provider/model. Turns off cards, HITL, hub, trigger, schedule, callAgent, notify, selfImprovement, delegate. Forces shared tools on. Own new workspace, `system.db`, skills and memory dirs. Inserted in the agent index (factory.ts:33). |
| Delegate cleanup | Deletes the temp agent after its task. | delegate.ts:100-106 | Removes the whole agent dir including `data/system.db` (paths.ts:79, :87), so the delegate's run, step and tool telemetry is deleted. No boot cleanup found after a crash. |
| `sub-run-watch` | Tracks sub-run progress and stops hung sub-runs. | tools/builtin/sub-run-watch.ts:7-9, 109-133, 157-222 | Idle timeout 15 min (paused while a nested sub-run is open, :171-173). Heartbeat 30 s. Last 8 calls kept, 600-char preview. Stops with the parent or on a per-task stop (runs.ts:55-61). |
| `@name` mentions | Convention only: no code parses or routes `@name`. | prompt rule: agents/systemPrompt.ts:55; tool text: call-agent.ts:60; UI autocomplete inserts plain text: ui/components/chat/MentionAutocomplete.tsx:20, 53; ui/lib/chat/composer-links.ts:4 | Renames rewrite mentions in text (agents/rename-references.ts:24, 94-95). `agent_files` strips a leading `@` (tools/builtin/agent-files.ts:10). |
| Team tools | Read-only view of other coworkers through the hub. | tools/builtin/team.ts:9-37; ui/app/api/_services/team-hub.service.ts:6-36 | `team_status`, `team_list_schedules`, `team_list_triggers`, `team_list_runs`, `team_get_run`. Hub checks `config.tools.team` (:20-24) and strips trigger URLs (:27-30). |
| Notification back to the caller | None exists. | db/repos/sessions.ts:17-18 | `origin_session_id` is stored but never read (grep `originSessionId`). |
| Board call links | The map draws a link from caller to callee while the callee session is working. | ui/lib/board/iso-adapter.ts:62-67 | Hub display only. |

## 4. Shared state

| Mechanism | What it does | Where | Limits or gaps seen in code |
|---|---|---|---|
| Shared SQL DB | One SQLite file every coworker reads and writes. | db/sharedDb.ts:28-43; config/paths.ts:33; tools/builtin/shared-db.ts:27-86 | **Disagreement:** the tool text says "shared database of this space" (shared-db.ts:32), but there is one file per engine (paths.ts:33) and "the engine knows no Box" (contracts/chat.ts:23-25). Table owner is recorded but never enforced (sharedDb.ts:69-92). `shared_db_execute` accepts any DDL/DML (shared-db.ts:51-73). Query returns at most 1,000 rows and 50k chars (:7, :36). "Never drop a table you did not create" is prompt text only. |
| Shared folder | File tools rooted in one shared directory. | tools/builtin/shared.ts:6-8; config/paths.ts:26 | One per engine. |
| `agent_files_*` | Lets the foreman read and edit coworker workspaces. | tools/registry.ts:39; tools/builtin/agent-files.ts:9-24 | Foreman only. Rooted at `workspace/`, so `.env` and DBs are out of reach. |
| Private agent DB | Each coworker's own `agent.db`. | db/agentDb.ts; config/paths.ts:85 | Per coworker. |
| Brain store | Company knowledge pages shared by all coworkers. | config/paths.ts:43; db/brainDb.ts:11-63 | One engine-wide DB: `brain_pages`, `brain_chunks`, `brain_chunks_fts`, `brain_links`, `brain_proposals`, `brain_revisions`. |
| `brain_write` | Saves a page directly. | tools/builtin/brain.ts:83-87, 150-181 | Refused when the run has no author (:181), which covers schedule, trigger, `call_agent`, delegate and `api` runs. Hash compare-and-swap. |
| `brain_propose` | Sends a page change for human review. | tools/builtin/brain.ts:88-128; brain/proposals.ts:32-35, 95-100 | Requires the current page hash (:95-98). Same fingerprint is refused, including dismissed ones. One open proposal per agent per page, replaced in place (:120-124). |
| Brain approval | A person (via the hub) or the foreman accepts or dismisses a proposal. | http/routes/brain.ts:61-69; brain/proposals.ts:133-175; tools/builtin/brain.ts:226-241 | Engine trusts `decidedBy` sent by the hub (routes/brain.ts:8-9). Accepting overwrites even when outdated (`force:true`, proposals.ts:155-161; outdated flag :62). |
| Memories | Per-coworker memories in `system.db` with decay. | db/systemDb.ts:42-56; memory/decay.ts:1-31; memory/store.ts:75; memory/maintenance.ts:6-34 | Half-lives from 72 h (task) to 2,160 h (preference). Dormant below 0.15 strength: hidden from recall unless `includeDormant`. Archived below 0.05 by an hourly sweep. |
| Skills (direct) | A coworker creates, edits or deletes its own skills directly. | tools/builtin/skills.ts:31-220 (e.g. `skill_create` :120-136); tools/registry.ts:50 | **No approval.** Only connector skills are read-only (:131). |
| `skill_propose` + apply | A coworker suggests a skill; a person accepts it and a background job writes it. | tools/builtin/skill-propose.ts:51-98; http/routes/skill-proposals.ts:20-40; skills/apply-proposal.ts:70-92 | Only when `selfImprovement.enabled` (registry.ts:51). The user accepts the idea, not the drafted text; the drafted skill is written without review. Fingerprint dedupe; one open proposal per session, merged (skill-propose.ts:66-74). |
| `system.db` tables (per coworker) | The coworker's runs, steps, tool calls and conversations. | db/systemDb.ts:13-145 (DDL), 172-224 (added columns); db/schema.ts:11-122 | `sessions`(id, agent_id, title, status, source, origin_agent_id, origin_session_id, created_at, updated_at); `messages`(id, session_id, role, content_json, tool_calls_json, created_at, author_id, author_name); `messages_fts`; `memories`(id, agent_id, path, content, embedding, kind, created_at, last_accessed_at, access_count); `memories_fts`; `runs`(id, agent_id, session_id, status, step_count, usage_json, provider, model, trigger_source, trigger_slug, cost_micros, input/output/cached_input/reasoning/total_tokens, started_at, finished_at, error); `run_steps`(id, run_id, agent_id, session_id, step_number, provider, model, finish_reason, the 5 token columns, cache_write_tokens, cost_micros, tool_call_count, text_length, duration_ms, created_at); `tool_calls`(id, run_id, agent_id, session_id, step_number, tool_call_id, tool_name, input_json, result_json, is_error, duration_ms, created_at); `compaction_checkpoints`; `skill_proposals`; `system_meta`; `paid_calls`; `paid_items`; `paid_keys`. **No tasks table.** Engine `sessions.status` is always `'open'` (sessions.ts:15; never updated). |
| Global index DB | The engine-wide list of coworkers and their status flag. | db/client.ts; db/migrate.ts:3-8; db/schema.ts:4-9 | `agents`(id, name, status idle/busy, created_at). Lives in the global DB, not in `system.db`. |

## 5. Reaching the user

| Mechanism | What it does | Where | Limits or gaps seen in code |
|---|---|---|---|
| `notify_user` | Sends an out-of-band message without pausing the run. | tools/builtin/notify.ts:8-31 | Kind is always `info` (:15); 16,000 chars max. The hub turns it into session status `awaiting_ack` (ui/lib/notifications/inbound.ts:14-22, 36), which a later `done` does not overwrite (ui/app/api/_services/notification.service.ts:172). |
| HITL card tools | Six cards that each end the turn. | tools/builtin/hitl.ts:9 | `ask_user` (:196-218); `request_approval`, 1-20 items (:220-240); `suggest_service`, 1-20 (:242-262); `request_secret`, 1-8, values never shown to the model (:264-290); `request_mcp_sign_in`, registered with the self tools (:292-305; self.ts:26); `request_takeover`, only for non-temporary, non-foreman coworkers with browser and desktop (:178-180, 307-318). Each `execute` only returns an acknowledgement (:112-114). |
| How the answer returns | The user's answer arrives as a new chat message on the same session, which starts a new run. | contracts/chat-hitl.ts:350-358 (approvals text); hitl.ts:97 | The original run has already ended. Approval is followed only through the prompt. |
| Status while waiting | The hub shows the session as awaiting; the engine shows the coworker idle. | loop.ts:112-133, 359-361; ui/lib/notifications/inbound.ts:31-37 | Hub statuses: `awaiting_question`, `awaiting_approval`, `awaiting_connector`. Engine side: run `done`, agent `idle`. |
| HITL in schedule/trigger runs | HITL tools stay on; the prompt says a human will answer later. | agents/systemPrompt.ts:179-180, 279, 301; scheduler.ts:47-56; trigger-runner.ts:20-29; notification.service.ts:53-55, 150-158 | The hub creates the session row first via `agent.session.created`. |
| HITL in `call_agent` callee | A card ends the callee run; a waiting caller gets only the callee's text. | call-agent.ts:157-160 | The callee session waits on the hub. The callee gets no "unattended" prompt note because its source is `chat` (systemPrompt.ts:279). |
| Delegates and the foreman | Delegates have no HITL at all; the foreman keeps the engine's own cards. | delegate.ts:70-73; tools/builtin/foreman.ts:57; agents/foreman.ts:20 | The hub ignores all foreman notifications (notification.service.ts:49). |
| Run terminal event | Announces the end of a run to the hub. | runtime/run-events.ts:36-88 | Events `agent.message.completed`, `agent.schedule.completed`, `agent.trigger.completed`. Automated runs carry `finalText` up to 2,000 chars (:5, :75-76). Cancelled runs are flagged (:17, :64). |
| Skill-proposal notice | Tells the hub a skill was proposed. | loop.ts:135-140, 379-380 | Sent after the terminal event. |
| `sendNotification` transport | Single POST to the hub webhook. | runtime/notify.ts:56-98 | `POST /api/webhooks/engine`, 5 s timeout, **no retry or outbox**. Skipped when the hub isn't configured. |
| Hub ingestion | Stores notifications and mirrors session status. | ui/app/api/webhooks/engine/route.ts:7-34; ui/app/api/_services/notification.service.ts:41-108, 164-181 | Stores the notification, mirrors session status, retitles automated runs, analytics, email, push. A cancelled run only updates status. |
| Unread / unseen | Tracks unread conversations and unseen automated runs. | ui/lib/notifications/unseen-runs.ts:5-53; ui/app/api/_services/notification-audience.service.ts:28 | Runs of the same schedule are folded into one line. |
| Per-coworker notification mode | Lets each user mute or follow a coworker. | contracts/agent.ts:208-214 | `default` / `everything` / `muted`. |
| In-memory run stream buffer | Lets the dashboard reattach to a live run. | runtime/run-streams.ts:10-59; runtime/stream.ts:8-32; runs.ts:63-69 | Buffer evicted 3 min after the run ends. Lost on restart. |
| `callHub` + hub tools | Coworker calls to the hub (catalog, publish, team). | runtime/hub.ts:6-40; tools/builtin/hub.ts:6-70 | 20 s timeout (foreman: 180 s, tools/builtin/foreman.ts:10). |

## 6. Gates and checks in code (not prompts)

| Mechanism | What it does | Where | Limits or gaps seen in code |
|---|---|---|---|
| Engine API auth | Single bearer key on every engine route. | http/auth.ts:4-11 | **Open when `RERUN_API_KEY` is unset.** |
| Foreman guard | Only allow-listed routes reach the foreman over HTTP. | http/foreman-guard.ts:8-41 | Only its model can be patched. |
| Foreman hub token and tool allow-list | The hub checks the foreman's signed token and allowed tools. | runtime/hub.ts:10-15; ui/app/api/hub/route.ts:36-54; ui/app/api/_services/foreman-hub.service.ts:20 | The hub also checks that the calling coworker belongs to the workspace (route.ts:53-54). |
| Tool switches per coworker | 26 on/off keys decide which tools a coworker gets. | contracts/agent.ts:23-50; tools/registry.ts:36-87; http/routes/agents.ts:107-153 | All on by default. MCP servers are separate (registry.ts:75-76). |
| Foreman fixed tool set | The foreman's tools are rewritten on every boot. | agents/foreman.ts:20-33 | Self-improvement off. |
| `enabled` switch | A switched-off coworker can't run. | contracts/agent.ts:147-150; chat.ts:28; call-agent.ts:87; scheduler.ts:31; trigger-runner.ts:16 | Hub-side cap on active coworkers per plan (ui/app/api/_services/capacity.service.ts:20-47). |
| Tool approvals | **None in code.** | agents/providers.ts:307-308 (Claude `bypassPermissions`), :359 and :376-378 (Codex `never`) | `request_approval` is a card; whether the agent waits is decided by the prompt only (hitl.ts:224). |
| Confirmation flags | Some destructive tools require `confirm: true`. | ui/lib/mcp/args.ts:34-46; tools/builtin/brain.ts:195 | The model sets the flag itself. |
| Shell guards | Blocks a few destructive command patterns; time limit. | tools/sandbox.ts:64-70; tools/builtin/shell.ts:26-29 | 8 regex patterns. Timeout 120 s by default, 600 s max. |
| File path sandbox | Keeps file tools inside their root. | tools/sandbox.ts:14, 52-62 | The comment calls it "defence in depth, not a boundary" (:51). |
| Host breaker | Stops calling a host after repeated failures. | tools/host-breaker.ts:1, 29 | 3 consecutive failures block the host for the rest of the run. |
| Budget latch | Pauses automated runs on Rerun models when the balance is spent. | runtime/budget-latch.ts:5-21; loop.ts:329 | 10 min, in memory. Checked by schedules and triggers, provider `rerun` only (scheduler.ts:40; trigger-runner.ts:18). Not checked by chat. |
| Plan-limit latch | Pauses schedules when a subscription hits its limit. | connections/plan-limits.ts:101-113; scheduler.ts:41 | 30 min. Schedules only. |
| Per-run token or cost ceiling | **None.** | loop.ts:481-552 | No `maxOutputTokens` on the run. The only ceiling is the compaction summary (compaction/config.ts:7). |
| Model per coworker / chat / schedule / trigger | Picks which model a run uses, with fallback. | contracts/agent.ts:156-165; agents/availability.ts:103-139; http/routes/schedules.ts:22-26; contracts/trigger.ts:32-36 | Schedules and triggers fall back with a warning when their pinned model is unusable (availability.ts:132-139). |
| Thinking / effort setting | **None** per coworker, schedule or trigger. | agents/reasoning.ts:13-17; agents/providers.ts:315, 395 | Fixed per provider. |
| Self-improvement switches | Turn on the curator, skill proposals and self-editing tools. | contracts/agent.ts:59-64; tools/registry.ts:51-52; tools/builtin/self.ts:43, 58, 75; runtime/curator.ts:39; UI ui/components/agent/AgentPanelTools.tsx:137, 157, 237 | Forced off for `call_agent` callees, delegates and the foreman. |
| Install gate | Limits what a coworker can do while its setup is pending. | tools/registry.ts:71-73; agents/setup.ts:33-46; schedules.ts:85 | One install session at a time. |
| Validation of run output | **None.** | sub-run-watch.ts:75-80 (failure markers, display only); tools/builtin/team.ts:28 (description only) | `done` only means "ended without a technical error". |

## 7. Scheduling and capacity

| Mechanism | What it does | Where | Limits or gaps seen in code |
|---|---|---|---|
| Scheduler loop | 30 s tick; also runs memory, brain and Codex maintenance. | runtime/scheduler.ts:21, 93-134 | Single process, in memory. |
| Session claim | At most one live run per session. | runtime/run-control.ts:5-50 | In memory. Released when the run ends (loop.ts:356). |
| Two runs of one coworker | Allowed in different sessions. | run-control.ts:52-55; scheduler.ts:35 | No per-coworker cap. The busy check is only used by schedules, and only for coworkers with a screen. The single status flag is wrong while two runs are live (loop.ts:348); the hub team status ignores it for that reason (ui/app/api/_services/team-status.service.ts:17-18). |
| Screen lease | One run at a time drives a coworker's screen. | tools/builtin/computer.ts:66-96 | Others wait up to 5 min. |
| Engine-wide concurrency | **No cap and no queue.** | http/routes/health.ts:20-22 | Run count is only reported. |
| Fan-out caps | 4 parallel calls / 4 parallel tasks. | call-agent.ts:34, 56; delegate.ts:27, 127 | Per run or per tool call, not per engine. Nesting multiplies them. |
| Client message queue | The web chat retries a queued message until the session is free. | ui/lib/chat/start-chat.ts:9-19; ui/components/chat/QueuedMessagePill.tsx:27 | Client-side. |
| Serialized foreman hub tools | Some foreman hub calls run one at a time. | tools/builtin/foreman.ts:12-18, 36 | Only when the hub marks the tool `serial`. |
| Hub zombie sweep | Flips stale "working" sessions to idle after checking the engine. | ui/lib/board/live-sessions.ts:25-49; ui/app/api/_services/board-agents.service.ts:40 | Over 5 min stale, at most 10 per board load, engine confirms. |

## 8. Observability

| Mechanism | What it does | Where | Limits or gaps seen in code |
|---|---|---|---|
| Run row | One row per run with totals. | db/repos/runs.ts:63-128 | Tokens and cost are written only on `done` (:104-118). Error and cancelled runs get none (:120-128). |
| Step telemetry | Per-step tokens (including cache write), cost, duration, finish reason. | loop.ts:167-190, 501-510 | Written for every step, including steps of runs that later fail. |
| Tool-call telemetry | Input and result JSON for each call. | loop.ts:191-207 | `is_error=1` means "no result found in that step", not "tool failed" (:203). `duration_ms` is always null (:204). |
| Cost | Cost per step and per run. | loop.ts:142-147 | Only from OpenRouter or OpenCode metadata. Null for every other provider. |
| Run routes | List, detail with output, steps, tools. | http/routes/runs.ts:71-103 | List limit 200. |
| Usage route | Daily token and cost totals. | runs.ts:18-24; db/repos/runs.ts:19-40 | Counts `done` runs only. |
| Stats route | Charts over runs, steps, tool calls, sessions. | http/routes/stats.ts:14-38; contracts/stats.ts:3, 20 | Grouped by model, status, trigger source, etc. |
| MCP server status | Probes each MCP server of a coworker. | http/routes/agents.ts:172-179; tools/mcp-status.ts:7-16 | 15 s timeout. |
| Health route | Active runs, claimed sessions, versions. | http/routes/health.ts:16-40 | — |
| Logs | Engine logs. | lib/logger.ts:4; loop.ts:534; cli/bin.ts:77-78 | pino, level from env. A `run usage` info line per run. |
| Gaps | What the telemetry misses. | delegate.ts:100-106; loop.ts:170, 193 | Delegate telemetry is deleted with the temp agent. Curator, compaction and skill-drafting calls are untracked. CLI providers run the whole turn as one step (hitl.ts:85-87, so one step row per turn is inferred, not verified). |
| Hub analytics | Chat run completed/failed events. | ui/app/api/_services/notification.service.ts:113-144 | Chat runs only. |

## 9. `tools/factory/*.py`

`die()` prints `REFUSED:` and exits 2. `run()` failures exit 1 (factory.py:42-51). Owner allow-list on repos (factory.py:69-73).

| Mechanism | What it does | Where | Hard refusal (non-zero) vs print |
|---|---|---|---|
| `packet` | Prints an issue or PR digest: body, CI, files, diff, comments. | factory.py:111-154 | Print. Exit 1 if not found. |
| `wt new` | Creates a builder worktree on `chunk/<issue>-<chunk>`. | factory.py:327-411 | Exit 2 on: bad id (:348-349), /data free < 30 GB (:373-374), memory < 4 GB (:375-377), work dir > 20 GB (:378-379), 2 active builders already (:251-254, :380, :398 under lock :211-249), no `PLAN READY`/`SMALL FIX` line on the issue (:257-270), missing base branch (:387-389). `EXISTS` prints and exits 0 (:369-371). |
| `wt done` | Removes a worktree after proving its work is saved. | factory.py:299-312, 353-368 | Exit 2 on uncommitted changes, fetch failure, or a failed rescue push. Pushes unsaved commits to `rescue/...` first. |
| `wt list` / `wt sweep` | Lists worktrees; sweep classifies KEEP/REMOVE/RESCUE. | factory.py:332-344, 423-475 | Print. Sweep is a dry run unless `--apply`. |
| `pr-open` | Pushes the chunk and opens a PR. | factory.py:498-543 | Exit 2 on: uncommitted changes, no commits ahead, workflow files, AI trailer in commits, PR already open without `--fix`, missing handoff sections (:16). `--fix` re-checks the builder cap (:519-525). |
| `ci-wait` | Waits for CI and reports. | factory.py:547-584 | **Prints GREEN/RED/WAITING/NONE, exit 0 in all cases**. Exit 1 only if the PR is not found. Writes a green marker (:571-573). 30-min queue limit, 450 s slice (:15). |
| `risk` | Names extra reviewers from file paths. | factory.py:588-632 | **Print only**, including STOP (:621-622). Sends the PR title and file names to `api.typesafe.ai` (:635-662). |
| `merge-dev` | Merges a PR into `dev` or `job/*`. | factory.py:666-701 | Exit 2 on: base main/default, base not dev or job, closed or draft, workflow files, CI not GREEN. **Does not run `gate.py` or check reviews.** Its `--note` comment (:689) does not match gate.py's review format (`REVIEW_RE`, gate.py:11) unless the note itself starts with `<NAME> ACCEPT`. |
| `job-open` / `release-pr` | Opens a work-order issue / a release PR. | factory.py:705-743 | Exit 2 on missing required sections (:713-715, :733-734) or a wrong head branch (:728-729). Release PR is never merged here (:743). |
| `repo-check` | Prints repo setup: branches, docs, CI, rulesets. | factory.py:747-775 | Print. |
| `gate` | 6 checks bound to the PR head SHA. | gate.py:230-373 | Checks: CI_GREEN (:254-259), DONE_TEST from the issue chunk line found as passed in job logs (:261-285), FAIL_BEFORE (changed test failed on an older commit, :287-314), REVIEWS (LINUS plus rule-based reviewers, ACCEPT comments at the head SHA, STOP for workflow files, :316-339), LIMITS (max-lines default 800, workflow files, do-not-touch globs, :341-359), HANDOFF (:361-363). Exit 0 PASS, **3 FAIL**, 1 could not answer, 2 usage (:412-423). Writes state JSON. Enforces nothing by itself. |
| `review` | Posts a `Review ACCEPT/REJECT @sha8: NAME ...` comment. | gate.py:376-403 | Exit 2 if the PR head moved past `--sha` (:393-395). `--as` is only regex-checked (:383-385), so no identity check. Exit 1 if `gh` fails. |
| `job-cost` | Read-only sum of tokens and tool calls for runs tagged `JOB <repo>#<n>`. | jobcost.py:1-44 | Exit 2 on usage only. Skips the foreman (:13). **No `cost_micros` or reasoning tokens** (:30). `--steps` is in the usage text but not implemented (:8). Delegate runs are invisible (their DBs are deleted). |
| `install.sh` / `bin/*` | Installs `python3 -I` wrappers. | install.sh:1-29; bin/* | Requires `--jev-keyfile` (:18). |

## 10. Web app (only what bears on the above)

| Mechanism | What it does | Where | Limits or gaps seen in code |
|---|---|---|---|
| Workspace map | Isometric board of Boxes and coworker tiles. | ui/components/builder/IsoBoard.tsx:69; ui/lib/board/iso-adapter.ts:27-67 | Tiles show status, "to handle" count, next-run countdown, results. Boxes are containers. Working calls are drawn as links. |
| Box = layout + access, not a machine | A Box groups coworkers and scopes access; the workspace has one machine. | ui/app/api/_services/capacity.service.ts:9-10; ui/app/api/_services/space.service.ts:13-15; ui/app/api/_auth/access.ts:146-186 | Engine has no Box concept (contracts/chat.ts:23-25). |
| Coworker status, map version | Status computed from the coworker's live hub sessions. | ui/lib/board/types.ts:52-63; ui/app/api/_services/board-agents.service.ts:40-42 | **Two derivations disagree** — map: ui/lib/board/types.ts:52; `team_status`: ui/lib/board/team-status.ts:23-31 with team-status.service.ts:19-68, which uses engine running runs. |
| Attention and next runs | Counts what waits on a person; finds each coworker's next run. | ui/lib/board/attention.ts:10-16; contracts/conversation.ts:11; ui/lib/board/next-runs.ts:12-24 | — |
| Runs in flight | Progress tree for sub-runs with per-task stop; pending card and queued message pills. | ui/components/chat/SubRunBlock.tsx:21-50; ui/components/chat/SubRunTree.tsx:58-66; ui/components/chat/MessageView.tsx:212; PendingHitlPill.tsx:9; QueuedMessagePill.tsx:27 | Per conversation. No engine-wide live-runs view found (not searched beyond these). |
| Run history, logs, monitoring | Per-coworker run list and usage charts. | ui/components/agent/AgentRunHistory.tsx:63; AgentPanelLogs.tsx:48, 57; AgentPanelMonitoring.tsx:44, 59, 73 | Polls every 30 s. |
| Schedules and triggers panels | Per-coworker editing of schedules and triggers. | ui/components/agent/AgentPanelScheduled.tsx:49; AgentPanelTriggers.tsx:31, 42 | Gated by "can manage". |
| Approvals UI | In-chat cards plus the workspace inbox. | ui/components/chat/ApprovalBlock.tsx:19; QuestionForm.tsx:45; SecretRequestBlock.tsx:24; McpSignInBlock.tsx:31; TakeoverAsk.tsx:21; SkillProposalBlock.tsx:18; BrainProposalBlock.tsx:10; ui/components/notifications/WorkspaceInbox.tsx:36 | Line for ActionApprovalBlock.tsx not determined. Whether a separate cross-coworker approvals page exists: not determined (not searched). |

## Things I expected and did not find

- **Step cap per run.** Grep `stepCountIs|maxSteps|maxTurns|max_turns` in `apps/engine/src`: only the provider-errors.ts:61 mapping.
- **Per-run token or cost budget.** Read `streamText` options (loop.ts:481-552), budget-latch.ts and compaction/config.ts: only the Rerun-balance latch and the compaction summary ceiling exist.
- **Call or delegation depth limit.** Grep `depth`: nothing relevant; `call_agent` only excludes self.
- **Engine-wide run queue or concurrency cap.** Grep `queue`: only paid-data backfill and the update command.
- **Rate limit on webhook fires.** Grep `rateLimit|throttle`: only Codex plan rate-limit reads.
- **Tasks or work-queue table.** db/schema.ts, systemDb.ts DDL, sharedDb.ts: none. "A queue several coworkers work through" is prompt text (agents/systemPrompt.ts:45).
- **`@mention` routing in code.** Grep `mention` in the engine: only rename rewriting and prompt text.
- **Result callback for a dispatched `call_agent`.** Grep `originSessionId`: stored, never read.
- **Code-enforced approval before a tool runs.** Every HITL `execute` returns an acknowledgement (hitl.ts:112-114), and the CLIs run with permissions bypassed.
- **Validation of run output.** Nothing beyond failed-finish classification.
- **Thinking or effort setting per coworker or per trigger.** Grep `effort|thinking`: fixed per provider only.
- **Boot cleanup of temp delegates left by a crash.** Grep `ephemeral|' delegate'`: none.
- **Retry or outbox for hub notifications.** runtime/notify.ts:56-98: a single fetch.
- **Run-level retry or resume after restart.** loop.ts and reconcile.ts: interrupted runs are only failed.
- **Plan-limit check on triggers.** trigger-runner.ts:14-40: only the budget latch.
- **Separate shared DB per space or Box.** config/paths.ts:33: one path per engine.

---
I did not read: the hub chat route body past what grep showed, `apps/mobile`, the engine sessions, memories and rewind routes, `skills/loader.ts`, `mcp-pool.ts`, or hub billing internals. The CLI "one step per turn" telemetry claim comes from a code comment and was not verified. Biggest risk for factory design: delegate telemetry is deleted with the temp agent, so `job-cost` and the usage routes under-count any job that used `delegate_tasks`.
