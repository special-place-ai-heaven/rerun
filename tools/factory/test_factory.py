"""factory.py tests on a temp clone with a local bare remote. FactoryCase points factory's paths and git at a temp
dir, so nothing touches /data. Run: python -I -m unittest discover -s . -p test_*.py"""
import contextlib, io, os, shutil, stat, subprocess, sys, tempfile, threading, types, unittest
from unittest import mock
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import factory as F

REPO = "rerun"
FULL = "special-place-ai-heaven/" + REPO


def git(cwd, *a, check=True):
    r = subprocess.run(["git", "-C", cwd] + list(a), capture_output=True, text=True)
    if check and r.returncode:
        raise AssertionError("git %s failed: %s" % (" ".join(a), r.stderr))
    return r.stdout.strip()


def write(d, name, text):
    with open(os.path.join(d, name), "w", newline="\n") as f:
        f.write(text)


def _writable(fn, p, *_):
    os.chmod(p, stat.S_IWRITE)  # git object files are read-only, rmtree on Windows needs this
    fn(p)


class FactoryCase(unittest.TestCase):
    """<tmp>/origin.git is a bare remote with branch dev; F.REPOS/rerun is its clone, as ensure_clone leaves it."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="factory-test-")
        self.addCleanup(shutil.rmtree, self.tmp, **({"onexc": _writable} if sys.version_info >= (3, 12) else {"onerror": _writable}))
        saved = {k: getattr(F, k) for k in ("GIT", "WORK", "REPOS", "WT", "STATE")}
        self.addCleanup(lambda: [setattr(F, k, v) for k, v in saved.items()])
        F.GIT, F.WORK = "git", os.path.join(self.tmp, "work")
        F.REPOS, F.WT, F.STATE = F.WORK + "/repos", F.WORK + "/wt", F.WORK + "/state"
        os.makedirs(F.STATE)
        self.origin = os.path.join(self.tmp, "origin.git")
        git(self.tmp, "init", "--quiet", "--bare", self.origin)
        seed = self.make_clone("seed", init=True)
        write(seed, "README.md", "seed\n")
        git(seed, "add", "-A")
        git(seed, "commit", "--quiet", "-m", "seed")
        git(seed, "push", "--quiet", self.origin, "HEAD:refs/heads/dev")
        self.clone = self.make_clone(os.path.join(F.REPOS, REPO))

    def make_clone(self, path, init=False):
        path = os.path.join(self.tmp, path)
        if init:
            git(self.tmp, "init", "--quiet", path)
        else:
            git(self.tmp, "clone", "--quiet", self.origin, path)
        for k, v in (("user.name", "factory-test"), ("user.email", "factory-test@localhost"), ("commit.gpgsign", "false")):
            git(path, "config", k, v)
        return path

    def wt(self, issue="7", chunk="1", base="dev"):
        """What `wt new` leaves behind, without the GitHub calls."""
        path = os.path.join(F.WT, REPO, "%s-%s" % (issue, chunk))
        branch = "chunk/%s-%s" % (issue, chunk)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        git(self.clone, "worktree", "add", "--quiet", "-b", branch, path, "origin/" + base)
        git(self.clone, "config", "branch.%s.factorybase" % branch, base)
        return path

    def commit(self, path, name="work.txt", text="work\n"):
        write(path, name, text)
        git(path, "add", "-A")
        git(path, "commit", "--quiet", "-m", "work on " + name)
        return git(path, "rev-parse", "HEAD")

    def remote_sha(self, ref):
        return git(self.origin, "rev-parse", "--verify", "--quiet", ref, check=False)

    def remote_refs(self, prefix="refs/heads/rescue/"):
        return git(self.origin, "for-each-ref", "--format=%(refname)", prefix)

    def has_branch(self, branch="chunk/7-1"):
        return bool(git(self.clone, "branch", "--list", branch))

    def call(self, fn, argv):
        out, code = io.StringIO(), 0
        with contextlib.redirect_stdout(out):
            try:
                fn(argv)
            except SystemExit as e:
                code = e.code
        return code, out.getvalue()


class WtDoneSaves(FactoryCase):
    """G1: wt done never destroys work."""

    def test_unpushed_commits_are_pushed_to_a_rescue_branch_first(self):
        p = self.wt()
        sha = self.commit(p)
        code, out = self.call(F.cmd_wt, ["done", REPO, "7", "1"])
        self.assertEqual(code, 0, out)
        self.assertEqual(self.remote_sha("refs/heads/rescue/chunk/7-1-" + sha[:8]), sha)
        self.assertIn("RESCUED", out)
        self.assertFalse(os.path.isdir(p))
        self.assertFalse(self.has_branch())

    def test_branch_without_worktree_dir_is_rescued_too(self):
        p = self.wt()
        sha = self.commit(p)
        git(self.clone, "worktree", "remove", "--force", p)
        code, out = self.call(F.cmd_wt, ["done", REPO, "7", "1"])
        self.assertEqual(code, 0, out)
        self.assertEqual(self.remote_sha("refs/heads/rescue/chunk/7-1-" + sha[:8]), sha)
        self.assertFalse(self.has_branch())

    def test_failed_push_refuses_and_deletes_nothing(self):
        p = self.wt()
        self.commit(p)
        open(F.marker(REPO, "chunk/7-1"), "w").close()
        git(self.clone, "config", "remote.origin.pushurl", os.path.join(self.tmp, "nowhere.git"))
        code, out = self.call(F.cmd_wt, ["done", REPO, "7", "1"])
        self.assertNotEqual(code, 0)
        self.assertIn("REFUSED", out)
        self.assertIn("Nothing deleted", out)
        self.assertTrue(os.path.isfile(os.path.join(p, "work.txt")))
        self.assertTrue(self.has_branch())
        self.assertTrue(os.path.exists(F.marker(REPO, "chunk/7-1")))

    def test_uncommitted_changes_refuse_and_deletes_nothing(self):
        p = self.wt()
        write(p, "README.md", "edited\n")
        write(p, "new.txt", "untracked\n")
        code, out = self.call(F.cmd_wt, ["done", REPO, "7", "1"])
        self.assertNotEqual(code, 0)
        self.assertIn("uncommitted changes", out)
        with open(os.path.join(p, "README.md")) as f:
            self.assertEqual(f.read(), "edited\n")
        self.assertTrue(os.path.isfile(os.path.join(p, "new.txt")))
        self.assertTrue(self.has_branch())
        self.assertEqual(self.remote_refs(), "")

    def test_unreachable_origin_refuses_even_when_pushed(self):
        p = self.wt()
        self.commit(p)
        git(p, "push", "--quiet", "origin", "chunk/7-1")
        git(self.clone, "config", "remote.origin.url", os.path.join(self.tmp, "nowhere.git"))
        code, out = self.call(F.cmd_wt, ["done", REPO, "7", "1"])
        self.assertNotEqual(code, 0)
        self.assertIn("cannot fetch origin", out)
        self.assertTrue(os.path.isdir(p))
        self.assertTrue(self.has_branch())

    def test_stale_tracking_ref_of_a_deleted_remote_branch_is_no_proof(self):
        p = self.wt()
        sha = self.commit(p)
        git(p, "push", "--quiet", "origin", "chunk/7-1")
        git(self.origin, "branch", "-D", "chunk/7-1")  # PR closed unmerged, branch deleted on GitHub
        self.assertTrue(git(self.clone, "rev-parse", "--verify", "--quiet", "refs/remotes/origin/chunk/7-1"))
        code, out = self.call(F.cmd_wt, ["done", REPO, "7", "1"])
        self.assertEqual(code, 0, out)
        self.assertEqual(self.remote_sha("refs/heads/rescue/chunk/7-1-" + sha[:8]), sha)
        self.assertFalse(os.path.isdir(p))


def make_link(link, target):
    if os.name == "nt":  # a junction needs no symlink privilege; it is the case that once emptied a target
        subprocess.run(["cmd", "/c", "mklink", "/J", os.path.normpath(link), os.path.normpath(target)], check=True, capture_output=True)
    else:
        os.symlink(target, link)


class WtDoneCleans(FactoryCase):
    """G2: saved or merged work is still cleaned up, links inside the worktree are only unlinked."""

    def assert_gone(self, p, out):
        self.assertIn("removed worktree", out)
        self.assertFalse(os.path.isdir(p))
        self.assertFalse(self.has_branch())
        self.assertNotIn(os.path.basename(p), git(self.clone, "worktree", "list", "--porcelain"))
        self.assertFalse(os.path.exists(F.marker(REPO, "chunk/7-1")))
        self.assertEqual(self.remote_refs(), "")

    def test_clean_pushed_worktree_is_removed_and_link_targets_survive(self):
        p = self.wt()
        self.commit(p)
        git(p, "push", "--quiet", "origin", "chunk/7-1")
        shared = os.path.join(self.tmp, "shared_node_modules")
        os.makedirs(os.path.join(shared, "pkg"))
        write(shared, "keep.txt", "keep\n")
        with open(os.path.join(self.clone, ".git", "info", "exclude"), "a") as f:
            f.write("\nnode_modules\n")
        os.makedirs(os.path.join(p, "sub"))
        make_link(os.path.join(p, "node_modules"), shared)
        make_link(os.path.join(p, "sub", "node_modules"), shared)
        open(F.marker(REPO, "chunk/7-1"), "w").close()
        code, out = self.call(F.cmd_wt, ["done", REPO, "7", "1"])
        self.assertEqual(code, 0, out)
        self.assert_gone(p, out)
        self.assertTrue(os.path.isfile(os.path.join(shared, "keep.txt")))
        self.assertTrue(os.path.isdir(os.path.join(shared, "pkg")))

    def test_merge_dev_cleans_up_after_merge_and_remote_branch_delete(self):
        p = self.wt()
        sha = self.commit(p)
        git(p, "push", "--quiet", "origin", "chunk/7-1")
        code, out = self.merge_dev(sha)
        self.assertEqual(code, 0, out)
        self.assertIn("MERGED", out)
        self.assertEqual(self.remote_sha("refs/heads/chunk/7-1"), "")
        self.assert_gone(p, out)

    def test_merge_dev_keeps_a_dirty_worktree_and_still_reports_the_merge(self):
        p = self.wt()
        sha = self.commit(p)
        git(p, "push", "--quiet", "origin", "chunk/7-1")
        write(p, "left.txt", "left behind\n")
        code, out = self.merge_dev(sha)
        self.assertEqual(code, 0, out)
        self.assertIn("MERGED", out)
        self.assertIn("KEPT", out)
        self.assertTrue(os.path.isfile(os.path.join(p, "left.txt")))

    def merge_dev(self, sha):
        """merge-dev with GitHub faked: the merge and the branch delete happen on the bare remote."""
        merger = self.make_clone("merger")
        pr = {"base": {"ref": "dev"}, "head": {"ref": "chunk/7-1", "sha": sha}, "state": "open", "draft": False, "merge_commit_sha": "0" * 40}
        real_run = F.run

        def fake_api(path, *a, **k):
            return [] if path.endswith("/files?per_page=100") else {"default_branch": "main"} if path == "repos/" + FULL else pr

        def fake_run(cmd, *a, **k):
            if cmd[0] != F.GH:
                return real_run(cmd, *a, **k)
            if cmd[1:3] == ["pr", "merge"]:
                git(merger, "fetch", "--quiet", "origin")
                git(merger, "checkout", "--quiet", "-B", "dev", "origin/dev")
                git(merger, "merge", "--quiet", "--no-ff", "-m", "merge", "origin/chunk/7-1")
                git(merger, "push", "--quiet", "origin", "dev")
            elif "DELETE" in cmd:
                git(self.origin, "branch", "-D", "chunk/7-1")
            return subprocess.CompletedProcess(cmd, 0, "", "")

        green = [{"name": "ci", "status": "completed", "conclusion": "success", "id": 1, "url": ""}]
        with mock.patch.object(F, "api", fake_api), mock.patch.object(F, "run", fake_run), mock.patch.object(F, "checks", lambda *a: green):
            return self.call(F.cmd_merge_dev, [REPO, "9"])


class BuilderCap(FactoryCase):
    """G3: at most MAX_BUILDERS active worktrees, also under two simultaneous calls and on `pr-open --fix`. G4: memory floor."""

    def setUp(self):
        super().setUp()
        for k, v in (("MAX_BUILDERS", 2), ("MEMINFO", os.path.join(self.tmp, "no-meminfo")), ("LOCK_WAIT_S", 30)):
            p = mock.patch.object(F, k, v)
            p.start()
            self.addCleanup(p.stop)
        self.lock = os.path.join(F.STATE, "builders.lock")

    @contextlib.contextmanager
    def wt_new_fakes(self, before_clone=lambda: None):
        """`wt new` with GitHub, /data and du faked; ensure_clone returns the test clone after before_clone()."""
        def fake_clone(full):
            before_clone()
            return self.clone
        with mock.patch.object(F.shutil, "disk_usage", lambda p: types.SimpleNamespace(free=1000 * 2**30)), \
                mock.patch.object(F, "du_gb", lambda p: 0.0), mock.patch.object(F, "api", lambda *a, **k: {"default_branch": "main"}), \
                mock.patch.object(F, "ensure_clone", fake_clone):
            yield

    def new(self, chunk):
        with self.wt_new_fakes():
            return self.call(F.cmd_wt, ["new", REPO, "7", chunk])

    def made(self, chunk):
        return os.path.isdir(os.path.join(F.WT, REPO, "7-" + chunk))

    def test_wt_new_below_the_cap_creates_the_worktree(self):
        self.wt(chunk="1")
        code, out = self.new("3")
        self.assertEqual(code, 0, out)
        self.assertIn("WORKTREE", out)
        self.assertTrue(self.made("3"))
        self.assertFalse(os.path.exists(self.lock))

    def test_wt_new_at_the_cap_refuses(self):
        self.wt(chunk="1")
        self.wt(chunk="2")
        code, out = self.new("3")
        self.assertEqual(code, 2, out)
        self.assertIn("builders are already active", out)
        self.assertFalse(self.made("3"))

    def test_green_worktree_does_not_count(self):
        self.wt(chunk="1")
        self.wt(chunk="2")
        open(F.marker(REPO, "chunk/7-2"), "w").close()
        code, out = self.new("3")
        self.assertEqual(code, 0, out)

    def test_two_simultaneous_wt_new_create_only_one(self):
        self.wt(chunk="1")
        both_past_first_check = threading.Barrier(2, timeout=20)
        codes, out = {}, io.StringIO()

        def one(chunk):
            try:
                F.cmd_wt(["new", REPO, "7", chunk])
                codes[chunk] = 0
            except SystemExit as e:
                codes[chunk] = e.code

        with self.wt_new_fakes(before_clone=both_past_first_check.wait), contextlib.redirect_stdout(out):
            ts = [threading.Thread(target=one, args=(c,)) for c in ("3", "4")]
            [t.start() for t in ts]
            [t.join(60) for t in ts]
        self.assertEqual(sorted(codes.values()), [0, 2], out.getvalue())
        self.assertEqual(self.made("3") + self.made("4"), 1, out.getvalue())
        self.assertIn("builders are already active", out.getvalue())
        self.assertFalse(os.path.exists(self.lock))

    def test_busy_lock_refuses_and_stale_lock_is_taken_over(self):
        def grab(_):
            with F.builder_lock():
                pass
        with mock.patch.object(F, "LOCK_WAIT_S", 0.3), F.builder_lock():
            code, out = self.call(grab, [])
        self.assertEqual(code, 2, out)
        self.assertIn("holds", out)
        self.assertFalse(os.path.exists(self.lock))
        open(self.lock, "w").close()
        old = os.path.getmtime(self.lock) - F.LOCK_STALE_S - 10
        os.utime(self.lock, (old, old))
        with mock.patch.object(F, "LOCK_WAIT_S", 0.3):
            code, out = self.call(grab, [])
        self.assertEqual(code, 0, out)
        self.assertFalse(os.path.exists(self.lock))

    def test_lock_is_released_when_the_holder_refuses(self):
        def refuse(_):
            with F.builder_lock():
                F.die("inside the lock")
        code, out = self.call(refuse, [])
        self.assertEqual(code, 2, out)
        self.assertFalse(os.path.exists(self.lock))

    def fix(self, chunk):
        """`pr-open --fix` in worktree 7-<chunk>, its PR already open; GitHub faked, the push goes to the bare remote."""
        p = os.path.join(F.WT, REPO, "7-" + chunk)
        real_run = F.run

        def fake_run(cmd, *a, **k):
            if cmd[0] != F.GH:
                return real_run(cmd, *a, **k)
            return subprocess.CompletedProcess(cmd, 0, '[{"number": 9, "url": "https://github.com/%s/pull/9"}]' % FULL, "")

        ctx = (p, FULL, "chunk/7-" + chunk, "dev", "7", chunk)
        with mock.patch.object(F, "wt_context", lambda: ctx), mock.patch.object(F, "run", fake_run):
            return self.call(F.cmd_pr_open, ["--fix"])

    def test_fix_on_a_green_worktree_at_the_cap_refuses_before_the_push(self):
        sha = self.commit(self.wt(chunk="1"))
        open(F.marker(REPO, "chunk/7-1"), "w").close()
        self.wt(chunk="2")
        self.wt(chunk="3")
        code, out = self.fix("1")
        self.assertEqual(code, 2, out)
        self.assertIn("builders are already active", out)
        self.assertTrue(os.path.exists(F.marker(REPO, "chunk/7-1")))
        self.assertNotEqual(self.remote_sha("refs/heads/chunk/7-1"), sha)
        self.assertFalse(os.path.exists(self.lock))

    def test_fix_on_a_green_worktree_below_the_cap_turns_it_active(self):
        sha = self.commit(self.wt(chunk="1"))
        open(F.marker(REPO, "chunk/7-1"), "w").close()
        self.wt(chunk="2")
        code, out = self.fix("1")
        self.assertEqual(code, 0, out)
        self.assertIn("PUSHED fix to", out)
        self.assertEqual(self.remote_sha("refs/heads/chunk/7-1"), sha)
        self.assertFalse(os.path.exists(F.marker(REPO, "chunk/7-1")))

    def test_fix_on_an_active_worktree_needs_no_free_slot(self):
        sha = self.commit(self.wt(chunk="1"))
        self.wt(chunk="2")
        self.wt(chunk="3")
        code, out = self.fix("1")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.remote_sha("refs/heads/chunk/7-1"), sha)

    def meminfo(self, kb):
        F.MEMINFO = os.path.join(self.tmp, "meminfo")
        write(self.tmp, "meminfo", "MemTotal:       16384000 kB\nMemFree:          100000 kB\nMemAvailable:   %8d kB\n" % kb)

    def test_meminfo_reader(self):
        self.assertIsNone(F.avail_mem_gb())  # no /proc/meminfo (Windows, macOS): skipped, not failed
        self.meminfo(2 * 1048576)
        self.assertEqual(F.avail_mem_gb(), 2.0)

    def test_wt_new_refuses_below_the_memory_floor(self):
        self.meminfo(int((F.MIN_FREE_MEM_GB - 0.5) * 1048576))
        code, out = self.new("3")
        self.assertEqual(code, 2, out)
        self.assertIn("memory", out)
        self.assertFalse(self.made("3"))

    def test_wt_new_above_the_memory_floor_and_without_meminfo_proceeds(self):
        self.assertEqual(self.new("3")[0], 0)
        self.meminfo(int((F.MIN_FREE_MEM_GB + 1) * 1048576))
        code, out = self.new("4")
        self.assertEqual(code, 0, out)
        self.assertTrue(self.made("4"))


class WorkOverride(unittest.TestCase):
    def paths(self, env):
        code = "import sys; sys.path.insert(0, %r); import factory as F; print(F.WORK, F.REPOS, F.WT, F.STATE)" % HERE
        e = {k: v for k, v in os.environ.items() if k != "FACTORY_WORK"}
        e.update(env)
        return subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, env=e, check=True).stdout.split()

    def test_factory_work_moves_every_path_and_default_stays(self):
        self.assertEqual(self.paths({"FACTORY_WORK": "/tmp/fw"}), ["/tmp/fw", "/tmp/fw/repos", "/tmp/fw/wt", "/tmp/fw/state"])
        self.assertEqual(self.paths({}), ["/data/work", "/data/work/repos", "/data/work/wt", "/data/work/state"])

    def test_gate_has_no_own_work_path(self):
        with open(os.path.join(HERE, "gate.py"), encoding="utf-8") as f:
            self.assertNotIn("/data/work", f.read())


if __name__ == "__main__":
    unittest.main()
