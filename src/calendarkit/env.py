"""Minimal .env loading and typed access to environment settings.

Deliberately dependency-free (no python-dotenv needed). Supported syntax:

    # comment
    KEY=value
    export KEY=value
    KEY="quoted value"     # quotes are stripped; no variable interpolation

Values already present in the real environment win over the file unless
``override=True`` is passed, so a launcher can still override a setting.

Typical use in an app's settings module::

    from calendarkit import env
    env.load_dotenv(BASE_DIR / ".env")
    PORT = env.get_int("PORT", 5000)
    TOKEN_FILE = env.get_path("GOOGLE_TOKEN_FILE", "token.json", base_dir=BASE_DIR)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional, Union

PathLike = Union[str, os.PathLike]

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off", ""}


class MissingSettingError(RuntimeError):
    """Raised by :func:`require` when a mandatory setting is not configured."""


def parse_dotenv(text: str) -> Dict[str, str]:
    """Parse .env-formatted *text* into a dict (later keys win)."""
    values: Dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        key, sep, value = line.partition("=")
        key = key.strip()
        if not sep or not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        elif " #" in value:                     # trailing comment on unquoted value
            value = value.split(" #", 1)[0].rstrip()
        values[key] = value
    return values


def load_dotenv(path: PathLike, override: bool = False) -> Dict[str, str]:
    """Load *path* into ``os.environ``. A missing file is not an error.

    Returns the key/values found in the file.
    """
    p = Path(path)
    if not p.is_file():
        return {}
    values = parse_dotenv(p.read_text(encoding="utf-8-sig"))
    for key, value in values.items():
        if override or key not in os.environ:
            os.environ[key] = value
    return values


def get(name: str, default: Optional[str] = None) -> Optional[str]:
    """Return the setting as a string (empty string counts as unset)."""
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def require(name: str) -> str:
    """Return the setting or raise :class:`MissingSettingError`."""
    value = get(name)
    if value is None:
        raise MissingSettingError(
            f"Setting {name} is not configured. Add it to the project's .env file "
            f"(see .env.example)."
        )
    return value


def get_int(name: str, default: int) -> int:
    value = get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Setting {name} must be an integer, got {value!r}") from exc


def get_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    v = value.strip().lower()
    if v in _TRUE:
        return True
    if v in _FALSE:
        return False
    raise ValueError(f"Setting {name} must be a boolean (true/false), got {value!r}")


def get_path(name: str, default: PathLike, base_dir: Optional[PathLike] = None) -> Path:
    """Return the setting as a Path; relative paths resolve against *base_dir*."""
    p = Path(get(name) or default).expanduser()
    if not p.is_absolute() and base_dir is not None:
        p = Path(base_dir) / p
    return p
