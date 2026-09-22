"""Locate bundled assets (skills, templates, samples, integrations).

During development the canonical assets live at the repository root
(``skills/``, ``templates/``, ``samples/``, ``integrations/``). When the
package is installed as a wheel, hatchling force-includes those same
directories into ``agent_kit/_bundled/``. This module hides that dual
location behind a single helper so no other module needs to care.
"""

from __future__ import annotations

import sys
from pathlib import Path

BUNDLED_DIR_NAME = "_bundled"

#: Asset directories that may be requested through :func:`asset_dir`.
ASSET_NAMES = ("skills", "templates", "samples", "integrations")


class AssetError(RuntimeError):
    """Raised when a bundled asset directory cannot be located."""


def package_root() -> Path:
    """Return the directory that contains the ``agent_kit`` package.

    Three layouts are supported:

    * **installed wheel** — ``site-packages/agent_kit``
    * **source checkout** — ``<repo>/src/agent_kit``
    * **frozen binary** (PyInstaller) — ``<_MEIPASS>/agent_kit``, where the
      bundled assets were placed next to the packaged modules
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        frozen = Path(meipass) / "agent_kit"
        if frozen.is_dir():
            return frozen
    return Path(__file__).resolve().parent


def runtime_origin() -> str:
    """Where this build runs from.

    Printed by ``agent-kit doctor`` so a stale installation (an old wheel or
    binary shadowing a newer source checkout) is visible immediately.
    """
    if getattr(sys, "_MEIPASS", None):
        return f"standalone binary: {sys.executable}"
    return f"python package: {package_root()}"


def repo_root_candidate() -> Path:
    """Best guess for the source checkout root (``<repo>/src/agent_kit`` -> ``<repo>``)."""
    return package_root().parent.parent


def asset_dir(name: str) -> Path:
    """Return the directory holding a bundled asset group.

    Installed wheels win over the source checkout, so behaviour matches what
    users actually installed.
    """
    if name not in ASSET_NAMES:
        raise AssetError(f"Unknown asset group '{name}'. Known groups: {', '.join(ASSET_NAMES)}.")

    bundled = package_root() / BUNDLED_DIR_NAME / name
    if bundled.is_dir():
        return bundled

    dev = repo_root_candidate() / name
    if dev.is_dir():
        return dev

    raise AssetError(
        f"Bundled asset directory '{name}' not found (looked in '{bundled}' and '{dev}'). "
        "Reinstall the package, e.g. uv tool install 'agent-kit-poc[openai]' --force."
    )


def skills_dir() -> Path:
    """Directory containing shipped skills (``<asset>/skills/<skill-name>/SKILL.md``)."""
    return asset_dir("skills")


def templates_dir() -> Path:
    """Directory containing project templates (``<asset>/templates/project``)."""
    return asset_dir("templates")


def samples_dir() -> Path:
    """Directory containing sample inputs and expected outputs."""
    return asset_dir("samples")


def integrations_dir() -> Path:
    """Directory containing editor/agent integrations (e.g. Kiro)."""
    return asset_dir("integrations")
