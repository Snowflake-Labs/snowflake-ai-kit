#
# Snowflake AI Kit — CLI Installer (Windows)
#
# Installs Snowflake CLI (snow) and Cortex Code CLI (cortex) if not already present,
# then verifies your Snowflake connection.
#
# Usage:
#   irm https://raw.githubusercontent.com/Snowflake-Labs/snowflake-ai-kit/main/install.ps1 | iex
#
#   # Download first, then run with options
#   irm https://raw.githubusercontent.com/Snowflake-Labs/snowflake-ai-kit/main/install.ps1 -OutFile install.ps1
#   .\install.ps1 -Check
#

param(
    [switch]$Check,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

$Troubleshoot = "https://github.com/Snowflake-Labs/snowflake-ai-kit#troubleshooting"

# ─── Output helpers ───────────────────────────────────────────

function Write-Msg  { param([string]$Text) Write-Host "  $Text" }
function Write-Ok   { param([string]$Text) Write-Host "  " -NoNewline; Write-Host "v" -ForegroundColor Green -NoNewline; Write-Host " $Text" }
function Write-Warn { param([string]$Text) Write-Host "  " -NoNewline; Write-Host "!" -ForegroundColor Yellow -NoNewline; Write-Host " $Text" }
function Write-Err  { param([string]$Text) Write-Host "  " -NoNewline; Write-Host "x" -ForegroundColor Red -NoNewline; Write-Host " $Text"; exit 1 }
function Write-Step { param([string]$Text) Write-Host ""; Write-Host "$Text" -ForegroundColor White }

# ─── Prereq checks ────────────────────────────────────────────

function Test-Command { param([string]$Name) return [bool](Get-Command $Name -ErrorAction SilentlyContinue) }

function Test-SnowflakeAuth {
    $configPath = Join-Path $env:USERPROFILE ".snowflake\connections.toml"
    if (Test-Path $configPath) {
        Write-Ok "Snowflake config found (~/.snowflake/connections.toml)"
        return $true
    }
    elseif ($env:SNOWFLAKE_HOST -or $env:SNOWFLAKE_ACCOUNT) {
        Write-Ok "Snowflake config found (environment variables)"
        return $true
    }
    else {
        Write-Warn "No Snowflake connection configured."
        Write-Msg "  Set one up (shared by both snow and cortex CLIs):"
        Write-Msg "    snow connection add"
        Write-Msg "  This creates ~/.snowflake/connections.toml, used by both tools."
        Write-Msg "  Docs: https://docs.snowflake.com/en/developer-guide/snowflake-cli/connecting/specify-credentials"
        Write-Msg "  More help: $Troubleshoot"
        return $false
    }
}

function Install-SnowflakeCLI {
    if (Test-Command "snow") {
        Write-Ok "Snowflake CLI (snow) already installed"
        return $true
    }

    Write-Msg "Installing Snowflake CLI..."
    if (Test-Command "pipx") {
        & pipx install snowflake-cli 2>$null
        if ($LASTEXITCODE -eq 0) { Write-Ok "Snowflake CLI installed via pipx"; return $true }
    }
    if (Test-Command "pip") {
        & pip install snowflake-cli 2>$null
        if ($LASTEXITCODE -eq 0) { Write-Ok "Snowflake CLI installed via pip"; return $true }
    }
    if (Test-Command "pip3") {
        & pip3 install snowflake-cli 2>$null
        if ($LASTEXITCODE -eq 0) { Write-Ok "Snowflake CLI installed via pip3"; return $true }
    }
    Write-Err "Could not install Snowflake CLI. See $Troubleshoot"
}

function Install-CortexCodeCLI {
    if (Test-Command "cortex") {
        Write-Ok "Cortex Code CLI (cortex) already installed"
        return $true
    }

    Write-Msg "Installing Cortex Code CLI..."
    try {
        $tempScript = Join-Path $env:TEMP "cc_install.ps1"
        Invoke-WebRequest -Uri "https://ai.snowflake.com/static/cc-scripts/install.ps1" -OutFile $tempScript -UseBasicParsing
        & $tempScript
        Remove-Item $tempScript -ErrorAction SilentlyContinue
        if ($LASTEXITCODE -eq 0) { Write-Ok "Cortex Code CLI installed"; return $true }
    }
    catch {
        # Fall through to error
    }
    Write-Err "Could not install Cortex Code CLI. See $Troubleshoot"
}

# ─── Help ──────────────────────────────────────────────────────

if ($Help) {
    Write-Host "Snowflake AI Kit — CLI Installer (Windows)"
    Write-Host ""
    Write-Host "Installs Snowflake CLI (snow) and Cortex Code CLI (cortex)."
    Write-Host ""
    Write-Host "Usage: .\install.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Check    Check installation status without installing"
    Write-Host "  -Help     Show this help"
    return
}

# ─── Execute ───────────────────────────────────────────────────

Write-Host ""
Write-Host "Snowflake AI Kit — CLI Installer" -ForegroundColor White
Write-Host "──────────────────────────────────"
Write-Host ""

if ($Check) {
    Write-Step "Checking installation status..."
    if (Test-Command "snow")   { Write-Ok "Snowflake CLI (snow) installed" }   else { Write-Warn "Snowflake CLI (snow) not found" }
    if (Test-Command "cortex") { Write-Ok "Cortex Code CLI (cortex) installed" } else { Write-Warn "Cortex Code CLI (cortex) not found" }
    Test-SnowflakeAuth | Out-Null
    Write-Host ""
    return
}

Write-Step "Installing Snowflake CLI and Cortex Code CLI..."
Install-SnowflakeCLI | Out-Null
Install-CortexCodeCLI | Out-Null

Write-Step "Checking Snowflake connection..."
Test-SnowflakeAuth | Out-Null

Write-Host ""
Write-Host "All done!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  snow --version       # Verify Snowflake CLI"
Write-Host "  cortex --version     # Verify Cortex Code CLI"
Write-Host "  cortex               # Start Cortex Code"
Write-Host ""
