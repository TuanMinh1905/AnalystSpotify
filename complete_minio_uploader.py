#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
☁️ COMPLETE MINIO UPLOADER
Ghép từ: container_upload.py + simple_upload.py
Upload file CSV lên MinIO với hỗ trợ cả container và host
"""

import os
import sys
import socket
from minio import Minio
from minio.error import S3Error

# MinIO Configuration (từ simple_upload.py)
MINIO_ENDPOINT = "localhost:9000"  
MINIO_ACCESS_KEY = "longminh"      
MINIO_SECRET_KEY = "longminh"      
MINIO_BUCKET = "music"             
MINIO_SECURE = False               

def find_minio_endpoint():
    """Tìm MinIO endpoint từ container (từ container_upload.py)"""
    # Thử các endpoint có thể (ưu tiên gateway IP)
    possible_endpoints = [
        "172.18.0.1:9000",     # Gateway của Hadoop network  
        "host.docker.internal:9000",  # Docker Desktop
        "172.20.0.1:9000",     # Gateway của MinIO network
        "172.17.0.1:9000",     # Docker bridge IP
        "minio:9000",          # Tên container MinIO (nếu cùng network)
        "localhost:9000"       # Fallback
    ]
    
    print("🔍 Tìm MinIO endpoint...")
    for endpoint in possible_endpoints:
        try:
            host, port = endpoint.split(':')
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((host, int(port)))
            sock.close()
            
            if result == 0:
                print(f"✅ Tìm thấy MinIO tại: {endpoint}")
                return endpoint
            else:
                print(f"❌ Không kết nối được: {endpoint}")
        except Exception as e:
            print(f"❌ Lỗi kiểm tra {endpoint}: {e}")
    
    print("⚠️ Không tìm thấy MinIO endpoint nào")
    return None

def upload_csv_to_minio_simple():
    """Upload file CSV duy nhất lên MinIO (từ simple_upload.py)"""
    print("☁️ UPLOAD VIETNAM SONGS DATABASE TO MINIO")
    print("=" * 50)
    
    # File cần upload
    csv_file = "data_tables/vietnam_songs_database.csv"
    
    # Kiểm tra file tồn tại
    if not os.path.exists(csv_file):
        print(f"❌ File không tồn tại: {csv_file}")
        print("💡 Chạy extract_songs_table.py trước để tạo dữ liệu")
        return False
    
    # Setup MinIO client
    try:
        client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE
        )
        
        # Kiểm tra bucket
        if not client.bucket_exists(MINIO_BUCKET):
            print(f"🪣 Tạo bucket '{MINIO_BUCKET}'...")
            client.make_bucket(MINIO_BUCKET)
        else:
            print(f"✅ Bucket '{MINIO_BUCKET}' đã tồn tại")
            
    except Exception as e:
        print(f"❌ Lỗi kết nối MinIO: {e}")
        return False
    
    # Upload file với tên gốc (không timestamp)
    object_name = "vietnam_songs_database.csv"
    
    try:
        # Upload file
        client.fput_object(MINIO_BUCKET, object_name, csv_file)
        
        file_size = os.path.getsize(csv_file)
        print(f"✅ Upload thành công: {object_name}")
        print(f"📊 Kích thước: {file_size/1024:.1f} KB")
        
        # Hiển thị URL truy cập
        print(f"\n🌐 Truy cập file tại:")
        print(f"   📁 MinIO Web UI: http://localhost:9001/browser/{MINIO_BUCKET}/")
        print(f"   🔗 Direct URL: http://{MINIO_ENDPOINT}/{MINIO_BUCKET}/{object_name}")
        
        return True
        
    except S3Error as e:
        print(f"❌ Lỗi S3: {e}")
        return False
    except Exception as e:
        print(f"❌ Lỗi upload: {e}")
        return False

def upload_csv_to_minio_container():
    """Upload file CSV từ container lên MinIO (từ container_upload.py)"""
    print("☁️ UPLOAD VIETNAM SONGS DATABASE TO MINIO (FROM CONTAINER)")
    print("=" * 60)
    
    # File cần upload
    csv_file = "data_tables/vietnam_songs_database.csv"
    
    # Kiểm tra file tồn tại
    if not os.path.exists(csv_file):
        print(f"❌ File không tồn tại: {csv_file}")
        return False
    
    # Tìm MinIO endpoint
    minio_endpoint = find_minio_endpoint()
    if not minio_endpoint:
        print("❌ Không thể tìm thấy MinIO server")
        print("💡 MinIO có thể chưa chạy hoặc không accessible từ container")
        return False
    
    # Setup MinIO client
    try:
        client = Minio(
            minio_endpoint,
            access_key="longminh",
            secret_key="longminh",
            secure=False
        )
        
        # Test connection
        bucket_name = "music"
        if not client.bucket_exists(bucket_name):
            print(f"🪣 Tạo bucket '{bucket_name}'...")
            client.make_bucket(bucket_name)
        else:
            print(f"✅ Bucket '{bucket_name}' đã tồn tại")
            
    except Exception as e:
        print(f"❌ Lỗi kết nối MinIO: {e}")
        return False
    
    # Upload file
    object_name = "vietnam_songs_database.csv"
    
    try:
        # Upload file
        client.fput_object(bucket_name, object_name, csv_file)
        
        file_size = os.path.getsize(csv_file)
        print(f"✅ Upload thành công: {object_name}")
        print(f"📊 Kích thước: {file_size/1024:.1f} KB")
        print(f"🌐 MinIO endpoint: {minio_endpoint}")
        
        return True
        
    except S3Error as e:
        print(f"❌ Lỗi S3: {e}")
        return False
    except Exception as e:
        print(f"❌ Lỗi upload: {e}")
        return False

def detect_environment():
    """Phát hiện môi trường chạy"""
    # Kiểm tra nếu đang chạy trong container
    if os.path.exists('/.dockerenv'):
        return "container"
    
    # Kiểm tra hostname patterns
    hostname = os.uname().nodename if hasattr(os, 'uname') else ""
    if any(x in hostname.lower() for x in ['master', 'worker', 'hadoop', 'container']):
        return "container"
    
    # Kiểm tra network interfaces (container thường có docker interfaces)
    try:
        import subprocess
        result = subprocess.run(['ip', 'route'], capture_output=True, text=True)
        if 'docker' in result.stdout.lower():
            return "container"
    except:
        pass
    
    return "host"

def main():
    """Main upload function - auto-detect environment"""
    print("☁️ COMPLETE MINIO UPLOADER")
    print("=" * 60)
    
    # Phát hiện môi trường
    env = detect_environment()
    print(f"🔍 Phát hiện môi trường: {env}")
    
    if env == "container":
        print("🐳 Chạy từ container - sử dụng container upload logic")
        success = upload_csv_to_minio_container()
        
        if success:
            print(f"\n🎉 Upload hoàn tất!")
            print("💡 File CSV đã có sẵn trên MinIO")
            print("🌐 Truy cập: http://localhost:9001/browser/music/")
        else:
            print(f"\n❌ Upload thất bại")
            print("💡 File CSV vẫn có sẵn tại: data_tables/vietnam_songs_database.csv")
            print("\n💾 COPY FILE VỀ HOST:")
            print("   docker cp master:/tmp/data_tables/vietnam_songs_database.csv ./")
            print("   Sau đó chạy: python3 complete_minio_uploader.py")
    
    else:
        print("🖥️ Chạy từ host - sử dụng simple upload logic")
        success = upload_csv_to_minio_simple()
        
        if success:
            print(f"\n🎉 Upload hoàn tất!")
            print("💡 File CSV đã có sẵn trên MinIO với tên: vietnam_songs_database.csv")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)