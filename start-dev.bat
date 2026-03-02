@echo off
setlocal
set "ROOT=%~dp0"

if not exist "%ROOT%backend\venv\Scripts\python.exe" (
  echo [ERROR] Backend virtualenv not found.
  echo Please run setup-dev.bat first.
  exit /b 1
)

if not exist "%ROOT%frontend\node_modules" (
  echo [ERROR] Frontend dependencies not found.
  echo Please run setup-dev.bat first.
  exit /b 1
)

start "Backend" cmd /k "cd /d ""%ROOT%backend"" && call venv\Scripts\activate.bat && python app.py"
start "Frontend" cmd /k "cd /d ""%ROOT%frontend"" && npm run dev"

endlocal
