# 🎨 Hướng dẫn Setup Apache Superset cho Spotify Data Analytics

## 📋 Tổng quan

Superset sẽ kết nối với SQLite database chứa dữ liệu từ MinIO Gold layer để tạo các biểu đồ phân tích.

## 🚀 Bước 1: Export Data từ MinIO sang SQLite

### 1.1. Copy file export script vào container

```bash
docker cp export_gold_to_sqlite.py master:/home/hadoopminhquang/
```

### 1.2. Chạy export script

```bash
docker exec -it master bash -c "cd /home/hadoopminhquang && python3 export_gold_to_sqlite.py"
```

**Kết quả:** File `spotify_gold.db` sẽ được tạo tại `/home/hadoopminhquang/spotify_gold.db`

---

## 🔧 Bước 2: Cài đặt Apache Superset

### 2.1. Copy setup script vào container

```bash
docker cp setup_superset.sh master:/home/hadoopminhquang/
```

### 2.2. Chạy cài đặt (mất ~5-10 phút)

```bash
docker exec -it master bash -c "cd /home/hadoopminhquang && chmod +x setup_superset.sh && bash setup_superset.sh"
```

**Thông tin đăng nhập:**

- Username: `admin`
- Password: `admin`

---

## 🌐 Bước 3: Khởi động Superset

### 3.1. Khởi động Superset server

```bash
docker exec -it master bash -c "cd /home/hadoopminhquang && chmod +x start_superset.sh && bash start_superset.sh"
```

### 3.2. Truy cập Web UI

Mở trình duyệt: **http://localhost:8088**

Login với:

- Username: `admin`
- Password: `admin`

---

## 🔗 Bước 4: Kết nối Database trong Superset

### 4.1. Thêm Database Connection

1. Vào **Settings** → **Database Connections**
2. Click **+ Database**
3. Chọn **SQLite**
4. Nhập thông tin:
   - **Display Name:** `Spotify Gold`
   - **SQLAlchemy URI:** `sqlite:////home/hadoopminhquang/spotify_gold.db`
5. Click **Test Connection**
6. Click **Connect**

---

## 📊 Bước 5: Tạo Datasets

### 5.1. Add Datasets

1. Vào **Data** → **Datasets**
2. Click **+ Dataset**
3. Chọn:
   - **Database:** `Spotify Gold`
   - **Schema:** (để trống cho SQLite)
   - **Table:** Chọn từng bảng sau:

**Các bảng quan trọng:**

- ✅ `dim_artist` - Thông tin nghệ sĩ
- ✅ `dim_date` - Thông tin thời gian
- ✅ `dim_market` - Thông tin thị trường
- ✅ `dim_genre` - Thông tin thể loại
- ✅ `fact_track_performance` - Dữ liệu hiệu suất tracks
- ✅ `agg_artist_performance` - Tổng hợp theo nghệ sĩ
- ✅ `agg_market_stats` - Tổng hợp theo thị trường
- ✅ `agg_genre_popularity` - Tổng hợp theo thể loại

4. Click **Add** cho mỗi bảng

---

## 📈 Bước 6: Tạo Charts (Biểu đồ mẫu)

### 📊 Chart 1: Top 10 Artists by Average Popularity

1. **Data** → **Datasets** → Click vào `agg_artist_performance`
2. Click **Create Chart**
3. Chọn **Chart Type:** `Bar Chart`
4. Cấu hình:
   - **Metrics:** `AVG(avg_popularity)`
   - **Dimensions:** `artist_name`
   - **Sort by:** `AVG(avg_popularity)` DESC
   - **Row Limit:** 10
5. Click **Run**
6. Click **Save** → Đặt tên: "Top 10 Artists by Popularity"

---

### 🌍 Chart 2: Track Distribution by Market

1. Chọn dataset `agg_market_stats`
2. **Chart Type:** `Pie Chart`
3. Cấu hình:
   - **Dimension:** `market_code`
   - **Metric:** `SUM(total_tracks)`
   - **Row Limit:** 15
4. Click **Run** → **Save**

---

### 🎵 Chart 3: Genre Popularity Distribution

1. Chọn dataset `agg_genre_popularity`
2. **Chart Type:** `Treemap`
3. Cấu hình:
   - **Dimensions:** `primary_genre`
   - **Metrics:** `AVG(avg_popularity)`
   - **Row Limit:** 20
4. Click **Run** → **Save**

---

### 📅 Chart 4: Releases Over Time

1. Chọn dataset `fact_track_performance`
2. Tạo **Virtual Dataset** với SQL:

```sql
SELECT
    d.year,
    d.month,
    COUNT(DISTINCT f.track_id) as total_releases,
    AVG(f.popularity) as avg_popularity
FROM fact_track_performance f
JOIN dim_date d ON f.date_id = d.date_id
GROUP BY d.year, d.month
ORDER BY d.year, d.month
```

