#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎵 PYSPARK ETL: SILVER → GOLD (Data Warehouse)
Xây dựng Star Schema với Dimension và Fact tables
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, row_number, monotonically_increasing_id, 
    split, explode, trim, when, avg, sum as spark_sum,
    count, max as spark_max, min as spark_min, concat_ws
)
from pyspark.sql.window import Window
import os

# ========= CẤU HÌNH MINIO =========
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "host.docker.internal:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "longminh")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "longminh")

SILVER_BUCKET = "silver"
GOLD_BUCKET = "gold"

INPUT_PATH = f"s3a://{SILVER_BUCKET}/global_songs_cleaned"
GOLD_BASE_PATH = f"s3a://{GOLD_BUCKET}"


def create_spark_session():
    """Tạo SparkSession với cấu hình MinIO"""
    print("🔧 Khởi tạo SparkSession...")
    
    spark = SparkSession.builder \
        .appName("Spotify_ETL_Silver_to_Gold") \
        .config("spark.hadoop.fs.s3a.endpoint", f"http://{MINIO_ENDPOINT}") \
        .config("spark.hadoop.fs.s3a.access.key", MINIO_ACCESS_KEY) \
        .config("spark.hadoop.fs.s3a.secret.key", MINIO_SECRET_KEY) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
        .config("spark.hadoop.fs.s3a.connection.timeout", "60000") \
        .config("spark.hadoop.fs.s3a.connection.establish.timeout", "60000") \
        .getOrCreate()
    
    print(f"✅ SparkSession: {spark.version}")
    return spark


def read_silver_data(spark):
    """Đọc dữ liệu từ silver layer"""
    print(f"\n📥 Đọc dữ liệu silver từ: {INPUT_PATH}")
    
    df = spark.read.csv(INPUT_PATH, header=True, inferSchema=True, escape='"')
    
    print(f"✅ Đọc thành công: {df.count()} dòng, {len(df.columns)} cột")
    return df


def create_dim_track(df_silver):
    """
    DIM_TRACK: Dimension bài hát
    - track_id (PK)
    - track_name
    - duration_minutes
    - explicit
    - is_collaboration
    - duration_category
    """
    print("\n🎵 Tạo DIM_TRACK...")
    
    dim_track = df_silver.select(
        col("track_id"),
        col("track_name"),
        col("duration_minutes"),
        col("explicit"),
        col("is_collaboration"),
        col("duration_category")
    ).dropDuplicates(["track_id"])
    
    print(f"✅ DIM_TRACK: {dim_track.count()} tracks unique")
    return dim_track


def create_dim_artist(df_silver):
    """
    DIM_ARTIST: Dimension nghệ sĩ
    - artist_id (PK) - generated
    - artist_name (từ primary_artist)
    - artist_popularity
    - artist_followers
    - primary_genres (1 genre chính)
    """
    print("\n🎤 Tạo DIM_ARTIST...")
    
    # Lấy unique artists từ primary_artist
    dim_artist = df_silver.select(
        col("primary_artist").alias("artist_name"),
        col("artist_popularity"),
        col("artist_followers"),
        col("primary_genres")
    ).dropDuplicates(["artist_name"])
    
    # Tạo artist_id (surrogate key)
    window = Window.orderBy("artist_name")
    dim_artist = dim_artist.withColumn("artist_id", row_number().over(window))
    
    # Sắp xếp lại cột
    dim_artist = dim_artist.select(
        "artist_id",
        "artist_name", 
        "artist_popularity",
        "artist_followers",
        "primary_genres"
    )
    
    print(f"✅ DIM_ARTIST: {dim_artist.count()} artists unique")
    return dim_artist


def create_dim_album(df_silver):
    """
    DIM_ALBUM: Dimension album
    - album_id (PK) - generated
    - album_name
    - album_type (album/single/compilation)
    - release_date
    - is_recent (>= 2020)
    """
    print("\n💿 Tạo DIM_ALBUM...")
    
    dim_album = df_silver.select(
        col("album_name"),
        col("album_type"),
        col("release_date"),
        col("is_recent")
    ).dropDuplicates(["album_name", "release_date"])
    
    # Tạo album_id
    window = Window.orderBy("album_name", "release_date")
    dim_album = dim_album.withColumn("album_id", row_number().over(window))
    
    dim_album = dim_album.select(
        "album_id",
        "album_name",
        "album_type",
        "release_date",
        "is_recent"
    )
    
    print(f"✅ DIM_ALBUM: {dim_album.count()} albums unique")
    return dim_album


