#
# validate-install.ps1 -- Post-install validation for Snowflake AI Kit
#
# Validates the cortex-code plugin structure and configuration.
# Updated for the plugin architecture (plugins/cortex-code/).
#
# Usage:
#   .\tests\validate-install.ps1                      # Auto-detect plugin dir
#   .\tests\validate-install.ps1 -PluginDir "C:\..."  # Explicit path
#

param(
    [string]$PluginDir = ""
)

$ErrorActionPreference = "Continue"
$Pass = 0; $Fail = 0; $Warn = 0

function Test-Check {
    param([string]$Name, [bool]$Result, [bool]$IsWarning = $false)
    if ($Result) {
        Write-Host "  PASS  " -ForegroundColor Green -NoNewline
        Write-Host $Name
        $script:Pass++
    }
    elseif ($IsWarning) {
        Write-Host "  WARN  " -ForegroundColor Yellow -NoNewline
        Write-Host $Name
        $script:Warn++
    }
    else {
        Write-Host "  FAIL  " -ForegroundColor Red -NoNewline
        Write-Host $Name
        $script:Fail++
    }
}

Write-Host ""
Write-Host "Snowflake AI Kit -- Install Validation (Plugin Architecture)" -ForegroundColor White
Write-Host "============================================================" 
Write-Host ""

# Resolve plugin directory: explicit param > repo-relative > installed cache
if (-not $PluginDir) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $RepoRoot = Split-Path -Parent $ScriptDir
    $repoPlugin = Join-Path $RepoRoot "plugins\cortex-code"
    if (Test-Path $repoPlugin) {
        $PluginDir = $repoPlugin
    }
    else {
        # Fall back to installed plugin cache
        $PluginDir = Join-Path $env:USERPROFILE ".claude\plugins\cache\snowflake-ai-kit\cortex-code"
        # Find latest version dir
        if (Test-Path $PluginDir) {
            $latest = Get-ChildItem $PluginDir -Directory | Sort-Object Name -Descending | Select-Object -First 1
            if ($latest) { $PluginDir = $latest.FullName }
        }
    }
}

$RouterDir = Join-Path $PluginDir "scripts\router"
Write-Host "Plugin dir: $PluginDir" -ForegroundColor DarkGray
Write-Host "Router dir: $RouterDir" -ForegroundColor DarkGray
Write-Host ""

# === 1. CLI availability ======================================

Write-Host "CLIs" -ForegroundColor Cyan

$snowFound = [bool](Get-Command "snow" -ErrorAction SilentlyContinue)
Test-Check "snow CLI in PATH" $snowFound

$cortexFound = [bool](Get-Command "cortex" -ErrorAction SilentlyContinue)
Test-Check "cortex CLI in PATH" $cortexFound

$pythonFound = [bool](Get-Command "python" -ErrorAction SilentlyContinue) -or [bool](Get-Command "python3" -ErrorAction SilentlyContinue)
Test-Check "Python in PATH" $pythonFound

if ($snowFound) {
    $snowVer = & snow --version 2>&1
    Test-Check "snow --version runs ($snowVer)" ($LASTEXITCODE -eq 0)
}

if ($cortexFound) {
    $cortexVer = & cortex --version 2>&1
    Test-Check "cortex --version runs ($cortexVer)" ($LASTEXITCODE -eq 0)
}

# === 2. Plugin file structure =================================

Write-Host ""
Write-Host "Plugin structure" -ForegroundColor Cyan

# Plugin manifest
$pluginJson = Join-Path $PluginDir ".claude-plugin\plugin.json"
Test-Check "plugin.json exists" (Test-Path $pluginJson)

# Skills dirs
$skillDirs = @("cortex-router", "cortex-run", "cortex-setup")
foreach ($d in $skillDirs) {
    $p = Join-Path $PluginDir "skills\$d"
    Test-Check "skills/$d exists" (Test-Path $p)
}

# Router scripts (current architecture)
$routerScripts = @(
    "config.yaml.example",
    "discover_cortex.py",
    "envelope_policy.py",
    "execute_cortex.py",
    "predict_tools.py",
    "prompt_filter.py",
    "read_cortex_sessions.py",
    "route_request.py",
    "session_state.py"
)
$allRouter = $true
foreach ($f in $routerScripts) {
    if (-not (Test-Path (Join-Path $RouterDir $f))) {
        Test-Check "router: $f" $false
        $allRouter = $false
    }
}
if ($allRouter) {
    Test-Check "All $($routerScripts.Count) router scripts present" $true
}

