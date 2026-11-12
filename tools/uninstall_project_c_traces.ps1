<#
.SYNOPSIS
    Remove ONLY the C: traces this project created, as recorded in the ledger.

.DESCRIPTION
    Removes exactly items 1-7 of docs/retrofit/C_DRIVE_LEDGER.md and nothing else:

      1. C:\Users\<you>\.ollama\                       (keypair + recommendations cache)
      2. %LOCALAPPDATA%\Ollama\                        (app/server logs + local sqlite)
      3. Start Menu\Programs\Ollama\                   (folder + shortcut)
      4. Start Menu\Programs\Ollama.lnk                (shortcut)
      5. Start Menu\Programs\Startup\Ollama.lnk        (auto-start shortcut)
      6. HKCU uninstall key for Ollama 0.34.4
      7. the single "F:\Tools\Ollama" element of HKCU\Environment\Path

    It deliberately does NOT touch:

      * C:\Users\<you>\.cache\chrome-devtools-mcp and \python-tldextract -- these are
        the 135.8 MB C: baseline, they predate this project, and they are not ours;
      * C:\Users\<you>\.claude\projects\... -- Claude Code's own session data, which
        holds this project's conversation history;
      * %LOCALAPPDATA%\Temp\claude\... -- the harness scratchpad;
      * anything on F:, including the Ollama program directory and the models.

    DRY RUN BY DEFAULT. Nothing is changed unless -Apply is passed.

    For a full Ollama removal including the F: program directory, run the vendor
    uninstaller F:\Tools\Ollama\unins000.exe FIRST, then run this script to sweep the
    C: leftovers it does not remove.

.PARAMETER Apply
    Actually perform the removals. Without it the script only reports.

.PARAMETER Only
    Restrict the run to the given ledger item id(s), 1-7. Everything else is skipped and
    reported as skipped. Retiring ONE ledger item at a time is the normal case: the
    ledger is a list of independent traces, not a single all-or-nothing install.

.EXAMPLE
    .\tools\uninstall_project_c_traces.ps1
    .\tools\uninstall_project_c_traces.ps1 -Only 7
    .\tools\uninstall_project_c_traces.ps1 -Only 7 -Apply
#>
[CmdletBinding()]
param(
    [switch]$Apply,
    [ValidateRange(1, 7)]
    [int[]]$Only
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$PathEntryToRemove = 'F:\Tools\Ollama'
$UninstallKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{44E83376-CE68-45EB-8FC1-393500EB558C}_is1'

$StartMenu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'

$Targets = @(
    [pscustomobject]@{ Id = 1; Kind = 'Dir';  Path = (Join-Path $env:USERPROFILE '.ollama');  Note = 'Ollama keypair + recommendations cache' }
    [pscustomobject]@{ Id = 2; Kind = 'Dir';  Path = (Join-Path $env:LOCALAPPDATA 'Ollama'); Note = 'Ollama app/server logs + local sqlite' }
    [pscustomobject]@{ Id = 3; Kind = 'Dir';  Path = (Join-Path $StartMenu 'Ollama');         Note = 'Start Menu folder + shortcut' }
    [pscustomobject]@{ Id = 4; Kind = 'File'; Path = (Join-Path $StartMenu 'Ollama.lnk');     Note = 'Start Menu shortcut' }
    [pscustomobject]@{ Id = 5; Kind = 'File'; Path = (Join-Path $StartMenu 'Startup\Ollama.lnk'); Note = 'auto-start shortcut' }
)

function Test-InScope {
    param([int]$Id)
    if ($null -eq $Only -or $Only.Count -eq 0) { return $true }
    return $Only -contains $Id
}

function Get-SizeBytes {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return 0 }
    $item = Get-Item -LiteralPath $Path -Force
    if ($item.PSIsContainer) {
        $sum = (Get-ChildItem -LiteralPath $Path -Recurse -File -Force -ErrorAction SilentlyContinue |
                Measure-Object -Property Length -Sum).Sum
        if ($null -eq $sum) { return 0 }
        return $sum
    }
    return $item.Length
}

$mode = if ($Apply) { 'APPLY  (changes WILL be made)' } else { 'DRY RUN (nothing will change)' }
$scope = if ($null -eq $Only -or $Only.Count -eq 0) { 'all ledger items (1-7)' } else { "ONLY item(s) $($Only -join ', ')" }
Write-Host ''
Write-Host ('=' * 78)
Write-Host "  Project C: trace removal -- $mode"
Write-Host "  Scope: $scope"
Write-Host ('=' * 78)
Write-Host ''

# --- check whether ollama is running: removing its logs under it is a bad idea ----
$running = @(Get-Process -Name 'ollama', 'ollama app' -ErrorAction SilentlyContinue)
if ($running.Count -gt 0) {
    # One format string: with `+` the -f would bind to the second operand only.
    Write-Warning ('Ollama is running (PID(s): {0}). Stop it before -Apply, or the log folder will be recreated immediately.' -f ($running.Id -join ', '))
    Write-Host ''
}

