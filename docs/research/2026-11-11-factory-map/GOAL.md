# Goal per run: adopting the standard

as_of 2026-11-13. Read in full for this page:

- Claude Code, "Keep Claude working toward a goal": <https://code.claude.com/docs/en/goal>
- OpenAI cookbook, "Using Goals in Codex": <https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex>
- The engine at dev `451b400`: `packages/contracts/src/run-goal.ts`, `apps/engine/src/runtime/goal-check.ts`,
  `apps/engine/src/agents/claude-goal-hook.ts`, `apps/engine/src/runtime/loop.ts`.

## The standard and the engine, side by side

| | Claude Code | Codex | Rerun engine today |
|---|---|---|---|
| What a goal is | one condition in plain words, up to 4,000 characters | an objective kept on the thread: outcome, what proves it, what must not regress | `lastLineForms` (1 to 4 fixed forms of the last line) and `turnLimit` (1 to 10) |
| Who judges | a small fast model after every turn, from the conversation only; it runs no tool and reads no file | the model audits the objective against evidence before it may mark it complete; pause, resume, clear and the budget stay with the user or the system | code: the last line against fixed patterns; no model |
| Verdicts | met; not yet met, with a reason that guides the next turn; impossible | active, paused, complete, budget-limited | met or not met per turn, with a reason; states `running`, `met`, `not_met`, `unchecked` |
| What keeps it going | a Stop hook that refuses the stop | a continuation, only when the thread is idle and inside the budget | the same Stop hook on the Claude path; one check at the end on the other providers |
| What stops spinning | several turns in a row with no tool call end the loop | a continuation turn with no tool call suppresses the next one | the turn limit |
| Bound | a turn or time clause written into the condition | an explicit budget; reaching it is not completion | the turn limit, and the delegator's three clocks |
| Errors | one the user must fix (sign-in, credit, context overflow, model gone) clears the goal; a passing one is retried three times, then the goal pauses; a usage limit pauses until it resets | an interruption pauses the objective | the delegator's classes: cancel, transient, plan, work |

## What is already the same

The mechanism. The engine refuses a stop through a Stop hook, hands the worker the reason, and records one
verdict per turn with its reason. That is how Claude Code builds `/goal`, and the engine's record
(`state`, `verdicts[{turn, met, reason}]`) has the standard's shape.

## What is missing

The condition. The engine proves that an answer ends in the right kind of line. It does not judge whether what
that line claims was shown. `PR: <url>` passes whether or not the done-test was run. In both harnesses the goal
is the claim itself: an end state, the check that proves it, and what must not change on the way.

## Adoption

1. **The goal gains an optional `condition`**: text of 1 to 4,000 characters, beside `lastLineForms` and
   `turnLimit`. The goal is stored as one text column, so the database does not change. A run without a
   condition behaves exactly as today.
2. **The forms stay and go first.** They are the delegator's handle on the answer and they cost nothing. Only
   when the last line passes and a condition is set does a small fast model judge the condition and return one
   of three verdicts with a reason: met, not met, impossible. Not met sends the run back with the reason, inside
   the same turn limit. Impossible ends the goal `not_met` at once with the reason.
3. **The judge calls no tool.** It reads text it is handed and nothing else: no file, no network. A condition
   must therefore ask for something the run itself can show ("the output of the run command is shown and every
   named test passes"), which is the rule both harnesses give. What exactly it is handed is open, below.
4. **The condition is written in the owner's goal shape** (objective, non-goals, two to six success criteria,
   constraints) and the delegator renders it from the issue: the title is the objective; **Files** are the
   non-goals ("touch only these paths"); **Done-test** and **Run** are the success criteria; the builder's
   rules are the constraints. The blocked exit is part of the condition ("or the last line is BLOCKED with the
   one thing that stopped the work"). An issue whose condition does not fit in 4,000 characters fails the intake
   check: it is too large a chunk. Measured on the thirteen factory issues of 2026-11-13 (#205 to #215, #220,
   #225): title, **Files**, **Done-test** and **Run** plus 600 characters of rules come to 1,300 to 2,400
   characters, so the limit would have refused none of them.
5. **A run sent back by the judge that answers without calling a tool, and is still not met, ends the goal.**
   This is the guard both harnesses use against a worker that argues instead of working. The engine counts a
   run's steps, so it can tell. It does not apply to a send-back for the form of the last line, where the
   worker is told to write that line and redo nothing.
6. **The condition is not proof.** The judge sees only what the run wrote. The delegator keeps its own checks:
   the pull request exists, the reviewed commit is the merged commit, the checks of that commit passed.
7. **Off unless a run carries a condition.** The run page shows the condition and each verdict's reason. A
   switch per coworker and per job type comes with the frontend work, as the owner asked for toggles.

## Open before the cut

- What the judge is handed. Claude Code's evaluator gets the conversation so far, tool results included. The
  engine's Stop hook gets only the last answer. A judge that reads only the worker's own words would break the
  rule of LOOPS.md that an exit check never rests on them, so it needs the run's tool output as well. Where
  that comes from (the run's stored steps, or the transcript the harness keeps) is settled at the cut, and
  until it is, the condition must not be switched on for a job.
  A stronger answer comes from the study of machinist
  ([MACHINIST.md](../2026-11-13-owainlewis-tutorials/MACHINIST.md), point 3), where it is an example in an
  essay and a proposal in the roadmap, not yet the shipped product: where a command can prove the claim, no
  model judges at all. The engine would run the issue's **Run** command in the run's own workspace when the
  worker stops; the exit code decides, and a failing output goes back to the worker as data, inside the same
  turn limit. The model judge is then kept for what no command can show. To be weighed at the cut: it needs
  the engine to run a command in the worker's workspace on its own account, which it does not do today, and a
  **Run** line that works as written (the form `python3 -I -m unittest <module>` does not find the module on
  Python 3.12; `discover -s . -p <file>` does).
- Which model judges on a connection that is not Claude's, and what one verdict costs on each. On the Claude
  path it is the small fast model of that connection.
- The other providers check the goal once, at the end, with no send-back. Whether they get the loop too is
  part of this job or its own.
- The error column above is the nearest thing to a published standard for retry classes. Compare it with the
  delegator's four classes when retries are next touched: "clears on its own" (retry), "repeats until something
  outside changes" (pause until it does), "needs a person" (stop).

## Build order

1. Contract and account tool: `condition` in `runGoalSchema`, passed through `send_message`; the verdict
   (`goalVerdictSchema`, today a strict `met` true or false) gains the third outcome, impossible.
2. Engine: the judge, called from the Stop hook after the form check; verdicts recorded as today.
3. Delegator: render the condition from the issue for build and fix runs; review runs keep their form.
4. Run page: the condition and the reasons.

This is cut together with phase B of the plan (#198). It depends on nothing in phase B.
