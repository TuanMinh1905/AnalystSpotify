@echo off
echo 🇻🇳 SPOTIFY VIETNAM DATA PIPELINE - SETUP & RUN
echo ================================================

echo 📦 Cài đặt Python packages...
pip install -r requirements.txt

echo.
echo 🐳 Kiểm tra MinIO container...
docker ps | findstr minio
if %ERRORLEVEL% NEQ 0 (
    echo ⚠️  MinIO container không chạy. Khởi động MinIO...
    docker compose -f "HaMu-main\config-hadoop\compose.yaml" up -d minio
    echo ⏳ Chờ MinIO khởi động...
    timeout /t 10 /nobreak > nul
)

echo.
echo 🚀 Chạy data pipeline...
python spotify_minio_pipeline.py

echo.
echo ✅ Hoàn thành! Truy cập MinIO tại: http://localhost:9001/browser/music/
pause