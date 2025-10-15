# 📊 Spotify Music Data Analytics với JSON Response Storage

Dự án phân tích dữ liệu âm nhạc từ Spotify API với khả năng lưu trữ và phân tích các JSON response.

## 🚀 Tính năng chính

### 1. **Phân tích xu hướng âm nhạc**

- Theo dõi top artists, genres, tracks theo quốc gia
- Phát hiện xu hướng genres mới nổi (emerging trends)
- Lưu snapshot theo thời gian để phân tích lịch sử

### 2. **Lưu trữ JSON Responses** ⭐ MỚI

- **Tự động lưu** tất cả JSON responses từ Spotify API
- **Timestamp và metadata** cho mỗi request
- **Organized storage** theo endpoint và thời gian
- **Backup và audit trail** đầy đủ

### 3. **Phân tích JSON Data**

- Tool phân tích các JSON response đã lưu
- Thống kê endpoint usage
- Chi tiết dữ liệu playlist và artists
- Tìm kiếm trong response data

## 📁 Cấu trúc thư mục

```
CuoiKi/
├── CaoDuLieu.py         # Script chính phân tích dữ liệu
├── analyze_json.py      # Tool phân tích JSON responses
├── test_search.py       # Test script tìm playlist
├── snapshots/           # Dữ liệu snapshot theo ngày
└── json_responses/      # 🆕 Raw JSON responses từ API
    ├── 20251012_134306_playlist_tracks_5KJDMJe9EJ7QRz8FG2MIpI_page1_US.json
    ├── 20251012_134307_artists_batch_1.json
    └── ...
```

## 🔧 Cài đặt và sử dụng

### Yêu cầu

```bash
pip install requests python-dateutil
```

### Cấu hình

1. Đăng ký ứng dụng tại [Spotify Developer Dashboard](https://developer.spotify.com/)
2. Cập nhật `CLIENT_ID` và `CLIENT_SECRET` trong `CaoDuLieu.py`

### Chạy phân tích

```bash
# Phân tích dữ liệu và lưu JSON responses
python CaoDuLieu.py
```

### Phân tích JSON responses

```bash
# Tổng quan
python analyze_json.py summary

# Chi tiết playlist cụ thể
python analyze_json.py playlist 4QtoFLP8qPILIVQuPEMhun

# Tìm kiếm trong responses
python analyze_json.py search "billie eilish"
```

## 📊 JSON Response Storage

### Tự động lưu các endpoint:

- **🎵 Playlist tracks**: `/playlists/{id}/tracks`
- **👤 Artist info**: `/artists`
- **🔍 Search**: `/search`
- **📂 Browse**: `/browse/*`

### Format file JSON:

```json
{
  "timestamp": "20251012_134306",
  "endpoint": "playlist_tracks_5KJDMJe9EJ7QRz8FG2MIpI_page1_US",
  "extra_info": {
    "url": "https://api.spotify.com/v1/playlists/5KJDMJe9EJ7QRz8FG2MIpI/tracks",
    "params": {"limit": 100, "market": "US"},
    "status_code": 200
  },
  "response": {
    "items": [...],
    "next": "...",
    "total": 146
  }
}
```

### Lợi ích:

- **🔄 Reproducible research**: Có thể tái tạo phân tích
- **🐛 Debugging**: Xem chính xác API trả về gì
- **📈 Historical analysis**: So sánh responses theo thời gian
- **⚡ Offline analysis**: Phân tích mà không cần gọi API lại
- **📋 Compliance**: Audit trail đầy đủ cho nghiên cứu

## 🎯 Kết quả mẫu

### Phân tích quốc gia:

```
=== VN (market=VN) | tracks=155 ===
Top genres:
  vinahouse: 153
  v-pop: 112
  vietnamese lo-fi: 50

💾 Saved JSON responses: 18 files (2.02 MB)
```

### JSON Analytics:

```
📊 PHÂN TÍCH 18 JSON RESPONSE FILES
📦 Tổng dung lượng: 2.02 MB
📈 Các endpoint được gọi:
  artists_batch_1: 4 lần
  playlist_tracks_*: 6 lần
```

## 📝 Use Cases

1. **Nghiên cứu học thuật**: Backup dữ liệu đầy đủ
2. **Industry analysis**: Theo dõi xu hướng âm nhạc
3. **API debugging**: Xem response thực tế
4. **Data mining**: Phân tích offline mà không giới hạn rate limit
5. **Compliance**: Đảm bảo minh bạch trong nghiên cứu

## 🚨 Lưu ý quan trọng

- ⚖️ **Tuân thủ Spotify Terms of Service**
- 🔒 **Không share CLIENT_SECRET** công khai
- 💾 **JSON files có thể rất lớn** - quản lý storage
- 🕐 **Rate limiting**: Spotify giới hạn request/giây

## 🆕 Tính năng mới trong phiên bản này

- ✅ Tự động lưu JSON responses với timestamp
- ✅ Tool phân tích JSON responses
- ✅ Error handling cải thiện
- ✅ Metadata và extra info đầy đủ
- ✅ Organized file naming convention
