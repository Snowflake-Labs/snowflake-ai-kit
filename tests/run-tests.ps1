#
# run-tests.ps1 -- Test harness for Snowflake AI Kit (Windows)
#
# Validates plugin structure, runs unit tests, checks content sanity.
# Updated for the plugin architecture (plugins/cortex-code/).
#
# Usage:
#   .\tests\run-tests.ps1                # Run all tests
#   .\tests\run-tests.ps1 -SkipUnit      # Skip unit tests
#   .\tests\run-tests.ps1 -Verbose       # Show extra detail
#

param(
    [switch]$SkipUnit,
    [switch]$Verbose
)

$ErrorActionPreference = "Continue"
$Pass = 0; $Fail = 0; $Warn = 0; $Skip = 0
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$PluginDir = Join-Path $RepoRoot "plugins\cortex-code"
$RouterDir = Join-Path $PluginDir "scripts\router"

# === Helpers ==================================================

function Write-Result {
    param([string]$Name, [string]$Status, [string]$Detail = "")
    switch ($Status) {
        "PASS" { Write-Host "  PASS  " -ForegroundColor Green -NoNewline; $script:Pass++ }
        "FAIL" { Write-Host "  FAIL  " -ForegroundColor Red -NoNewline; $script:Fail++ }
        "WARN" { Write-Host "  WARN  " -ForegroundColor Yellow -NoNewline; $script:Warn++ }
        "SKIP" { Write-Host "  SKIP  " -ForegroundColor DarkGray -NoNewline; $script:Skip++ }
    }
    Write-Host $Name
    if ($Detail -and $Verbose) { Write-Host "         $Detail" -ForegroundColor DarkGray }
}

# ==============================================================

Write-Host ""
Write-Host "Snowflake AI Kit -- Test Harness (Windows)" -ForegroundColor White
Write-Host "==========================================="
Write-Host ""

# === 1. Prerequisites =========================================

Write-Host "Prerequisites" -ForegroundColor Cyan

$hasPython = [bool](Get-Command "python" -ErrorAction SilentlyContinue)
Write-Result "Python available" $(if ($hasPython) { "PASS" } else { "FAIL" })

$hasGit = [bool](Get-Command "git" -ErrorAction SilentlyContinue)
Write-Result "Git available" $(if ($hasGit) { "PASS" } else { "FAIL" })

$hasCortex = [bool](Get-Command "cortex" -ErrorAction SilentlyContinue)
Write-Result "cortex CLI in PATH" $(if ($hasCortex) { "PASS" } else { "WARN" })

$hasSnow = [bool](Get-Command "snow" -ErrorAction SilentlyContinue)
Write-Result "snow CLI in PATH" $(if ($hasSnow) { "PASS" } else { "WARN" })

if ($hasCortex) {
    $cortexVer = & cortex --version 2>&1
    Write-Result "cortex --version runs ($cortexVer)" $(if ($LASTEXITCODE -eq 0) { "PASS" } else { "FAIL" })
}

if (-not (Test-Path $PluginDir)) {
    Write-Host ""
    Write-Host "ERROR: Plugin dir not found at $PluginDir" -ForegroundColor Red
    Write-Host "Run this script from the repo root: .\tests\run-tests.ps1" -ForegroundColor Red
    exit 1
}

# === 2. Plugin file structure ==================================

Write-Host ""
Write-Host "Plugin structure" -ForegroundColor Cyan

# Plugin manifest
$pluginJson = Join-Path $PluginDir ".claude-plugin\plugin.json"
Write-Result "plugin.json exists" $(if (Test-Path $pluginJson) { "PASS" } else { "FAIL" })

# Skills dirs
$skillDirs = @("cortex-router", "cortex-run", "cortex-setup")
foreach ($d in $skillDirs) {
    $p = Join-Path $PluginDir "skills\$d"
    Write-Result "skills/$d exists" $(if (Test-Path $p) { "PASS" } else { "FAIL" })
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
        Write-Result "router: $f" "FAIL"
        $allRouter = $false
    }
}
if ($allRouter) {
    Write-Result "All $($routerScripts.Count) router scripts present" "PASS"
}

# Test files
Write-Result "test_envelope_policy.py exists" $(if (Test-Path (Join-Path $RouterDir "test_envelope_policy.py")) { "PASS" } else { "FAIL" })
Write-Result "test_plugin_units.py exists" $(if (Test-Path (Join-Path $RouterDir "test_plugin_units.py")) { "PASS" } else { "FAIL" })

# === 3. Content checks ========================================

Write-Host ""
Write-Host "Content checks" -ForegroundColor Cyan

# plugin.json is valid JSON
if (Test-Path $pluginJson) {
    try {
        Get-Content $pluginJson -Raw | ConvertFrom-Json | Out-Null
        Write-Result "plugin.json is valid JSON" "PASS"
    }
    catch {
        Write-Result "plugin.json is valid JSON" "FAIL"
    }
}

