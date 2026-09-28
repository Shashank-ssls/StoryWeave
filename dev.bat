@echo off
REM StoryWeave dev environment activation (cmd.exe).
REM Session-only: nothing here touches system/user environment variables.
REM Usage:
REM   dev.bat        -> activates the light .venv (app/CLI/tests/serving the API)
REM   dev.bat ml      -> activates .venv-ml (GLiNER/torch pipeline: ingest/extract/relate/...)

set "REPO_ROOT=%~dp0"
set "LOCAL_ROOT=%REPO_ROOT%.local"

REM --- Caches routed to the project drive, never C: (session-only; no setx anywhere) ---
set "PIP_CACHE_DIR=%LOCAL_ROOT%\pip_cache"
set "TORCH_HOME=%LOCAL_ROOT%\torch_cache"
set "PLAYWRIGHT_BROWSERS_PATH=%LOCAL_ROOT%\ms-playwright"
set "npm_config_cache=%LOCAL_ROOT%\npm_cache"
set "OLLAMA_MODELS=%LOCAL_ROOT%\ollama_models"
set "TEMP=%LOCAL_ROOT%\tmp"
set "TMP=%LOCAL_ROOT%\tmp"
REM HF_HOME deliberately points OUTSIDE the repo at the machine-wide cache on F:,
REM where the GLiNER/deberta/relex weights already live - see dev.ps1 for the full
REM reasoning and the cache table in CLAUDE.md (retrofit block).
set "HF_HOME=F:\Dev\shared\hf-cache"

for %%D in ("%PIP_CACHE_DIR%" "%TORCH_HOME%" "%PLAYWRIGHT_BROWSERS_PATH%" "%npm_config_cache%" "%OLLAMA_MODELS%" "%TEMP%") do (
    if not exist "%%~D" mkdir "%%~D"
)

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
