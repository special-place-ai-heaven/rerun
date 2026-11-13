import contextlib, gc, io, json, os, sys, tempfile, unittest, unittest.mock, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dispatch as D

HEAD = "abcdef1234567890"
PR_LINE = "Done.\nPR: https://github.com/o/r/pull/42"


class World:
    """Fake account server and gh. A coworker run stays running until the test finishes it."""

    def __init__(self, issues=None):
        self.issues = issues if issues is not None else [{"number": 5, "title": "Fix x", "body": "", "comments": []}]
        self.sends, self.runs, self.order = [], {}, []
        self.gh_calls, self.merges = [], []
        self.workflows, self.pr_state, self.clock = {}, "OPEN", 1000.0
        self.cut_off_next_send = False
        self.mergeable, self.unlabelled = "MERGEABLE", set()
        self.open_numbers = {7, 129}

    def account(self, tool, args):
        if tool == "send_message":
            rid = "run%d" % (len(self.sends) + 1)
            self.sends.append((args["agentId"], args["message"], args["waitSeconds"]))
            self.runs[rid] = {"status": "running"}
            self.order.append((rid, args["agentId"]))
            if self.cut_off_next_send:
                self.cut_off_next_send = False
                raise D.Error("account send_message failed: TimeoutError")
            return {"runId": rid, "status": "running"}
        return dict(self.runs[args["runId"]], runId=args["runId"])

    def finish(self, agent, output, status="done"):
        rid = [r for r, a in self.order if a == agent][-1]
        self.runs[rid] = {"status": status, "output": output, "error": "boom" if status == "error" else None}

    def issue(self, n):
        return next(i for i in self.issues if i["number"] == int(n))

    def gh(self, args):
        a = list(args)
        self.gh_calls.append(a)
        if a[:2] == ["issue", "list"] and "--label" not in a:
            return json.dumps([{"number": n} for n in sorted(self.open_numbers)])
        if a[:2] == ["issue", "list"]:
            return json.dumps([{"number": i["number"], "title": i["title"], "body": i["body"]} for i in self.issues if i["number"] not in self.unlabelled])
        if a[:2] == ["issue", "view"]:
            i = self.issue(a[2])
            return json.dumps({"body": i["body"], "comments": [{"body": c} for c in i["comments"]]})
        if a[:2] == ["issue", "comment"]:
            self.issue(a[2])["comments"].append(a[a.index("--body") + 1])
            return ""
        if a[:2] == ["issue", "edit"]:
            if "--remove-label" in a:
                self.unlabelled.add(int(a[2]))
            return ""
        if a[:2] == ["pr", "view"]:
            return json.dumps({"headRefOid": HEAD, "state": self.pr_state, "mergeable": self.mergeable})
        if a[0] == "api":
            sha = a[1].split("head_sha=")[1].split("&")[0]
            return json.dumps({"workflow_runs": self.workflows.get(sha, [])})
        if a[:2] == ["pr", "merge"]:
            self.merges.append(a)
            self.pr_state = "MERGED"
            return ""
        raise AssertionError("unexpected gh call %r" % a)

    def edits(self, n):
        return [c for c in self.gh_calls if c[:3] == ["issue", "edit", str(n)]]


def wf(name, conclusion, status="completed", wid=1):
    return {"name": name, "workflow_id": wid, "status": status, "conclusion": conclusion}


class Base(unittest.TestCase):
    builders = ["b1", "b2"]

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.w = World()
        self.cfg = {"repo": "o/r", "label": "factory", "max_jobs": 8, "checks_timeout_s": 1800, "auto_plan_marker": True,
                    "state_file": os.path.join(self.dir.name, "state.json"),
                    "builders": [{"id": b, "name": b.upper()} for b in self.builders],
                    "reviewers": [{"id": r, "name": r.upper()} for r in ("r1", "r2")]}
        self.out = io.StringIO()

    def new(self):
        return D.Dispatcher(self.cfg, self.w.account, self.w.gh, now=lambda: self.w.clock)

    def tick(self, n=1, fresh=False):
        """n passes; fresh builds a new dispatcher from the state file before every pass, as after a restart."""
        d = getattr(self, "d", None)
        for _ in range(n):
            if fresh or d is None:
                d = self.d = self.new()
            with contextlib.redirect_stdout(self.out):
                d.once()

    def state(self, n=5):
        with open(self.cfg["state_file"]) as f:
            return json.load(f)["jobs"][str(n)]["state"]

    def to_review(self):
        self.tick()
        self.w.finish("b1", PR_LINE)
        self.tick(2)

    def to_checks(self):
        self.to_review()
        self.w.finish("r1", "ok\nVERDICT: ACCEPT @abcdef1")
        self.tick()


