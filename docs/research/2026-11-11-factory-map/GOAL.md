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
   when the last line passes and a condition is set does a small fast model get the condition and the run's
   answers, and return one of three verdicts with a reason: met, not met, impossible. Not met sends the run
   back with the reason, inside the same turn limit. Impossible ends the goal `not_met` at once with the reason.
3. **The judge reads text and nothing else.** It gets the condition and the answers; no tool, no file, no
   network. A condition must therefore ask for something the worker's own output can show ("the output of the
   run command is shown and every named test passes"), which is the rule both harnesses give.
4. **The condition is written in the owner's goal shape** (objective, non-goals, two to six success criteria,
   constraints) and the delegator renders it from the issue: the title is the objective; **Files** are the
   non-goals ("touch only these paths"); **Done-test** and **Run** are the success criteria; the builder's
   rules are the constraints. The blocked exit is part of the condition ("or the last line is BLOCKED with the
   one thing that stopped the work"). An issue whose condition does not fit in 4,000 characters fails the intake
   check: it is too large a chunk.
5. **Not met twice for the same reason ends the goal.** That is the standard's guard against a worker that
   answers the judge without doing anything.
6. **The condition is not proof.** The judge sees only what the run wrote. The delegator keeps its own checks:
   the pull request exists, the reviewed commit is the merged commit, the checks of that commit passed.
7. **Off unless a run carries a condition.** The run page shows the condition and each verdict's reason. A
   switch per coworker and per job type comes with the frontend work, as the owner asked for toggles.

## Open before the cut

- Which model judges on a connection that is not Claude's, and what one verdict costs on each. On the Claude
  path it is the small fast model of that connection.
- The other providers check the goal once, at the end, with no send-back. Whether they get the loop too is
  part of this job or its own.
- The error column above is the nearest thing to a published standard for retry classes. Compare it with the
  delegator's four classes when retries are next touched: "clears on its own" (retry), "repeats until something
  outside changes" (pause until it does), "needs a person" (stop).

## Build order

1. Contract and account tool: `condition` in `runGoalSchema`, passed through `send_message`.
2. Engine: the judge, called from the Stop hook after the form check; verdicts recorded as today.
3. Delegator: render the condition from the issue for build and fix runs; review runs keep their form.
4. Run page: the condition and the reasons.

This is cut together with phase B of the plan (#198). It depends on nothing in phase B.
