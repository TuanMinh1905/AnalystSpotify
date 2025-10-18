#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GLOBAL OFFICIAL MUSIC COLLECTOR (No Remix)
- Quét toàn bộ markets do Spotify hỗ trợ -> New Releases -> Albums -> Tracks
- Lọc bỏ remix / sped-up / re-edit / nightcore / bootleg / mashup / karaoke...
- Gắn popularity (v1/tracks), genres + followers (v1/artists)
- Xuất CSV + Excel

Endpoints (Spotify Web API):
- Markets:          https://api.spotify.com/v1/markets        (docs: https://developer.spotify.com/documentation/web-api/reference/get-available-markets)
- New Releases:     https://api.spotify.com/v1/browse/new-releases (docs: https://developer.spotify.com/documentation/web-api/reference/get-new-releases)
- Several Albums:   https://api.spotify.com/v1/albums?ids=... (max 20 ids) (docs: https://developer.spotify.com/documentation/web-api/reference/get-multiple-albums)
- Several Tracks:   https://api.spotify.com/v1/tracks?ids=... (max 50 ids) (docs: https://developer.spotify.com/documentation/web-api/reference/get-several-tracks)
- Artists (batch):  https://api.spotify.com/v1/artists?ids=... (max 50 ids)
Rate limits: https://developer.spotify.com/documentation/web-api/concepts/rate-limits
"""

import os
import sys
import csv
import re
import time
import math
import json
import argparse
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Tuple

import requests
import pandas as pd

try:
    from minio import Minio
    from minio.error import S3Error
except ImportError:
    Minio = None
    S3Error = None

# ========= CONFIG =========
SPOTIFY_CLIENT_ID = os.getenv("820ea85e09f642e396d3224165d7e72e", "820ea85e09f642e396d3224165d7e72e").strip()
SPOTIFY_CLIENT_SECRET = os.getenv("e5e4c0c69e3b4abfb190117b0f6110b0", "e5e4c0c69e3b4abfb190117b0f6110b0").strip()

# Tăng/giảm để kiểm soát lượng dữ liệu (mặc định lớn để lấy nhiều bản ghi)
DEFAULT_MAX_ALBUMS_PER_MARKET = 500   # có thể tăng 1000 nếu quota đủ
REQUESTS_TIMEOUT = 30
SAVE_JSON = True                      # lưu response JSON để debug/trace
SLEEP_BETWEEN_CALLS = 0.05            # sleep ngắn để thân thiện rate limit

# Thư mục output
BASE_DIR = os.path.abspath(os.getcwd())
JSON_RESPONSES_DIR = os.path.join(BASE_DIR, "json_responses")
SNAPSHOT_DIR = os.path.join(BASE_DIR, "snapshots")
OUTPUT_DIR = os.path.join(BASE_DIR, "data_tables")
os.makedirs(JSON_RESPONSES_DIR, exist_ok=True)
os.makedirs(SNAPSHOT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Bộ lọc bỏ remix/sped-up/... (có thể mở rộng thêm từ khóa nếu muốn)
REMIX_REGEX = re.compile(
    r"(remix|mix|re[-\s]?work|re[-\s]?edit|edit|vip|extended\s+mix|club\s+mix|radio\s+edit|"
    r"sped\s*up|speed\s*up|slowed|reverb|nightcore|bootleg|mash[-\s]?up|karaoke|tiktok\s*version)",
    re.IGNORECASE,
)

# MinIO Configuration
MINIO_ENDPOINT = "localhost:9000"  
MINIO_ACCESS_KEY = "longminh"      
MINIO_SECRET_KEY = "longminh"      
MINIO_BUCKET = "bronze"            # Đổi từ 'music' sang 'bronze'
MINIO_SECURE = False

# ========= UTILITIES =========
def log(msg: str) -> None:
    ts = datetime.utcnow().strftime("%H:%M:%S")
    print(f"[{ts} UTC] {msg}", flush=True)

def save_json_response(endpoint_name: str, response_data, extra_info=None):
    if not SAVE_JSON:
        return
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{endpoint_name}.json"
    filepath = os.path.join(JSON_RESPONSES_DIR, filename)
    data_to_save = {
        "timestamp": timestamp,
        "endpoint": endpoint_name,
        "extra_info": extra_info,
        "response": response_data,
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=2)

def get_app_token(client_id: str, client_secret: str) -> Tuple[str, int]:
    if not client_id or not client_secret:
        raise RuntimeError(
            "Thiếu SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET. "
            "Hãy export ENV hoặc chỉnh trực tiếp trong code."
        )
    url = "https://accounts.spotify.com/api/token"
    auth_header = requests.auth.HTTPBasicAuth(client_id, client_secret)
    data = {"grant_type": "client_credentials"}
    r = requests.post(url, data=data, auth=auth_header, timeout=REQUESTS_TIMEOUT)
    r.raise_for_status()
    j = r.json()
    return j["access_token"], j.get("expires_in", 3600)

class SpotifyClient:
    """HTTP client với retry 429/5xx, lưu JSON, và session keep-alive."""
    def __init__(self, token: str):
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.max_retries = 6

    def get(self, url: str, params: dict | None = None, endpoint_name: str | None = None):
        params = params or {}
        backoff = 1.0
        for attempt in range(self.max_retries):
            r = self.session.get(url, params=params, timeout=REQUESTS_TIMEOUT)
            # Rate-limit
            if r.status_code == 429:
                retry_after = float(r.headers.get("Retry-After", "1"))
                time.sleep(retry_after + 0.5)
                continue
            # 5xx -> exponential backoff
            if 500 <= r.status_code < 600:
                if attempt < self.max_retries - 1:
                    time.sleep(backoff)
                    backoff *= 1.6
                    continue
            try:
                r.raise_for_status()
            except requests.HTTPError as e:
                # không retry thêm
                raise RuntimeError(
                    f"HTTP {r.status_code} for {url} | params={params} | resp={r.text[:200]}"
                ) from e
            j = r.json()
            if endpoint_name:
                save_json_response(endpoint_name, j, {"url": url, "params": params, "status": r.status_code})
            if SLEEP_BETWEEN_CALLS:
                time.sleep(SLEEP_BETWEEN_CALLS)
            return j
        raise RuntimeError(f"GET failed after retries: {url}")

# ========= CORE FETCHERS =========
def get_available_markets(sp: SpotifyClient) -> List[str]:
    j = sp.get("https://api.spotify.com/v1/markets", endpoint_name="markets")
    markets = j.get("markets", []) or []
    return list(sorted(set(markets)))

def fetch_market_new_releases(sp: SpotifyClient, market: str, max_albums: int) -> List[str]:
    """Lấy các album id từ new-releases của 1 market (phân trang sâu)."""
    album_ids: List[str] = []
    limit = 50  # tối đa theo docs
    offset = 0
    page = 1
    url = "https://api.spotify.com/v1/browse/new-releases"
    while len(album_ids) < max_albums:
        params = {"country": market, "limit": limit, "offset": offset}
        j = sp.get(url, params=params, endpoint_name=f"new_releases_{market}_p{page}")
        albums = (j.get("albums") or {}).get("items", []) or []
        if not albums:
            break
        for a in albums:
            aid = a.get("id")
            if aid:
                album_ids.append(aid)
        if len(albums) < limit:
            break
        offset += limit
        page += 1
    return album_ids[:max_albums]

def batched(seq, n):
    batch = []
    for x in seq:
        batch.append(x)
        if len(batch) == n:
            yield batch
            batch = []
    if batch:
        yield batch

def fetch_albums_details(sp: SpotifyClient, album_ids: List[str], market: str | None = None) -> List[dict]:
    """/v1/albums, batch 20 ids/lần. Trả về album objects có kèm tracks.items (simplified)."""
    out = []
    for i, batch_ids in enumerate(batched([x for x in album_ids if x], 20), start=1):
        params = {"ids": ",".join(batch_ids)}
        if market:
            params["market"] = market
        j = sp.get("https://api.spotify.com/v1/albums", params=params, endpoint_name=f"albums_batch_{market}_{i}")
        out.extend(j.get("albums", []) or [])
    return out

def fetch_tracks_popularity(sp: SpotifyClient, track_ids: List[str]) -> Dict[str, int]:
    """/v1/tracks, batch 50 ids/lần để lấy popularity."""
    pop_map: Dict[str, int] = {}
    idx = 1
    for batch_ids in batched([x for x in track_ids if x], 50):
        params = {"ids": ",".join(batch_ids)}
        j = sp.get("https://api.spotify.com/v1/tracks", params=params, endpoint_name=f"tracks_popularity_b{idx}")
        idx += 1
        for t in j.get("tracks", []) or []:
            tid = t.get("id")
            if tid:
                pop_map[tid] = t.get("popularity", 0)
    return pop_map

def fetch_artists_data(sp: SpotifyClient, artist_ids: List[str]) -> Dict[str, dict]:
    """/v1/artists, batch 50 ids/lần: genres, popularity, followers."""
    out: Dict[str, dict] = {}
    for i, batch_ids in enumerate(batched([x for x in artist_ids if x], 50), start=1):
        params = {"ids": ",".join(batch_ids)}
        j = sp.get("https://api.spotify.com/v1/artists", params=params, endpoint_name=f"artists_b{i}")
        for a in j.get("artists", []) or []:
            aid = a.get("id")
            if not aid:
                continue
            out[aid] = {
                "genres": a.get("genres", []) or [],
                "popularity": a.get("popularity", 0) or 0,
                "followers": ((a.get("followers") or {}).get("total") or 0),
                "name": a.get("name", ""),
            }
    return out

def is_official_release(track_name: str, album_name: str) -> bool:
    text = f"{track_name} {album_name}"
    return REMIX_REGEX.search(text) is None

# ========= ROW BUILDER & EXPORT =========
def popularity_tier(pop: int) -> str:
    if pop >= 80: return "Viral"
    if pop >= 60: return "Popular"
    if pop >= 40: return "Moderate"
    if pop >= 20: return "Niche"
    return "Underground"

def duration_category(mins: float) -> str:
    if mins < 2: return "Short"
    if mins < 3.5: return "Standard"
    if mins < 5: return "Long"
    return "Extended"

def build_rows(events: List[Tuple[dict, dict, str, str]],
               popularity_map: Dict[str, int],
               artists_map: Dict[str, dict]) -> List[dict]:
    """
    events: list of (track_obj, album_obj, market, extracted_ts)
    track_obj: simplified track from album.tracks.items (có duration_ms, explicit, preview_url,...)
    album_obj: full album (name, release_date, album_type, images, id, artists[])
    """
    rows: List[dict] = []
    for tr, album, market, ts in events:
        try:
            tid = tr.get("id", "")
            tname = tr.get("name", "")
            if not tid or not tname:
                continue

            # album info
            album_name = album.get("name", "")
            release_date = album.get("release_date", "") or ""
            album_type = album.get("album_type", "") or ""
            images = album.get("images", []) or []
            album_image_url = images[0]["url"] if images else ""

            # artists
            tr_artists = tr.get("artists", []) or []
            all_artist_names = [a.get("name", "") for a in tr_artists if a]
            all_artist_ids = [a.get("id", "") for a in tr_artists if a and a.get("id")]
            primary_artist_name = all_artist_names[0] if all_artist_names else ""
            primary_artist_id = all_artist_ids[0] if all_artist_ids else ""
            artist_detail = artists_map.get(primary_artist_id, {}) if primary_artist_id else {}
            artist_pop = artist_detail.get("popularity", 0)
            artist_followers = artist_detail.get("followers", 0)
            primary_genres = artist_detail.get("genres", [])

            # all genres from all artists
            all_genres = set()
            for aid in all_artist_ids:
                g = artists_map.get(aid, {}).get("genres", [])
                all_genres.update(g)

            # track features
            duration_ms = tr.get("duration_ms") or 0
            duration_min = round(duration_ms / 60000.0, 2) if duration_ms else 0.0
            explicit = bool(tr.get("explicit", False))
            spotify_url = (tr.get("external_urls") or {}).get("spotify", "") or ""
            pop = popularity_map.get(tid, 0)

            rows.append({
                "track_id": tid,
                "track_name": tname,
                "duration_minutes": duration_min,
                "popularity": pop,
                "explicit": explicit,
                "spotify_url": spotify_url,

                "primary_artist": primary_artist_name,
                "primary_artist_id": primary_artist_id,
                "all_artists": " | ".join(all_artist_names),
                "artist_count": len(all_artist_names),
                "artist_popularity": artist_pop,
                "artist_followers": artist_followers,

                "primary_genres": " | ".join(primary_genres),
                "all_genres": " | ".join(sorted(all_genres)),
                "genre_count": len(all_genres),
                "main_genre": list(all_genres)[0] if all_genres else "",

                "album_name": album_name,
                "album_type": album_type,
                "release_date": release_date,
                "release_year": release_date[:4] if len(release_date) >= 4 else "",
                "album_image_url": album_image_url,

                "market": market,
                "source_id": album.get("id", ""),       # id của album (nguồn new-releases)
                "content_source": "new_releases",
                "extracted_at": ts,

                "is_collaboration": len(all_artist_names) > 1,
                "is_recent": bool(release_date) and release_date >= "2020",
                "popularity_tier": popularity_tier(pop),
                "duration_category": duration_category(duration_min),
            })
        except Exception as e:
            log(f"⚠️ Lỗi build row: {e}")
            continue
    return rows

def save_to_csv(rows: List[dict], filename: str) -> str:
    if not rows:
        raise RuntimeError("Không có dữ liệu để lưu CSV.")
    path = os.path.join(OUTPUT_DIR, filename)
    cols = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    return path

def save_to_excel(rows: List[dict], filename: str) -> str:
    if not rows:
        raise RuntimeError("Không có dữ liệu để lưu Excel.")
    path = os.path.join(OUTPUT_DIR, filename)
    df = pd.DataFrame(rows)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="All_Songs", index=False)

        # Stats by country
        market_stats = (
            df.groupby("market")
              .agg(track_count=("track_id", "count"),
                   popularity_mean=("popularity", "mean"),
                   artist_followers_mean=("artist_followers", "mean"),
                   duration_minutes_mean=("duration_minutes", "mean"))
              .round(2)
              .sort_values("track_count", ascending=False)
        )
        market_stats.to_excel(writer, sheet_name="Stats_By_Market")

        # Top artists (global)
        artist_stats = (
            df.groupby("primary_artist")
              .agg(track_count=("track_id", "count"),
                   popularity_mean=("popularity", "mean"),
                   artist_followers=("artist_followers", "max"))
              .sort_values("track_count", ascending=False)
              .head(200)
        )
        artist_stats.to_excel(writer, sheet_name="Top_Global_Artists")

        # Genres
        genre_records = []
        for _, row in df.iterrows():
            if pd.notna(row["all_genres"]) and row["all_genres"]:
                for g in str(row["all_genres"]).split(" | "):
                    if g:
                        genre_records.append({"genre": g, "market": row["market"]})
        if genre_records:
            gdf = pd.DataFrame(genre_records)
            top_genres = gdf.groupby("genre").size().sort_values(ascending=False).head(200)
            top_genres.to_excel(writer, sheet_name="Top_Global_Genres")
            gm = gdf.groupby(["market", "genre"]).size().reset_index(name="track_count")
            gm.sort_values(["market", "track_count"], ascending=[True, False], inplace=True)
            gm.to_excel(writer, sheet_name="Genres_By_Market", index=False)
    return path

def upload_to_minio(csv_path: str) -> bool:
    """Upload CSV file to MinIO bronze bucket"""
    if Minio is None:
        log("⚠️ MinIO library not installed, skipping upload")
        return False
    
    try:
        # Detect environment and choose appropriate endpoint
        endpoint = MINIO_ENDPOINT
        if os.path.exists('/.dockerenv'):
            # Running in container, try host.docker.internal
            endpoint = "host.docker.internal:9000"
        
        log(f"☁️ Connecting to MinIO at {endpoint}...")
        client = Minio(
            endpoint,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE
        )
        
        # Ensure bucket exists
        if not client.bucket_exists(MINIO_BUCKET):
            log(f"🪣 Creating bucket '{MINIO_BUCKET}'...")
            client.make_bucket(MINIO_BUCKET)
        else:
            log(f"✅ Bucket '{MINIO_BUCKET}' exists")
        
        # Upload file
        object_name = os.path.basename(csv_path)
        log(f"📤 Uploading {object_name} to bucket '{MINIO_BUCKET}'...")
        client.fput_object(MINIO_BUCKET, object_name, csv_path)
        
        file_size = os.path.getsize(csv_path) / 1024
        log(f"✅ Upload successful: {object_name} ({file_size:.1f} KB)")
        log(f"🌐 Access at: http://localhost:9001/browser/{MINIO_BUCKET}/{object_name}")
        return True
        
    except Exception as e:
        log(f"❌ MinIO upload failed: {e}")
        return False

# ========= PIPELINE =========
def collect_global_official_rows(sp: SpotifyClient, markets: List[str], max_albums_per_market: int) -> List[dict]:
    all_events: List[Tuple[dict, dict, str, str]] = []
    all_track_ids: set[str] = set()
    all_artist_ids: set[str] = set()
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    for m in markets:
        try:
            album_ids = fetch_market_new_releases(sp, m, max_albums=max_albums_per_market)
            if not album_ids:
                log(f"• {m}: 0 albums")
                continue
            albums = fetch_albums_details(sp, album_ids, market=m)
            kept = 0
            for album in albums:
                album_name = album.get("name", "")
                tracks = ((album.get("tracks") or {}).get("items")) or []
                for tr in tracks:
                    if not tr or not tr.get("id"):
                        continue
                    tname = tr.get("name", "")
                    if not is_official_release(tname, album_name):
                        continue
                    all_events.append((tr, album, m, ts))
                    kept += 1
                    all_track_ids.add(tr["id"])
                    for a in tr.get("artists", []) or []:
                        aid = a.get("id")
                        if aid:
                            all_artist_ids.add(aid)
            log(f"• {m}: albums={len(albums)} | tracks_kept={kept}")
        except Exception as e:
            log(f"⚠️ {m}: lỗi lấy dữ liệu: {e}")

    if not all_events:
        return []

    # Popularity + Artists data
    log(f"🔎 Fetching popularity for {len(all_track_ids)} unique tracks...")
    pop_map = fetch_tracks_popularity(sp, list(all_track_ids))

    log(f"🔎 Fetching artist genres/followers for {len(all_artist_ids)} unique artists...")
    art_map = fetch_artists_data(sp, list(all_artist_ids))

    log("🧩 Building rows...")
    rows = build_rows(all_events, pop_map, art_map)
    return rows

def main():
    parser = argparse.ArgumentParser(description="Global Official New Releases (No Remix)")
    parser.add_argument("--max-per-market", type=int, default=DEFAULT_MAX_ALBUMS_PER_MARKET,
                        help="Số album tối đa lấy cho mỗi market (default: %(default)s)")
    parser.add_argument("--markets", type=str, default="",
                        help="Danh sách markets (ví dụ: US,GB,VN). Để trống sẽ quét tất cả.")
    parser.add_argument("--no-excel", action="store_true", help="Không xuất Excel, chỉ CSV")
    args = parser.parse_args()

    log("🚀 START Global Official New Releases (No Remix)")
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        raise SystemExit("❌ Thiếu ENV SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET")

    token, _ = get_app_token(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)
    sp = SpotifyClient(token)

    # Markets
    if args.markets.strip():
        markets = [m.strip().upper() for m in args.markets.split(",") if m.strip()]
    else:
        markets = get_available_markets(sp)
    log(f"🌍 Markets: {len(markets)} -> {', '.join(markets[:10])}{' ...' if len(markets)>10 else ''}")

    # Collect
    rows = collect_global_official_rows(sp, markets, args.max_per_market)
    if not rows:
        raise SystemExit("❌ Không thu được bản ghi nào (kiểm tra quota, token, hoặc thử giảm --max-per-market).")

    # Snapshot ngắn
    date_str = datetime.utcnow().strftime("%Y%m%d")
    snap = {"mode": "new_releases_global_no_remix", "date": date_str, "rows": len(rows), "markets": len(markets)}
    with open(os.path.join(SNAPSHOT_DIR, f"{date_str}_GLOBAL.json"), "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=2)

    # Export
    csv_path = save_to_csv(rows, "global_official_new_releases.csv")
    log(f"💾 CSV: {csv_path}")
    if not args.no_excel:
        xlsx_path = save_to_excel(rows, "global_official_new_releases.xlsx")
        log(f"📊 Excel: {xlsx_path}")

    # Upload to MinIO
    log("☁️ Uploading to MinIO bronze bucket...")
    upload_to_minio(csv_path)

    # Report
    df = pd.DataFrame(rows)
    log(f"✅ Tổng số bản ghi: {len(df)} | Markets: {df['market'].nunique()} | Nghệ sĩ unique: {df['primary_artist'].nunique()}")
    log("🎉 DONE")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ Stopped by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)