# StoryWeave dev environment activation (PowerShell).
# Session-only: nothing here touches system/user environment variables.
# Usage:
#   .\dev.ps1        -> activates the light .venv (app/CLI/tests/serving the API)
#   .\dev.ps1 -Ml     -> activates .venv-ml (GLiNER/torch pipeline: ingest/extract/relate/...)
#
# If PowerShell blocks script execution, run once for this process only (not a system change):
#   powershell -ExecutionPolicy Bypass -File .\dev.ps1

param(
    [switch]$Ml
)

$RepoRoot = $PSScriptRoot

# --- Caches routed to the project drive, never C: ---
# Session-only ($env: scope). Nothing below writes a system or user environment
# variable. tools/check_local_env.py asserts every one of these resolves off C:.
$LocalRoot = Join-Path $RepoRoot ".local"

$env:PIP_CACHE_DIR = Join-Path $LocalRoot "pip_cache"
$env:TORCH_HOME = Join-Path $LocalRoot "torch_cache"
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $LocalRoot "ms-playwright"
$env:npm_config_cache = Join-Path $LocalRoot "npm_cache"
$env:OLLAMA_MODELS = Join-Path $LocalRoot "ollama_models"
# pip/torch/HF unpack their archives into TEMP; on C: by default, so redirect it.
$env:TEMP = Join-Path $LocalRoot "tmp"
$env:TMP = $env:TEMP

# HF_HOME is the one cache that lives OUTSIDE the repo, by decision: the GLiNER,
# deberta and relex weights are already downloaded to the machine-wide cache
# F:\Dev\shared\hf-cache (still on F:, never C:). Pointing it at <repo>\.hf-cache
# would split the cache and force a ~1 GB re-download. See the cache table in
# CLAUDE.md (retrofit block). storyweave.config defaults hf_home to
# <repo>\.hf-cache, but configure_hf_cache() uses os.environ.setdefault, so this
# explicit value wins for any process started from this shell.
$env:HF_HOME = "F:\Dev\shared\hf-cache"

foreach ($dir in @(
        $env:PIP_CACHE_DIR, $env:TORCH_HOME, $env:PLAYWRIGHT_BROWSERS_PATH,
        $env:npm_config_cache, $env:OLLAMA_MODELS, $env:TEMP)) {
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
}

if ($Ml) {
    $VenvPath = Join-Path $RepoRoot ".venv-ml"
    $Label = ".venv-ml (Python 3.12, heavy NLP/ML)"
} else {
    $VenvPath = Join-Path $RepoRoot ".venv"
    $Label = ".venv (Python 3.14, light app/CLI/tests)"
}

$ActivateScript = Join-Path $VenvPath "Scripts\Activate.ps1"
if (-not (Test-Path $ActivateScript)) {
    Write-Host "Venv not found at $VenvPath - create it first (see README.md)." -ForegroundColor Red
    return
}

& $ActivateScript

Write-Host "Activated: $Label"
Write-Host "Python: $((Get-Command python).Source)"
python -c "import sys; print('Version:', sys.version.split()[0])"

if ($Ml) {
    python -c "
try:
    import torch
    print('torch', torch.__version__, '| CUDA available:', torch.cuda.is_available())
    if torch.cuda.is_available():
        print('device:', torch.cuda.get_device_name(0))
except ImportError:
    print('torch not installed in this venv')
"
} else {
    Write-Host "(light venv has no torch - use '.\dev.ps1 -Ml' for the ML pipeline)"
}
