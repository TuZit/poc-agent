"""``agent-kit config`` — inspect and update ``.agent/config.yaml``.

Note: ``config set`` rewrites the file with ``yaml.safe_dump``, so comments in
the file are not preserved. This is an accepted POC trade-off.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer
import yaml

from agent_kit.cli.common import fail, info, relative_to
from agent_kit.config import ConfigError, default_config_path, dump_config, load_config

config_app = typer.Typer(
    help="Inspect and update .agent/config.yaml.",
    no_args_is_help=True,
)


def _read_raw(project: Path) -> tuple[Path, dict[str, Any]]:
    path = default_config_path(project)
    if not path.is_file():
        fail(f"Configuration not found at {path}. Run 'agent-kit init <project>' first.")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        fail(f"Invalid YAML in {path}: {exc}")
    if not isinstance(data, dict):
        fail(f"{path} must contain a YAML mapping at the top level.")
    return path, data


def _coerce(value: str) -> Any:
    """Turn a CLI string into a YAML-friendly scalar."""
    lowered = value.strip().lower()
    if lowered in {"true", "yes", "on"}:
        return True
    if lowered in {"false", "no", "off"}:
        return False
    if lowered in {"null", "none", "~"}:
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _split(key: str) -> list[str]:
    parts = [part for part in key.split(".") if part]
    if not parts:
        fail("Key must not be empty, e.g. 'model.provider'.")
    return parts


def _get(data: Any, key: str) -> Any:
    current = data
    for part in _split(key):
        if isinstance(current, dict):
            if part not in current:
                fail(f"Key '{key}' not found in configuration.")
            current = current[part]
        elif isinstance(current, list):
            if not part.isdigit() or int(part) >= len(current):
                fail(f"Key '{key}' not found in configuration.")
            current = current[int(part)]
        else:
            fail(f"Key '{key}' not found in configuration.")
    return current


def _set(data: dict[str, Any], key: str, value: Any) -> None:
    parts = _split(key)
    current: Any = data
    for part in parts[:-1]:
        if isinstance(current, dict):
            if part not in current or not isinstance(current[part], (dict, list)):
                current[part] = {}
            current = current[part]
        elif isinstance(current, list) and part.isdigit():
            index = int(part)
            while len(current) <= index:
                current.append({})
            if not isinstance(current[index], (dict, list)):
                current[index] = {}
            current = current[index]
        else:  # pragma: no cover - defensive
            fail(f"Cannot descend into '{part}' while setting '{key}'.")

    last = parts[-1]
    if isinstance(current, dict):
        current[last] = value
    elif isinstance(current, list) and last.isdigit():
        index = int(last)
        while len(current) <= index:
            current.append(None)
        current[index] = value
    else:  # pragma: no cover - defensive
        fail(f"Cannot set '{key}'.")


@config_app.command("show")
def show_command(
    project: Path = typer.Option(Path("."), "--project", "-p", help="Project root."),
) -> None:
    """Print the resolved (validated) configuration as YAML."""
    try:
        config = load_config(project)
    except ConfigError as exc:
        fail(str(exc))
    info(dump_config(config.to_dict()).rstrip())


@config_app.command("get")
def get_command(
    key: str = typer.Argument(..., help="Dotted key, e.g. model.provider."),
    project: Path = typer.Option(Path("."), "--project", "-p", help="Project root."),
) -> None:
    """Print one configuration value."""
    _, data = _read_raw(project)
    value = _get(data, key)
    if isinstance(value, (dict, list)):
        info(dump_config(value).rstrip())
    else:
        info(str(value))


@config_app.command("set")
def set_command(
    key: str = typer.Argument(..., help="Dotted key, e.g. model.provider."),
    value: str = typer.Argument(..., help="New value (booleans/numbers are coerced)."),
    project: Path = typer.Option(Path("."), "--project", "-p", help="Project root."),
) -> None:
    """Set one configuration value and rewrite .agent/config.yaml."""
    path, data = _read_raw(project)
    _set(data, key, _coerce(value))
    path.write_text(dump_config(data), encoding="utf-8")
    info(f"✓ {key} = {_coerce(value)!r} in {relative_to(path, Path(project))}")
