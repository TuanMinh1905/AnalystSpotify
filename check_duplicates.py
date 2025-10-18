#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kiểm tra duplicates trong bronze data"""

import pandas as pd
from minio import Minio
from io import BytesIO

# Kết nối MinIO
client = Minio('host.docker.internal:9000', access_key='longminh', secret_key='longminh', secure=False)
data = client.get_object('bronze', 'global_official_new_releases.csv')
df = pd.read_csv(BytesIO(data.read()))

print('📊 PHÂN TÍCH DỮ LIỆU BRONZE:')
print('=' * 70)
print(f'Tổng số dòng: {len(df):,}')
print(f'Số track_id unique: {df["track_id"].nunique():,}')
print(f'Số dòng trùng lặp 100%: {df.duplicated().sum():,}')

print(f'\n🔍 VÍ DỤ 1 TRACK XUẤT HIỆN Ở NHIỀU MARKET:')
print('=' * 70)
# Lấy track_id xuất hiện nhiều nhất
most_common_track = df["track_id"].value_counts().index[0]
track_example = df[df["track_id"] == most_common_track]
print(f'Track: {track_example.iloc[0]["track_name"]} - {track_example.iloc[0]["primary_artist"]}')
print(f'Xuất hiện ở {len(track_example)} markets!')
print(f'\nCác markets:')
print(track_example[["track_id", "track_name", "market"]].to_string(index=False))

print(f'\n📊 NULL VALUES:')
print('=' * 70)
null_counts = df.isnull().sum()
null_counts = null_counts[null_counts > 0]
if len(null_counts) > 0:
    for col, count in null_counts.items():
        print(f'{col}: {count:,} ({count/len(df)*100:.2f}%)')
else:
    print('✅ Không có null values')

print(f'\n📊 PHÂN TÍCH DUPLICATE THEO TỪNG TIÊU CHÍ:')
print('=' * 70)
print(f'1. Duplicate theo track_id only: {len(df) - df["track_id"].nunique():,}')
print(f'2. Duplicate 100% (tất cả cột): {df.duplicated().sum():,}')
print(f'3. Duplicate theo track_id + market: {len(df) - len(df.drop_duplicates(["track_id", "market"])):,}')
