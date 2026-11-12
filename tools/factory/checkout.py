import os, subprocess


def _git(cwd, *a):
    return subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class Reader:
    def __init__(self, root):
        self.root = os.path.realpath(root)

    def open(self, rel, mode="r"):
        if mode.strip("rbt") != "":
            raise PermissionError("reader is read-only")
        p = os.path.realpath(os.path.join(self.root, rel))
        if p != self.root and not p.startswith(self.root + os.sep):
            raise PermissionError("path outside checkout")
        return open(p, mode)


class Checkout:
    def __init__(self, path, url, base):
        self.path, self.url, self.base = path, url, base

    def ensure(self):
        if not os.path.isdir(os.path.join(self.path, ".git")):
            os.makedirs(self.path, exist_ok=True)
            _git(self.path, "init", "-q")
            _git(self.path, "remote", "add", "origin", self.url)
        _git(self.path, "fetch", "-q", "origin")
        _git(self.path, "checkout", "-qf", "--detach", self.base)
        return self.path

    def reader(self):
        for d, _, fs in os.walk(self.path):
            for f in fs if ".git" not in d.split(os.sep) else ():
                p = os.path.join(d, f)
                os.chmod(p, os.stat(p).st_mode & ~0o222)
        return Reader(self.path)
