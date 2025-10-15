@echo off
echo 🐧 DEPLOY TO HADOOP UBUNTU & RUN PIPELINE
echo ================================================
echo.

echo 📋 Copying files to Hadoop master container...
docker cp CaoDuLieu.py master:/tmp/
docker cp extract_songs_table.py master:/tmp/
docker cp simple_upload.py master:/tmp/
docker cp container_upload.py master:/tmp/
docker cp abc.py master:/tmp/

echo.
echo 🚀 Running pipeline in Hadoop Ubuntu container with ROOT privileges...
echo ================================================
docker exec -it master bash -c "cd /tmp && python3 abc.py"

echo.
echo 📁 Copying result back to host...
docker cp master:/tmp/data_tables/vietnam_songs_database.csv ./
if exist vietnam_songs_database.csv (
    echo ✅ File copied successfully: vietnam_songs_database.csv
) else (
    echo ⚠️ File not found, check pipeline output above
)

echo.
echo ✅ Pipeline completed!
echo 💡 Check result file: vietnam_songs_database.csv
echo 💡 Check MinIO at: http://localhost:9001/browser/music/
pause