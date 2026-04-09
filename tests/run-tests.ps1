#
# run-tests.ps1 -- Full test harness for Snowflake AI Kit installers
#
# Tests all installer modes: -Help, -Check, full install, idempotency, -Update, npx.
# Designed to run on a fresh Windows 11 VM (Parallels or otherwise).
#
# Usage:
#   .\tests\run-tests.ps1                # Run all tests
#   .\tests\run-tests.ps1 -SkipInstall   # Skip actual install (validate only)
#   .\tests\run-tests.ps1 -Verbose       # Show command output
#

param(
    [switch]$SkipInstall,
    [switch]$Verbose
)

$ErrorActionPreference = "Continue"
$Pass = 0; $Fail = 0; $Skip = 0
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$SkillDir = Join-Path $env:USERPROFILE ".claude\skills\cortex-code"
$InstallerPs1 = Join-Path $RepoRoot "install.ps1"

# === Helpers ==================================================

function Write-Result {
    param([string]$Name, [string]$Status, [string]$Detail = "")
    switch ($Status) {
        "PASS" { Write-Host "  PASS  " -ForegroundColor Green -NoNewline; $script:Pass++ }
        "FAIL" { Write-Host "  FAIL  " -ForegroundColor Red -NoNewline; $script:Fail++ }
        "SKIP" { Write-Host "  SKIP  " -ForegroundColor DarkGray -NoNewline; $script:Skip++ }
    }
    Write-Host $Name
    if ($Detail -and $Verbose) { Write-Host "         $Detail" -ForegroundColor DarkGray }
}

function Invoke-Installer {
    param([string[]]$Args)
    $output = & powershell -NoProfile -ExecutionPolicy Bypass -File $InstallerPs1 @Args 2>&1 | Out-String
    return @{ Output = $output; ExitCode = $LASTEXITCODE }
}

