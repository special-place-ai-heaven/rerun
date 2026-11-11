import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate as G

T = "2026-11-10T23:00:00.0000000Z "
NEXT = T + "        FAIL [   0.071s] (  3/9) terminal_commander_daemon bucket_wait::wake_on_match\n" + \
       T + "        PASS [   0.010s] ( 4/9) terminal_commander_core bucket::tests::fills\n"
CARGO = T + "     Running tests/bucket_wait.rs (target/debug/deps/bucket_wait-abc)\n" + T + "test wake_on_match ... FAILED\n" + \
        T + "     Running unittests src/lib.rs (target/debug/deps/x-1)\n" + T + "test bucket::tests::fills ... ok\n"
JEST = T + "PASS packages/a/src/x.spec.ts\n" + T + "FAIL src/y.test.ts\n"
NEXT = T + "        FAIL [   0.071s] (  3/9) terminal_commander_daemon::bucket_wait wake_on_match\n" + \
       T + "        FAIL [   0.010s] ( 4/9) terminal_commander_core bucket::tests::fills\n"
class G_(unittest.TestCase):
    def test_nextest(self):
        r = G.results(NEXT)
        self.assertEqual(r[0][:3], ("nextest-it", "terminal_commander_daemon::bucket_wait::wake_on_match", False))
        self.assertTrue(G.test_hit("crates/daemon/tests/bucket_wait.rs", r[0][1], r[0][0]))
        self.assertFalse(G.test_hit("crates/daemon/tests/other.rs", r[0][1], r[0][0]))
        self.assertFalse(G.test_hit("crates/core/tests/bucket.rs", r[1][1], r[1][0]))  # unit result is not an integration binary
        self.assertTrue(G.test_hit("crates/core/src/bucket.rs", r[1][1], r[1][0]))
        self.assertFalse(G.test_hit("crates/core/src/bucket.rs", r[0][1], r[0][0]))
    def test_cargo(self):
        r = G.results(CARGO)
        self.assertEqual(r[0][:2], ("cargo-it", "bucket_wait::wake_on_match"))
        self.assertTrue(G.test_hit("crates/daemon/tests/bucket_wait.rs", r[0][1], r[0][0]))
        self.assertEqual(r[1][:2], ("cargo-unit", "bucket::tests::fills"))
        self.assertFalse(G.test_hit("crates/tc/tests/bucket.rs", r[1][1], r[1][0]))
    def test_inline_src(self):
        h = G.test_hit
        self.assertTrue(h("crates/core/src/bucket.rs", "terminal_commander_core::bucket::tests::fills", "nextest-unit"))
        self.assertTrue(h("crates/core/src/bucket.rs", "bucket::tests::fills", "cargo-unit"))
        self.assertTrue(h("crates/core/src/a/b.rs", "c::a::b::tests::t", "nextest-unit"))
        self.assertTrue(h("crates/core/src/lib.rs", "c::tests::t", "nextest-unit"))
        self.assertFalse(h("crates/core/src/lib.rs", "c::exec::tests::t", "nextest-unit"))
        self.assertFalse(h("crates/core/src/bucket.rs", "other::tests::fills", "cargo-unit"))
        self.assertFalse(h("crates/core/src/ucket.rs", "bucket::tests::fills", "cargo-unit"))
        self.assertTrue(G.inline_rust_test({"filename": "crates/core/src/bucket.rs", "patch": "@@ -1 +1 @@\n+#[test]\n+fn x(){}"}))
        self.assertFalse(G.inline_rust_test({"filename": "crates/core/src/bucket.rs", "patch": "@@ -1 +1 @@ mod tests {\n mod tests {\n-a\n+b"}))
    def test_done_test_colons(self):
        self.assertTrue(G.same("terminal_commander_daemon::bucket_wait::wake_on_match", "bucket_wait::wake_on_match"))
        self.assertFalse(G.same("a::b::wake_on_match", "wake_on_match") and False)
    def test_jest_unchanged(self):
        r = G.results(JEST)
        self.assertEqual([(x[1], x[2]) for x in r], [("packages/a/src/x.spec.ts", True), ("src/y.test.ts", False)])
        self.assertTrue(G.test_hit("a/src/y.test.ts", "src/y.test.ts", "jest"))
        self.assertFalse(G.test_hit("src/z.test.ts", "src/y.test.ts", "jest"))
if __name__ == "__main__":
    unittest.main()
