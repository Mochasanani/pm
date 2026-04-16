@echo off
cd /d "%~dp0\.."

where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: docker is not installed.
    exit /b 1
)

echo Building and starting Kanban Studio...
docker compose up --build -d
echo Kanban Studio is running at http://localhost:8000
