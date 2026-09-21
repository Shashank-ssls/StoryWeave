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
$env:PIP_CACHE_DIR = Join-Path $RepoRoot ".local\pip_cache"
$env:TORCH_HOME = Join-Path $RepoRoot ".local\torch_cache"
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $RepoRoot ".local\ms-playwright"
# HF_HOME is intentionally NOT set here: storyweave.config.Settings already defaults it to
# <repo>\.hf-cache (storyweave/nlp/extractor.py:configure_hf_cache, applied via
# os.environ.setdefault before any HuggingFace import) and the models are already downloaded
# there. Overriding it to .local\hf_cache here would just split the cache and force a
# re-download. Set $env:HF_HOME yourself before running this script if you want a different
# location.

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
