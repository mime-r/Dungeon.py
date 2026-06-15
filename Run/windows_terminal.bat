@echo off
where py >nul 2>nul && (set "RUN=py") || (set "RUN=python")
wt nt -p "Command Prompt" -d "%~dp0..\Dungeon" cmd /k "%RUN% Dungeon.py"
