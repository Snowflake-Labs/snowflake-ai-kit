#
# Snowflake AI Kit — Unified Installer (Windows)
#
# One command to install skills, builder apps, or both.
# Also installs Snowflake CLI (snow) and Cortex Code CLI (cortex) if missing.
#
# Usage:
#   # Download and run interactively
#   irm https://raw.githubusercontent.com/Snowflake-Labs/snowflake-ai-kit/main/install.ps1 | iex
#
#   # Download first, then run with options
#   irm https://raw.githubusercontent.com/Snowflake-Labs/snowflake-ai-kit/main/install.ps1 -OutFile install.ps1
#   .\install.ps1 -SkillsOnly
#   .\install.ps1 -App cortex-agent
#   .\install.ps1 -All
#   .\install.ps1 -List
#

param(
    [switch]$SkillsOnly,
    [string]$App,
    [switch]$All,
    [string]$Agent,
    [switch]$List,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

$RepoUrl = "https://github.com/Snowflake-Labs/snowflake-ai-kit.git"
$Troubleshoot = "https://github.com/Snowflake-Labs/snowflake-ai-kit#troubleshooting"
$RepoRaw = "https://raw.githubusercontent.com/Snowflake-Labs/snowflake-ai-kit/main"

# ─── Output helpers ───────────────────────────────────────────

function Write-Msg  { param([string]$Text) Write-Host "  $Text" }
function Write-Ok   { param([string]$Text) Write-Host "  " -NoNewline; Write-Host "v" -ForegroundColor Green -NoNewline; Write-Host " $Text" }
function Write-Warn { param([string]$Text) Write-Host "  " -NoNewline; Write-Host "!" -ForegroundColor Yellow -NoNewline; Write-Host " $Text" }
function Write-Err  { param([string]$Text) Write-Host "  " -NoNewline; Write-Host "x" -ForegroundColor Red -NoNewline; Write-Host " $Text"; exit 1 }
function Write-Step { param([string]$Text) Write-Host ""; Write-Host "$Text" -ForegroundColor White }

# ─── Prereq checks ────────────────────────────────────────────

function Test-Command { param([string]$Name) return [bool](Get-Command $Name -ErrorAction SilentlyContinue) }

function Test-Prerequisites {
    $missing = @()
    if (-not (Test-Command "python"))  { if (-not (Test-Command "python3")) { $missing += "python" } }
    if (-not (Test-Command "node"))    { $missing += "node" }
    if (-not (Test-Command "npm"))     { $missing += "npm" }

    if ($missing.Count -gt 0) {
        Write-Warn "Missing prerequisites: $($missing -join ', ')"
        return $false
    }
    Write-Ok "Prerequisites OK (python, node, npm)"
    return $true
}

function Get-PythonCmd {
    if (Test-Command "python") { return "python" }
    if (Test-Command "python3") { return "python3" }
    return $null
}

function Get-PipCmd {
    if (Test-Command "uv") { return "uv pip" }
    if (Test-Command "pip") { return "pip" }
    if (Test-Command "pip3") { return "pip3" }
    return "pip"
}

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
    $pipCmd = Get-PipCmd
    if ($pipCmd) {
        if ($pipCmd -eq "uv pip") {
            & uv pip install snowflake-cli 2>$null
        } else {
            & $pipCmd install snowflake-cli 2>$null
        }
        if ($LASTEXITCODE -eq 0) { Write-Ok "Snowflake CLI installed via $pipCmd"; return $true }
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

# ─── Detect repo root ─────────────────────────────────────────

function Find-RepoRoot {
    if ((Test-Path "snowflake-skills") -and (Test-Path "README.md")) {
        return "."
    }
    if (Test-Path "snowflake-ai-kit\snowflake-skills") {
        return "snowflake-ai-kit"
    }
    return $null
}

function Ensure-Repo {
    $root = Find-RepoRoot
    if ($root) {
        $script:RepoRoot = $root
        Write-Ok "Found repo at $script:RepoRoot"
    }
    else {
        Write-Step "Cloning snowflake-ai-kit..."
        if (Test-Command "git") {
            git clone $RepoUrl snowflake-ai-kit 2>$null
            if ($LASTEXITCODE -ne 0) { Write-Err "Failed to clone repo" }
            $script:RepoRoot = "snowflake-ai-kit"
            Write-Ok "Cloned to .\snowflake-ai-kit"
        }
        else {
            Write-Err "git is required to install builder apps. Install git or use -SkillsOnly."
        }
    }
}

# ─── Install skills ────────────────────────────────────────────

function Install-Skills {
    param([string[]]$ExtraArgs = @())

    $root = Find-RepoRoot
    if ($root) {
        $scriptPath = Join-Path $root "snowflake-skills\install_skills.sh"
        if (Test-Command "bash") {
            $allArgs = @($scriptPath) + $ExtraArgs
            & bash @allArgs
        }
        else {
            # Fallback: download skills directly via PowerShell
            Install-SkillsDirect -ExtraArgs $ExtraArgs
        }
    }
    else {
        if (Test-Command "bash") {
            $tempScript = Join-Path $env:TEMP "install_skills.sh"
            Invoke-WebRequest -Uri "$RepoRaw/snowflake-skills/install_skills.sh" -OutFile $tempScript -UseBasicParsing
            $allArgs = @($tempScript) + $ExtraArgs
            & bash @allArgs
            Remove-Item $tempScript -ErrorAction SilentlyContinue
        }
        else {
            Install-SkillsDirect -ExtraArgs $ExtraArgs
        }
    }
}

function Install-SkillsDirect {
    param([string[]]$ExtraArgs = @())

    # Pure PowerShell skill installer (no bash dependency)
    $skills = @(
        "cortex-agents", "cortex-ai-pipeline", "cortex-mcp-server", "cortex-search-rag",
        "data-product-sharing", "dynamic-tables-pipeline", "iceberg-tables", "ml-model-registry",
        "snowflake-docs", "snowflake-postgres", "snowpipe-streaming-java", "snowpipe-streaming-python",
        "ssis-to-dbt-replatform-migration", "streamlit-in-snowflake", "tasks-and-streams"
    )
    $generalSkills = @("docker-dev-setup", "drizzle-orm-setup", "supabase-auth-rls")

    if ($ExtraArgs -contains "--list" -or $ExtraArgs -contains "-l") {
        Write-Host ""
        Write-Host "Snowflake Skills" -ForegroundColor White
        Write-Host "------------------------------"
        foreach ($s in $skills) { Write-Host "  $s" }
        Write-Host ""
        Write-Host "General-Purpose Skills" -ForegroundColor White
        Write-Host "------------------------------"
        foreach ($s in $generalSkills) { Write-Host "  $s" }
        Write-Host ""
        return
    }

    # Detect agent
    $agentIdx = [Array]::IndexOf($ExtraArgs, "--agent")
    if ($agentIdx -eq -1) { $agentIdx = [Array]::IndexOf($ExtraArgs, "-a") }
    $targetAgent = ""
    if ($agentIdx -ge 0 -and ($agentIdx + 1) -lt $ExtraArgs.Count) {
        $targetAgent = $ExtraArgs[$agentIdx + 1]
    }

    $agents = @()
    if ($targetAgent) {
        $agents = @($targetAgent)
    }
    else {
        # Auto-detect
        if (Test-Path ".cursor")   { $agents += "cursor" }
        if (Test-Path ".windsurf") { $agents += "windsurf" }
        if (Test-Path ".claude")   { $agents += "claude" }
        if (Test-Path ".gemini")   { $agents += "gemini" }
        if ($agents.Count -eq 0)   { $agents = @("cursor", "windsurf", "claude", "gemini") }
    }

    Write-Host ""
    Write-Host "Snowflake AI Kit - Skills Installer" -ForegroundColor White
    Write-Host "------------------------------------"
    Write-Host ""

    $allSkills = $skills + $generalSkills
    $count = 0

    foreach ($skill in $allSkills) {
        $skillPath = if ($skill -in $generalSkills) { "general-skills" } else { "snowflake-skills" }
        $url = "$RepoRaw/$skillPath/$skill/SKILL.md"

        foreach ($agent in $agents) {
            switch ($agent) {
                "cursor"   { $dir = ".cursor\rules"; $ext = ".mdc" }
                "windsurf" { $dir = ".windsurf\rules"; $ext = ".md" }
                "claude"   { $dir = ".claude\rules"; $ext = ".md" }
                "gemini"   { $dir = ".gemini"; $ext = ".md" }
                default    { continue }
            }

            if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
            $outFile = Join-Path $dir "$skill$ext"

            try {
                Invoke-WebRequest -Uri $url -OutFile $outFile -UseBasicParsing -ErrorAction Stop
                Write-Ok "$skill -> $agent"
            }
            catch {
                Write-Warn "Failed to download $skill for $agent"
            }
        }
        $count++
    }

    Write-Host ""
    Write-Host "Done! Installed $count skill(s) for: $($agents -join ', ')" -ForegroundColor Green
    Write-Host "Skills are ready to use. Your AI coding agent will load them automatically."
    Write-Host ""
}

# ─── Install builder app ──────────────────────────────────────

function Install-App {
    param([string]$AppName)

    $appDir = Join-Path $script:RepoRoot "builder-apps\$AppName"
    if (-not (Test-Path $appDir)) { Write-Err "App not found: $appDir" }

    Write-Step "Setting up $AppName..."

    $hasPrereqs = Test-Prerequisites
    if (-not $hasPrereqs) { Write-Err "Install missing prerequisites and try again." }
    Test-SnowflakeAuth | Out-Null

    # Create .env.local
    $envLocal = Join-Path $appDir ".env.local"
    $envExample = Join-Path $appDir ".env.example"
    if (-not (Test-Path $envLocal)) {
        Copy-Item $envExample $envLocal
        Write-Ok "Created .env.local from .env.example"
    }
    else {
        Write-Msg ".env.local already exists, skipping"
    }

    # Install Python deps
    $pipCmd = Get-PipCmd
    Write-Msg "Installing Python dependencies..."
    Push-Location $appDir
    try {
        if ($pipCmd -eq "uv pip") {
            & uv pip install -r requirements.txt
        }
        else {
            & $pipCmd install -r requirements.txt
        }

        # claude-agent has editable packages
        if ($AppName -eq "claude-agent") {
            if ($pipCmd -eq "uv pip") {
                & uv pip install -e packages/snowflake-tools-core -e packages/snowflake-mcp-server
            }
            else {
                & $pipCmd install -e packages/snowflake-tools-core -e packages/snowflake-mcp-server
            }
        }
    }
    finally { Pop-Location }
    Write-Ok "Python dependencies installed"

    # Install Node deps
    Write-Msg "Installing Node dependencies..."
    Push-Location (Join-Path $appDir "client")
    try { & npm install }
    finally { Pop-Location }
    Write-Ok "Node dependencies installed"

    # claude-agent needs projects dir
    if ($AppName -eq "claude-agent") {
        $projDir = Join-Path $appDir "projects"
        if (-not (Test-Path $projDir)) { New-Item -ItemType Directory -Path $projDir -Force | Out-Null }
    }

    Write-Host ""
    Write-Ok "$AppName is ready"
    Write-Host ""

    if ($AppName -eq "cortex-agent") {
        Write-Msg "Next steps:"
        Write-Msg "  1. Run setup.sql in a Snowflake worksheet to create sample data + agent"
        Write-Msg "  2. Edit $appDir\.env.local with your Snowflake credentials"
        Write-Msg "  3. Start the app: cd $appDir; .\scripts\dev.sh"
    }
    elseif ($AppName -eq "claude-agent") {
        Write-Msg "Next steps:"
        Write-Msg "  1. Edit $appDir\.env.local with your Snowflake + Anthropic credentials"
        Write-Msg "  2. Start the app: cd $appDir; .\scripts\dev.sh"
    }
}

# ─── Interactive mode ──────────────────────────────────────────

function Start-Interactive {
    Write-Host ""
    Write-Host "Snowflake AI Kit - Installer" -ForegroundColor White
    Write-Host "------------------------------"
    Write-Host ""

    Write-Step "Checking prerequisites..."
    $hasPrereqs = Test-Prerequisites
    Test-SnowflakeAuth | Out-Null

    # Install Snowflake CLIs if missing
    Write-Step "Installing Snowflake CLI and Cortex Code CLI (if needed)..."
    Install-SnowflakeCLI | Out-Null
    Install-CortexCodeCLI | Out-Null
    Write-Host ""

    Write-Host "What would you like to install?"
    Write-Host ""
    Write-Host "  1  Skills only - add Snowflake skills to your AI coding agent" -ForegroundColor White
    if ($hasPrereqs) {
        Write-Host "  2  Skills + Claude Agent App - needs Anthropic API key" -ForegroundColor White
        Write-Host "  3  Skills + Cortex Agent App - no external API key needed" -ForegroundColor White
        Write-Host "  4  Everything - skills + all builder apps" -ForegroundColor White
    }
    else {
        Write-Host "  2  Skills + Claude Agent App (requires python, node, npm)" -ForegroundColor DarkGray
        Write-Host "  3  Skills + Cortex Agent App (requires python, node, npm)" -ForegroundColor DarkGray
        Write-Host "  4  Everything (requires python, node, npm)" -ForegroundColor DarkGray
    }
    Write-Host ""
    $choice = Read-Host "  Choose [1-4]"

    switch ($choice) {
        "1" {
            Install-Skills
        }
        "2" {
            Install-Skills
            Ensure-Repo
            Install-App "claude-agent"
        }
        "3" {
            Install-Skills
            Ensure-Repo
            Install-App "cortex-agent"
        }
        "4" {
            Install-Skills
            Ensure-Repo
            Install-App "claude-agent"
            Install-App "cortex-agent"
        }
        default {
            Write-Err "Invalid choice: $choice"
        }
    }
}

# ─── Help ──────────────────────────────────────────────────────

if ($Help) {
    Write-Host "Snowflake AI Kit - Unified Installer (Windows)"
    Write-Host ""
    Write-Host "Installs Snowflake CLI (snow) and Cortex Code CLI (cortex) automatically,"
    Write-Host "then sets up skills, builder apps, or both."
    Write-Host ""
    Write-Host "Usage: .\install.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Modes:"
    Write-Host "  (no flags)             Interactive - prompts for what to install"
    Write-Host "  -SkillsOnly            Install skills only (no builder apps)"
    Write-Host "  -App NAME              Install skills + a builder app (claude-agent or cortex-agent)"
    Write-Host "  -All                   Install skills + all builder apps"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Agent NAME            Install for specific agent (cursor, windsurf, claude, gemini, cortex)"
    Write-Host "  -List                  List available skills"
    Write-Host "  -Help                  Show this help"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\install.ps1                          # Interactive"
    Write-Host "  .\install.ps1 -SkillsOnly              # Just skills, auto-detect agents"
    Write-Host "  .\install.ps1 -App cortex-agent         # Skills + Cortex Agent app"
    Write-Host "  .\install.ps1 -All -Agent cursor        # Everything, skills for Cursor only"
    Write-Host "  .\install.ps1 -List                     # List available skills"
    return
}

# ─── Execute ───────────────────────────────────────────────────

$extraArgs = @()
if ($Agent) { $extraArgs += "--agent"; $extraArgs += $Agent }

if ($List) {
    Install-Skills -ExtraArgs @("--list")
    return
}

# Install Snowflake CLIs if missing (skip for --list)
Write-Step "Installing Snowflake CLI and Cortex Code CLI (if needed)..."
Install-SnowflakeCLI | Out-Null
Install-CortexCodeCLI | Out-Null

if ($SkillsOnly) {
    Install-Skills -ExtraArgs $extraArgs
}
elseif ($App) {
    if ($App -ne "claude-agent" -and $App -ne "cortex-agent") {
        Write-Err "Unknown app: $App (choose: claude-agent, cortex-agent)"
    }
    Install-Skills -ExtraArgs $extraArgs
    Ensure-Repo
    Install-App $App
}
elseif ($All) {
    Install-Skills -ExtraArgs $extraArgs
    Ensure-Repo
    Install-App "claude-agent"
    Install-App "cortex-agent"
}
else {
    Start-Interactive
}

Write-Host ""
Write-Host "All done!" -ForegroundColor Green
Write-Host ""