class Intake(Base):
    def test_labelled_issue_taken_and_build_goes_to_a_free_builder(self):
        self.tick()
        self.assertEqual(len(self.w.sends), 1)
        agent, msg, wait = self.w.sends[0]
        self.assertEqual((agent, wait), ("b1", D.WAIT_S))
        self.assertIn('rerun #5, "Fix x"', msg)
        self.assertEqual(self.w.issue(5)["comments"], ["SMALL FIX: taken by the factory dispatcher on the owner's label."])
        self.assertEqual(self.state(), "building")

    def test_no_plan_comment_when_the_issue_has_a_plan_line(self):
        self.w.issues[0]["body"] = "intro\nPLAN READY: three chunks"
        self.tick()
        self.assertEqual(self.w.issue(5)["comments"], [])
        self.assertEqual(len(self.w.sends), 1)

    def test_max_jobs_limits_intake(self):
        self.w.issues = [{"number": n, "title": "t%d" % n, "body": "SMALL FIX", "comments": []} for n in (1, 2, 3)]
        self.cfg["max_jobs"] = 2
        self.tick()
        with open(self.cfg["state_file"]) as f:
            self.assertEqual(sorted(json.load(f)["jobs"]), ["1", "2"])


class Depends(Base):
    def job(self, n, line, title=None):
        return {"number": n, "title": title or "t%d" % n, "body": "intro\n" + line + "\nmore", "comments": []}

    def open_calls(self):
        return [c for c in self.w.gh_calls if c[:2] == ["issue", "list"] and "--label" not in c]

    def test_waits_while_dependency_is_open_then_is_taken(self):
        self.w.issues = [self.job(5, "**Depends on**: #7")]
        self.tick(3)
        self.assertEqual(self.w.issue(5)["comments"], [])
        self.assertEqual(self.out.getvalue().count("waits on #7"), 1)
        with open(self.cfg["state_file"]) as f:
            self.assertEqual(json.load(f)["jobs"], {})
        self.w.open_numbers.discard(7)
        self.tick()
        self.assertEqual(self.state(), "building")
        self.assertEqual(len(self.w.sends), 1)
        with open(self.cfg["state_file"]) as f:
            self.assertNotIn("5", json.load(f).get("waiting", {}))

    def test_waiting_line_not_repeated_after_a_restart(self):
        self.w.issues = [self.job(5, "Depends on: #7")]
        self.tick(3, fresh=True)
        self.assertEqual(self.out.getvalue().count("waits on #7"), 1)

    def test_none_and_no_line_are_taken_as_before(self):
        self.w.issues = [self.job(5, "**Depends on**: none"), {"number": 6, "title": "t6", "body": "", "comments": []}]
        self.tick()
        self.assertEqual(self.state(5), "building")
        self.assertEqual(self.state(6), "building")
        self.assertEqual(self.open_calls(), [])

    def test_waiting_issue_does_not_use_room(self):
        self.w.issues = [self.job(5, "**Depends on**: #7"), self.job(6, "**Depends on**: none")]
        self.cfg["max_jobs"] = 1
        self.tick()
        self.assertEqual(self.state(6), "building")
        with open(self.cfg["state_file"]) as f:
            self.assertEqual(sorted(json.load(f)["jobs"]), ["6"])

    def test_open_issues_read_once_per_pass(self):
        self.w.issues = [self.job(5, "**Depends on**: #7"), self.job(6, "**Depends on**: #129")]
        self.tick()
        self.assertEqual(len(self.open_calls()), 1)

    def test_partial_dependencies_log_only_the_open_one(self):
        self.w.issues = [self.job(5, "**Depends on**: #135, #129 (a note in brackets)")]
        self.tick()
        self.assertIn("waits on #129", self.out.getvalue())
        self.assertNotIn("#135", self.out.getvalue())
        self.assertEqual(self.w.sends, [])


class OneBuilder(Base):
    builders = ["b1"]

    def test_two_jobs_never_share_a_coworker(self):
        self.w.issues.append({"number": 6, "title": "Fix y", "body": "", "comments": []})
        self.tick(3)
        self.assertEqual([s[0] for s in self.w.sends], ["b1"])  # job 6 waits while b1 builds job 5
        self.assertEqual(self.state(6), "queued")
        self.w.finish("b1", PR_LINE)
        self.tick()
        self.assertEqual([s[0] for s in self.w.sends], ["b1", "b1"])
        self.assertIn("rerun #6", self.w.sends[1][1])

    def test_fix_waits_for_its_builder(self):
        self.w.issues.append({"number": 6, "title": "Fix y", "body": "", "comments": []})
        self.to_review()  # b1 is now building job 6
        self.w.finish("r1", "VERDICT: REJECT @abcdef1: wrong")
        self.tick(2)
        self.assertEqual(self.state(), "fix_wait")
        self.assertEqual(len([s for s in self.w.sends if s[0] == "b1"]), 2)
        self.w.finish("b1", "BLOCKED: no")  # job 6 ends, b1 is free on the next pass
        self.tick(2)
        self.assertEqual(self.state(), "fixing")
        self.assertIn("One fix round", self.w.sends[-1][1])