function Remove-Skills {
    if (Test-Path $SkillDir) {
        Remove-Item $SkillDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# === Prereq check ============================================

Write-Host ""
Write-Host "Snowflake AI Kit -- Test Harness" -ForegroundColor White
Write-Host "================================"
Write-Host ""

Write-Host "Prerequisites" -ForegroundColor Cyan

$hasPython = [bool](Get-Command "python" -ErrorAction SilentlyContinue)
Write-Result "Python available" $(if ($hasPython) { "PASS" } else { "FAIL" }) 

$hasGit = [bool](Get-Command "git" -ErrorAction SilentlyContinue)
Write-Result "Git available" $(if ($hasGit) { "PASS" } else { "FAIL" })

$hasNode = [bool](Get-Command "node" -ErrorAction SilentlyContinue)
Write-Result "Node.js available (for npx test)" $(if ($hasNode) { "PASS" } else { "SKIP" })

if (-not (Test-Path $InstallerPs1)) {
    Write-Host ""
    Write-Host "ERROR: install.ps1 not found at $InstallerPs1" -ForegroundColor Red
    Write-Host "Run this script from the repo: .\tests\run-tests.ps1" -ForegroundColor Red
    exit 1
}

# ==============================================================
# TEST 1: -Help flag
# ==============================================================

Write-Host ""
Write-Host "Test 1: -Help flag" -ForegroundColor Cyan

$r = Invoke-Installer -Args @("-Help")
Write-Result "-Help exits cleanly" $(if ($r.ExitCode -eq 0) { "PASS" } else { "FAIL" }) $r.Output
Write-Result "-Help output contains usage info" $(if ($r.Output -match "(?i)usage|options|help") { "PASS" } else { "FAIL" })
Write-Result "-Help does not install anything" $(if ($r.Output -notmatch "(?i)installing") { "PASS" } else { "FAIL" })

# ==============================================================
# TEST 2: -Check on clean machine (before install)
# ==============================================================

Write-Host ""
Write-Host "Test 2: -Check (pre-install)" -ForegroundColor Cyan

# Remove skills to simulate clean state for this test
$hadSkills = Test-Path (Join-Path $SkillDir "SKILL.md")
Remove-Skills

$r = Invoke-Installer -Args @("-Check")
Write-Result "-Check exits cleanly" $(if ($r.ExitCode -eq 0) { "PASS" } else { "FAIL" }) $r.Output
Write-Result "-Check reports skill status" $(if ($r.Output -match "(?i)(skill|router)") { "PASS" } else { "FAIL" })
Write-Result "-Check does not modify filesystem" $(if (-not (Test-Path (Join-Path $SkillDir "SKILL.md"))) { "PASS" } else { "FAIL" })

# ==============================================================
# TEST 3: Full install
# ==============================================================

Write-Host ""
Write-Host "Test 3: Full install" -ForegroundColor Cyan

if ($SkipInstall) {
    Write-Result "Full install (skipped via -SkipInstall)" "SKIP"
}
else {
    Remove-Skills
    $r = Invoke-Installer
    Write-Result "Installer exits cleanly" $(if ($r.ExitCode -eq 0) { "PASS" } else { "FAIL" }) $r.Output
    Write-Result "Output contains 'All done'" $(if ($r.Output -match "(?i)all done") { "PASS" } else { "FAIL" })

    # Validate file structure
    $coreFiles = @("SKILL.md", "README.md", "config.yaml.example")
    foreach ($f in $coreFiles) {
        $exists = Test-Path (Join-Path $SkillDir $f)
        Write-Result "Installed: $f" $(if ($exists) { "PASS" } else { "FAIL" })
    }

    $scriptFiles = @("discover_cortex.py","execute_cortex.py","predict_tools.py","read_cortex_sessions.py","route_request.py","security_wrapper.py")
    $allScripts = $true
    foreach ($f in $scriptFiles) {
        if (-not (Test-Path (Join-Path $SkillDir "scripts\$f"))) { $allScripts = $false; break }
    }
    Write-Result "All 6 script files present" $(if ($allScripts) { "PASS" } else { "FAIL" })

    $secFiles = @("__init__.py","approval_handler.py","audit_logger.py","cache_manager.py","config_manager.py","prompt_sanitizer.py")
    $allSec = $true
    foreach ($f in $secFiles) {
        if (-not (Test-Path (Join-Path $SkillDir "security\$f"))) { $allSec = $false; break }
    }
    Write-Result "All 6 security module files present" $(if ($allSec) { "PASS" } else { "FAIL" })

    Write-Result "Policy YAML present" $(if (Test-Path (Join-Path $SkillDir "security\policies\default_policy.yaml")) { "PASS" } else { "FAIL" })

    $refFiles = @("cortex-cli-reference.md","routing-examples.md","troubleshooting-guide.md")
    $allRefs = $true
    foreach ($f in $refFiles) {
        if (-not (Test-Path (Join-Path $SkillDir "references\$f"))) { $allRefs = $false; break }
    }
    Write-Result "All 3 reference files present" $(if ($allRefs) { "PASS" } else { "FAIL" })

    # Temp dir cleanup
    $leftover = Get-ChildItem $env:TEMP -Directory -Filter "snowflake-ai-kit-*" -ErrorAction SilentlyContinue
    Write-Result "Temp dir cleaned up" $(if ($null -eq $leftover -or $leftover.Count -eq 0) { "PASS" } else { "FAIL" })
}

# ==============================================================
# TEST 4: Idempotency (run again, should skip everything)
# ==============================================================

Write-Host ""
Write-Host "Test 4: Idempotency" -ForegroundColor Cyan

if ($SkipInstall) {
    Write-Result "Idempotency (skipped via -SkipInstall)" "SKIP"
}
else {
    $r = Invoke-Installer
    Write-Result "Second run exits cleanly" $(if ($r.ExitCode -eq 0) { "PASS" } else { "FAIL" }) $r.Output
    Write-Result "Reports already installed" $(if ($r.Output -match "(?i)already installed") { "PASS" } else { "FAIL" })
}

# ==============================================================
# TEST 5: -Update flag (overwrites skills)
# ==============================================================

Write-Host ""
Write-Host "Test 5: -Update flag" -ForegroundColor Cyan

if ($SkipInstall) {
    Write-Result "Update (skipped via -SkipInstall)" "SKIP"
}
else {
    # Tamper with a file so we can verify overwrite
    $markerFile = Join-Path $SkillDir "SKILL.md"
    if (Test-Path $markerFile) {
        $originalSize = (Get-Item $markerFile).Length
        Add-Content $markerFile "`n# TAMPERED BY TEST"
        $tamperedSize = (Get-Item $markerFile).Length
        Write-Result "Tampered SKILL.md for overwrite test" $(if ($tamperedSize -gt $originalSize) { "PASS" } else { "FAIL" })
    }

    $r = Invoke-Installer -Args @("-Update")
    Write-Result "-Update exits cleanly" $(if ($r.ExitCode -eq 0) { "PASS" } else { "FAIL" }) $r.Output

    # Check the tamper was reverted
    if (Test-Path $markerFile) {
        $content = Get-Content $markerFile -Raw
        Write-Result "SKILL.md restored (tamper removed)" $(if ($content -notmatch "TAMPERED BY TEST") { "PASS" } else { "FAIL" })
    }
}

# ==============================================================
# TEST 6: -Check after install
# ==============================================================

Write-Host ""
Write-Host "Test 6: -Check (post-install)" -ForegroundColor Cyan

if ($SkipInstall) {
    Write-Result "Post-install check (skipped via -SkipInstall)" "SKIP"
}
else {
    $r = Invoke-Installer -Args @("-Check")
    Write-Result "-Check exits cleanly" $(if ($r.ExitCode -eq 0) { "PASS" } else { "FAIL" }) $r.Output
    # After full install, skill should show as installed
    Write-Result "-Check reports skill installed" $(if ($r.Output -match "(?i)skill.*installed") { "PASS" } else { "FAIL" })
}

# ==============================================================
# TEST 7: npx path (if Node available)
# ==============================================================

Write-Host ""
Write-Host "Test 7: npx entry point" -ForegroundColor Cyan

if (-not $hasNode) {
    Write-Result "npx test (Node.js not available)" "SKIP"
}
elseif ($SkipInstall) {
    Write-Result "npx test (skipped via -SkipInstall)" "SKIP"
}
else {
    # Just test that install.mjs detects Windows correctly
    $mjs = Join-Path $RepoRoot "bin\install.mjs"
    if (Test-Path $mjs) {
        $content = Get-Content $mjs -Raw
        Write-Result "install.mjs exists" "PASS"
        Write-Result "install.mjs detects win32" $(if ($content -match 'win32') { "PASS" } else { "FAIL" })
        Write-Result "install.mjs calls install.ps1" $(if ($content -match 'install\.ps1') { "PASS" } else { "FAIL" })
    }
    else {
        Write-Result "install.mjs exists" "FAIL"
    }
}

# ==============================================================
# TEST 8: No-git scenario (skill install graceful failure)
# ==============================================================

Write-Host ""
Write-Host "Test 8: Graceful failure scenarios" -ForegroundColor Cyan

# We can't easily remove git, but we can test that the installer
# handles a bad repo URL gracefully by checking the code structure
$ps1Content = Get-Content $InstallerPs1 -Raw
Write-Result "Installer has try/catch for clone" $(if ($ps1Content -match "try\s*\{[\s\S]*?clone[\s\S]*?\}\s*catch") { "PASS" } else { "FAIL" })
Write-Result "Installer has finally cleanup" $(if ($ps1Content -match "finally\s*\{[\s\S]*?Remove-Item") { "PASS" } else { "FAIL" })
Write-Result "Installer shows manual install fallback" $(if ($ps1Content -match "(?i)manual install") { "PASS" } else { "FAIL" })

# ==============================================================
# Summary
# ==============================================================

Write-Host ""
Write-Host "================================"
$total = $Pass + $Fail + $Skip
Write-Host "Results ($total tests): " -NoNewline
Write-Host "$Pass passed" -ForegroundColor Green -NoNewline
Write-Host ", " -NoNewline
if ($Fail -gt 0) { Write-Host "$Fail failed" -ForegroundColor Red -NoNewline }
else { Write-Host "0 failed" -NoNewline }
Write-Host ", " -NoNewline
Write-Host "$Skip skipped" -ForegroundColor DarkGray
Write-Host ""

if ($Fail -gt 0) {
    Write-Host "SOME TESTS FAILED -- review output above." -ForegroundColor Red
    exit 1
}
else {
    Write-Host "All tests passed." -ForegroundColor Green
    exit 0
}
