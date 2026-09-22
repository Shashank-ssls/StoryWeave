# StoryWeave one-command run (PowerShell): builds the frontend and serves it from
# the same FastAPI process as the API (integration phase Part C.1) - one origin, no
# CORS needed. The two-server dev mode (dev.ps1 + `npm run dev`) keeps working
# unchanged; this is an alternative, not a replacement.
#
# Usage:
#   .\run.ps1                                    -> builds + serves storyweave-demo.sqlite on :8000
#   .\run.ps1 -Db my.sqlite -Port 8080            -> a different DB / port
#   .\run.ps1 -SkipBuild                          -> reuse frontend/dist as-is (faster iteration)
#
# If PowerShell blocks script execution, run once for this process only (not a system change):
#   powershell -ExecutionPolicy Bypass -File .\run.ps1

param(
    [string]$Db = "storyweave-demo.sqlite",
    [int]$Port = 8000,
    [switch]$SkipBuild
)

$RepoRoot = $PSScriptRoot
$env:PIP_CACHE_DIR = Join-Path $RepoRoot ".local\pip_cache"
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $RepoRoot ".local\ms-playwright"

if (-not $SkipBuild) {
    Write-Host "Building frontend..." -ForegroundColor Cyan
    Push-Location (Join-Path $RepoRoot "frontend")
    npm run build
    if ($LASTEXITCODE -ne 0) {
        Pop-Location
        Write-Host "Frontend build failed - aborting." -ForegroundColor Red
        exit 1
    }
    Pop-Location
} else {
    Write-Host "Skipping build (-SkipBuild) - serving frontend/dist as-is." -ForegroundColor Yellow
}

$DistPath = Join-Path $RepoRoot "frontend\dist"
if (-not (Test-Path (Join-Path $DistPath "index.html"))) {
    Write-Host "frontend/dist/index.html not found - build the frontend first (omit -SkipBuild)." -ForegroundColor Red
    exit 1
}

$VenvActivate = Join-Path $RepoRoot ".venv\Scripts\Activate.ps1"
if (-not (Test-Path $VenvActivate)) {
    Write-Host "Light .venv not found - create it first (see README.md / SETUP_NOTES.md)." -ForegroundColor Red
    exit 1
}
& $VenvActivate

$env:STORYWEAVE_DB_PATH = $Db
Write-Host ""
Write-Host "Serving StoryWeave (API + built frontend, one origin) at http://127.0.0.1:$Port" -ForegroundColor Green
Write-Host "DB: $Db" -ForegroundColor Green
Write-Host ""

python -m uvicorn storyweave.api.app:app --port $Port
