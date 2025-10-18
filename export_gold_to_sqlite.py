"""
Export dữ liệu từ MinIO Gold layer sang SQLite để Superset có thể query
"""

from pyspark.sql import SparkSession
import os

# MinIO Configuration
MINIO_ENDPOINT = "host.docker.internal:9000"
MINIO_ACCESS_KEY = "longminh"
MINIO_SECRET_KEY = "longminh"
GOLD_BUCKET = "gold"

# SQLite Database path
SQLITE_DB_PATH = "/home/hadoopminhquang/spotify_gold.db"

print("=" * 80)
print("🔄 EXPORT DATA TỪ MINIO GOLD LAYER SANG SQLITE")
print("=" * 80)

# Tạo SparkSession
spark = SparkSession.builder \
    .appName("Gold_to_SQLite_Exporter") \
    .config("spark.hadoop.fs.s3a.endpoint", f"http://{MINIO_ENDPOINT}") \
    .config("spark.hadoop.fs.s3a.access.key", MINIO_ACCESS_KEY) \
    .config("spark.hadoop.fs.s3a.secret.key", MINIO_SECRET_KEY) \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
    .config("spark.jars.packages", "org.xerial:sqlite-jdbc:3.42.0.0") \
    .getOrCreate()

print(f"✅ SparkSession created: {spark.version}\n")

# JDBC URL cho SQLite
jdbc_url = f"jdbc:sqlite:{SQLITE_DB_PATH}"

# Danh sách các bảng cần export
tables = [
    "dim_track",
    "dim_artist", 
    "dim_album",
    "dim_market",
    "dim_genre",
    "dim_date",
    "fact_track_performance",
    "bridge_track_genre",
    "agg_artist_performance",
    "agg_market_stats",
    "agg_genre_popularity"
]

print("📊 BẮT ĐẦU EXPORT CÁC BẢNG:")
print("=" * 80)

for table_name in tables:
    try:
        # Đọc từ MinIO
        s3_path = f"s3a://{GOLD_BUCKET}/{table_name}"
        df = spark.read.csv(s3_path, header=True, inferSchema=True)
        record_count = df.count()
        
        # Ghi vào SQLite
        df.write \
            .format("jdbc") \
            .option("url", jdbc_url) \
            .option("dbtable", table_name) \
            .option("driver", "org.sqlite.JDBC") \
            .mode("overwrite") \
            .save()
        
        print(f"✅ {table_name}: {record_count} records exported")
        
    except Exception as e:
        print(f"❌ Lỗi khi export {table_name}: {str(e)}")

print("\n" + "=" * 80)
print("✅ EXPORT HOÀN TẤT!")
print("=" * 80)
print(f"📁 Database location: {SQLITE_DB_PATH}")
print(f"📊 Total tables: {len(tables)}")
print("\n🔗 Sử dụng connection string trong Superset:")
print(f"   sqlite:///{SQLITE_DB_PATH}")

# Đóng SparkSession
spark.stop()
print("\n✅ SparkSession đã đóng")