# envelope_policy.py defines decide()
$epPath = Join-Path $RouterDir "envelope_policy.py"
if (Test-Path $epPath) {
    $content = Get-Content $epPath -Raw
    Write-Result "envelope_policy.py defines decide()" $(if ($content -match "def decide\(") { "PASS" } else { "FAIL" })
}

# execute_cortex.py uses --permission-prompt-tool
$exPath = Join-Path $RouterDir "execute_cortex.py"
if (Test-Path $exPath) {
    $content = Get-Content $exPath -Raw
    Write-Result "execute_cortex.py uses --permission-prompt-tool" $(if ($content -match "permission-prompt-tool") { "PASS" } else { "FAIL" })
    Write-Result "execute_cortex.py imports envelope_policy" $(if ($content -match "from envelope_policy import") { "PASS" } else { "FAIL" })
}

# session_state.py defines expected functions
$ssPath = Join-Path $RouterDir "session_state.py"
if (Test-Path $ssPath) {
    $content = Get-Content $ssPath -Raw
    Write-Result "session_state.py defines load_active_session()" $(if ($content -match "def load_active_session") { "PASS" } else { "FAIL" })
    Write-Result "session_state.py defines save_active_session()" $(if ($content -match "def save_active_session") { "PASS" } else { "FAIL" })
    Write-Result "session_state.py defines clear_active_session()" $(if ($content -match "def clear_active_session") { "PASS" } else { "FAIL" })
}

# config.yaml.example is non-empty
$cfgPath = Join-Path $RouterDir "config.yaml.example"
if (Test-Path $cfgPath) {
    Write-Result "config.yaml.example is non-empty" $(if ((Get-Item $cfgPath).Length -gt 10) { "PASS" } else { "FAIL" })
}

# === 4. Unit tests =============================================

Write-Host ""
Write-Host "Unit tests" -ForegroundColor Cyan

if ($SkipUnit) {
    Write-Result "Unit tests (skipped via -SkipUnit)" "SKIP"
}
elseif (-not $hasPython) {
    Write-Result "Unit tests (Python not available)" "SKIP"
}
else {
    # Run envelope policy tests
    Write-Host "  Running test_envelope_policy.py..."
    $output = & python -c "import sys; sys.path.insert(0, r'$RouterDir'); exec(open(r'$RouterDir\test_envelope_policy.py').read())" 2>&1 | Out-String
    if ($output -match "(\d+)/(\d+) passed") {
        $passed = $Matches[1]; $total = $Matches[2]
        Write-Result "test_envelope_policy.py: $passed/$total passed" $(if ($passed -eq $total) { "PASS" } else { "FAIL" }) $output
    }
    else {
        Write-Result "test_envelope_policy.py: could not parse results" "FAIL" $output
    }

    # Run plugin unit tests
    Write-Host "  Running test_plugin_units.py..."
    $output = & python -c "import sys; sys.path.insert(0, r'$RouterDir'); exec(open(r'$RouterDir\test_plugin_units.py').read())" 2>&1 | Out-String
    if ($output -match "(\d+)/(\d+) passed") {
        $passed = $Matches[1]; $total = $Matches[2]
        Write-Result "test_plugin_units.py: $passed/$total passed" $(if ($passed -eq $total) { "PASS" } else { "FAIL" }) $output
    }
    else {
        Write-Result "test_plugin_units.py: could not parse results" "FAIL" $output
    }
}

# === 5. Snowflake connection ===================================

Write-Host ""
Write-Host "Snowflake connection" -ForegroundColor Cyan

$connToml = Join-Path $env:USERPROFILE ".snowflake\connections.toml"
$cfgToml  = Join-Path $env:USERPROFILE ".snowflake\config.toml"
$hasConfig = (Test-Path $connToml) -or (Test-Path $cfgToml) -or $env:SNOWFLAKE_HOST -or $env:SNOWFLAKE_ACCOUNT
Write-Result "Snowflake connection configured" $(if ($hasConfig) { "PASS" } else { "WARN" })

# === Summary ===================================================

Write-Host ""
Write-Host "==========================================="
$total = $Pass + $Fail + $Warn + $Skip
Write-Host "Results ($total tests): " -NoNewline
Write-Host "$Pass passed" -ForegroundColor Green -NoNewline
Write-Host ", " -NoNewline
if ($Fail -gt 0) { Write-Host "$Fail failed" -ForegroundColor Red -NoNewline }
else { Write-Host "0 failed" -NoNewline }
Write-Host ", " -NoNewline
Write-Host "$Warn warnings" -ForegroundColor Yellow -NoNewline
Write-Host ", " -NoNewline
Write-Host "$Skip skipped" -ForegroundColor DarkGray
Write-Host ""

if ($Fail -gt 0) {
    Write-Host "SOME TESTS FAILED -- review output above." -ForegroundColor Red
    exit 1
}
elseif ($Warn -gt 0) {
    Write-Host "All critical checks passed. Warnings are non-blocking." -ForegroundColor Yellow
    exit 0
}
else {
    Write-Host "All tests passed." -ForegroundColor Green
    exit 0
}
