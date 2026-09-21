#!/usr/bin/env sh
# Agent Kit POC installer — downloads the standalone `agent-kit` binary.
#
#   curl -fsSL https://YOUR-HOST/agent-kit/install.sh | sh
#
# No Python, pip or uv is required: the binary is self-contained.
#
# Environment variables:
#   AGENT_KIT_VERSION      version to install        (default: 0.1.0)
#   AGENT_KIT_BASE_URL     release base URL          (default: <placeholder>)
#   AGENT_KIT_INSTALL_DIR  install directory         (default: ~/.local/bin)
#   AGENT_KIT_TARGET       override platform tag     (e.g. linux-x86_64)
#
# Artifact layout expected on the release host:
#   <AGENT_KIT_BASE_URL>/v<VERSION>/agent-kit-<os>-<arch>
#   os: darwin | linux     arch: arm64 | x86_64
set -eu

VERSION="${AGENT_KIT_VERSION:-0.1.0}"
BASE_URL="${AGENT_KIT_BASE_URL:-https://github.com/your-org/agent-kit-poc/releases/download}"
INSTALL_DIR="${AGENT_KIT_INSTALL_DIR:-$HOME/.local/bin}"

detect_target() {
  os="$(uname -s)"
  arch="$(uname -m)"

  case "$os" in
    Darwin) os="darwin" ;;
    Linux)  os="linux" ;;
    *) echo "✗ Unsupported operating system: $os (use install.ps1 on Windows)" >&2; exit 1 ;;
  esac

  case "$arch" in
    arm64|aarch64) arch="arm64" ;;
    x86_64|amd64)  arch="x86_64" ;;
    *) echo "✗ Unsupported architecture: $arch" >&2; exit 1 ;;
  esac

  # darwin-arm64 | darwin-x86_64 | linux-arm64 | linux-x86_64
  if [ "$os" = "darwin" ] && [ "$arch" = "x86_64" ]; then
    echo "darwin-x86_64"
  else
    echo "${os}-${arch}"
  fi
}

TARGET="${AGENT_KIT_TARGET:-$(detect_target)}"
URL="${BASE_URL}/v${VERSION}/agent-kit-${TARGET}"

echo "Agent Kit POC ${VERSION} (${TARGET})"
echo "→ ${URL}"

TMP_FILE="$(mktemp)"
trap 'rm -f "$TMP_FILE"' EXIT INT TERM

if command -v curl >/dev/null 2>&1; then
  curl -fsSL "$URL" -o "$TMP_FILE"
elif command -v wget >/dev/null 2>&1; then
  wget -qO "$TMP_FILE" "$URL"
else
  echo "✗ Neither curl nor wget is available; install one and retry." >&2
  exit 1
fi

chmod 0755 "$TMP_FILE"
mkdir -p "$INSTALL_DIR"
mv "$TMP_FILE" "$INSTALL_DIR/agent-kit"
trap - EXIT INT TERM

echo "✓ Installed $INSTALL_DIR/agent-kit"

case ":${PATH}:" in
  *":${INSTALL_DIR}:"*) ;;
  *) echo "! ${INSTALL_DIR} is not on your PATH. Add it:"
     echo "    export PATH=\"${INSTALL_DIR}:\$PATH\"     # add to ~/.zshrc to persist" ;;
esac

if command -v agent-kit >/dev/null 2>&1; then
  echo
  agent-kit --version
else
  "$INSTALL_DIR/agent-kit" --version
fi

cat <<'EOF'

Next steps:
  agent-kit init my-project --ai kiro     # create a project (Kiro integration)
  cd my-project
  agent-kit doctor                        # check the environment
  agent-kit config set model.provider mock
  agent-kit run
  agent-kit evaluate output/sample-001.md
EOF
