import os
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
DEFAULT_MODEL = "gemini-3.5-flash"


def read_env_file(path=ENV_FILE):
    # KEY=VALUE lines, # for notes. small on purpose, no package needed.
    values = {}
    path = Path(path)
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def settings(env=None, file_values=None):
    # a real environment variable wins over the .env file
    env = os.environ if env is None else env
    file_values = read_env_file() if file_values is None else file_values

    def get(key, default=""):
        return env.get(key) or file_values.get(key) or default

    return {
        "fake": get("FAKE_MODEL", "1").strip() != "0",  # fake unless someone writes 0
        "key": get("GEMINI_API_KEY").strip(),
        "model": get("GEMINI_MODEL", DEFAULT_MODEL).strip(),
    }
