@echo off
echo ========================================
echo OpenClaw Dashboard - Development Setup
echo ========================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

echo Starting Docker containers (PostgreSQL, Redis, Backend, Celery)...
cd docker
docker-compose -f docker-compose.dev.yml up -d --build

echo.
echo Waiting for services to be ready...
timeout /t 10 /nobreak >nul

echo.
echo Running database migrations and seeding data...
docker-compose -f docker-compose.dev.yml exec backend python manage.py migrate --noinput
docker-compose -f docker-compose.dev.yml exec backend python manage.py seed_data

echo.
echo ========================================
echo Backend is running at: http://localhost:8000
echo Admin panel: http://localhost:8000/admin
echo.
echo Test user credentials:
echo   Email: test@example.com
echo   Password: testpass123
echo ========================================
echo.
echo Now starting the frontend...
echo.

cd ../frontend
call npm install
start cmd /k "npm run dev"

echo.
echo ========================================
echo Frontend is starting at: http://localhost:3000
echo ========================================
echo.
echo Press any key to view Docker logs (Ctrl+C to exit logs)
pause >nul

cd ../docker
docker-compose -f docker-compose.dev.yml logs -f
