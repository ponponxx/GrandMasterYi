@echo off
setlocal
set "ROOT=%~dp0"

start "Backend" cmd /k "cd /d ""%ROOT%backend"" && call venv\Scripts\activate.bat && python app.py"
start "Frontend" cmd /k "cd /d ""%ROOT%frontend"" && npm run dev"

endlocal