3. **Chart Type:** `Line Chart`
4. Cấu hình:
   - **X-Axis:** `year, month`
   - **Metrics:** `total_releases`, `avg_popularity`
5. Click **Run** → **Save**

---

### 🔥 Chart 5: Artist Followers vs Popularity Scatter

1. Chọn dataset `agg_artist_performance`
2. **Chart Type:** `Scatter Plot`
3. Cấu hình:
   - **X-Axis:** `artist_followers`
   - **Y-Axis:** `avg_popularity`
   - **Size:** `total_tracks`
   - **Labels:** `artist_name`
4. Click **Run** → **Save**

---

## 🎨 Bước 7: Tạo Dashboard

### 7.1. Create Dashboard

1. Vào **Dashboards** → **+ Dashboard**
2. Đặt tên: **"Spotify Analytics Dashboard"**
3. Click **Save**

### 7.2. Add Charts to Dashboard

1. Click **Edit Dashboard**
2. Kéo thả các charts đã tạo vào dashboard:
   - Top 10 Artists (góc trên trái)
   - Track Distribution by Market (góc trên phải)
   - Genre Popularity (giữa trái)
   - Releases Over Time (giữa phải)
   - Artist Followers vs Popularity (dưới cùng)
3. Resize và sắp xếp layout
4. Click **Save**

---

## 🎯 SQL Queries Nâng cao (Custom Charts)

### Query 1: Top Artists by Year

```sql
SELECT
    d.year,
    a.artist_name,
    AVG(f.popularity) as avg_popularity,
    COUNT(DISTINCT f.track_id) as total_tracks
FROM fact_track_performance f
JOIN dim_artist a ON f.artist_id = a.artist_id
JOIN dim_date d ON f.date_id = d.date_id
GROUP BY d.year, a.artist_name
ORDER BY d.year DESC, avg_popularity DESC
```

### Query 2: Market Performance Comparison

```sql
SELECT
    m.market_code,
    m.market_name,
    COUNT(DISTINCT f.track_id) as unique_tracks,
    AVG(f.popularity) as avg_popularity,
    COUNT(DISTINCT f.artist_id) as unique_artists
FROM fact_track_performance f
JOIN dim_market m ON f.market_id = m.market_id
GROUP BY m.market_code, m.market_name
ORDER BY unique_tracks DESC
LIMIT 20
```

### Query 3: Genre Trends by Year

```sql
SELECT
    d.year,
    g.primary_genre,
    AVG(f.popularity) as avg_popularity,
    COUNT(*) as track_count
FROM fact_track_performance f
JOIN dim_date d ON f.date_id = d.date_id
JOIN bridge_track_genre b ON f.track_id = b.track_id
JOIN dim_genre g ON b.genre_id = g.genre_id
GROUP BY d.year, g.primary_genre
ORDER BY d.year DESC, avg_popularity DESC
```

---

## 🎨 Filters và Interactivity

### Thêm Filters vào Dashboard

1. Edit Dashboard
2. Click **Add Filter** (icon phễu ở góc phải)
3. Thêm filters:
   - **Year Filter:** Từ `dim_date.year`
   - **Market Filter:** Từ `dim_market.market_code`
   - **Genre Filter:** Từ `dim_genre.primary_genre`
4. Apply filters cho tất cả charts
5. Save Dashboard

---

## 📝 Lưu ý

### Performance Tips:

1. ✅ Sử dụng aggregate tables (`agg_*`) cho queries nhanh
2. ✅ Tạo indexes trong SQLite nếu query chậm
3. ✅ Cache charts để tăng tốc độ load
4. ✅ Giới hạn số rows (Row Limit) cho big tables

### Troubleshooting:

- ❗ Nếu không connect được database: Kiểm tra đường dẫn SQLite
- ❗ Nếu charts lỗi: Check SQL syntax và column names
- ❗ Nếu Superset crash: Restart với `start_superset.sh`

---

## 🌟 Advanced Features

### 1. Alert & Reports

- Setup email alerts khi metrics vượt ngưỡng
- Schedule automated reports

### 2. Row Level Security

- Giới hạn data access theo user

### 3. CSS Customization

- Tùy chỉnh theme và colors

### 4. API Integration

- Export charts qua REST API
- Embed charts vào web apps

---

## 📚 Resources

- **Superset Docs:** https://superset.apache.org/docs/intro
- **Chart Gallery:** https://superset.apache.org/docs/gallery
- **Community:** https://github.com/apache/superset

---

## ✅ Checklist

- [ ] Export data từ MinIO sang SQLite
- [ ] Cài đặt Superset thành công
- [ ] Khởi động Superset tại http://localhost:8088
- [ ] Kết nối SQLite database
- [ ] Add tất cả datasets
- [ ] Tạo 5+ charts
- [ ] Tạo dashboard với filters
- [ ] Test interactivity và performance

**Good luck! 🚀**
