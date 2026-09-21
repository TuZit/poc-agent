"""PyInstaller entry point.

Mirrors the ``agent-kit`` console script defined in ``pyproject.toml`` so a
frozen binary behaves exactly like an installed one.
"""

from agent_kit.cli.main import app

if __name__ == "__main__":
    app()
