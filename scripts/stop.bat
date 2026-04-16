@echo off
cd /d "%~dp0\.."

echo Stopping Kanban Studio...
docker compose down
echo Kanban Studio stopped.
