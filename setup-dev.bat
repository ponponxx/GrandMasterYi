@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"
set "REQ_FILE=%BACKEND%\requirements.lock.txt"

if not exist "%REQ_FILE%" set "REQ_FILE=%BACKEND%\requirements.txt"

if not exist "%BACKEND%\venv\Scripts\python.exe" (
  where py >nul 2>&1
  if !ERRORLEVEL! EQU 0 (
    py -3.10 -m venv "%BACKEND%\venv" >nul 2>&1
    if !ERRORLEVEL! NEQ 0 (
      py -3 -m venv "%BACKEND%\venv"
    )
  ) else (
    where python >nul 2>&1
    if !ERRORLEVEL! NEQ 0 (
      echo [ERROR] Python not found. Install Python 3.10+ first.
      exit /b 1
    )
    python -m venv "%BACKEND%\venv"
  )
)

if not exist "%BACKEND%\venv\Scripts\python.exe" (
  echo [ERROR] Failed to create backend virtualenv.
  exit /b 1
)

echo [1/3] Installing backend dependencies from %REQ_FILE%
"%BACKEND%\venv\Scripts\python.exe" -m pip install --upgrade pip
if !ERRORLEVEL! NEQ 0 exit /b 1
"%BACKEND%\venv\Scripts\python.exe" -m pip install -r "%REQ_FILE%"
if !ERRORLEVEL! NEQ 0 exit /b 1

echo [2/3] Installing frontend dependencies with npm ci
pushd "%FRONTEND%"
call npm ci
if !ERRORLEVEL! NEQ 0 (
  popd
  exit /b 1
)
popd

if not exist "%ROOT%\.env" if exist "%ROOT%\.env.example" (
  copy /Y "%ROOT%\.env.example" "%ROOT%\.env" >nul
  echo [3/3] .env created from .env.example
) else (
  echo [3/3] .env already exists
)

echo Setup complete. Update .env values, then run start-dev.bat
endlocal
