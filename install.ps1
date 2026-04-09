#
# Snowflake AI Kit -- CLI Installer (Windows)
#
# Installs Snowflake CLI (snow), Cortex Code CLI (cortex), and Claude Code CLI (claude)
# if not already present, then verifies your Snowflake connection.
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
    [switch]$Update,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

$RepoUrl = "https://github.com/Snowflake-Labs/snowflake-ai-kit.git"
$SkillDir = Join-Path $env:USERPROFILE ".claude\skills\cortex-code"
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
    Write-Msg "  Install Node.js from https://nodejs.org then re-run."
    Write-Msg "  Or install manually: npm install -g @anthropic-ai/claude-code"
    return $false
}

function Install-Skills {
    $skillMd = Join-Path $SkillDir "SKILL.md"
    if ((Test-Path $skillMd) -and (-not $Update)) {
        Write-Ok "Claude-to-Cortex Code Router skill already installed"
        Write-Msg "  Re-run with -Update to overwrite"
        return $true
    }

    Write-Msg "Installing Claude-to-Cortex Code Router skill..."

    $tmpDir = Join-Path $env:TEMP "snowflake-ai-kit-$(Get-Random)"
    try {
        & git clone --depth 1 $RepoUrl $tmpDir 2>$null
        if ($LASTEXITCODE -ne 0) { throw "clone failed" }

        $src = Join-Path $tmpDir "agent-to-agent-skills\claude-cortex-code-router"

        # Create directories
        New-Item -ItemType Directory -Force -Path (Join-Path $SkillDir "scripts") | Out-Null
        New-Item -ItemType Directory -Force -Path (Join-Path $SkillDir "security\policies") | Out-Null
        New-Item -ItemType Directory -Force -Path (Join-Path $SkillDir "references") | Out-Null

        # Core files
        Copy-Item "$src\SKILL.md" $SkillDir -Force
        Copy-Item "$src\README.md" $SkillDir -Force
        Copy-Item "$src\config.yaml.example" $SkillDir -Force

        # Scripts
        foreach ($f in @("discover_cortex.py","execute_cortex.py","predict_tools.py","read_cortex_sessions.py","route_request.py","security_wrapper.py")) {
            Copy-Item "$src\scripts\$f" (Join-Path $SkillDir "scripts") -Force
        }

        # Security module
        foreach ($f in @("__init__.py","approval_handler.py","audit_logger.py","cache_manager.py","config_manager.py","prompt_sanitizer.py")) {
            Copy-Item "$src\security\$f" (Join-Path $SkillDir "security") -Force
        }
        Copy-Item "$src\security\policies\default_policy.yaml" (Join-Path $SkillDir "security\policies") -Force

        # References
        foreach ($f in @("cortex-cli-reference.md","routing-examples.md","troubleshooting-guide.md")) {
            Copy-Item "$src\references\$f" (Join-Path $SkillDir "references") -Force
        }

        # Optional docs
        foreach ($f in @("CHANGELOG.md","MIGRATION.md","SECURITY.md","SECURITY_GUIDE.md")) {
            $p = Join-Path $src $f
            if (Test-Path $p) { Copy-Item $p $SkillDir -Force }
        }

        Write-Ok "Claude-to-Cortex Code Router skill installed to $SkillDir"
        return $true
    }
    catch {
        Write-Warn "Could not clone repo (SSH access required for Snowflake-Labs members)."
        Write-Msg "  Manual install: git clone $RepoUrl and copy agent-to-agent-skills\claude-cortex-code-router\ to $SkillDir"
        return $false
    }
    finally {
        if (Test-Path $tmpDir) { Remove-Item $tmpDir -Recurse -Force -ErrorAction SilentlyContinue }
    }
}

# === Help ======================================================

if ($Help) {
    Write-Host "Snowflake AI Kit -- CLI Installer (Windows)"
    Write-Host ""
    Write-Host "Installs Snowflake CLI (snow), Cortex Code CLI (cortex), Claude Code CLI (claude), and skills."
    Write-Host ""
    Write-Host "Usage: .\install.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Check    Check installation status without installing"
    Write-Host "  -Update   Re-install skills (overwrite existing)"
    Write-Host "  -Help     Show this help"
    return
}

# === Execute ===================================================

Write-Host ""
Write-Host "Snowflake AI Kit -- CLI Installer" -ForegroundColor White
Write-Host "=================================="
Write-Host ""

if ($Check) {
    Write-Step "Checking installation status..."
    if (Test-Command "snow")   { Write-Ok "Snowflake CLI (snow) installed" }   else { Write-Warn "Snowflake CLI (snow) not found" }
    if (Test-Command "cortex") { Write-Ok "Cortex Code CLI (cortex) installed" } else { Write-Warn "Cortex Code CLI (cortex) not found" }
    if (Test-Command "claude") { Write-Ok "Claude Code CLI (claude) installed" }   else { Write-Warn "Claude Code CLI (claude) not found" }
    if (Test-Path (Join-Path $SkillDir "SKILL.md")) { Write-Ok "Claude-to-Cortex Code Router skill installed" } else { Write-Warn "Claude-to-Cortex Code Router skill not found" }
    Test-SnowflakeAuth | Out-Null
    Write-Host ""
    return
}

Write-Step "Installing CLIs..."
Install-SnowflakeCLI | Out-Null
Install-CortexCodeCLI | Out-Null
Install-ClaudeCodeCLI | Out-Null

Write-Step "Installing skills..."
Install-Skills | Out-Null

Write-Step "Checking Snowflake connection..."
Test-SnowflakeAuth | Out-Null

Write-Host ""
Write-Host "All done!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  snow --version       # Verify Snowflake CLI"
Write-Host "  cortex --version     # Verify Cortex Code CLI"
Write-Host "  claude --version     # Verify Claude Code CLI"
Write-Host "  cortex               # Start Cortex Code"
Write-Host ""
