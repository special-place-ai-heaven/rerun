# Defect scan: the dry run

as_of 2026-11-13.

## Result

The scan works, and it paid for itself on its first real use. Pointed at the code the delegator's next restart
would bring (`tools/factory`, 59bc1c4 to 453a057), it reported three defects. All three were confirmed against
the code and against the day's runs. One of them would have cancelled about one healthy build in four. They
were fixed through the factory as #235 (pull request #236, built, reviewed and merged in about ten minutes)
before any restart.

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
two downloads and files in its own temp folder.

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
| The delegator's runs take the runner's limits by fallback: 400,000 tokens | `clocks.outcome` on a run at 450,000 tokens returns CANCEL; of the day's finished builder runs, 13 of 49 used more than 400,000 (largest 1,056,302), none ran over 45 minutes | real, and the worst: one healthy build in four cancelled. `dispatch.json` now has its own clocks, token cap 3,000,000 |
| A delegator stopped while a send is in flight leaves a row without its intent; the job fails after 20 passes with a KeyError while its run goes on | read in `send()` and `lost_run()` | real. The intent is now on the row before its first save; an old row without one ends `blocked` at once with a plain reason |
| At the first beat after the move to the ledger, a run in flight for more than 10 minutes is cancelled as stalled | `clocks.seen_after` with no earlier sighting dates the last step at the run's start | real, once only. Such a run's first sighting is now dated at that beat |

3.5 minutes, 850,000 tokens, nothing written on GitHub (checked: no issue, pull request or comment in the
window but the fix issue). After the fix merged, `test_dispatch.py` was run on `dev` at d0ccc3c: 76 tests pass.

The orchestrator had read the same diff an hour earlier and found none of the three as a defect. It had noticed
the second one and judged it rare, and had assumed the opposite of the third without reading `clocks.py`.

## What this does not show

- One graded sample and one live sample. The fault it missed needed knowledge of how another program joins
  text; a scan scoped to one folder will miss that kind again.
- The token clock's new value is three times the largest healthy run of one day, not a studied limit.
- Whether a weekly scan over the whole repository finds enough to be worth about a million tokens a run.

## Before it may file issues itself

Three more dry runs with every finding checked, and at least four findings in five surviving the check. Until
then its cards go to the orchestrator, who files.
