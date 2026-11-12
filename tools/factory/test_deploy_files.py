"""Checks of the dev-engine and runner compose files and the status script (rerun#60 C2). Text checks only: no docker."""
import os, re, unittest

VPS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "deploy", "vps")


def read(name):
    with open(os.path.join(VPS, name), encoding="utf-8") as f:
        return f.read()


def code(text):
    return "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#"))


class DevEngine(unittest.TestCase):
    def test_key_comes_from_one_required_variable(self):
        self.assertIn("RERUN_API_KEY: ${RERUN_DEV_ENGINE_KEY:?", read("dev-engine.yml"))

    def test_no_literal_key_no_ports_no_socket(self):
        c = code(read("dev-engine.yml"))
        self.assertNotRegex(c, r"RERUN_API_KEY:\s*[^$\s]")
        for bad in ("ports:", "docker.sock", "privileged", "env_file", "RERUN_ENGINE_API_KEY"):
            self.assertNotIn(bad, c)


class Runner(unittest.TestCase):
    def setUp(self):
        self.t = read("factory-runner.yml")
        self.c = code(self.t)

    def test_same_network_project_as_dev_engine(self):
        self.assertIn("name: rerun-dev", self.c)
        self.assertNotIn("networks:", self.c)

    def test_only_the_dev_key_and_url(self):
        self.assertIn("RERUN_DEV_ENGINE_KEY: ${RERUN_DEV_ENGINE_KEY:?", self.c)
        self.assertIn("RERUN_DEV_ENGINE_URL: http://engine-dev:3000", self.c)
        self.assertNotIn("RERUN_ENGINE_API_KEY", self.c)
        self.assertNotIn("env_file", self.c)

    def test_hardening(self):
        for bad in ("ports:", "docker.sock", "privileged: true", "cap_add", "network_mode", "pid:"):
            self.assertNotIn(bad, self.c)
        for need in ("restart: unless-stopped", "mem_limit:", "max-size:", "cap_drop:", "no-new-privileges:true", "read_only: true"):
            self.assertIn(need, self.c)

    def test_tools_mounted_read_only_and_own_volume(self):
        self.assertIn("../../tools/factory:/app:ro", self.c)
        self.assertRegex(self.c, r"factory-runner-data:/state")
        mounts = re.findall(r"^\s+- (\S+:/\S+)$", self.c, re.M)
        self.assertEqual(len(mounts), 2, mounts)


class StatusScript(unittest.TestCase):
    def setUp(self):
        self.s = read("dev-engine-status.sh")
        self.c = code(self.s)

    def test_bearer_from_dev_key_only(self):
        self.assertIn("RERUN_DEV_ENGINE_KEY", self.c)
        self.assertNotIn("RERUN_ENGINE_API_KEY", self.s)
        self.assertNotRegex(self.c, r"sed -n 's/\^RERUN_ENGINE")

    def test_key_never_echoed(self):
        for line in self.c.splitlines():
            if "$DEVKEY" in line and not line.startswith("[ -n"):
                self.assertNotRegex(line, r"\b(say|echo)\b")
                self.assertNotIn("docker exec -e", line)


if __name__ == "__main__":
    unittest.main()
