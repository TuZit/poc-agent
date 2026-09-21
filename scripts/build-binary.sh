#!/usr/bin/env bash
# Build the standalone `agent-kit` binary for the current platform.
#
#   bash scripts/build-binary.sh
#
# Output: dist/bin/agent-kit-<os>-<arch>   (single file, no Python required)
#
# The build environment needs the `package` dependency group (PyInstaller) and
# the `openai` extra, so the binary supports the real provider as well as the
# offline mock model.
set -euo pipefail

cd "$(dirname "$0")/.."

OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"

case "${OS}-${ARCH}" in
  darwin-arm64)           TARGET="darwin-arm64" ;;
  darwin-x86_64)          TARGET="darwin-x86_64" ;;
  linux-x86_64|linux-amd64) TARGET="linux-x86_64" ;;
  linux-aarch64|linux-arm64) TARGET="linux-arm64" ;;
  *)
    echo "Unsupported platform: ${OS}-${ARCH}" >&2
    echo "Supported: darwin-arm64, darwin-x86_64, linux-x86_64, linux-arm64." >&2
    echo "On Windows, run the spec under PowerShell: see docs/end-user-install.md" >&2
    exit 1
    ;;
esac

echo "==> Syncing build environment (package group + openai extra)"
uv sync --extra openai --group package

echo "==> Freezing with PyInstaller"
uv run --extra openai --group package pyinstaller packaging/agent-kit.spec --noconfirm --clean

mkdir -p dist/bin
install -m 0755 dist/agent-kit "dist/bin/agent-kit-${TARGET}"

echo
echo "==> Built dist/bin/agent-kit-${TARGET} ($(du -h "dist/bin/agent-kit-${TARGET}" | cut -f1))"
echo "    Smoke test: dist/bin/agent-kit-${TARGET} --version"
