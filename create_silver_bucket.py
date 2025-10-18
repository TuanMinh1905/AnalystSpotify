#!/usr/bin/env python3
from minio import Minio

client = Minio(
    'host.docker.internal:9000',
    access_key='longminh',
    secret_key='longminh',
    secure=False
)

if not client.bucket_exists('silver'):
    client.make_bucket('silver')
    print('✅ Đã tạo bucket silver')
else:
    print('✅ Bucket silver đã tồn tại')
