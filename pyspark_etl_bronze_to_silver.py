#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎵 PYSPARK ETL: BRONZE → SILVER
Xử lý và chuẩn hóa dữ liệu Spotify từ bucket bronze (music) sang silver
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import split, col, trim
import os

# ========= CẤU HÌNH MINIO =========
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "host.docker.internal:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "longminh")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "longminh")

# Bucket paths (S3-compatible URLs)
BRONZE_BUCKET = "bronze"  # Bucket hiện tại chứa vietnam_songs_database.csv
SILVER_BUCKET = "silver"  # Bucket đích để lưu dữ liệu đã chuẩn hóa

INPUT_FILE = f"s3a://{BRONZE_BUCKET}/global_official_new_releases.csv"
OUTPUT_PATH = f"s3a://{SILVER_BUCKET}/global_songs_cleaned"


def create_spark_session():
    """
    Tạo SparkSession với cấu hình MinIO (S3-compatible storage)
    
    Giải thích các config:
    - spark.hadoop.fs.s3a.endpoint: Địa chỉ MinIO server
    - spark.hadoop.fs.s3a.access.key: Access key để xác thực
    - spark.hadoop.fs.s3a.secret.key: Secret key
    - spark.hadoop.fs.s3a.path.style.access: Dùng path-style (minio yêu cầu)
    - spark.hadoop.fs.s3a.impl: Implementation class cho S3A filesystem
    """
    print("🔧 Khởi tạo SparkSession với cấu hình MinIO...")
    
    spark = SparkSession.builder \
        .appName("Spotify_ETL_Bronze_to_Silver") \
        .config("spark.hadoop.fs.s3a.endpoint", f"http://{MINIO_ENDPOINT}") \
        .config("spark.hadoop.fs.s3a.access.key", MINIO_ACCESS_KEY) \
        .config("spark.hadoop.fs.s3a.secret.key", MINIO_SECRET_KEY) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
        .config("spark.hadoop.fs.s3a.connection.timeout", "60000") \
        .config("spark.hadoop.fs.s3a.connection.establish.timeout", "60000") \
        .config("spark.hadoop.fs.s3a.attempts.maximum", "3") \
        .config("spark.hadoop.fs.s3a.connection.maximum", "15") \
        .config("spark.hadoop.fs.s3a.threads.max", "10") \
        .config("spark.hadoop.fs.s3a.threads.core", "5") \
        .config("spark.hadoop.fs.s3a.max.total.tasks", "10") \
        .config("spark.hadoop.fs.s3a.multipart.size", "104857600") \
        .getOrCreate()
    
    print(f"✅ SparkSession đã khởi tạo: {spark.version}")
    return spark


def read_bronze_data(spark):
    """
    Đọc dữ liệu từ bronze bucket (music/vietnam_songs_database.csv)
    
    Giải thích:
    - header=True: Dòng đầu là tên cột
    - inferSchema=True: Tự động nhận diện kiểu dữ liệu (int, string, etc)
    - escape='"': Xử lý trường hợp có dấu ngoặc trong CSV
    """
    print(f"\n📥 Đọc dữ liệu từ: {INPUT_FILE}")
    
    try:
        df = spark.read.csv(
            INPUT_FILE,
            header=True,
            inferSchema=True,
            escape='"'
        )
        
        print(f"✅ Đọc thành công: {df.count()} dòng, {len(df.columns)} cột")
        print(f"📋 Các cột gốc: {', '.join(df.columns)}")
        
        return df
        
    except Exception as e:
        print(f"❌ Lỗi khi đọc dữ liệu: {e}")
        raise


def check_data_quality(df, stage=""):
    """
    Kiểm tra chất lượng dữ liệu: null values và duplicates
    
    Giải thích:
    - Đếm null cho từng cột quan trọng
    - Đếm số bản ghi trùng lặp
    - In báo cáo chi tiết
    """
    print(f"\n📊 KIỂM TRA CHẤT LƯỢNG DỮ LIỆU {stage}")
    print("-" * 50)
    
    total_rows = df.count()
    print(f"📈 Tổng số dòng: {total_rows}")
    
    # Kiểm tra null values cho các cột quan trọng
    critical_columns = ['track_id', 'track_name', 'primary_artist']
    null_counts = {}
    
    print("\n🔍 Kiểm tra NULL values:")
    for col_name in df.columns:
        null_count = df.filter(col(col_name).isNull()).count()
        if null_count > 0:
            null_counts[col_name] = null_count
            marker = "⚠️" if col_name in critical_columns else "ℹ️"
            print(f"  {marker} {col_name}: {null_count} nulls ({null_count/total_rows*100:.2f}%)")
    
    if not null_counts:
        print("  ✅ Không có null values")
    
    # Kiểm tra duplicates dựa trên track_id
    if 'track_id' in df.columns:
        duplicate_count = df.count() - df.dropDuplicates(['track_id']).count()
        print(f"\n🔍 Kiểm tra DUPLICATE records (theo track_id):")
        if duplicate_count > 0:
            print(f"  ⚠️ Tìm thấy {duplicate_count} bản ghi trùng lặp ({duplicate_count/total_rows*100:.2f}%)")
        else:
            print(f"  ✅ Không có bản ghi trùng lắp")
    
    return null_counts


