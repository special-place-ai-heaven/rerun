"""Gate fixture tests: real-shaped CI logs (jest; cargo + nextest). Run with PYTHONPATH=tools/factory."""
import os, unittest
import gate as G

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return f.read()


class Fixtures(unittest.TestCase):
    def test_jest_ci_log_fixture(self):
        r = G.results(load("jest_ci.log"))
        self.assertEqual([(x[0], x[1], x[2]) for x in r], [
            ("jest", "packages/core/src/parser.spec.ts", True),
            ("jest", "apps/web/src/button.test.tsx", True),
            ("jest", "apps/server/src/routes/health.test.ts", False),
            ("jest", "packages/shared/__tests__/util.test.js", True)])
        self.assertTrue(G.test_hit("src/routes/health.test.ts", "apps/server/src/routes/health.test.ts", "jest"))

    def test_rust_ci_log_fixture(self):
        r = G.results(load("rust_ci.log"))
        kinds = {x[0] for x in r}
        self.assertIn("nextest-it", kinds)
        self.assertIn("cargo-unit", kinds)
        nx = [x for x in r if x[0] == "nextest-it"]
        cg = [x for x in r if x[0] == "cargo-unit"]
        self.assertEqual(len(nx), 30)
        self.assertEqual(len(cg), 9)
        self.assertEqual(nx[0][:3], ("nextest-it", "terminal-commander-probes::governor_limits::alloc_helper", True))
        self.assertEqual(nx[-1][:3], ("nextest-it", "terminal-commander-probes::governor_limits::synthetic_failure_case", False))
        self.assertEqual(cg[0][:3], ("cargo-unit", "concurrent_probes_buckets_do_not_cross_talk", True))
        self.assertEqual(cg[-1][:3], ("cargo-unit", "synthetic_failed_case", False))
        self.assertEqual(sum(1 for x in r if not x[2]), 2)


if __name__ == "__main__":
    unittest.main()
