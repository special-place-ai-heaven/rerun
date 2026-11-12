import os, re, unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")


class ImageFiles(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(ROOT, "deploy", "vps", "factory-runner.Dockerfile")) as f:
            self.text = f.read()

    def test_git_askpass_no_token(self):
        self.assertRegex(self.text, r"(?m)^FROM python:3\.12-slim")
        self.assertRegex(self.text, r"apt-get install[^\n]*\bgit\b")
        self.assertIn("GIT_ASKPASS=", self.text)
        self.assertIn("$FACTORY_GIT_TOKEN", self.text)  # read from the environment at run time
        self.assertNotRegex(self.text, r"gh[pousr]_\w{10}|github_pat_|https?://\S+@")
        self.assertNotRegex(self.text, r"(?m)^(ENV|ARG)\s+\w*(TOKEN|KEY)\w*\s*=?\s*\S")

    def test_runs_unprivileged(self):
        self.assertRegex(self.text, r"(?m)^USER\s+(?!root)\S+")


if __name__ == "__main__":
    unittest.main()
