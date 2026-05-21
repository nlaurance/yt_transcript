"""Load the right .env file based on APP_ENV.

Convention
----------
APP_ENV=prod   → loads .env.prod   (production values)
APP_ENV=<any>  → loads .env        (dev values, default)

The file is resolved relative to the project root (one level up from
this pipeline/ directory), so it works regardless of where you run the
script from.

Usage in scripts
----------------
    from pipeline.env_loader import load_env
    load_env()

Usage from the shell
--------------------
    # dev (default)
    uv run --group pipeline yt-transcript <URL>

    # production
    APP_ENV=prod uv run --group pipeline yt-transcript <URL>
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Project root is one level up from pipeline/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_env() -> Path | None:
    """Load the appropriate .env file and return the path that was loaded."""
    env = os.environ.get("APP_ENV", "dev")
    env_file = _PROJECT_ROOT / (".env.prod" if env == "prod" else ".env")

    if not env_file.exists():
        return None

    load_dotenv(env_file, override=True)
    return env_file
