@echo off
where py >nul 2>nul && (set "RUN=py") || (set "RUN=python")
start "Dungeon.py" cmd /k "cd /d "%~dp0..\Dungeon" && %RUN% Dungeon.py"
