import gc, os, unittest, warnings

import test_factory as T

F = T.F


class Exclude(T.FactoryCase):
    wt_new_fakes = T.BuilderCap.wt_new_fakes

    def test_wt_new_leaves_no_open_handle_on_the_exclude_list(self):
        with warnings.catch_warnings(record=True) as seen:
            warnings.simplefilter("always")
            with self.wt_new_fakes():
                c1, _ = self.call(F.cmd_wt, ["new", "rerun", "7", "1"])
                c2, _ = self.call(F.cmd_wt, ["new", "rerun", "7", "2"])
            gc.collect()
        self.assertEqual((c1, c2), (0, 0))
        bad = [str(w.message) for w in seen if issubclass(w.category, ResourceWarning) and "exclude" in str(w.message)]
        self.assertEqual(bad, [])
        with open(os.path.join(self.clone, ".git", "info", "exclude")) as f:
            lines = f.read().splitlines()
        self.assertEqual(lines.count(".symforge/"), 1)


if __name__ == "__main__":
    unittest.main()
