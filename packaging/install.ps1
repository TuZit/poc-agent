<#
.SYNOPSIS
    Agent Kit POC installer for Windows — downloads the standalone agent-kit binary.

.DESCRIPTION
    No Python, pip or uv is required: the binary is self-contained.

    Usage:
        irm https://YOUR-HOST/agent-kit/install.ps1 | iex

    Environment variables (or parameters):
        AGENT_KIT_VERSION      version to install     (default: 0.1.0)
        AGENT_KIT_BASE_URL     release base URL       (default: <placeholder>)
        AGENT_KIT_INSTALL_DIR  install directory      (default: $env:LOCALAPPDATA\Programs\agent-kit)

.NOTES
    Status: provided for parity with packaging/install.sh, but NOT yet verified on
    Windows — the release pipeline must first build agent-kit-windows-<arch>.exe by
    running `pyinstaller packaging/agent-kit.spec` on a Windows runner.
#>
param(
    [string]$Version = $(if ($env:AGENT_KIT_VERSION) { $env:AGENT_KIT_VERSION } else { "0.1.0" }),
    [string]$BaseUrl = $(if ($env:AGENT_KIT_BASE_URL) { $env:AGENT_KIT_BASE_URL } else { "https://github.com/your-org/agent-kit-poc/releases/download" }),
    [string]$InstallDir = $(if ($env:AGENT_KIT_INSTALL_DIR) { $env:AGENT_KIT_INSTALL_DIR } else { Join-Path $env:LOCALAPPDATA "Programs\agent-kit" })
)

$ErrorActionPreference = "Stop"

$arch = if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") { "arm64" } else { "x86_64" }
$target = "windows-$arch"
$url = "$BaseUrl/v$Version/agent-kit-$target.exe"

Write-Host "Agent Kit POC $Version ($target)"
Write-Host "-> $url"

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
$destination = Join-Path $InstallDir "agent-kit.exe"

try {
    Invoke-WebRequest -Uri $url -OutFile $destination -UseBasicParsing
} catch {
    Write-Error "Download failed: $($_.Exception.Message)"
    exit 1
}

Write-Host "OK Installed $destination"

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$InstallDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$InstallDir", "User")
    Write-Host "! Added $InstallDir to your user PATH (restart the terminal to pick it up)."
}

& $destination --version

Write-Host @"

Next steps:
  agent-kit init my-project --ai kiro
  cd my-project
  agent-kit doctor
  agent-kit config set model.provider mock
  agent-kit run
  agent-kit evaluate output/sample-001.md
"@