def clean_null_and_duplicates(df):
    """
    Xử lý null values và duplicates
    
    CHIẾN LƯỢC MỚI:
    1. XÓA dòng nếu có BẤT KỲ cột nào là NULL
    2. XÓA dòng trùng lặp 100% (tất cả các cột giống nhau)
    
    Giải thích:
    - dropna(): Xóa dòng có bất kỳ null nào
    - dropDuplicates(): Xóa duplicate 100% (tất cả cột), giữ first occurrence
    """
    print("\n🧹 XỬ LÝ NULL VÀ DUPLICATE")
    print("-" * 50)
    
    initial_count = df.count()
    
    # Bước 1: XÓA dòng có BẤT KỲ null nào
    print(f"🗑️ Xóa dòng có BẤT KỲ cột nào null...")
    df_cleaned = df.dropna(how='any')  # how='any' = xóa nếu có bất kỳ null nào
    
    dropped_null = initial_count - df_cleaned.count()
    if dropped_null > 0:
        print(f"  ❌ Đã xóa {dropped_null} dòng có null ({dropped_null/initial_count*100:.2f}%)")
    else:
        print(f"  ✅ Không có dòng nào có null")
    
    # Bước 2: Xóa duplicates 100% (tất cả các cột giống nhau)
    before_dedup = df_cleaned.count()
    print(f"\n🔄 Xóa bản ghi trùng lặp 100% (tất cả cột giống nhau)...")
    df_cleaned = df_cleaned.dropDuplicates()  # Không chỉ định subset = kiểm tra TẤT CẢ các cột
    
    dropped_dup = before_dedup - df_cleaned.count()
    if dropped_dup > 0:
        print(f"  ❌ Đã xóa {dropped_dup} bản ghi trùng lặp 100%")
    else:
        print(f"  ✅ Không có bản ghi trùng lặp 100%")
    
    final_count = df_cleaned.count()
    total_dropped = initial_count - final_count
    
    print(f"\n📊 KẾT QUẢ CLEANING:")
    print(f"  Số dòng ban đầu: {initial_count}")
    print(f"  Số dòng sau khi clean: {final_count}")
    print(f"  Tổng số dòng đã xóa: {total_dropped} ({total_dropped/initial_count*100:.2f}%)")
    
    return df_cleaned


def transform_data(df):
    """
    Xử lý và chuẩn hóa dữ liệu theo yêu cầu:
    1. Bỏ các cột không cần thiết
    2. Cột primary_genres: chỉ lấy giá trị đầu tiên trước dấu |
    
    Giải thích transform:
    - drop(): Xóa cột
    - split(): Tách chuỗi theo delimiter
    - getItem(0): Lấy phần tử đầu tiên của array
    - trim(): Xóa khoảng trắng thừa
    """
    print("\n🔄 BẮT ĐẦU TRANSFORM DỮ LIỆU")
    print("-" * 50)
    
    # Danh sách các cột cần XÓA (BỎ 'market' ra khỏi danh sách)
    columns_to_drop = [
        'spotify_url',
        'primary_artist_id',
        'main_genre',
        'release_year',
        'album_image_url',
        'playlist_id',
        'added_at',
        'added_by',
        'extracted_at'
    ]
    
    print(f"🗑️ Xóa {len(columns_to_drop)} cột: {', '.join(columns_to_drop)}")
    
    # Xóa các cột không cần thiết
    df_cleaned = df.drop(*columns_to_drop)
    
    # Transform primary_genres: lấy giá trị đầu tiên trước dấu |
    # Ví dụ: "vinahouse|v-pop|lo-fi" → "vinahouse"
    if 'primary_genres' in df_cleaned.columns:
        print("✂️ Transform primary_genres: lấy genre đầu tiên trước dấu |")
        df_cleaned = df_cleaned.withColumn(
            'primary_genres',
            trim(split(col('primary_genres'), r'\|').getItem(0))
        )
    
    print(f"✅ Transform hoàn thành: {len(df_cleaned.columns)} cột còn lại")
    print(f"📋 Các cột sau khi xử lý: {', '.join(df_cleaned.columns)}")
    
    return df_cleaned