def create_dim_market(df_silver):
    """
    DIM_MARKET: Dimension thị trường/quốc gia
    - market_id (PK) - generated
    - market_code (US, GB, VN, ...)
    """
    print("\n🌍 Tạo DIM_MARKET...")
    
    dim_market = df_silver.select(
        col("market").alias("market_code")
    ).dropDuplicates(["market_code"])
    
    window = Window.orderBy("market_code")
    dim_market = dim_market.withColumn("market_id", row_number().over(window))
    
    dim_market = dim_market.select("market_id", "market_code")
    
    print(f"✅ DIM_MARKET: {dim_market.count()} markets")
    return dim_market


def create_dim_genre(df_silver):
    """
    DIM_GENRE: Dimension thể loại nhạc
    - genre_id (PK)
    - genre_name
    
    Explode all_genres để lấy tất cả thể loại
    """
    print("\n🎼 Tạo DIM_GENRE...")
    
    # Split all_genres và explode
    genres_exploded = df_silver.select(
        explode(split(col("all_genres"), r"\s*\|\s*")).alias("genre_name")
    ).filter(col("genre_name").isNotNull() & (col("genre_name") != ""))
    
    dim_genre = genres_exploded.dropDuplicates(["genre_name"])
    
    window = Window.orderBy("genre_name")
    dim_genre = dim_genre.withColumn("genre_id", row_number().over(window))
    
    dim_genre = dim_genre.select("genre_id", "genre_name")
    
    print(f"✅ DIM_GENRE: {dim_genre.count()} genres unique")
    return dim_genre


def create_dim_date(df_silver):
    """
    DIM_DATE: Dimension thời gian
    - date_id (PK) - format: YYYYMMDD
    - date (date)
    - year
    - month
    - day
    - quarter
    """
    print("\n📅 Tạo DIM_DATE...")
    
    from pyspark.sql.functions import year, month, dayofmonth, quarter, date_format
    
    dim_date = df_silver.select(
        col("release_date").alias("date")
    ).filter(col("date").isNotNull()).dropDuplicates()
    
    dim_date = dim_date.withColumn("date_id", date_format(col("date"), "yyyyMMdd").cast("int")) \
        .withColumn("year", year(col("date"))) \
        .withColumn("month", month(col("date"))) \
        .withColumn("day", dayofmonth(col("date"))) \
        .withColumn("quarter", quarter(col("date")))
    
    dim_date = dim_date.select("date_id", "date", "year", "month", "day", "quarter")
    
    print(f"✅ DIM_DATE: {dim_date.count()} dates unique")
    return dim_date


def create_fact_track_performance(df_silver, dim_track, dim_artist, dim_album, dim_market, dim_date):
    """
    FACT_TRACK_PERFORMANCE: Fact table chính
    - track_id (FK -> DIM_TRACK)
    - artist_id (FK -> DIM_ARTIST)
    - album_id (FK -> DIM_ALBUM)
    - market_id (FK -> DIM_MARKET)
    - date_id (FK -> DIM_DATE)
    - popularity (measure)
    - artist_count (measure)
    - genre_count (measure)
    - popularity_tier (descriptive)
    
    Grain: 1 track x 1 market x 1 release_date
    """
    print("\n📊 Tạo FACT_TRACK_PERFORMANCE...")
    
    from pyspark.sql.functions import date_format
    
    # Join với dimensions để lấy surrogate keys
    fact = df_silver.alias("s")
    
    # Join DIM_ARTIST
    fact = fact.join(
        dim_artist.alias("a"),
        col("s.primary_artist") == col("a.artist_name"),
        "left"
    )
    
    # Join DIM_ALBUM
    fact = fact.join(
        dim_album.alias("al"),
        (col("s.album_name") == col("al.album_name")) & 
        (col("s.release_date") == col("al.release_date")),
        "left"
    )
    
    # Join DIM_MARKET
    fact = fact.join(
        dim_market.alias("m"),
        col("s.market") == col("m.market_code"),
        "left"
    )
    
    # Join DIM_DATE
    fact = fact.withColumn("date_id_temp", date_format(col("s.release_date"), "yyyyMMdd").cast("int"))
    fact = fact.join(
        dim_date.alias("d"),
        col("date_id_temp") == col("d.date_id"),
        "left"
    )
    
    # Select fact columns
    fact = fact.select(
        col("s.track_id"),
        col("a.artist_id"),
        col("al.album_id"),
        col("m.market_id"),
        col("d.date_id"),
        col("s.popularity"),
        col("s.artist_count"),
        col("s.genre_count"),
        col("s.popularity_tier")
    )
    
    print(f"✅ FACT_TRACK_PERFORMANCE: {fact.count()} records")
    return fact


