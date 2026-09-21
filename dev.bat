@echo off
REM StoryWeave dev environment activation (cmd.exe).
REM Session-only: nothing here touches system/user environment variables.
REM Usage:
REM   dev.bat        -> activates the light .venv (app/CLI/tests/serving the API)
REM   dev.bat ml      -> activates .venv-ml (GLiNER/torch pipeline: ingest/extract/relate/...)

set "REPO_ROOT=%~dp0"
set "PIP_CACHE_DIR=%REPO_ROOT%.local\pip_cache"
set "TORCH_HOME=%REPO_ROOT%.local\torch_cache"
REM HF_HOME intentionally not set here - see dev.ps1 for why (app already defaults it to
REM <repo>\.hf-cache and the models are already downloaded there).

if /i "%~1"=="ml" (
    set "VENV_DIR=%REPO_ROOT%.venv-ml"
    set "LABEL=.venv-ml (Python 3.12, heavy NLP/ML)"
) else (
    set "VENV_DIR=%REPO_ROOT%.venv"
    set "LABEL=.venv (Python 3.14, light app/CLI/tests)"
)

if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo Venv not found at %VENV_DIR% - create it first ^(see README.md^).
    exit /b 1
)

call "%VENV_DIR%\Scripts\activate.bat"

echo Activated: %LABEL%
where python
python -c "import sys; print('Version:', sys.version.split()[0])"

if /i "%~1"=="ml" (
    python -c "import torch; print('torch', torch.__version__, '| CUDA available:', torch.cuda.is_available())"
) else (
    echo (light venv has no torch - use "dev.bat ml" for the ML pipeline)
)
