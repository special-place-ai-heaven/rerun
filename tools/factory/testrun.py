import os
import subprocess


def _rc(path, cmd, timeout):
    env = {k: v for k, v in os.environ.items() if k not in ("FACTORY_GIT_TOKEN", "GIT_ASKPASS")}
    try:
        return subprocess.run(cmd, cwd=path, env=env, capture_output=True, timeout=timeout).returncode
    except subprocess.TimeoutExpired:
        return 124
    except OSError:
        return 127


def run(base_path, head_path, cmd, timeout=600):
    """The done-test must fail on base and pass on head."""
    base, head = _rc(base_path, cmd, timeout), _rc(head_path, cmd, timeout)
    verdict = "passes_on_base" if base == 0 else "fails_on_head" if head else "ok"
    return {"verdict": verdict, "base": base, "head": head}