def create_bridge_track_genre(df_silver, dim_track, dim_genre):
    """
    BRIDGE_TRACK_GENRE: Bridge table (many-to-many)
    Liên kết track với nhiều genres
    - track_id (FK)
    - genre_id (FK)
    """
    print("\n🔗 Tạo BRIDGE_TRACK_GENRE...")
    
    # Explode all_genres cho từng track
    bridge = df_silver.select(
        col("track_id"),
        explode(split(col("all_genres"), r"\s*\|\s*")).alias("genre_name")
    ).filter(col("genre_name").isNotNull() & (col("genre_name") != ""))
    
    # Join với dim_genre để lấy genre_id
    bridge = bridge.join(
        dim_genre,
        bridge.genre_name == dim_genre.genre_name,
        "left"
    ).select(
        bridge.track_id,
        dim_genre.genre_id
    ).dropDuplicates()
    
    print(f"✅ BRIDGE_TRACK_GENRE: {bridge.count()} associations")
    return bridge


def create_aggregate_tables(fact, dim_track, dim_artist, dim_market, dim_genre, bridge):
    """
    Tạo các bảng aggregate để phân tích nhanh
    """
    print("\n📈 Tạo AGGREGATE TABLES...")
    
    # AGG_ARTIST_PERFORMANCE: Tổng hợp theo artist
    agg_artist = fact.groupBy("artist_id").agg(
        count("track_id").alias("total_tracks"),
        avg("popularity").alias("avg_popularity"),
        spark_sum("artist_count").alias("total_collaborations")
    )
    agg_artist = agg_artist.join(dim_artist, "artist_id")
    print(f"  ✅ AGG_ARTIST_PERFORMANCE: {agg_artist.count()} artists")
    
    # AGG_MARKET_STATS: Tổng hợp theo market
    agg_market = fact.groupBy("market_id").agg(
        count("track_id").alias("total_tracks"),
        avg("popularity").alias("avg_popularity"),
        count(when(col("popularity") >= 60, 1)).alias("popular_tracks_count")
    )
    agg_market = agg_market.join(dim_market, "market_id")
    print(f"  ✅ AGG_MARKET_STATS: {agg_market.count()} markets")
    
    # AGG_GENRE_POPULARITY: Tổng hợp theo genre
    agg_genre = bridge.join(fact, "track_id") \
        .groupBy("genre_id").agg(
            count("track_id").alias("total_tracks"),
            avg("popularity").alias("avg_popularity")
        )
    agg_genre = agg_genre.join(dim_genre, "genre_id")
    print(f"  ✅ AGG_GENRE_POPULARITY: {agg_genre.count()} genres")
    
    return agg_artist, agg_market, agg_genre


def write_to_gold(df, table_name):
    """Ghi dữ liệu vào gold bucket"""
    output_path = f"{GOLD_BASE_PATH}/{table_name}"
    print(f"  💾 Ghi {table_name} -> {output_path}")
    
    df.coalesce(1).write \
        .mode('overwrite') \
        .option('header', 'true') \
        .csv(output_path)


