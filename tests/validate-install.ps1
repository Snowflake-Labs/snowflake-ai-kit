#
# validate-install.ps1 -- Post-install validation for Snowflake AI Kit
#
# Run after install.ps1 to verify everything landed correctly.
#
# Usage:
#   .\tests\validate-install.ps1
#

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
Write-Host "Snowflake AI Kit -- Install Validation" -ForegroundColor White
Write-Host "======================================" 
Write-Host ""

# === 1. CLI availability ======================================

Write-Host "CLIs" -ForegroundColor Cyan

$snowFound = [bool](Get-Command "snow" -ErrorAction SilentlyContinue)
Test-Check "snow CLI in PATH" $snowFound

$cortexFound = [bool](Get-Command "cortex" -ErrorAction SilentlyContinue)
Test-Check "cortex CLI in PATH" $cortexFound

$claudeFound = [bool](Get-Command "claude" -ErrorAction SilentlyContinue)
Test-Check "claude CLI in PATH" $claudeFound -IsWarning:$true

if ($snowFound) {
    $snowVer = & snow --version 2>&1
    Test-Check "snow --version runs ($snowVer)" ($LASTEXITCODE -eq 0)
}

if ($cortexFound) {
    $cortexVer = & cortex --version 2>&1
    Test-Check "cortex --version runs ($cortexVer)" ($LASTEXITCODE -eq 0)
}

if ($claudeFound) {
    $claudeVer = & claude --version 2>&1
    Test-Check "claude --version runs ($claudeVer)" ($LASTEXITCODE -eq 0)
}

# === 2. Skill file structure =================================

Write-Host ""
Write-Host "Skill files" -ForegroundColor Cyan

$skillDir = Join-Path $env:USERPROFILE ".claude\skills\cortex-code"

# Core files
$coreFiles = @("SKILL.md", "README.md", "config.yaml.example")
foreach ($f in $coreFiles) {
    $p = Join-Path $skillDir $f
    Test-Check "core: $f" (Test-Path $p)
}

# Scripts
$scripts = @(
    "discover_cortex.py",
    "execute_cortex.py",
    "predict_tools.py",
    "read_cortex_sessions.py",
    "route_request.py",
    "security_wrapper.py"
)
foreach ($f in $scripts) {
    $p = Join-Path $skillDir "scripts\$f"
    Test-Check "scripts: $f" (Test-Path $p)
}

# Security module
$secFiles = @(
    "__init__.py",
    "approval_handler.py",
    "audit_logger.py",
    "cache_manager.py",
    "config_manager.py",
    "prompt_sanitizer.py"
)
foreach ($f in $secFiles) {
    $p = Join-Path $skillDir "security\$f"
    Test-Check "security: $f" (Test-Path $p)
}

$policyPath = Join-Path $skillDir "security\policies\default_policy.yaml"
Test-Check "security: policies/default_policy.yaml" (Test-Path $policyPath)

# References
$refs = @(
    "cortex-cli-reference.md",
    "routing-examples.md",
    "troubleshooting-guide.md"
)
foreach ($f in $refs) {
    $p = Join-Path $skillDir "references\$f"
    Test-Check "references: $f" (Test-Path $p)
}

# Optional docs (warn-only if missing)
$optDocs = @("CHANGELOG.md", "MIGRATION.md", "SECURITY.md", "SECURITY_GUIDE.md")
foreach ($f in $optDocs) {
    $p = Join-Path $skillDir $f
    Test-Check "optional: $f" (Test-Path $p) -IsWarning:$true
}

# === 3. File content sanity ==================================

Write-Host ""
Write-Host "Content checks" -ForegroundColor Cyan

$skillMd = Join-Path $skillDir "SKILL.md"
if (Test-Path $skillMd) {
    $content = Get-Content $skillMd -Raw
    Test-Check "SKILL.md is non-empty" ($content.Length -gt 100)
    Test-Check "SKILL.md contains routing keyword" ($content -match "(?i)(route|cortex|claude)")
}

$configExample = Join-Path $skillDir "config.yaml.example"
if (Test-Path $configExample) {
    $content = Get-Content $configExample -Raw
    Test-Check "config.yaml.example is non-empty" ($content.Length -gt 10)
}

# === 4. Snowflake connection =================================

Write-Host ""
Write-Host "Snowflake connection" -ForegroundColor Cyan

$configPath = Join-Path $env:USERPROFILE ".snowflake\connections.toml"
$hasConfig = (Test-Path $configPath) -or $env:SNOWFLAKE_HOST -or $env:SNOWFLAKE_ACCOUNT
Test-Check "Snowflake connection configured" $hasConfig -IsWarning:$true

# === 5. Temp dir cleanup =====================================

Write-Host ""
Write-Host "Cleanup" -ForegroundColor Cyan

$leftover = Get-ChildItem $env:TEMP -Directory -Filter "snowflake-ai-kit-*" -ErrorAction SilentlyContinue
Test-Check "No leftover temp dirs" ($null -eq $leftover -or $leftover.Count -eq 0)

# === Summary ==================================================

Write-Host ""
Write-Host "======================================" 
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
