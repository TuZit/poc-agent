# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — build a single-file ``agent-kit`` binary.

End users install this binary; they do not need Python, uv or pip.

Build (from the repository root)::

    uv run --extra openai --group package pyinstaller packaging/agent-kit.spec --noconfirm --clean

or simply ``bash scripts/build-binary.sh``, which also renames the artifact to
``dist/bin/agent-kit-<os>-<arch>``.

The spec bundles the same assets that hatchling force-includes into the wheel
(``skills``, ``templates``, ``samples``, ``integrations``) under
``agent_kit/_bundled/``, which is exactly where :mod:`agent_kit.paths` looks
inside a frozen application (``sys._MEIPASS``).
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

REPO_ROOT = Path(SPECPATH).resolve().parent  # noqa: F821 - provided by PyInstaller

# --- assets: must mirror [tool.hatch.build.targets.wheel.force-include] ------
datas = [
    (str(REPO_ROOT / "skills"), "agent_kit/_bundled/skills"),
    (str(REPO_ROOT / "templates"), "agent_kit/_bundled/templates"),
    (str(REPO_ROOT / "samples"), "agent_kit/_bundled/samples"),
    (str(REPO_ROOT / "integrations"), "agent_kit/_bundled/integrations"),
]
# typer vendors its own click fork; collect it so submodules are not missed.
datas += collect_data_files("typer")

hiddenimports = (
    collect_submodules("agent_kit")
    + collect_submodules("typer")
    + collect_submodules("yaml")
    + collect_submodules("openai")
)

a = Analysis(  # noqa: F821 - provided by PyInstaller
    [str(REPO_ROOT / "packaging" / "entrypoint.py")],
    pathex=[str(REPO_ROOT / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Dev-only tooling never ships inside the binary.
    excludes=["pytest", "ruff", "tkinter", "_tkinter", "matplotlib", "numpy"],
    noarchive=False,
)

pyz = PYZ(a.pure)  # noqa: F821 - provided by PyInstaller

exe = EXE(  # noqa: F821 - provided by PyInstaller
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="agent-kit",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
