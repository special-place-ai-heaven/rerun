# Principles of the factory

Set by Rob on 2026-11-11. His words are quoted as he wrote them. The design that follows from them is in
[MAP.md](MAP.md); the plan is rerun issue #42. Read this page first, before planning or changing anything in
Rerun or in how the coworker team works. When a principle and a convenient shortcut disagree, the principle wins.

## 1. The win condition

> "Win condition is a superior product at a lower cost and grater speed. 3 metrics that should be tracked, analyzed from input to output."

- **Quality, cost, speed.** All three, from the request to the merged and deployed result.
- A change that improves one by hurting another is not a win.
- > "the resulting product must be superior at a lower cost."
- All three are read from records. None is reported by a coworker.

## 2. A self-correcting line

> "Changes proposed, changes made, monitored again, gaging the results, pivoting when needed. A selfcorecting line"

> "I am always about efficiency projected over a whole session or project. Analyze what cost most and why, deal with the culprit so the next run is better, cheaper."

- Measure, find the largest cause, change one thing, measure again, keep or remove.
- Baseline first. No claim of improvement without the same figures from before.
- Every change gets a row in the change log (MAP.md, section 12), and its measured result is filled in later.
- > "we must have self correcting and learning sessions with proper analysis and improvement mechanics."
- Learning is gated: a coworker or a script proposes, a check decides, the effect is measured on the next jobs. Nothing rewrites itself unchecked.

## 3. Mechanism, not request

> "we need to make this happen automagically and dynamically, so proper workflows, rules, skills used, verification and other loops, before it even reaches the workers. and same goes for when work is completed"

> "as in any factory, you have rules, regulations, procedures, automated steps and people or robots to manage it all so a product churn is smooth and KPI stays green. Here instead of people and robots we have our LLMs."

- A rule in a prompt is a request; a stage in a pipeline is a mechanism. What must happen is enforced by code.
- Code decides what happens next. Models plan, build and judge inside a stage.
- Nothing is done without evidence a script can check.
- > "we can script procedure and leave him only levers and control mechanisms. find smart ways to achieve the same or better, but at a lower cost (less instruction bloat)"

## 4. Planning first

> "I noticed our planning department was quiet throughout use today. 0 planning, direct task delegation only. This is bad. Planning should consist of 70% of our work if we do all things right."

> "so general plan, milestones, sprints, tasks, subtasks,... loops for reviews and proofs"

- No builder starts without a plan on the job's issue: outcome and done-tests, facts with file and line, the design decision and the alternatives rejected, the pieces, the risks.
- The plan is written by planning coworkers and challenged once by someone who did not write it.
- A builder who finds the plan wrong stops and returns it. A third review round returns the job to planning.
- Loops are bounded and written down.

## 5. Small pieces, well labelled

> "we deserve a really good task/ledger chunker. SOmething that can properly create many many smaller tasks which are easily handles by small LLMs"

> "the better task chunking and organization we have, and the better queuing mechanism for the loadbalancer, the better off we will be. JEV is great at loadbalancing and delegation if everything is properly labeled and tagged."

> "we need to be able to better chunk work into smaller pieces and paralelize work in worktrees, faster commits, and queued review ... keep note of which worktrees are not needed any more so we have a cleanup policy. Workers can and should be spun on demmand"

- A chunk is right when a small model can finish it from its packet alone.
- Labels make routing a lookup.
- Something must know the queue and the occupancy of the system: > "something must know the task queue/ledger occupancy of resources/system."
- > "Keep unique coworkers as we have now, and spawn paralel copies of any bottlenecked one"
- One job, one builder, one branch. Additions to a running job go on its issue.

## 6. Build the least

> "overengineering is a curse and a blight. As Elon Musk says 'the best part is no part'."

- A part is built only when a measured failure demands it.
- A check at a place work already passes through beats a new service.
- Every new part must delete something.
- Nothing is built for a later milestone's sake.

## 7. Tokens are for thinking

> "tests should cost 0 tokens. As they run automatically by the script and can be monitored by terminal commander. Test preparation (scripts creation) is the only thing that should cost tokens."

- Tests, builds, waiting and routing cost no model tokens. A check every PR needs belongs in CI.
- Cost is the number of model calls times the context each call re-reads. Fewer calls and a smaller context, in that order of ease.

## 8. Know what burns

> "All I need to know is not actual money, but what is burning most tokens and degrades my weekly the most."

> "if you have 3 bots and they ammount to 1% you won't know which one contributed to most waste. thats why we need both percentage of weekly and tokens"

> "I want it granular, analytics style." ... "We need to be able to point to a culprit."

> "token use depends on LLM model and thinking level" ... "those states must be monitored as well per agent and subagent"

- Tokens by kind and share of the weekly allowance, always both, never money.
- Collected without spending tokens.
- What can be measured can be set: model, thinking level and helper model per coworker.

## 9. Knowledge that is delivered

> "our brain is either not wired correctly or it is a graveyard of stuff no one reads. No knowledge graph with proper memory layer and data injection, and no always improving agents possible at all"

> "documentation is important I find. So no ammount of context wipe and sessions could diminish of what we are working on towards"

- Knowledge is pushed into a stage's packet by label, never left to be looked up.
- Decisions and designs go into the repo and the issues the same day, not only into a session.
- What nobody reads is measured, then archived.

## 10. No wall, careful grafting

> "NO limit should stop us. this is software after all and we do know it is possible in principle."

> "we have source to mold and recode however we like. if we are careful and code in terms of extensions or addons, we can even stay compatible with core rerun as it itself gets updated. But we will need to make a decision when and if to properly properly fork split away"

> "it depends what brick wall we it, if anny"

- Beside the engine first, then thin seams, then deep changes.
- A limit in the code becomes a feature on the plan. Limits outside the code (the machine, the weekly allowance, dependencies in the work itself) are managed, not denied.
- The split from upstream is decided on evidence, when a wall is actually hit.

## 11. Standing rules for the products

- **Dependencies:** > "we must always go latest version, not pin to lower to satisfy some piece of code, we must correct code to match new features in any such large dependency bump" and for important libraries > "someone should read all the release notes and make sure the changes are properly addressed and any feature enhancements used properly"
- **Platforms:** > "Remove any mac build requirements, we only build for linux and windows if needed by the project"
- **Never delete work.** Unpushed work is saved before anything is removed.
- **Code is read with SymForge; commands run through Terminal Commander; orchestration is scripted.**

## 12. How the work is run

> "I don't care why it failed, I only care for you to fix the issues. Simple as that. I give you authority to enhance our products and rid it of all its flaws to the best of your ability."

> "we cant affort stalling, idling"

> "I leave you in charge to make all this happen."

- Fix and report the outcome; lead with what changed, not with the diagnosis.
- Do not wait when work can move.
- Still Rob's alone: spending money, deleting data that cannot be regenerated, anything on shared systems beyond his own products, messages to outsiders in his name, and the split from upstream.