class Flow(Base):
    def test_pr_line_parsed_and_review_sent_with_the_head_commit(self):
        self.to_review()
        agent, msg, _ = self.w.sends[-1]
        self.assertEqual(agent, "r1")
        self.assertIn("pull request #42 of rerun, for job #5", msg)
        self.assertIn("at commit abcdef1.", msg)
        self.assertEqual(self.state(), "reviewing")

    def test_no_pr_line_blocks_with_the_last_line(self):
        self.tick()
        self.w.finish("b1", "tried\nBLOCKED: the issue names no file")
        self.tick()
        self.assertEqual(self.state(), "blocked")
        self.assertIn("BLOCKED: the issue names no file", self.w.issue(5)["comments"][-1])

    def test_accept_then_green_runs_merge_once_at_that_commit(self):
        self.to_checks()
        self.tick()
        self.assertEqual(self.w.merges, [])  # no runs yet: wait
        self.w.workflows[HEAD] = [wf("ci", None, "in_progress")]
        self.tick()
        self.assertEqual(self.w.merges, [])
        self.w.workflows[HEAD] = [wf("ci", "success"), wf("docs", "skipped", wid=2), wf("ci", "cancelled")]
        self.tick(3)
        self.assertEqual(self.w.merges, [["pr", "merge", "42", "-R", "o/r", "--merge", "--match-head-commit", HEAD, "--delete-branch"]])
        self.assertEqual(self.state(), "merged")
        self.assertIn("merged pull request #42", self.w.issue(5)["comments"][-1])
        self.assertEqual(self.w.edits(5), [["issue", "edit", "5", "-R", "o/r", "--remove-label", "factory", "--add-label", "factory-done"]])

    def test_failed_workflow_run_blocks_the_merge(self):
        self.to_checks()
        self.w.workflows[HEAD] = [wf("ci", "success", wid=1), wf("e2e", "failure", wid=2)]
        self.tick(2)
        self.assertEqual(self.w.merges, [])
        self.assertEqual(self.state(), "failed")
        self.assertIn("e2e", self.w.issue(5)["comments"][-1])
        self.assertEqual(self.w.edits(5)[0][-1], "factory-blocked")

    def test_refused_merge_ends_the_job(self):
        self.to_checks()
        self.w.workflows[HEAD] = [wf("ci", "success")]
        gh, merges = self.w.gh, []
        def merge_refused(args):
            if list(args[:2]) == ["pr", "merge"]:
                merges.append(list(args))
                raise D.Error("gh pr merge failed: exit 1")
            return gh(args)
        self.w.gh = merge_refused
        self.tick(3, fresh=True)
        self.assertEqual(len(merges), 1)
        self.assertEqual(self.state(), "failed")
        self.assertIn("merge of #42 at abcdef1 refused", self.w.issue(5)["comments"][-1])
        self.assertEqual(self.w.edits(5)[0][-1], "factory-blocked")

    def test_cancelled_run_without_a_success_of_its_workflow_does_not_merge(self):
        self.to_checks()
        self.w.workflows[HEAD] = [wf("ci", "success", wid=1), wf("e2e", "cancelled", wid=2)]
        self.tick()
        self.assertEqual(self.w.merges, [])
        self.w.clock += 1801
        self.tick()
        self.assertEqual(self.state(), "failed")
        self.assertIn("e2e cancelled", self.w.issue(5)["comments"][-1])

    def test_reject_gives_one_fix_round_and_a_second_reject_ends_the_job(self):
        self.to_review()
        self.w.finish("r1", "bad\nVERDICT: REJECT @abcdef1: wrong sum")
        self.tick(2)
        fix = self.w.sends[-1]
        self.assertEqual(fix[0], "b1")
        self.assertIn("VERDICT: REJECT @abcdef1: wrong sum", fix[1])
        self.w.finish("b1", "PUSHED: 1234567")
        self.tick(2)
        self.assertEqual(self.w.sends[-1][0], "r1")
        self.assertIn("One review", self.w.sends[-1][1])
        self.w.finish("r1", "VERDICT: REJECT @abcdef1: still wrong")
        self.tick(3)
        self.assertEqual(self.state(), "rejected")
        self.assertEqual(len([s for s in self.w.sends if "One fix round" in s[1]]), 1)
        self.assertEqual(len(self.w.sends), 4)
        self.assertIn("still wrong", self.w.issue(5)["comments"][-1])

    def test_no_verdict_line_rejects(self):
        self.to_review()
        self.w.finish("r1", "I looked at it.")
        self.tick()
        self.assertEqual(self.state(), "rejected")

    def test_run_in_error_is_sent_again_once(self):
        self.tick()
        self.w.finish("b1", "", status="error")
        self.tick()
        self.assertEqual(len(self.w.sends), 2)
        self.assertEqual(self.w.sends[0][:2], self.w.sends[1][:2])
        self.assertEqual(self.state(), "building")
        self.w.finish("b1", "", status="error")
        self.tick(2)
        self.assertEqual(len(self.w.sends), 2)
        self.assertEqual(self.state(), "failed")


