#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🇻🇳 VIETNAM MUSIC DATA COLLECTOR & PROCESSOR
Ghép từ: CaoDuLieu.py + extract_songs_table.py + main.py (setup environment)
Thu thập và xử lý dữ liệu nhạc Việt Nam từ Spotify API
"""

# pip install requests python-dateutil minio
import os
import sys
import json
import base64
import socket
import requests
import pandas as pd
import csv
import subprocess
import time
import math
from collections import Counter, defaultdict
from datetime import datetime
try:
    from minio import Minio
    from minio.error import S3Error
except ImportError:
    print("⚠️ MinIO library chưa cài đặt, sẽ cài đặt tự động...")
    Minio = None
    S3Error = None

# ========= CONFIG =========
# Ưu tiên đọc từ biến môi trường cho an toàn; nếu thiếu thì thay trực tiếp ở đây khi test cục bộ.
CLIENT_ID = os.getenv("820ea85e09f642e396d3224165d7e72e", "820ea85e09f642e396d3224165d7e72e")
CLIENT_SECRET = os.getenv("e5e4c0c69e3b4abfb190117b0f6110b0", "e5e4c0c69e3b4abfb190117b0f6110b0")

# Playlist ID chỉ cho Việt Nam
PLAYLISTS_BY_COUNTRY = {
    "VN": "4QtoFLP8qPILIVQuPEMhun",     # Nhạc Remix HOT TIKTOK 2025 (hoạt động)
}

# Market code cho Việt Nam
MARKET_BY_COUNTRY = {
    "VN": "VN",
}

# Thư mục lưu snapshot theo ngày
SNAPSHOT_DIR = "snapshots"
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

# Thư mục lưu raw JSON responses từ Spotify API
JSON_RESPONSES_DIR = "json_responses"
os.makedirs(JSON_RESPONSES_DIR, exist_ok=True)

# Thư mục lưu raw JSON responses từ Spotify API
JSON_RESPONSES_DIR = "json_responses"
os.makedirs(JSON_RESPONSES_DIR, exist_ok=True)

# Cấu hình cho extract_songs_table
JSON_DIR = "json_responses"
OUTPUT_DIR = "data_tables"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# MinIO Configuration
MINIO_ENDPOINT = "localhost:9000"  
MINIO_ACCESS_KEY = "longminh"      
MINIO_SECRET_KEY = "longminh"      
MINIO_BUCKET = "music"             
MINIO_SECURE = False

# ========= ENVIRONMENT SETUP (từ main.py) =========
def run_command(command, description, show_output=False):
    """Chạy lệnh shell và hiển thị kết quả"""
    print(f"🔄 {description}...")
    try:
        if show_output:
            # Hiển thị output real-time
            result = subprocess.run(command, shell=True, text=True)
            success = result.returncode == 0
        else:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            success = result.returncode == 0
            if not success and result.stderr:
                print(f"   Error: {result.stderr.strip()}")
        
        if success:
            print(f"✅ {description}: Thành công")
        else:
            print(f"❌ {description}: Thất bại")
        
        return success
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def setup_environment():
    """Cài đặt môi trường Python với root privileges"""
    print("🔧 THIẾT LẬP MÔI TRƯỜNG")
    print("-" * 50)
    
    # Update package list
    if not run_command("apt-get update -y", "Cập nhật package list"):
        print("⚠️ Không thể update packages, tiếp tục...")
    
    # Install pip3 và python dev tools
    if not run_command("apt-get install -y python3-pip python3-dev build-essential", "Cài đặt pip3 và dev tools"):
        print("⚠️ Không thể cài đặt pip3, thử cách khác...")
        # Fallback: try với --force-yes
        run_command("apt-get install -y --force-yes python3-pip", "Cài đặt pip3 (force)")
    
    # Upgrade pip
    run_command("python3 -m pip install --upgrade pip", "Upgrade pip")
    
    # Install Python dependencies
    dependencies = [
        "requests",
        "pandas", 
        "openpyxl",
        "python-dateutil",
        "minio"
    ]
    
    print("\n📦 CÀI ĐẶT PYTHON PACKAGES")
    print("-" * 30)
    for package in dependencies:
        run_command(f"python3 -m pip install {package}", f"Cài đặt {package}")
    
    print("✅ Environment setup hoàn tất!")
    return True

# ========= AUTH (từ CaoDuLieu.py) =========
def get_app_token(client_id: str, client_secret: str):
    if not client_id or not client_secret or "YOUR_" in client_id or "YOUR_" in client_secret:
        raise RuntimeError("Thiếu CLIENT_ID/CLIENT_SECRET. Đặt biến môi trường SPOTIFY_CLIENT_ID và SPOTIFY_CLIENT_SECRET hoặc sửa trong code.")
    token_url = "https://accounts.spotify.com/api/token"
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}"}
    data = {"grant_type": "client_credentials"}
    r = requests.post(token_url, headers=headers, data=data, timeout=30)
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        raise RuntimeError(f"Lỗi lấy access token: {e} | resp={r.text[:200]}") from e
    j = r.json()
    return j["access_token"], j["expires_in"]

# ========= API HELPERS (từ CaoDuLieu.py) =========
def save_json_response(endpoint_name: str, response_data, extra_info=None):
    """Lưu JSON response vào file với timestamp"""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{endpoint_name}.json"
    filepath = os.path.join(JSON_RESPONSES_DIR, filename)

    data_to_save = {
        "timestamp": timestamp,
        "endpoint": endpoint_name,
        "extra_info": extra_info,
        "response": response_data
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data_to_save, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved JSON response: {filename}")

def list_saved_json_responses():
    """Hiển thị danh sách các JSON response đã lưu"""
    if not os.path.exists(JSON_RESPONSES_DIR):
        print("📁 Chưa có JSON responses nào được lưu")
        return

    files = [f for f in os.listdir(JSON_RESPONSES_DIR) if f.endswith('.json')]
    if not files:
        print("📁 Chưa có JSON responses nào được lưu")
        return

    print(f"\n📊 Đã lưu {len(files)} JSON response files:")
    files.sort()
    for f in files[-10:]:  # Hiển thị 10 file mới nhất
        filepath = os.path.join(JSON_RESPONSES_DIR, f)
        size = os.path.getsize(filepath) / 1024  # KB
        print(f"  🗂️  {f} ({size:.1f} KB)")

    if len(files) > 10:
        print(f"  ... và {len(files) - 10} file khác")

def sp_get(url: str, token: str, params=None, save_response=True, endpoint_name=None):
    h = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=h, params=params or {}, timeout=30)
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        raise RuntimeError(f"HTTP {r.status_code} for {url} | params={params} | resp={r.text[:200]}") from e

    response_json = r.json()

    # Lưu response nếu được yêu cầu
    if save_response and endpoint_name:
        extra_info = {
            "url": url,
            "params": params,
            "status_code": r.status_code
        }
        save_json_response(endpoint_name, response_json, extra_info)

    return response_json

def batched(iterable, n=50):
    batch = []
    for x in iterable:
        batch.append(x)
        if len(batch) == n:
            yield batch
            batch = []
    if batch:
        yield batch

# ---- Tìm playlist bằng search (thay vì browse bị lỗi) ----
def get_toplists_playlists(token: str, market: str = "VN"):
    # Search cho các playlist Top hits phổ biến
    search_terms = ["Top 50", "Today's Top Hits", "Viral 50"]
    all_items = []

    for term in search_terms:
        try:
            url = "https://api.spotify.com/v1/search"
            params = {"q": term, "type": "playlist", "limit": 10, "market": market}
            j = sp_get(url, token, params=params, endpoint_name=f"search_playlists_{term.replace(' ', '_')}_{market}")
            items = j.get("playlists", {}).get("items", []) or []
            # Lọc bỏ các phần tử null
            items = [item for item in items if item is not None]
            all_items.extend(items)
        except Exception as e:
            print(f"Warning: Search failed for '{term}': {e}")
            continue

    return all_items

def pick_chart_playlist_id(token: str, market: str, prefer_keywords=None):
    if prefer_keywords is None:
        prefer_keywords = ["Top 50", "Viral 50", "Today's Top Hits"]

    items = get_toplists_playlists(token, market)
    # Ưu tiên playlist do Spotify sở hữu và tên có từ khóa mong muốn
    def is_spotify_owner(it):
        owner = ((it.get("owner") or {}).get("id") or "").lower()
        return owner in {"spotify", "spotifycharts"}
    # lọc theo keyword
    for kw in prefer_keywords:
        for it in items:
            name = it.get("name", "")
            if kw.lower() in name.lower() and is_spotify_owner(it):
                return it.get("id"), name

    # fallback: bất kỳ playlist đầu tiên
    if items:
        it0 = items[0]
        return it0.get("id"), it0.get("name")
    return None, None

# ---- Fallback: tìm bằng Search (nếu toplists rỗng) ----
def find_playlist_id_by_search(name: str, token: str, market: str = "VN"):
    url = "https://api.spotify.com/v1/search"
    params = {"q": name, "type": "playlist", "limit": 5, "market": market}
    j = sp_get(url, token, params=params, endpoint_name=f"find_playlist_{name.replace(' ', '_')}_{market}")
    items = j.get("playlists", {}).get("items", []) or []
    # Lọc bỏ các phần tử null
    items = [item for item in items if item is not None]
    preferred_owners = {"spotify", "spotifycharts"}
    for it in items:
        owner = (it.get("owner", {}) or {}).get("id", "").lower()
        if owner in preferred_owners:
            return it.get("id"), it.get("name")
            
    if items:
        it0 = items[0]
        return it0.get("id"), it0.get("name")
    return None, None

# ---- Lấy track trong playlist (có phân trang) ----
def get_playlist_items(playlist_id: str, token: str, market: str, limit=100):
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    items = []
    params = {"limit": limit, "market": market}
    page_num = 1

    while True:
        j = sp_get(url, token, params=params, endpoint_name=f"playlist_tracks_{playlist_id}_page{page_num}_{market}")
        items.extend(j.get("items", []))
        next_url = j.get("next")
        if not next_url:
            break
        url, params = next_url, {}  # next đã bao gồm query
        page_num += 1

    tracks = [it["track"] for it in items if it and it.get("track")]
    return tracks

def get_artists_genres(artist_ids, token: str):
    genres_by_artist = {}
    ids = [aid for aid in artist_ids if aid]
    for i, batch in enumerate(batched(ids, 50)):
        url = "https://api.spotify.com/v1/artists"
        j = sp_get(url, token, params={"ids": ",".join(batch)}, endpoint_name=f"artists_batch_{i+1}")
        for a in j.get("artists", []):
            if a and a.get("id"):
                genres_by_artist[a["id"]] = {
                    "genres": a.get("genres", []),
                    "popularity": a.get("popularity", 0),
                    "followers": a.get("followers", {}).get("total", 0)
                }
    return genres_by_artist

# ========= ANALYTICS (từ CaoDuLieu.py) =========
def analyze_country(country: str, token: str):
    market = MARKET_BY_COUNTRY.get(country, "VN")

    # Sử dụng playlist ID trực tiếp từ config
    if country in PLAYLISTS_BY_COUNTRY:
        pid = PLAYLISTS_BY_COUNTRY[country]
        pname = f"Predefined playlist for {country}"
    else:
        # Fallback: tìm bằng search
        pid, pname = pick_chart_playlist_id(token, market)
        if not pid:
            pid, pname = find_playlist_id_by_search("Top 50", token, market)
        if not pid:
            return {}

    try:
        tracks = get_playlist_items(pid, token, market=market)
        if not tracks:
            return {}
    except Exception as e:
        print(f"❌ [{country}] Lỗi phân tích: {e}")
        return {
            "country": country,
            "market": market,
            "playlist_id": pid,
            "playlist_name": pname,
            "top_artists": [],
            "top_genres": [],
            "top_tracks": [],
            "raw_count": 0
        }
    artist_counter = Counter()
    genre_counter = Counter()
    track_popularity = []  # (name, popularity, artists)

    # gom artist IDs
    artist_ids = set()
    for t in tracks:
        for a in t.get("artists", []):
            if a and a.get("id"):
                artist_ids.add(a["id"])

    genres_by_artist = get_artists_genres(artist_ids, token)

    for t in tracks:
        artists = t.get("artists", [])
        names = [a.get("name") for a in artists if a]
        ids = [a.get("id") for a in artists if a and a.get("id")]
        for n in names:
            artist_counter[n] += 1

        # suy genre từ artist
        gset = set()
        for aid in ids:
            if aid in genres_by_artist:
                gset.update(genres_by_artist[aid].get("genres", []))
        for g in gset:
            genre_counter[g] += 1

        track_popularity.append((t.get("name"), t.get("popularity", 0), names))

    top_artists = artist_counter.most_common(15)
    top_genres = genre_counter.most_common(15)
    track_popularity.sort(key=lambda x: x[1], reverse=True)
    top_tracks = track_popularity[:15]

    return {
        "country": country,
        "market": market,
        "playlist_id": pid,
        "playlist_name": pname,
        "top_artists": top_artists,
        "top_genres": top_genres,
        "top_tracks": top_tracks,
        "raw_count": len(tracks),
    }

def save_snapshot(date_str: str, country: str, analysis: dict):
    path = os.path.join(SNAPSHOT_DIR, f"{date_str}_{country}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    return path

def load_snapshots(country: str | None = None):
    files = sorted([f for f in os.listdir(SNAPSHOT_DIR) if f.endswith(".json")])
    if country:
        files = [f for f in files if f"_{country}.json" in f]
    data = []
    for fn in files:
        with open(os.path.join(SNAPSHOT_DIR, fn), "r", encoding="utf-8") as f:
            data.append((fn[:-5], json.load(f)))
    return data

def detect_emerging_genres(country: str, min_points=3):
    """
    So sánh snapshot mới nhất với trung bình lịch sử (z-score thô) để tìm genre 'đang nổi'.
    Yêu cầu >= min_points snapshot.
    """
    series = load_snapshots(country)
    if len(series) < min_points:
        return []

    timeline = []
    all_genres = set()
    for date_str, snap in series:
        counts = dict(snap.get("top_genres", []))
        all_genres |= set(counts.keys())
        timeline.append(counts)

    scores = []
    for g in all_genres:
        arr = [t.get(g, 0) for t in timeline]
        if len(arr) < 2:
            continue
        mean = sum(arr[:-1]) / max(1, len(arr) - 1)
        var = sum((x - mean) ** 2 for x in arr[:-1]) / max(1, len(arr) - 1)
        std = math.sqrt(var)
        latest = arr[-1]
        z = (latest - mean) / (std + 1e-6)
        growth = latest - arr[-2]
        scores.append((g, z, growth, latest))

    scores.sort(key=lambda x: (x[1], x[2], x[3]), reverse=True)
    return scores[:10]

# ========= EXTRACT SONGS DATA (từ extract_songs_table.py) =========
def extract_songs_data():
    """Trích xuất dữ liệu bài hát từ các JSON files - CHỈ VIỆT NAM"""
    print("🇻🇳 TRÍCH XUẤT DỮ LIỆU BÀI HÁT VIỆT NAM...")
    
    # Tìm playlist tracks files CHỈ cho Việt Nam (market VN)
    playlist_files = [f for f in os.listdir(JSON_DIR) 
                     if f.endswith('.json') and 'playlist_tracks' in f and '_VN.json' in f]
    
    # Nếu không có file _VN.json, tìm file có chứa playlist ID Việt Nam
    if not playlist_files:
        vn_playlist_id = "4QtoFLP8qPILIVQuPEMhun"  # ID playlist Việt Nam
        playlist_files = [f for f in os.listdir(JSON_DIR) 
                         if f.endswith('.json') and 'playlist_tracks' in f and vn_playlist_id in f]
    
    # Tìm tất cả artists files (cần để lấy thông tin nghệ sĩ)
    artist_files = [f for f in os.listdir(JSON_DIR)
                   if f.endswith('.json') and 'artists_batch' in f]
    
    print(f"📁 Tìm thấy {len(playlist_files)} playlist files Việt Nam và {len(artist_files)} artist files")
    
    if not playlist_files:
        print("❌ Không tìm thấy file playlist Việt Nam nào!")
        print("💡 Hãy chạy CaoDuLieu.py trước để tạo dữ liệu Việt Nam")
        return []
    
    # Load artist data trước
    artists_data = load_artists_data(artist_files)
    print(f"👤 Loaded {len(artists_data)} artists data")
    
    # Trích xuất tracks data
    all_songs = []
    
    for filename in playlist_files:
        filepath = os.path.join(JSON_DIR, filename)
        
        # Parse metadata từ filename
        parts = filename.replace('.json', '').split('_')
        timestamp = f"{parts[0]}_{parts[1]}"
        market = "VN"  # Chỉ xử lý Việt Nam
        playlist_id = "4QtoFLP8qPILIVQuPEMhun"  # Playlist Việt Nam
        
        # Xác nhận đây là file Việt Nam
        if 'VN' not in filename and '4QtoFLP8qPILIVQuPEMhun' not in filename:
            print(f"⏭️  Bỏ qua file không phải Việt Nam: {filename}")
            continue
        
        print(f"📄 Processing: {filename}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            response = data.get('response', {})
            items = response.get('items', [])
            
            for item in items:
                if item and item.get('track'):
                    track = item['track']
                    song_info = extract_track_info(track, item, market, playlist_id, timestamp, artists_data)
                    if song_info:
                        all_songs.append(song_info)
                    
        except Exception as e:
            print(f"❌ Lỗi xử lý file {filename}: {e}")
            continue
    
    print(f"✅ Trích xuất được {len(all_songs)} bài hát")
    return all_songs

def load_artists_data(artist_files):
    """Load dữ liệu artists từ JSON files"""
    artists_data = {}
    
    for filename in artist_files:
        filepath = os.path.join(JSON_DIR, filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            response = data.get("response", {})
            artists = response.get("artists", [])
            
            for artist in artists:
                if artist and artist.get("id"):
                    artists_data[artist["id"]] = {
                        "genres": artist.get("genres", []),
                        "popularity": artist.get("popularity", 0),
                        "followers": artist.get("followers", {}).get("total", 0)
                    }
                    
        except Exception as e:
            print(f"⚠️ Lỗi đọc file {filename}: {e}")
    
    return artists_data

def extract_track_info(track, item, market, playlist_id, timestamp, artists_data):
    """Trích xuất thông tin chi tiết của một bài hát"""
    try:
        # Thông tin cơ bản về track
        track_id = track.get('id', '')
        track_name = track.get('name', '')
        
        if not track_id or not track_name:
            return None
        
        # Album info
        album = track.get('album', {})
        album_name = album.get('name', '')
        release_date = album.get('release_date', '')
        album_type = album.get('album_type', '')
        
        # Artists info
        track_artists = track.get('artists', [])
        primary_artist = track_artists[0] if track_artists else {}
        primary_artist_name = primary_artist.get('name', '')
        primary_artist_id = primary_artist.get('id', '')
        
        # Thông tin chi tiết từ artists_data
        artist_detail = artists_data.get(primary_artist_id, {})
        artist_popularity = artist_detail.get('popularity', 0)
        artist_followers = artist_detail.get('followers', 0)
        artist_genres = artist_detail.get('genres', [])
        
        # Tất cả artists
        all_artists = [a.get('name', '') for a in track_artists if a]
        all_artist_ids = [a.get('id', '') for a in track_artists if a and a.get('id')]
        
        # Collect tất cả genres từ tất cả artists
        all_genres = set()
        for aid in all_artist_ids:
            if aid in artists_data:
                all_genres.update(artists_data[aid].get('genres', []))
        
        # Track features
        duration_ms = track.get('duration_ms', 0)
        duration_min = round(duration_ms / 60000, 2) if duration_ms else 0
        popularity = track.get('popularity', 0)
        explicit = track.get('explicit', False)
        
        # Playlist/context info
        added_at = item.get('added_at', '')
        added_by = item.get('added_by', {}).get('id', '') if item.get('added_by') else ''
        
        # Preview và external URLs
        preview_url = track.get('preview_url', '')
        external_url = track.get('external_urls', {}).get('spotify', '')
        
        # Album images
        album_images = album.get('images', [])
        album_image_url = album_images[0].get('url', '') if album_images else ''
        
        return {
            # Thông tin track cơ bản
            'track_id': track_id,
            'track_name': track_name,
            'duration_minutes': duration_min,
            'popularity': popularity,
            'explicit': explicit,
            'preview_url': preview_url,
            'spotify_url': external_url,
            # Thông tin nghệ sĩ
            'primary_artist': primary_artist_name,
            'primary_artist_id': primary_artist_id,
            'all_artists': ' | '.join(all_artists),
            'artist_count': len(all_artists),
            'artist_popularity': artist_popularity,
            'artist_followers': artist_followers,
            # Thông tin thể loại
            'primary_genres': ' | '.join(artist_genres),
            'all_genres': ' | '.join(sorted(all_genres)),
            'genre_count': len(all_genres),
            'main_genre': list(all_genres)[0] if all_genres else '',
            # Thông tin album  
            'album_name': album_name,
            'album_type': album_type,
            'release_date': release_date,
            'release_year': release_date[:4] if len(release_date) >= 4 else '',
            'album_image_url': album_image_url,
            # Thông tin context
            'market': market,
            'playlist_id': playlist_id,
            'added_at': added_at,
            'added_by': added_by,
            'extracted_at': timestamp,
            # Thông tin phân loại
            'is_collaboration': len(all_artists) > 1,
            'is_recent': release_date >= '2020' if release_date else False,
            'popularity_tier': get_popularity_tier(popularity),
            'duration_category': get_duration_category(duration_min),
        }
        
    except Exception as e:
        print(f"❌ Lỗi extract track {track.get('name', 'Unknown')}: {e}")
        return None

def get_popularity_tier(popularity):
    """Phân loại độ phổ biến"""
    if popularity >= 80:
        return "Viral"
    elif popularity >= 60:
        return "Popular"
    elif popularity >= 40:
        return "Moderate"
    elif popularity >= 20:
        return "Niche"
    else:
        return "Underground"

def get_duration_category(duration_min):
    """Phân loại thời lượng bài hát"""
    if duration_min < 2:
        return "Short"
    elif duration_min < 3.5:
        return "Standard"
    elif duration_min < 5:
        return "Long"
    else:
        return "Extended"

def save_to_csv(songs_data, filename="vietnam_songs_database.csv"):
    """Lưu dữ liệu ra file CSV - CHỈ VIỆT NAM"""
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    if not songs_data:
        print("❌ Không có dữ liệu để lưu")
        return
    
    # Lấy tất cả columns
    columns = list(songs_data[0].keys())
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(songs_data)
    
    print(f"💾 Đã lưu {len(songs_data)} bài hát vào {filepath}")
    return filepath

def save_to_excel(songs_data, filename="vietnam_songs_database.xlsx"):
    """Lưu dữ liệu ra file Excel với multiple sheets - CHỈ VIỆT NAM"""
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    if not songs_data:
        print("❌ Không có dữ liệu để lưu")
        return
    
    # Tạo DataFrame
    df = pd.DataFrame(songs_data)
    
    # Tạo Excel với multiple sheets
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        # Sheet chính với tất cả dữ liệu Việt Nam
        df.to_excel(writer, sheet_name='Vietnam_Songs', index=False)
        
        # Sheet thống kê Việt Nam
        vn_stats = df.agg({
            'track_id': 'count',
            'popularity': 'mean',
            'artist_followers': 'mean',
            'duration_minutes': 'mean'
        }).round(2)
        vn_stats_df = pd.DataFrame([vn_stats], index=['Vietnam'])
        vn_stats_df.to_excel(writer, sheet_name='Vietnam_Stats')
        
        # Sheet top Vietnamese artists
        artist_stats = df.groupby('primary_artist').agg({
            'track_id': 'count',
            'popularity': 'mean',
            'artist_followers': 'first'
        }).sort_values('track_id', ascending=False).head(50)
        artist_stats.to_excel(writer, sheet_name='Top_VN_Artists')
        
        # Sheet top genres
        genre_data = []
        for _, row in df.iterrows():
            if pd.notna(row['all_genres']):
                for genre in row['all_genres'].split(' | '):
                    if genre:
                        genre_data.append({
                            'genre': genre,
                            'track_count': 1
                        })
        
        if genre_data:
            genre_df = pd.DataFrame(genre_data).groupby('genre')['track_count'].sum().sort_values(ascending=False).head(30)
            genre_df.to_excel(writer, sheet_name='Top_VN_Genres')
    
    print(f"📊 Đã lưu {len(songs_data)} bài hát vào {filepath} với multiple sheets")
    return filepath

def generate_summary_report(songs_data):
    """Tạo báo cáo tổng kết"""
    if not songs_data:
        return
    
    print(f"\n📊 BÁO CÁO TỔNG KẾT - NHẠC VIỆT NAM")
    print("=" * 50)
    
    df = pd.DataFrame(songs_data)
    
    print(f"🎵 Tổng số bài hát Việt Nam: {len(df)}")
    print(f"👤 Số nghệ sĩ Việt Nam unique: {df['primary_artist'].nunique()}")
    print(f"🎭 Số thể loại nhạc unique: {len(set([g for genres in df['all_genres'].dropna() for g in genres.split(' | ') if g]))}")
    print(f"🇻🇳 Market: Việt Nam (VN)")
    print(f"💿 Số album unique: {df['album_name'].nunique()}")
    
    print(f"\n📈 THỐNG KÊ POPULARITY:")
    print(f"   Trung bình: {df['popularity'].mean():.1f}")
    print(f"   Cao nhất: {df['popularity'].max()}")
    print(f"   Thấp nhất: {df['popularity'].min()}")
    
    print(f"\n⏱️ THỐNG KÊ THỜI LƯỢNG:")
    print(f"   Trung bình: {df['duration_minutes'].mean():.2f} phút")
    print(f"   Dài nhất: {df['duration_minutes'].max():.2f} phút")
    print(f"   Ngắn nhất: {df['duration_minutes'].min():.2f} phút")
    
    print(f"\n🔥 TOP 10 NGHỆ SĨ VIỆT NAM:")
    top_artists = df.groupby('primary_artist').size().sort_values(ascending=False).head(10)
    for artist, count in top_artists.items():
        print(f"   {artist}: {count} bài")
    
    print(f"\n🎭 TOP 10 THỂ LOẠI NHẠC VIỆT:")
    genre_counts = {}
    for genres_str in df['all_genres'].dropna():
        for genre in genres_str.split(' | '):
            if genre:
                genre_counts[genre] = genre_counts.get(genre, 0) + 1
    
    top_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    for genre, count in top_genres:
        print(f"   {genre}: {count} bài")

# ========= MAIN PIPELINE =========
def run_data_collection():
    """Chạy thu thập dữ liệu từ Spotify API (từ CaoDuLieu.py)"""
    print("🇻🇳 PHÂN TÍCH NHẠC VIỆT NAM - SPOTIFY DATA ANALYSIS")
    print("=" * 60)
    
    token, _ = get_app_token(CLIENT_ID, CLIENT_SECRET)
    date_str = datetime.utcnow().strftime("%Y%m%d")

    all_results = {}
    for country in PLAYLISTS_BY_COUNTRY.keys():
        try:
            analysis = analyze_country(country, token)
            all_results[country] = analysis
            save_snapshot(date_str, country, analysis)
        except Exception as e:
            print(f"❌ Lỗi phân tích {country}: {e}")

    # In kết quả tổng quan
    for country, res in all_results.items():
        print(f"\n=== {country} (market={res['market']}) | tracks={res['raw_count']} ===")
        print(f"Playlist: {res['playlist_name']}  (ID: {res['playlist_id']})")
        print("Top artists:")
        for name, cnt in res["top_artists"][:10]:
            print(f"  {name}: {cnt}")
        print("Top genres:")
        for g, cnt in res["top_genres"][:10]:
            print(f"  {g}: {cnt}")
        print("Top tracks (by popularity):")
        for name, pop, artists in res["top_tracks"][:5]:
            print(f"  {name} (pop={pop}) by {artists}")

    # Emerging genres per country (cần >=3 snapshot)
    for country in PLAYLISTS_BY_COUNTRY.keys():
        emerging = detect_emerging_genres(country, min_points=3)
        if emerging:
            print(f"\n🔥 Emerging genres in {country}:")
            for g, z, growth, latest in emerging[:5]:
                print(f"  {g}: z-score={z:.2f}, growth={growth}, latest={latest}")
        else:
            print(f"\n📊 {country}: Cần >=3 snapshot để phát hiện emerging genres")

    # Hiển thị thông tin về JSON responses đã lưu
    list_saved_json_responses()
    
    return True

def run_data_processing():
    """Chạy xử lý dữ liệu thành CSV (từ extract_songs_table.py)"""
    print("\n🇻🇳 TRÍCH XUẤT DỮ LIỆU BÀI HÁT VIỆT NAM - SPOTIFY DATABASE")
    print("=" * 60)
    
    # Kiểm tra JSON directory
    if not os.path.exists(JSON_DIR):
        print(f"❌ Thư mục {JSON_DIR} không tồn tại!")
        return False
    
    # Trích xuất dữ liệu
    songs_data = extract_songs_data()
    
    if not songs_data:
        print("❌ Không trích xuất được dữ liệu nào!")
        return False
    
    # Lưu vào CSV
    csv_path = save_to_csv(songs_data)
    
    # Lưu vào Excel
    excel_path = save_to_excel(songs_data)
    
    # Tạo báo cáo tổng kết
    generate_summary_report(songs_data)
    
    print(f"\n✅ HOÀN THÀNH! 🇻🇳")
    print(f"📁 Files dữ liệu Việt Nam được tạo:")
    print(f"   📄 {csv_path}")
    print(f"   📊 {excel_path}")
    print(f"\n💡 Dữ liệu này chứa:")
    print(f"   🎵 Bài hát hot TikTok Việt Nam")
    print(f"   👥 Thông tin nghệ sĩ Việt")
    print(f"   🎭 Thể loại: V-Pop, Vinahouse, Vietnamese Lo-Fi, v.v.")
    print(f"   📊 Mở file Excel để phân tích chi tiết!")
    
    return True

# ========= MINIO UPLOAD FUNCTIONS =========
def find_minio_endpoint():
    """Tìm MinIO endpoint từ container"""
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
    """Upload file CSV từ host lên MinIO"""
    print("☁️ UPLOAD VIETNAM SONGS DATABASE TO MINIO (HOST)")
    print("=" * 50)
    
    # File cần upload
    csv_file = "data_tables/vietnam_songs_database.csv"
    
    # Kiểm tra file tồn tại
    if not os.path.exists(csv_file):
        print(f"❌ File không tồn tại: {csv_file}")
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
        
    except Exception as e:
        print(f"❌ Lỗi upload: {e}")
        return False

def upload_csv_to_minio_container():
    """Upload file CSV từ container lên MinIO"""
    print("☁️ UPLOAD VIETNAM SONGS DATABASE TO MINIO (CONTAINER)")
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
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE
        )
        
        # Test connection
        if not client.bucket_exists(MINIO_BUCKET):
            print(f"🪣 Tạo bucket '{MINIO_BUCKET}'...")
            client.make_bucket(MINIO_BUCKET)
        else:
            print(f"✅ Bucket '{MINIO_BUCKET}' đã tồn tại")
            
    except Exception as e:
        print(f"❌ Lỗi kết nối MinIO: {e}")
        return False
    
    # Upload file
    object_name = "vietnam_songs_database.csv"
    
    try:
        # Upload file
        client.fput_object(MINIO_BUCKET, object_name, csv_file)
        
        file_size = os.path.getsize(csv_file)
        print(f"✅ Upload thành công: {object_name}")
        print(f"📊 Kích thước: {file_size/1024:.1f} KB")
        print(f"🌐 MinIO endpoint: {minio_endpoint}")
        
        return True
        
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
        result = subprocess.run(['ip', 'route'], capture_output=True, text=True)
        if 'docker' in result.stdout.lower():
            return "container"
    except:
        pass
    
    return "host"

def run_minio_upload():
    """Chạy upload lên MinIO"""
    print("\n☁️ BƯỚC 3: UPLOAD LÊN MINIO")
    print("-" * 40)
    
    # Import minio nếu chưa có
    global Minio, S3Error
    if Minio is None:
        try:
            from minio import Minio
            from minio.error import S3Error
        except ImportError:
            print("❌ MinIO library chưa được cài đặt")
            print("💡 Hãy chạy: pip install minio")
            return False
    
    # Phát hiện môi trường
    env = detect_environment()
    print(f"🔍 Phát hiện môi trường: {env}")
    
    if env == "container":
        print("🐳 Chạy từ container - sử dụng container upload logic")
        success = upload_csv_to_minio_container()
        
        if success:
            print(f"🎉 Upload hoàn tất từ container!")
            print("💡 File CSV đã có sẵn trên MinIO")
            print("🌐 Truy cập: http://localhost:9001/browser/music/")
        else:
            print(f"❌ Upload thất bại từ container")
            print("💡 File CSV vẫn có sẵn tại: data_tables/vietnam_songs_database.csv")
            print("\n💾 COPY FILE VỀ HOST:")
            print("   docker cp master:/home/hadoopminhquang/data_tables/vietnam_songs_database.csv ./")
    
    else:
        print("🖥️ Chạy từ host - sử dụng simple upload logic")
        success = upload_csv_to_minio_simple()
        
        if success:
            print(f"🎉 Upload hoàn tất từ host!")
            print("💡 File CSV đã có sẵn trên MinIO với tên: vietnam_songs_database.csv")
    
    return success

def run_pipeline():
    """Chạy pipeline chính (từ main.py)"""
    print("\n🚀 CHẠY PIPELINE")
    print("-" * 50)
    
    # Tạo thư mục cần thiết
    print("📁 Tạo thư mục làm việc...")
    for directory in ["json_responses", "data_tables", "snapshots"]:
        run_command(f"mkdir -p {directory}", f"Tạo thư mục {directory}")
    
    # Bước 1: Thu thập dữ liệu từ Spotify
    print("\n🎵 BƯỚC 1: THU THẬP DỮ LIỆU SPOTIFY")
    print("-" * 40)
    success1 = run_data_collection()
    
    if not success1:
        print("❌ Không thể thu thập dữ liệu từ Spotify")
        return False
    
    time.sleep(2)
    
    # Bước 2: Xử lý dữ liệu
    print("\n📊 BƯỚC 2: XỬ LÝ DỮ LIỆU")
    print("-" * 40)
    success2 = run_data_processing()
    
    if not success2:
        print("❌ Không thể xử lý dữ liệu")
        return False
    
    # Kiểm tra file đã tạo
    print("\n📋 KIỂM TRA KẾT QUẢ")
    print("-" * 30)
    run_command("ls -la data_tables/", "Liệt kê files trong data_tables")
    
    # Đếm số dòng trong CSV
    if run_command("test -f data_tables/vietnam_songs_database.csv", "Kiểm tra file CSV tồn tại"):
        run_command("wc -l data_tables/vietnam_songs_database.csv", "Đếm số dòng trong CSV")
        run_command("head -5 data_tables/vietnam_songs_database.csv", "Hiển thị 5 dòng đầu CSV")
    
    # Bước 3: Upload lên MinIO
    time.sleep(1)
    success3 = run_minio_upload()
    
    if not success3:
        print("⚠️ Upload lên MinIO thất bại, nhưng dữ liệu đã được tạo")
        print("💡 Bạn có thể upload thủ công sau")
    
    return True

def main():
    """Main function"""
    print("🐧 SPOTIFY VIETNAM DATA PIPELINE")
    print("=" * 60)
    print(f"⏰ Bắt đầu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📍 Thư mục: {os.getcwd()}")
    print("=" * 60)
    
    # Kiểm tra quyền root
    if os.geteuid() != 0:
        print("⚠️ Cảnh báo: Không chạy với quyền root")
        print("💡 Một số cài đặt có thể thất bại")
    
    # Kiểm tra Python version
    print(f"🐍 Python version: {sys.version}")
    
    # Setup environment
    if not setup_environment():
        print("❌ Không thể thiết lập môi trường")
        return False
    
    # Run pipeline
    if not run_pipeline():
        print("\n❌ PIPELINE THẤT BẠI")
        return False
    
    # Kết quả cuối cùng
    print("\n" + "=" * 60)
    print("🎉 PIPELINE HOÀN THÀNH THÀNH CÔNG!")
    print("=" * 60)
    print(f"⏰ Hoàn thành: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("📊 KẾT QUẢ:")
    print("   ✅ Dữ liệu Spotify đã thu thập từ API")
    print("   ✅ File CSV/Excel đã được tạo: data_tables/vietnam_songs_database.*")
    print("   ✅ Dữ liệu đã được upload lên MinIO (nếu có)")
    print("   🌐 Truy cập: http://localhost:9001/browser/music/")
    print()
    print("💡 Toàn bộ pipeline đã hoàn thành - từ thu thập đến upload!")
    print("🔄 CHẠY LẠI: python3 complete_data_pipeline.py")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️ Pipeline bị người dùng dừng (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Lỗi không mong muốn: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)