def main():
    print("=" * 70)
    print("🎵 PYSPARK ETL: SILVER → GOLD (Data Warehouse)")
    print("   Xây dựng Star Schema: Dimensions + Fact Tables")
    print("=" * 70)
    
    try:
        # 1. Khởi tạo Spark
        spark = create_spark_session()
        
        # 2. Đọc silver data
        df_silver = read_silver_data(spark)
        
        print("\n" + "=" * 70)
        print("🏗️  BUILDING DIMENSION TABLES")
        print("=" * 70)
        
        # 3. Tạo Dimension Tables
        dim_track = create_dim_track(df_silver)
        dim_artist = create_dim_artist(df_silver)
        dim_album = create_dim_album(df_silver)
        dim_market = create_dim_market(df_silver)
        dim_genre = create_dim_genre(df_silver)
        dim_date = create_dim_date(df_silver)
        
        print("\n" + "=" * 70)
        print("🏗️  BUILDING FACT TABLE")
        print("=" * 70)
        
        # 4. Tạo Fact Table
        fact_performance = create_fact_track_performance(
            df_silver, dim_track, dim_artist, dim_album, dim_market, dim_date
        )
        
        # 5. Tạo Bridge Table
        bridge_track_genre = create_bridge_track_genre(df_silver, dim_track, dim_genre)
        
        print("\n" + "=" * 70)
        print("🏗️  BUILDING AGGREGATE TABLES")
        print("=" * 70)
        
        # 6. Tạo Aggregate Tables
        agg_artist, agg_market, agg_genre = create_aggregate_tables(
            fact_performance, dim_track, dim_artist, dim_market, dim_genre, bridge_track_genre
        )
        
        print("\n" + "=" * 70)
        print("💾 WRITING TO GOLD LAYER")
        print("=" * 70)
        
        # 7. Ghi vào Gold
        write_to_gold(dim_track, "dim_track")
        write_to_gold(dim_artist, "dim_artist")
        write_to_gold(dim_album, "dim_album")
        write_to_gold(dim_market, "dim_market")
        write_to_gold(dim_genre, "dim_genre")
        write_to_gold(dim_date, "dim_date")
        write_to_gold(fact_performance, "fact_track_performance")
        write_to_gold(bridge_track_genre, "bridge_track_genre")
        write_to_gold(agg_artist, "agg_artist_performance")
        write_to_gold(agg_market, "agg_market_stats")
        write_to_gold(agg_genre, "agg_genre_popularity")
        
        # 8. Summary
        print("\n" + "=" * 70)
        print("🎉 DATA WAREHOUSE HOÀN THÀNH!")
        print("=" * 70)
        print("📊 DIMENSION TABLES:")
        print(f"   • DIM_TRACK: {dim_track.count()} records")
        print(f"   • DIM_ARTIST: {dim_artist.count()} records")
        print(f"   • DIM_ALBUM: {dim_album.count()} records")
        print(f"   • DIM_MARKET: {dim_market.count()} records")
        print(f"   • DIM_GENRE: {dim_genre.count()} records")
        print(f"   • DIM_DATE: {dim_date.count()} records")
        print(f"\n📈 FACT TABLE:")
        print(f"   • FACT_TRACK_PERFORMANCE: {fact_performance.count()} records")
        print(f"\n🔗 BRIDGE TABLE:")
        print(f"   • BRIDGE_TRACK_GENRE: {bridge_track_genre.count()} records")
        print(f"\n📊 AGGREGATE TABLES:")
        print(f"   • AGG_ARTIST_PERFORMANCE: {agg_artist.count()} records")
        print(f"   • AGG_MARKET_STATS: {agg_market.count()} records")
        print(f"   • AGG_GENRE_POPULARITY: {agg_genre.count()} records")
        print(f"\n🌐 Truy cập Gold layer tại:")
        print(f"   http://localhost:9001/browser/{GOLD_BUCKET}/")
        print("=" * 70)
        
        spark.stop()
        print("\n✅ SparkSession đã đóng")
        return True
        
    except Exception as e:
        print(f"\n❌ LỖI: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