class Restart(Base):
    def test_fresh_dispatcher_every_pass_sends_each_step_once(self):
        self.tick(2, fresh=True)
        self.w.finish("b1", PR_LINE)
        self.tick(3, fresh=True)
        self.w.finish("r1", "VERDICT: REJECT @abcdef1: x")
        self.tick(3, fresh=True)
        self.w.finish("b1", "PUSHED: 1234567")
        self.tick(3, fresh=True)
        self.w.finish("r1", "VERDICT: ACCEPT @abcdef1")
        self.w.workflows[HEAD] = [wf("ci", "success")]
        self.tick(4, fresh=True)
        self.assertEqual([s[0] for s in self.w.sends], ["b1", "r1", "b1", "r1"])
        self.assertEqual(len(self.w.merges), 1)
        self.assertEqual(len(self.w.issue(5)["comments"]), 2)  # plan line and the end comment
        self.assertEqual(len(self.w.edits(5)), 1)

    def test_send_cut_off_after_it_went_out_is_never_sent_again(self):
        self.w.cut_off_next_send = True
        self.tick()
        self.tick(3, fresh=True)
        self.assertEqual(len(self.w.sends), 1)
        self.assertEqual(self.state(), "blocked")
        self.assertIn("not sent again", self.w.issue(5)["comments"][-1])

    def test_merge_done_before_a_restart_is_not_repeated(self):
        self.to_checks()
        self.w.workflows[HEAD] = [wf("ci", "success")]
        self.w.pr_state = "MERGED"  # merged, but the state file was not written
        gh = self.w.gh
        def merge_fails(args):
            if list(args[:2]) == ["pr", "merge"]:
                raise D.Error("gh pr merge failed: exit 1")
            return gh(args)
        self.w.gh = merge_fails
        self.tick(fresh=True)
        self.assertEqual(self.state(), "merged")


class Report(Base):
    def test_failed_relabel_is_retried_without_a_second_comment(self):
        self.tick()
        self.w.finish("b1", "BLOCKED: no")
        gh, fails = self.w.gh, [1]
        def edit_fails_once(args):
            if list(args[:2]) == ["issue", "edit"] and fails:
                fails.pop()
                raise D.Error("gh issue edit failed: exit 1")
            return gh(args)
        self.w.gh = edit_fails_once
        self.tick(3, fresh=True)
        self.assertEqual(len(self.w.issue(5)["comments"]), 2)
        self.assertEqual(len(self.w.edits(5)), 1)
        self.assertIn("stopped this job: blocked. Pull request: none.", self.w.issue(5)["comments"][-1])


