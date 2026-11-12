@echo off
REM StoryWeave one-command run (cmd.exe): builds the frontend and serves it from the
REM same FastAPI process as the API (integration phase Part C.1) - one origin, no
REM CORS needed. The two-server dev mode (dev.bat + `npm run dev`) keeps working
REM unchanged; this is an alternative, not a replacement.
REM
REM Usage:
REM   run.bat                    -> builds + serves storyweave-demo.sqlite on :8000
REM   run.bat my.sqlite 8080     -> a different DB / port
REM   set SKIP_BUILD=1 & run.bat -> reuse frontend/dist as-is (faster iteration)

set "REPO_ROOT=%~dp0"
set "PIP_CACHE_DIR=%REPO_ROOT%.local\pip_cache"
set "PLAYWRIGHT_BROWSERS_PATH=%REPO_ROOT%.local\ms-playwright"

set "DB=%~1"
if "%DB%"=="" set "DB=storyweave-demo.sqlite"
set "PORT=%~2"
if "%PORT%"=="" set "PORT=8000"

if "%SKIP_BUILD%"=="1" (
    echo Skipping build ^(SKIP_BUILD=1^) - serving frontend\dist as-is.
) else (
    echo Building frontend...
    pushd "%REPO_ROOT%frontend"
    call npm run build
    if errorlevel 1 (
        popd
        echo Frontend build failed - aborting.
        exit /b 1
    )
    popd
)

if not exist "%REPO_ROOT%frontend\dist\index.html" (
    echo frontend\dist\index.html not found - build the frontend first.
    exit /b 1
)

if not exist "%REPO_ROOT%.venv\Scripts\activate.bat" (
    echo Light .venv not found - create it first ^(see README.md / SETUP_NOTES.md^).
    exit /b 1
)
call "%REPO_ROOT%.venv\Scripts\activate.bat"

set "STORYWEAVE_DB_PATH=%DB%"
echo.
echo Serving StoryWeave (API + built frontend, one origin) at http://127.0.0.1:%PORT%
echo DB: %DB%
echo.

python -m uvicorn storyweave.api.app:app --port %PORT%
