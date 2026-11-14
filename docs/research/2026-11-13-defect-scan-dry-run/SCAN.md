# Defect scan: the dry run

as_of 2026-11-13.

## Result

The scan works, and it paid for itself on its first real use. Pointed at the code the delegator's next restart
would bring (`tools/factory`, 59bc1c4 to 453a057), it reported three defects. All three were confirmed against
the code and against the day's runs. One of them would have cancelled a large share of healthy builds. They
were fixed through the factory as #235 (pull request #236, built, reviewed and merged in about ten minutes)
before any restart. Checking that fix against the day's runs then showed a fourth fault of the same kind, in a
limit the scan had not questioned (below, #238).

Recommended use: run it before every restart or deploy of the delegator, over the difference between the
running commit and `dev`. A weekly schedule over the rest of the repository is the owner's choice and is not
set up.

## The loop

| | |
|---|---|
| Job | find defects that the changes between two commits introduced in one named folder |
| Inputs | an archive of each commit, fetched into a temp folder; for the check on duplicates, the open issues |
| Allowed | read; run the folder's own Python tests and short snippets inside the temp folder |
| Forbidden | any write on GitHub, any change outside the temp folder, calling another coworker, memory |
| Output | at most five cards (where, failing path, impact, proof and whether it was run, confidence, existing issue, would file), or "no confirmed defect" |
| Evaluation | a finding counts only with a failing path; every finding is proven or killed by the orchestrator with a test before it is reported |
| Escalation | last line `BLOCKED: ...`; a finding of critical or high impact on code about to go live stops the restart |

Worker: the debugging coworker. One run per scan, with the goal `SCANNED: ...` or `BLOCKED: ...`.

## Graded run: known faults, answers hidden

The pass bar was written before any result was read. The code was the delegator between 44cd2bf and 6ed3bb6,
where three faults were known (each found on live jobs that evening and fixed later). The run got two archives
and no history, and was forbidden GitHub and memory; its nine tool calls were read afterwards and show only the
two downloads and files in its own temp folder. The brief did tell it where to look: follow each changed line
into the account tools, the contracts and the engine, and check that the two sides agree. That is the class
all three known faults belong to, so the grade says less about a scan given no such direction.

| Known fault | Impact | Found |
|---|---|---|
| the goal sent as a bare list while the account tool takes one object, so no job starts (fixed by #217) | critical | yes, with a proof it ran |
| the reason of a goal not met read from fields the record does not have (fixed by #203) | medium | yes, with a proof it ran |
| the final line found only at the start of a line while the engine joined text pieces with a space (fixed by #221) | high | no |

Two of three, no false finding, 2 minutes, 350,000 tokens. Pass, by the bar set beforehand (the critical one
and at least one other, at most two findings that do not survive). One run is one sample.

## Live run: the code about to go live

| Finding | Checked how | Outcome |
|---|---|---|
| The delegator's runs take the runner's limits by fallback: 400,000 tokens | `clocks.outcome` on a run at 450,000 tokens returns CANCEL; of the 49 runs that two builder coworkers finished that day (every run of theirs, not only factory builds), 13 used more than 400,000 (largest 1,056,302), and none ran over 45 minutes | real, and the worst of the three. `dispatch.json` now has its own clocks, token cap 3,000,000 |
| A delegator stopped while a send is in flight leaves a row without its intent; the job fails after 20 passes with a KeyError while its run goes on | read in `send()` and `lost_run()` | real. The intent is now on the row before its first save; an old row without one ends `blocked` at once with a plain reason |
| At the first beat after the move to the ledger, a run in flight for more than 10 minutes is cancelled as stalled | `clocks.seen_after` with no earlier sighting dates the last step at the run's start | real, once only. Such a run's first sighting is now dated at that beat |

3.5 minutes, 850,000 tokens, nothing written on GitHub (checked: no issue, pull request or comment in the
window but the fix issue). After the fix merged, `test_dispatch.py` was run on `dev` at d0ccc3c: 76 tests pass.

The orchestrator had read the same diff an hour earlier and found none of the three as a defect. It had noticed
the second one and judged it rare, and had assumed the opposite of the third without reading `clocks.py`.

## The fourth, found by checking the fix against real runs

The fix kept the stall clock: a run whose step count has not changed for 10 minutes is cancelled. Nobody had
looked at how the step count behaves on the live engine. Of that day's builds by one builder, a run of 1,391
seconds with 25 recorded tool calls ended with a step count of 1, and so did a run of 1,502 seconds; a third
run with 10 tool calls ended with 10. The count is not a sign of life for every run, and one tool call can
itself outlast 10 minutes. Both long builds would have been cancelled twice and ended `failed`.

The delegator's stall clock was switched off (#238); the 45-minute limit and the token cap stay.

**Corrected the same evening (#240).** The count itself was not at fault. For the command-line providers a whole
turn is one step of the SDK, so every run counted 1 until the live count of tool calls (#121) reached the server
with that afternoon's update, at about 17:25 UTC. Both long builds ran before it; the run that counted 10 ran
after it. Sorted by start time, every run of five coworkers that day splits the same way: 1 before the update,
the number of recorded tool calls after it. The comparison above set runs from both sides of an engine update
side by side without their times.

The clock stays off for the reason that does hold. The count rises when a tool call starts, not when it returns,
so a limit must be longer than the longest single call of a healthy run, and nothing records that: the engine
writes the calls of such a turn together when the step ends, with no time per call. No measuring is built for
it now. The 45-minute limit and the token cap bound a run that hangs, and a hung run spends no tokens.

Both clock faults have one cause: a limit was written down from a number that looked reasonable and shipped
without being held against real runs. A limit is now measured before it ships.

## The same check on the retry classes

After the restart the delegator's retry classes were held against the error text of real runs: 967 finished
runs, up to 200 per coworker. Four had ended in error, with three texts. One was already handled (an engine
restart). The other two were classed as failed attempts though a second try clears both: a run cut because the
engine renewed the Claude sign-in under it, and two runs refused at the provider's edge in the same second,
during minutes in which a session on another machine and network was refused too. Both texts become class
`transient` in #241. Only texts seen on real runs were added.

## Third run: the phase B code, before its restart

2026-11-13, 23:50 UTC. Scope: `tools/factory` between the commit running on the server (5a9851f) and dev
(3fc43f1): 18 files, 891 added lines, merged within one hour by fifteen jobs, six of them editing `dispatch.py`
one after another, each reviewed alone.

| Finding | Checked how | Outcome |
|---|---|---|
| While sending is held for a spent plan, a step that failed for an ordinary reason is still sent again at once: the resend in `failed_attempt` did not look at the hold | a test of the orchestrator's own on dev: two builds, one ends on a spent plan, the other on an ordinary error; a third send goes out in the same beat | real, low to medium: no job lost, but the job spends its one retry on a refusal. Fixed as #278 before the restart |

One finding, one survived. 4.5 minutes, 2,580,000 tokens. It also checked and cleared: a job left running by the
older code keeps its coworker and is not sent twice; the team list has the shape the new start-up code expects;
the three text patterns equal the contract's. The run broke one of its own rules: it kept probe scripts outside
its temp folder, said so, and removed them.

What this run could not find, because it was not there yet or not in its scope:
- A plan that contradicted a pinned test (#262). The builder found it and ended blocked, as it should.
- A rule that reads every AI connection where it should read one (#284). It came from reading two jobs that
  merged after the scan, before their restart.

## Fourth run: the hold and the copies setting, before their restart

2026-11-14, shortly after 01:00 UTC. Scope: `tools/factory` between the commit running on the server (bd7eb36)
and the head of the pilot's settings branch (fe8159a): six files, 193 added lines. Two things were new: a hold
on sending before a sign-in runs out, and the first setting that gives one coworker more than one run.

| Finding | Checked how | Outcome |
|---|---|---|
| The hold stops every send once the sign-in has 50 minutes left, but the engine renews a sign-in only when a run starts or the last one ends. On an idle line the hold stops the one thing that would end it | a test of the orchestrator's own: one labelled issue, nothing out, 40 minutes left: nothing is sent after four beats | real: the line would have stood still until someone started a run by hand. Fixed as #291 before the restart: the hold applies only while a run of the delegator is out |
| With more than one run on a coworker, a send that was cut off can adopt the run of a sibling job from the run list | a test: one coder with three runs, three issues, the first send raises; job 1 follows the build of issue 2, issue 2 is sent twice, issue 1 is never built | real, and in the path of the pilot. Fixed as #292 before the restart: a coworker with an unresolved send gets no further send |

Two findings, two survived. 638,000 tokens.

What this run could not find:
- A hole in the fix of its own second finding. The rule went into the two places that pick a coworker; the
  resend of a failed attempt sends without passing through either. It came from a read of the merged change of
  #292 before its restart, was confirmed with a test, and was fixed as #296.
- The stray file of the pilot (`docs/research/2026-11-14-copies-pilot/PILOT.md`). The worktree tool had not
  changed, so it was outside the difference under scan, and the fault needed a build to leave a file in the
  wrong folder.

## What this does not show

- One graded sample and one live sample. The fault it missed needed knowledge of how another program joins
  text; a scan scoped to one folder will miss that kind again.
- The token clock's new value is three times the largest healthy run of one day, not a studied limit.
- Whether a weekly scan over the whole repository finds enough to be worth about a million tokens a run.

## Before it may file issues itself

Three more dry runs with every finding checked, and at least four findings in five surviving the check. Until
then its cards go to the orchestrator, who files. Count on 2026-11-14: two of the three done (the third and
the fourth run above), three findings, three survived.
