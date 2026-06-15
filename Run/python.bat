@echo off
cd /d "%~dp0..\Dungeon"
where py >nul 2>nul
if %errorlevel%==0 (
    py Dungeon.py
) else (
    python Dungeon.py
)
pause