def write_to_silver(df):
    """
    Ghi dữ liệu đã chuẩn hóa vào silver bucket
    
    Giải thích write options:
    - coalesce(1): GỘP TẤT CẢ dữ liệu vào 1 file duy nhất (thay vì nhiều partitions)
    - mode('overwrite'): Ghi đè nếu đã tồn tại
    - format('csv'): Lưu dạng CSV
    - header=True: Có header (tên cột)
    - option('compression', 'none'): Không nén (có thể đổi thành 'gzip' để tiết kiệm)
    """
    print(f"\n💾 Ghi dữ liệu vào: {OUTPUT_PATH}")
    print("📦 Gộp dữ liệu thành 1 file duy nhất (coalesce)...")
    
    try:
        df.coalesce(1).write \
            .mode('overwrite') \
            .option('header', 'true') \
            .option('compression', 'none') \
            .csv(OUTPUT_PATH)
        
        print(f"✅ Ghi thành công vào bucket '{SILVER_BUCKET}'")
        print(f"📄 Đã gộp thành 1 file CSV duy nhất")
        print(f"🌐 Truy cập: http://localhost:9001/browser/{SILVER_BUCKET}/")
        
    except Exception as e:
        print(f"❌ Lỗi khi ghi dữ liệu: {e}")
        raise


def show_sample_data(df, num_rows=5):
    """Hiển thị mẫu dữ liệu để kiểm tra"""
    print(f"\n📊 Hiển thị {num_rows} dòng mẫu:")
    df.show(num_rows, truncate=False)
    
    print("\n📈 Schema của dữ liệu:")
    df.printSchema()


def main():
    """
    Hàm chính để chạy ETL pipeline
    
    Flow:
    1. Khởi tạo Spark với config MinIO
    2. Đọc dữ liệu từ bronze bucket
    3. Transform và làm sạch dữ liệu
    4. Ghi vào silver bucket
    5. Hiển thị sample để kiểm tra
    """
    print("=" * 70)
    print("🎵 PYSPARK ETL: BRONZE → SILVER")
    print("   Xử lý dữ liệu Spotify Vietnam từ MinIO")
    print("=" * 70)
    
    try:
        # Bước 1: Khởi tạo Spark
        spark = create_spark_session()
        
        # Bước 2: Đọc dữ liệu bronze
        df_bronze = read_bronze_data(spark)
        
        # Bước 2.1: Kiểm tra chất lượng dữ liệu GỐC
        check_data_quality(df_bronze, stage="(BRONZE - GỐC)")
        
        # Bước 2.2: Xử lý null và duplicates
        df_bronze_cleaned = clean_null_and_duplicates(df_bronze)
        
        # Bước 2.3: Kiểm tra lại sau khi clean
        check_data_quality(df_bronze_cleaned, stage="(SAU KHI CLEAN)")
        
        # Hiển thị sample dữ liệu gốc
        print("\n📊 TRƯỚC KHI TRANSFORM:")
        show_sample_data(df_bronze_cleaned, num_rows=3)
        
        # Bước 3: Transform dữ liệu
        df_silver = transform_data(df_bronze_cleaned)
        
        # Hiển thị sample sau khi xử lý
        print("\n📊 SAU KHI TRANSFORM:")
        show_sample_data(df_silver, num_rows=3)
        
        # Kiểm tra chất lượng cuối cùng
        check_data_quality(df_silver, stage="(SILVER - CUỐI CÙNG)")
        
        # Bước 4: Ghi vào silver bucket
        write_to_silver(df_silver)
        
        # Thống kê cuối cùng
        print("\n" + "=" * 70)
        print("🎉 ETL HOÀN THÀNH THÀNH CÔNG!")
        print("=" * 70)
        print(f"📊 Tổng số bài hát đã xử lý: {df_silver.count()}")
        print(f"📋 Số cột ban đầu: {len(df_bronze.columns)}")
        print(f"📋 Số cột sau xử lý: {len(df_silver.columns)}")
        print(f"📉 Đã xóa: {len(df_bronze.columns) - len(df_silver.columns)} cột")
        print(f"📊 Số dòng ban đầu: {df_bronze.count()}")
        print(f"📊 Số dòng cuối cùng: {df_silver.count()}")
        print(f"📉 Đã xóa: {df_bronze.count() - df_silver.count()} dòng (null + duplicate)")
        print(f"\n🌐 Kiểm tra kết quả tại:")
        print(f"   http://localhost:9001/browser/{SILVER_BUCKET}/")
        print("=" * 70)
        
        # Dừng Spark
        spark.stop()
        print("\n✅ SparkSession đã đóng")
        
    except Exception as e:
        print(f"\n❌ LỖI: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
