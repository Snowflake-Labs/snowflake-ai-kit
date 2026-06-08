#
# Snowflake AI Kit -- Installer (Windows)
#
# Installs Snowflake CLI (snow) and Cortex Code CLI (cortex).
# Optionally installs Claude Code CLI and/or OpenAI Codex CLI,
# then verifies your Snowflake connection.
#
# Usage:
#   .\install.ps1
#   .\install.ps1 -Check
#   .\install.ps1 -WithClaude -WithCodex
#

param(
    [switch]$Check,
    [switch]$WithClaude,
    [switch]$WithCodex,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

$Troubleshoot = "https://github.com/Snowflake-Labs/snowflake-ai-kit#troubleshooting"

# === Output helpers ===========================================

function Write-Msg  { param([string]$Text) Write-Host "  $Text" }
function Write-Ok   { param([string]$Text) Write-Host "  " -NoNewline; Write-Host "v" -ForegroundColor Green -NoNewline; Write-Host " $Text" }
function Write-Warn { param([string]$Text) Write-Host "  " -NoNewline; Write-Host "!" -ForegroundColor Yellow -NoNewline; Write-Host " $Text" }
function Write-Err  { param([string]$Text) Write-Host "  " -NoNewline; Write-Host "x" -ForegroundColor Red -NoNewline; Write-Host " $Text"; exit 1 }
function Write-Step { param([string]$Text) Write-Host ""; Write-Host "$Text" -ForegroundColor White }

# === Prereq checks ============================================

function Test-Command { param([string]$Name) return [bool](Get-Command $Name -ErrorAction SilentlyContinue) }

function Test-SnowflakeAuth {
    $connToml = Join-Path $env:USERPROFILE ".snowflake\connections.toml"
    $cfgToml  = Join-Path $env:USERPROFILE ".snowflake\config.toml"
    if (Test-Path $connToml) {
        Write-Ok "Snowflake config found (~/.snowflake/connections.toml)"
        return $true
    }
    elseif (Test-Path $cfgToml) {
        Write-Ok "Snowflake config found (~/.snowflake/config.toml)"
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
        Write-Msg "  Docs: https://docs.snowflake.com/en/developer-guide/snowflake-cli/connecting/specify-credentials"
        return $false
    }
}

# === CLI installers ============================================

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
    if (Test-Command "python") {
        & python -m pip install snowflake-cli 2>$null
        if ($LASTEXITCODE -eq 0) { Write-Ok "Snowflake CLI installed via pip"; return $true }
    }
    if (Test-Command "pip") {
        & pip install snowflake-cli 2>$null
        if ($LASTEXITCODE -eq 0) { Write-Ok "Snowflake CLI installed via pip"; return $true }
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
    catch { }
    Write-Err "Could not install Cortex Code CLI. See $Troubleshoot"
}

function Install-ClaudeCodeCLI {
    if (Test-Command "claude") {
        Write-Ok "Claude Code CLI (claude) already installed"
        return $true
    }

    Write-Msg "Installing Claude Code CLI..."
    if (Test-Command "npm") {
        & npm install -g @anthropic-ai/claude-code 2>$null
        if ($LASTEXITCODE -eq 0) { Write-Ok "Claude Code CLI installed via npm"; return $true }
    }
    Write-Warn "Could not install Claude Code CLI (requires Node.js + npm)."
    Write-Msg "  Install manually: npm install -g @anthropic-ai/claude-code"
    return $false
}

function Install-CodexCLI {
    if (Test-Command "codex") {
        Write-Ok "OpenAI Codex CLI (codex) already installed"
        return $true
    }

    Write-Msg "Installing OpenAI Codex CLI..."
    if (Test-Command "npm") {
        & npm install -g @openai/codex 2>$null
        if ($LASTEXITCODE -eq 0) { Write-Ok "OpenAI Codex CLI installed via npm"; return $true }
    }
    Write-Warn "Could not install OpenAI Codex CLI (requires Node.js + npm)."
    Write-Msg "  Install manually: npm install -g @openai/codex"
    return $false
}

# === Help ======================================================

if ($Help) {
    Write-Host "Snowflake AI Kit -- Installer (Windows)"
    Write-Host ""
    Write-Host "Installs Snowflake CLI (snow) and Cortex Code CLI (cortex)."
    Write-Host "Optionally installs Claude Code CLI and/or OpenAI Codex CLI."
    Write-Host ""
    Write-Host "Usage: .\install.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Check       Check installation status without installing"
    Write-Host "  -WithClaude  Also install Claude Code CLI"
    Write-Host "  -WithCodex   Also install OpenAI Codex CLI"
    Write-Host "  -Help        Show this help"
    return
}

# === Execute ===================================================

Write-Host ""
Write-Host "Snowflake AI Kit -- Installer" -ForegroundColor White
Write-Host "=============================="
Write-Host ""

if ($Check) {
    Write-Step "Checking installation status..."
    if (Test-Command "snow")   { Write-Ok "Snowflake CLI (snow) installed" }     else { Write-Warn "Snowflake CLI (snow) not found" }
    if (Test-Command "cortex") { Write-Ok "Cortex Code CLI (cortex) installed" } else { Write-Warn "Cortex Code CLI (cortex) not found" }
    if (Test-Command "claude") { Write-Ok "Claude Code CLI (claude) installed" } else { Write-Warn "Claude Code CLI (claude) not found" }
    if (Test-Command "codex")  { Write-Ok "OpenAI Codex CLI (codex) installed" } else { Write-Warn "OpenAI Codex CLI (codex) not found" }
    Test-SnowflakeAuth | Out-Null
    Write-Host ""
    return
}

Write-Step "Installing core CLIs..."
Install-SnowflakeCLI | Out-Null
Install-CortexCodeCLI | Out-Null

# Optional: Claude Code CLI
if ($WithClaude -or (Test-Command "claude")) {
    Write-Step "Installing Claude Code CLI..."
    Install-ClaudeCodeCLI | Out-Null
}

# Optional: OpenAI Codex CLI
if ($WithCodex -or (Test-Command "codex")) {
    Write-Step "Installing OpenAI Codex CLI..."
    Install-CodexCLI | Out-Null
}

# Plugin setup
Write-Step "Setting up plugins..."

if (Test-Command "codex") {
    $codexList = & codex plugin marketplace list 2>$null
    if ($codexList -match "snowflake-ai-kit") {
        Write-Ok "Codex marketplace already configured"
    } else {
        & codex plugin marketplace add Snowflake-Labs/snowflake-ai-kit 2>$null
        if ($LASTEXITCODE -eq 0) { Write-Ok "Codex marketplace added (Snowflake-Labs/snowflake-ai-kit)" }
        else { Write-Warn "Could not add Codex marketplace. Run: codex plugin marketplace add Snowflake-Labs/snowflake-ai-kit" }
    }
    $codexPlugins = & codex plugin list 2>$null
    if ($codexPlugins -match "snowflake-cortex-code.*installed") {
        Write-Ok "Codex plugin already installed"
    } else {
        & codex plugin add "snowflake-cortex-code@snowflake-ai-kit" 2>$null
        if ($LASTEXITCODE -eq 0) { Write-Ok "Codex plugin installed (snowflake-cortex-code)" }
        else { Write-Warn "Could not install Codex plugin. Run: codex plugin add snowflake-cortex-code@snowflake-ai-kit" }
    }
}

if (Test-Command "claude") {
    $claudeList = & claude plugin marketplace list 2>$null
    if ($claudeList -match "claude-plugins-official") {
        Write-Ok "Claude Code marketplace already configured"
    } else {
        & claude plugin marketplace add anthropics/claude-plugins-official 2>$null
        if ($LASTEXITCODE -eq 0) { Write-Ok "Claude Code marketplace added (anthropics/claude-plugins-official)" }
        else { Write-Warn "Could not add Claude Code marketplace. Run: claude plugin marketplace add anthropics/claude-plugins-official" }
    }
    $claudePlugins = & claude plugin list 2>$null
    if ($claudePlugins -match "snowflake-cortex-code") {
        Write-Ok "Claude Code plugin already installed"
    } else {
        & claude plugin install snowflake-cortex-code 2>$null
        if ($LASTEXITCODE -eq 0) { Write-Ok "Claude Code plugin installed (snowflake-cortex-code)" }
        else { Write-Warn "Could not install Claude Code plugin. Run: claude plugin install snowflake-cortex-code" }
    }
}

if (-not (Test-Command "codex") -and -not (Test-Command "claude")) {
    Write-Msg "  No agent CLI found. Install one with -WithClaude or -WithCodex"
}

Write-Step "Checking Snowflake connection..."
Test-SnowflakeAuth | Out-Null

Write-Host ""
Write-Host "All done!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  cortex               # Start Cortex Code (interactive AI assistant)"
Write-Host "  snow --version       # Verify Snowflake CLI"
Write-Host ""