# Test files
Test-Check "test_envelope_policy.py exists" (Test-Path (Join-Path $RouterDir "test_envelope_policy.py"))
Test-Check "test_plugin_units.py exists" (Test-Path (Join-Path $RouterDir "test_plugin_units.py"))

# === 3. Content checks ========================================

Write-Host ""
Write-Host "Content checks" -ForegroundColor Cyan

# plugin.json is valid JSON
if (Test-Path $pluginJson) {
    try {
        Get-Content $pluginJson -Raw | ConvertFrom-Json | Out-Null
        Test-Check "plugin.json is valid JSON" $true
    }
    catch {
        Test-Check "plugin.json is valid JSON" $false
    }
}

# envelope_policy.py defines decide()
$epPath = Join-Path $RouterDir "envelope_policy.py"
if (Test-Path $epPath) {
    $content = Get-Content $epPath -Raw
    Test-Check "envelope_policy.py defines decide()" ($content -match "(?m)^def decide\(" )
}

# execute_cortex.py uses --permission-prompt-tool
$exPath = Join-Path $RouterDir "execute_cortex.py"
if (Test-Path $exPath) {
    $content = Get-Content $exPath -Raw
    Test-Check "execute_cortex.py uses --permission-prompt-tool" ($content -match "permission-prompt-tool")
    Test-Check "execute_cortex.py imports envelope_policy" ($content -match "from envelope_policy import")
}

# session_state.py defines expected functions
$ssPath = Join-Path $RouterDir "session_state.py"
if (Test-Path $ssPath) {
    $content = Get-Content $ssPath -Raw
    Test-Check "session_state.py defines load_active_session()" ($content -match "def load_active_session")
    Test-Check "session_state.py defines save_active_session()" ($content -match "def save_active_session")
    Test-Check "session_state.py defines clear_active_session()" ($content -match "def clear_active_session")
}

# config.yaml.example is non-empty
$cfgPath = Join-Path $RouterDir "config.yaml.example"
if (Test-Path $cfgPath) {
    Test-Check "config.yaml.example is non-empty" ((Get-Item $cfgPath).Length -gt 10)
}

# === 4. Snowflake connection ==================================

Write-Host ""
Write-Host "Snowflake connection" -ForegroundColor Cyan

$connToml = Join-Path $env:USERPROFILE ".snowflake\connections.toml"
$cfgToml  = Join-Path $env:USERPROFILE ".snowflake\config.toml"
$hasConfig = (Test-Path $connToml) -or (Test-Path $cfgToml) -or $env:SNOWFLAKE_HOST -or $env:SNOWFLAKE_ACCOUNT
Test-Check "Snowflake connection configured" $hasConfig -IsWarning:$true

# === 5. Temp dir cleanup =====================================

Write-Host ""
Write-Host "Cleanup" -ForegroundColor Cyan

$leftover = Get-ChildItem $env:TEMP -Directory -Filter "snowflake-ai-kit-*" -ErrorAction SilentlyContinue
Test-Check "No leftover temp dirs" ($null -eq $leftover -or $leftover.Count -eq 0)

# === Summary ==================================================

Write-Host ""
Write-Host "============================================================" 
Write-Host "Results: " -NoNewline
Write-Host "$Pass passed" -ForegroundColor Green -NoNewline
Write-Host ", " -NoNewline
if ($Fail -gt 0) {
    Write-Host "$Fail failed" -ForegroundColor Red -NoNewline
} else {
    Write-Host "0 failed" -NoNewline
}
Write-Host ", " -NoNewline
Write-Host "$Warn warnings" -ForegroundColor Yellow
Write-Host ""

if ($Fail -gt 0) {
    Write-Host "Some checks failed. Review output above." -ForegroundColor Red
    exit 1
}
elseif ($Warn -gt 0) {
    Write-Host "All critical checks passed. Warnings are non-blocking." -ForegroundColor Yellow
    exit 0
}
else {
    Write-Host "All checks passed." -ForegroundColor Green
    exit 0
}
