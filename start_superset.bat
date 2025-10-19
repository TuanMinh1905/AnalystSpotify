@echo off
echo ========================================
echo   STARTING APACHE SUPERSET
echo ========================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running!
    echo Please start Docker Desktop first.
    pause
    exit /b 1
)

echo [1/5] Checking SQLite database...
if not exist "spotify_gold.db" (
    echo [ERROR] spotify_gold.db not found!
    echo Please run export_gold_to_sqlite.py first.
    pause
    exit /b 1
)
echo   ✓ Database found: spotify_gold.db
echo.

echo [2/5] Creating superset_home directory...
if not exist "superset_home" mkdir superset_home
echo   ✓ Directory created
echo.

echo [3/5] Starting Superset container...
docker-compose -f docker-compose-superset.yml up -d
echo   ✓ Container started
echo.

echo [4/5] Waiting for Superset to initialize (this may take 2-3 minutes)...
timeout /t 30 /nobreak >nul
echo   ✓ Initial wait complete
echo.

echo [5/5] Checking container status...
docker ps | findstr superset
echo.

echo ========================================
echo   SUPERSET IS STARTING!
echo ========================================
echo.
echo   URL: http://localhost:8088
echo   Username: admin
echo   Password: admin
echo.
echo   Database Connection String:
echo   sqlite:////app/spotify_gold.db
echo.
echo ========================================
echo.
echo Wait 2-3 minutes for full initialization...
echo Then open: http://localhost:8088
echo.

pause
