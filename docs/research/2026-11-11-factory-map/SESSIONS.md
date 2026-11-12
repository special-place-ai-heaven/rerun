# Sessions, worktrees and messages: the factory's protocol (draft for challenge)

Rob, 2026-11-12: "each works in a very temporary worktree, commits work, once commited work is reviewed and checked
properly, the worktree can be deleted. we must keep cleanliness else disk is going to run out in a day ... devise
protocols to keep it efficient and 100% work safe." and "I do not know what communication bridge or mechanism is used in
rerun so all these sessions can communicate between each other. We must lean in on that and make it even more efficient."

This is a proposal by Rob's local Claude, reviewed once by its advisor. It becomes a work order of its own, with a
challenge by Devils Advocate, before anything is built or removed. Points marked **unverified** have not been tried.

## 0. What is on the server today (measured 2026-11-12, read-only)

| | Size | Note |
|---|---:|---|
| Disk `/data` | 193 GB, 89 GB free | shared with everything else on the VPS |
| Shared clones (`/data/work/repos`) | 2.0 GB | 4 repos |
| Factory worktrees | 2.8 GB | 5, all clean and pushed; 3 have their tip on `main`; some hold dependency folders (0.4-0.9 GB) and a code index (36-179 MB each) |
| **Clones outside the factory folder** | **about 8.5 GB, 43 clones** | in coworkers' workspaces and `/tmp`: reviewers and planners clone a whole repo per review or per plan; one reviewer's workspace alone is 3.3 GB |
| Other folders under `/data/work` (`e2e`, `review`) | about 3 GB | hand-made worktrees; who uses them is not yet known |
| Caches (`~/.npm`, `~/.cache`) | 2.0 GB | regenerable |
| Total used by the factory | about 20 GB | grows by several GB per working day at the current habits |

The worktrees are not the leak. The leak is every reader making its own clone, and nothing ever removing one.

## A. How Rerun sessions reach each other today (read from the engine code on dev)

There is no channel into a running session; a busy session refuses a message. Everything is one of four things:

| Mechanism | What it does | Cost while waiting |
|---|---|---|
| `call_agent` | one coworker starts a NEW session of another with a message; can wait for the answer; four at a time | the caller's session stays open and re-reads its whole context when the answer returns |
| `delegate_tasks` | a coworker starts short-lived copies of itself for subtasks, four at a time | the parent session stays open |
| Webhook trigger, schedule | something outside starts a NEW session with a fixed instruction and a payload | none: nobody is waiting |
| Shared storage | the space's shared database, the shared folder, the brain, memories; and GitHub | none |

Plus two ways to reach the user: `notify` (out-of-band message) and the ask-the-user cards (a session shows choices and
its status becomes "waiting for a person").

Rules for jobs the runner drives (ordinary handoffs between coworkers outside the factory stay as they are; they worked
well on 2026-11-11):
1. **A factory stage does not wait on another session.** The runner starts a stage through a trigger, with a packet. A
   stage ends by leaving evidence on GitHub. Nobody holds a context open to wait.
2. **A message is a pointer plus a packet**, at most 8 KB: repo, issue, branch, the commit to read, chunk line, paths,
   done-test, and on a retry the tail of the failing log. Never a transcript, never "as I said earlier".
3. **One record, one writer.** The job's issue and the runner's ledger comment are the record. Sessions do not write
   shared files directly (a handoff file was overwritten on 2026-11-11); they append through a script or not at all.
4. **The user is reached through the side bot**, with Rerun's own ask-the-user card for the plan approval and `notify`
   for a BLOCKED job. **Unverified:** the side bot's open routes list no trigger route, and the engine's own comment
   says a "waiting for a person" status has nowhere to land in a session started by another coworker. This needs a probe
   before the approval stage is designed on it.
5. **A new job gets a new session.** Boss's one long session reads about 440,000 input tokens per message today. A new
   session should start at about 30-40,000 (**to be measured on one message**). The check "no Boss run in progress"
   stays, because a fresh session is not refused the way a busy one is.
6. Later, when measured need shows it: the space's shared database as the runner's fast local index (queue, capacity,
   claims) beside GitHub; and delivery into a live session (an engine change).

## B. Worktrees: the rule

**No session, no worktree.** A worktree is a workbench that exists exactly as long as one session uses it. The work's
home is GitHub from the moment it is committed. Review and checks happen against GitHub and CI, not in a folder on the
server. (This is one step stricter than Rob's wording: the folder goes when the session ends and its work is proven to
be on GitHub, not after the review. The review does not need the folder, and a fix gets a fresh one in seconds.)

1. **One session, one worktree, one branch.** The runner creates the worktree just before it fires the stage and passes
   the path in the packet. A builder never creates, shares or removes one. Path and branch as today:
   `/data/work/wt/<repo>/<issue>-<chunk>` on `chunk/<issue>-<chunk>`; a retry reuses the name after the old one is gone.
2. **Commit means push.** The builder's whole procedure is: edit, commit, push, end. Evidence of a finished stage is a
   pushed commit; a local commit counts for nothing.
3. **Source only by default.** No dependency folders and no per-worktree code index. Type check and the chunk's test run
   in CI through a single-file workflow. That workflow exists only in testpilot today; rerun and the other repos need
   their own before this rule holds there. (Measured later: if chunks need more than about 1.3 attempts on average, add
   ONE shared, read-only dependency folder per repo and lockfile, linked into worktrees; never a copy per worktree.)
