"""Loads KEY=VALUE pairs from a .env file into os.environ, if present.

Not used in CI: GitHub Actions injects secrets directly as environment
variables, so there's no .env file there and this becomes a no-op.
"""

import os
from pathlib import Path


def load_env(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)