# --- files and folders ------------------------------------------------------------
$total = 0L
foreach ($t in $Targets) {
    if (-not (Test-InScope -Id $t.Id)) {
        Write-Host ("[{0}] skipped (out of scope)  {1}" -f $t.Id, $t.Path)
        continue
    }
    if (Test-Path -LiteralPath $t.Path) {
        $bytes = Get-SizeBytes -Path $t.Path
        $total += $bytes
        Write-Host ("[{0}] REMOVE  {1}" -f $t.Id, $t.Path)
        Write-Host ("         {0}, {1:N0} bytes" -f $t.Note, $bytes)
        if ($Apply) {
            Remove-Item -LiteralPath $t.Path -Recurse -Force
            Write-Host '         removed.'
        }
    }
    else {
        Write-Host ("[{0}] absent  {1}" -f $t.Id, $t.Path)
    }
}

# --- registry: uninstall key ------------------------------------------------------
Write-Host ''
if (-not (Test-InScope -Id 6)) {
    Write-Host '[6] skipped (out of scope)'
}
elseif (Test-Path -LiteralPath $UninstallKey) {
    $dn = (Get-ItemProperty -LiteralPath $UninstallKey).DisplayName
    Write-Host ("[6] REMOVE  {0}" -f $UninstallKey)
    Write-Host ("         uninstall entry for '{0}'" -f $dn)
    if ($Apply) {
        Remove-Item -LiteralPath $UninstallKey -Recurse -Force
        Write-Host '         removed.'
    }
}
else {
    Write-Host ("[6] absent  {0}" -f $UninstallKey)
}

# --- registry: the single PATH element --------------------------------------------
# Read the RAW (unexpanded) value so a REG_EXPAND_SZ PATH is not flattened -- writing
# back an expanded PATH would silently bake in today's values of %USERPROFILE% etc.
Write-Host ''
$skipPath = -not (Test-InScope -Id 7)
$raw = $null
try {
    $rk = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey('Environment', $false)
    if ($null -ne $rk) {
        $raw = $rk.GetValue('Path', $null, [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)
        $kind = $rk.GetValueKind('Path')
        $rk.Close()
    }
}
catch { $raw = $null }

if ($skipPath) {
    Write-Host '[7] skipped (out of scope)'
}
elseif ([string]::IsNullOrEmpty($raw)) {
    Write-Host '[7] absent  HKCU\Environment\Path has no value'
}
else {
    $parts = $raw -split ';'
    $keep = @($parts | Where-Object { $_.Trim().TrimEnd('\') -ne $PathEntryToRemove.TrimEnd('\') })
    $removedCount = $parts.Count - $keep.Count
    if ($removedCount -eq 0) {
        Write-Host ("[7] absent  '{0}' is not in HKCU\Environment\Path" -f $PathEntryToRemove)
    }
    else {
        Write-Host ("[7] REMOVE  '{0}' from HKCU\Environment\Path" -f $PathEntryToRemove)
        Write-Host ("         value kind: {0} (preserved on write)" -f $kind)
        Write-Host ("         {0} element(s) removed; {1} other element(s) kept untouched" -f $removedCount, $keep.Count)
        $newValue = ($keep -join ';')
        Write-Host ''
        Write-Host '         --- BEFORE (raw, unexpanded) ---'
        foreach ($e in $parts) {
            $mark = if ($e.Trim().TrimEnd('\') -eq $PathEntryToRemove.TrimEnd('\')) { ' <== REMOVE' } else { '' }
            Write-Host ("           {0}{1}" -f $e, $mark)
        }
        Write-Host '         --- AFTER (raw, unexpanded) ---'
        foreach ($e in $keep) { Write-Host ("           {0}" -f $e) }
        Write-Host ''
        if ($Apply) {
            $rk = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey('Environment', $true)
            $rk.SetValue('Path', $newValue, $kind)
            $rk.Close()
            Write-Host '         removed. (Open a new shell for it to take effect.)'
        }
    }
}

# --- explicitly protected ---------------------------------------------------------
Write-Host ''
Write-Host ('-' * 78)
Write-Host '  NOT TOUCHED (not created by this project, or harness-owned):'
foreach ($p in @(
        (Join-Path $env:USERPROFILE '.cache\chrome-devtools-mcp'),
        (Join-Path $env:USERPROFILE '.cache\python-tldextract'),
        (Join-Path $env:USERPROFILE '.claude\projects'),
        (Join-Path $env:LOCALAPPDATA 'Temp\claude'))) {
    $state = if (Test-Path -LiteralPath $p) { 'present, left alone' } else { 'absent' }
    Write-Host ("    {0,-62} {1}" -f $p, $state)
}
Write-Host ('-' * 78)

Write-Host ''
Write-Host ("  Files/folders in scope: {0:N0} bytes ({1:N2} MB)" -f $total, ($total / 1MB))
if (-not $Apply) {
    Write-Host '  DRY RUN -- nothing was changed. Re-run with -Apply to remove.'
}
Write-Host ''