4. **Readers never clone.** Planners, reviewers and the code index read one shared checkout per repo that the runner
   refreshes between sessions; the packet names the commit, so a reader knows what it is looking at. A reviewer who
   needs a pull request's head gets a detached worktree from the runner with the same lifecycle. **Unverified:** the
   code index writes its own folder and a `.gitignore` line into the checkout, so "read-only" needs a decision on where
   the index lives.

## C. End of a session: the removal sequence (nothing is deleted before it is proven saved)

Already built and tested in `tools/factory` (PR #49): the proof that every commit is on a remote branch, the rescue
push, unlinking of links before removal, the register, and the sweep. New in this protocol: salvage of uncommitted
changes, the runner owning creation and removal, and the process check.

Run by the runner on its tick, for every worktree whose session is no longer running. Every step can be repeated;
removal is last; any failure keeps the worktree and reports `KEPT <reason>`.

1. The run is not `running` in the coworker's runs table, and no process has its working folder inside the worktree
   (a command started through Terminal Commander can outlive the session). Otherwise the worktree is not touched.
2. **Uncommitted changes are never deleted.** If the worktree is dirty, everything tracked or untracked-and-not-ignored
   is committed to a salvage ref in the repo's shared clone (`refs/salvage/<branch>/<run id>`), which outlives the
   worktree. Salvage stays on the server and is listed on the job's issue. It is not pushed: an unreviewed stray file
   must not reach GitHub, and one of the repos is public. Salvage is removed only after its job is merged; salvage of a
   job that ended any other way is listed for a decision, like rescue branches, and never removed on a timer.
3. **Committed work is on GitHub or the worktree stays.** Fetch; the branch tip must be contained in a remote branch. If
   not, push it (never forced); if the remote moved, push to `rescue/<branch>-<sha8>`; fetch again and re-check.
4. Unlink any links inside the worktree, remove it, prune, delete the local branch, remove its register entry. All
   under the shared clone's lock.
5. One line in the ledger: removed, where its commits are, where its salvage is.

A retry of a chunk gets a fresh worktree from the branch tip, and its packet names the salvage ref if one exists.

One fix to the sweep that is worth doing at once: a worktree that is clean and whose tip is contained in the default
branch is REMOVE, whatever its pull request says (today `189-1` is kept although its tip is on `main`).

## D. Branches on GitHub

| Branch | Writer | Deleted when |
|---|---|---|
| `job/<issue>` | the runner only (merges of green chunks) | its pull request is merged |
| `chunk/<issue>-<k>` | the one session that owns the chunk | merged into the job branch (checked, not assumed) |
| `rescue/...` | the removal sequence | never automatically while unmerged; listed weekly for a decision |
| anything else (`measure/...`, ad-hoc) | not allowed | listed weekly; not auto-deleted |

No force push anywhere. `main` and `dev` refuse force pushes and deletion by rule on GitHub (checked by `repo-check`).

## E. The shared clone and the disk

- All git commands that change the shared clone (fetch, worktree add and remove, prune) run in the factory scripts
  under one lock. Sessions run git only inside their own worktree. `gc.auto` is off in shared clones; packing runs in
  the nightly pass when no session is live.
- **Disk guard, every tick, zero tokens:** the sweep removes what section C allows; `wt new` already refuses below a
  free-space floor and above a work-folder ceiling; a worktree `KEPT` for more than two hours, or free space under the
  alarm line, becomes one BLOCKED line and one `notify`.
- **Nightly pass, when no session is live:** pack shared clones; trim the package cache; run the stray-clone pass of
  section F; list salvage and rescue refs whose jobs are closed; write the sizes of the work folder, the coworkers'
  workspaces, `/tmp` and the caches into the weekly numbers.
- **Budget from today's measurement:** the factory's own footprint stays under 12 GB (today about 20 GB); alarm at
  16 GB; `wt new` refuses when `/data` has less than 40 GB free.

## F. Clones outside the factory folder

A clone is not a worktree: it has its own object store, several local branches, possibly a stash and a detached HEAD.
So it gets its own procedure, by script, dry run first:

1. Skip any clone a running session or a live process is using.
2. Fetch every local branch, the stash and HEAD from the clone into the shared clone of the same repo, under
   `refs/salvage/clones/<name>/...`. After that, nothing reachable in the clone exists only there.
3. If the tree is dirty, salvage it as in section C.
4. Only then remove the clone, and write one line: what was removed, what was kept as salvage.

**Order, and why this does not run today:** first the shared read checkout exists and reviewers and planners are told to
use it (otherwise they simply clone again); then it is established what uses `/data/work/e2e/mainsrc` and
`/data/work/review/linus-191`; then the dry run is posted; then the pass runs at a moment when no builder or reviewer
session is live.

## G. What makes "work safe" checkable

Each rule has a test in `tools/factory` against a real temp repo with a local remote: a dirty worktree leaves a salvage
ref holding the file and is then removed; an unpushed commit is on the remote before removal; a failed push removes
nothing; a link's target survives; a running session and a live process are skipped; two removals at once do not race;
a retry sees the salvage ref; a clone with an unpushed branch, a stash and a detached HEAD has all three in the shared
clone before it is removed.

Limits, stated plainly:
- Salvage of uncommitted leftovers exists only on the server. A lost server disk loses the uncommitted leftovers of
  sessions that crashed, and nothing that was committed.
- All coworkers push from one account, so "the one session that owns the chunk" is enforced by the runner creating the
  worktree and by the branch name, not by GitHub permissions.
- A coworker can still run `git clone` or delete a folder by hand. On 2026-11-11 a worktree (`terminal-commander/296-1`)
  disappeared and nobody knows how. Until the nightly pass and the trigger bodies make hand-made folders pointless, "the
  removal sequence is the only thing that deletes" is a goal, not a fact.
