@echo off
cd /d "%~dp0"

start "Django" cmd /c "cd backend && python manage.py runserver"
start "Vite" cmd /c "cd frontend && npm run dev"

timeout /t 5 >nul

start "ngrok" cmd /c "D:\ngrok\ngrok.exe http http://localhost:5173"

pause