class Secrets(Base):
    KEY, TOKEN = "acct-key-SECRET-0123456789", "ghp_SECRETtoken0123456789"

    def test_no_key_or_token_in_anything_printed(self):
        seen, ran = [], []

        class Resp:
            def __init__(self, text):
                self.text = text
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False
            def read(self):
                return self.text.encode()

        def opener(req, timeout):
            seen.append(dict(req.header_items()))
            args = json.loads(req.data)["params"]["arguments"]
            if args.get("agentId") == "b2":
                raise ValueError("Invalid header value %r" % self.KEY)  # what http.client says of a bad header
            if args.get("agentId") == "b1":
                raise urllib.error.HTTPError(req.full_url, 500, "echo " + self.KEY, {}, io.BytesIO(self.KEY.encode()))
            fake = self.w.account(json.loads(req.data)["params"]["name"], args)
            body = {"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": json.dumps(fake)}]}}
            return Resp("event: message\ndata: " + json.dumps(body) + "\n\n")

        class Proc:
            def __init__(self, rc, out):
                self.returncode, self.stdout, self.stderr = rc, out, "error " + Secrets.TOKEN

        fail_once = [1]

        def run(argv, capture_output, text, env, timeout):
            ran.append((argv, env))
            if argv[1:3] == ["issue", "comment"] and fail_once:
                fail_once.pop()
                return Proc(1, "")
            return Proc(0, self.w.gh(argv[1:]))

        self.cfg["builders"].reverse()  # job 5 goes to b2 (a ValueError), job 6 to b1 (HTTP 500)
        self.w.issues.append({"number": 6, "title": "Fix y", "body": "SMALL FIX", "comments": []})
        err = io.StringIO()
        d = D.Dispatcher(self.cfg, D.make_account("https://acct.example/mcp", self.KEY, opener), D.make_gh(self.TOKEN, run))
        with contextlib.redirect_stdout(self.out), contextlib.redirect_stderr(err):
            for _ in range(3):
                d.once()
            gc.collect()  # Python's warning about an unclosed HTTP error repeats its text, whenever it is collected
        printed = self.out.getvalue() + err.getvalue()
        self.assertIn("ValueError", printed)
        self.assertIn("HTTP 500", printed)
        self.assertIn("exit 1", printed)
        self.assertNotIn(self.KEY, printed)
        self.assertNotIn(self.TOKEN, printed)
        self.assertTrue(seen and all(h["Authorization"] == "Bearer " + self.KEY for h in seen))
        self.assertTrue(ran and all(e["GH_TOKEN"] == self.TOKEN and self.TOKEN not in " ".join(a) for a, e in ran))
        with open(self.cfg["state_file"]) as f:
            self.assertNotIn(self.TOKEN, f.read())

    def test_status_needs_no_key_files(self):
        self.tick()
        saved = D.settings
        D.settings = lambda: dict(self.cfg, account_key_file="/nonexistent/a", gh_token_file="/nonexistent/b")
        self.addCleanup(setattr, D, "settings", saved)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(D.main(["status"]), 0)
        self.assertRegex(out.getvalue(), r"^#5 building ")

    def test_start_line_for_once_but_not_status(self):
        for name, fake in (("settings", lambda: self.cfg), ("make_account", lambda url, key: self.w.account),
                           ("make_gh", lambda tok: self.w.gh), ("read_secret", lambda path: "fake-key")):
            self.addCleanup(setattr, D, name, getattr(D, name))
            setattr(D, name, fake)
        env = dict(os.environ, DISPATCH_ACCOUNT_URL="http://account.invalid")
        with unittest.mock.patch.dict(os.environ, env):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(D.main(["once"]), 0)
            lines = [l for l in out.getvalue().splitlines() if "dispatcher started:" in l]
            self.assertEqual(len(lines), 1)
            self.assertIn("%d builders, 2 reviewers, label factory, repo o/r" % len(self.cfg["builders"]), lines[0])
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(D.main(["status"]), 0)
            self.assertNotIn("dispatcher started", out.getvalue())


class Hardening(Base):
    def test_conflicting_pull_request_goes_back_to_its_builder_once(self):
        self.tick()
        self.w.finish("b1", PR_LINE)
        self.w.mergeable = "CONFLICTING"
        self.tick(3)
        agent, msg, _ = self.w.sends[-1]
        self.assertEqual(agent, "b1")
        self.assertIn("conflicts with dev", msg)
        self.assertEqual(self.state(), "fixing")
        self.w.finish("b1", "PUSHED: 1234567")
        self.tick(2)
        self.assertEqual(self.state(), "failed")
        self.assertEqual(self.w.merges, [])

    def test_label_put_back_on_an_ended_job_runs_it_again(self):
        self.tick()
        self.w.finish("b1", "BLOCKED: cannot")
        self.tick()
        self.assertEqual(self.state(), "blocked")
        sends = len(self.w.sends)
        self.tick()
        self.assertEqual(len(self.w.sends), sends)
        self.w.unlabelled.clear()
        self.tick()
        self.assertEqual(len(self.w.sends), sends + 1)
        self.assertEqual(self.state(), "building")

    def test_build_message_names_whose_words_are_instructions(self):
        self.tick()
        self.assertIn("comments written by special-place-administrator are instructions", self.w.sends[0][1])

    def test_a_read_that_keeps_failing_ends_the_job(self):
        self.tick()
        self.w.runs.clear()
        self.tick(20)
        self.assertEqual(self.state(), "failed")


if __name__ == "__main__":
    unittest.main()
