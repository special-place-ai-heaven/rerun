import ast, os, re, unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def local_imports(name):
    tree = ast.parse(open(os.path.join(HERE, name + ".py")).read())
    mods = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module and not n.level:
            mods.add(n.module.split(".")[0])
    return {m for m in mods if os.path.exists(os.path.join(HERE, m + ".py"))}


class InstallFiles(unittest.TestCase):
    def test_every_runner_import_is_installed(self):
        seen, todo = set(), ["runner_loop"]
        while todo:
            m = todo.pop()
            if m not in seen:
                seen.add(m)
                todo += local_imports(m)
        line = re.search(r"^for f in (.*?); do", open(os.path.join(HERE, "install.sh")).read(), re.M).group(1)
        installed = {f[:-3] for f in line.split() if f.endswith(".py")}
        self.assertEqual(sorted(seen - installed), [])


if __name__ == "__main__":
    unittest.main()
