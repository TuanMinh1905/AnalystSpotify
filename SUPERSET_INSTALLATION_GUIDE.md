# 🚀 Hướng dẫn Cài đặt Apache Superset và Tạo Dashboard

## 📋 Mục lục

1. [Cài đặt Superset](#bước-1-cài-đặt-superset)
2. [Kết nối Database](#bước-2-kết-nối-database)
3. [Tạo Dataset](#bước-3-tạo-dataset)
4. [Tạo Charts](#bước-4-tạo-charts)
5. [Tạo Dashboard](#bước-5-tạo-dashboard)

---

## 📦 Bước 1: Cài đặt Superset

### **Option 1: Cài đặt bằng Docker (Khuyến nghị)**

```bash
# 1. Clone Superset repository
git clone https://github.com/apache/superset.git
cd superset

# 2. Start Superset với Docker Compose
docker-compose -f docker-compose-non-dev.yml up -d

# 3. Đợi 2-3 phút để Superset khởi động
# Truy cập: http://localhost:8088

# Default credentials:
# Username: admin
# Password: admin
```

### **Option 2: Cài đặt bằng pip (Windows)**

```bash
# 1. Tạo virtual environment
python -m venv superset_venv
.\superset_venv\Scripts\activate

# 2. Upgrade pip
python -m pip install --upgrade pip

# 3. Cài đặt Superset
pip install apache-superset

# 4. Cài đặt SQLite driver
pip install pysqlite3-binary

# 5. Initialize database
superset db upgrade

# 6. Tạo admin user
superset fab create-admin

# 7. Load examples (optional)
superset load_examples

# 8. Initialize roles và permissions
superset init

# 9. Start development server
superset run -p 8088 --with-threads --reload --debugger
```

---

## 🔗 Bước 2: Kết nối Database

### **2.1. Login vào Superset**

- Truy cập: http://localhost:8088
- Username: `admin`
- Password: (password bạn đã tạo)

### **2.2. Thêm Database Connection**

1. **Menu:** Settings → Database Connections → + Database

2. **Chọn:** SQLite

3. **SQLAlchemy URI:**

   ```
   sqlite:///C:/Users/MINH/Desktop/School_HK2_2425/BigDataAnalyst/CuoiKi/spotify_gold.db
   ```

   **Lưu ý:**

   - Windows: Dùng `/` thay vì `\`
   - Absolute path
   - 3 dấu `/` sau `sqlite:`

4. **Display Name:** `Spotify Gold Layer`

5. **Test Connection** → **Connect**

### **2.3. Verify Connection**

```sql
-- Test query
SELECT COUNT(*) FROM fact_track_performance;
```

---

## 📊 Bước 3: Tạo Dataset

### **3.1. Tạo Dataset từ Tables**

**Menu:** Data → Datasets → + Dataset

Tạo dataset cho các bảng sau:

#### **Dimension Tables:**

- ✅ `dim_track`
- ✅ `dim_artist`
- ✅ `dim_album`
- ✅ `dim_market`
- ✅ `dim_genre`
- ✅ `dim_date`

#### **Fact Table:**

- ✅ `fact_track_performance`

#### **Aggregate Tables:**

- ✅ `agg_artist_performance`
- ✅ `agg_market_stats`
- ✅ `agg_genre_popularity`

### **3.2. Tạo Virtual Dataset (SQL Query)**

**Menu:** SQL Lab → SQL Editor

#### **Dataset 1: Top Artists Analysis**

```sql
-- Saved as: "vw_top_artists"
SELECT
    artist_name,
    artist_popularity,
    artist_followers,
    total_tracks,
    ROUND(avg_popularity, 2) as avg_track_popularity,
    primary_genres
FROM agg_artist_performance
ORDER BY artist_popularity DESC
```

#### **Dataset 2: Genre Popularity**

```sql
-- Saved as: "vw_genre_popularity"
SELECT
    genre_name,
    ROUND(avg_popularity, 2) as avg_popularity,
    total_tracks,
    unique_artists
FROM agg_genre_popularity
ORDER BY avg_popularity DESC
```

#### **Dataset 3: Market Analysis**

```sql
-- Saved as: "vw_market_analysis"
SELECT
    m.market_code,
    ms.total_tracks,
    ROUND(ms.avg_popularity, 2) as avg_popularity,
    ms.popular_tracks_count
FROM agg_market_stats ms
JOIN dim_market m ON ms.market_id = m.market_id
ORDER BY ms.avg_popularity DESC
```

#### **Dataset 4: Timeline Analysis**

```sql
-- Saved as: "vw_timeline_analysis"
SELECT
    d.year,
    d.month_name,
    d.month,
    COUNT(DISTINCT f.track_id) as track_count,
    ROUND(AVG(f.popularity), 2) as avg_popularity
FROM fact_track_performance f
JOIN dim_date d ON f.date_id = d.date_id
GROUP BY d.year, d.month_name, d.month
ORDER BY d.year DESC, d.month DESC
```

#### **Dataset 5: Artist-Track Details**

```sql
-- Saved as: "vw_artist_track_details"
SELECT
    a.artist_name,
    a.artist_followers,
    a.artist_popularity,
    t.track_name,
    t.duration_minutes,
    t.explicit,
    AVG(f.popularity) as avg_popularity,
    COUNT(DISTINCT f.market_id) as market_count
FROM fact_track_performance f
JOIN dim_artist a ON f.artist_id = a.artist_id
JOIN dim_track t ON f.track_id = t.track_id
GROUP BY a.artist_name, a.artist_followers, a.artist_popularity,
         t.track_name, t.duration_minutes, t.explicit
```

**Cách lưu Virtual Dataset:**

1. Paste SQL vào SQL Editor
2. **Run Query** để test
3. Click **Save** → **Save as dataset**
4. Đặt tên dataset

---

## 📈 Bước 4: Tạo Charts

### **Chart 1: Top 10 Artists by Popularity**

**Dataset:** `vw_top_artists`

**Chart Type:** Bar Chart (Horizontal)

**Configuration:**

- **Metrics:** `MAX(artist_popularity)`
- **Dimensions:** `artist_name`
- **Sort:** Descending
- **Limit:** 10
- **Color Scheme:** Superset Default

**Customize:**

- **Title:** "🎤 Top 10 Artists by Popularity"
- **Show Values:** Yes
- **Show Legend:** No

---

### **Chart 2: Genre Popularity Distribution**

**Dataset:** `vw_genre_popularity`

**Chart Type:** Bar Chart (Horizontal)

**Configuration:**

- **Metrics:** `AVG(avg_popularity)`
- **Dimensions:** `genre_name`
- **Sort:** Descending
- **Limit:** 15
- **Color Scheme:** Blue Shades

**Customize:**

- **Title:** "🎵 Genre Popularity Distribution"
- **Show Values:** Yes

---

### **Chart 3: Release Timeline**

**Dataset:** `vw_timeline_analysis`

**Chart Type:** Line Chart

**Configuration:**

- **X-Axis:** `month_name` (ordered by `month`)
- **Metrics:**
  - `SUM(track_count)` (Tracks Released)
  - `AVG(avg_popularity)` (Avg Popularity)
- **Group By:** `year`
- **Color Scheme:** Sequential

**Customize:**

- **Title:** "📅 Release Timeline Analysis"
- **Show Legend:** Yes
- **Y-Axis:** Dual axis

---

### **Chart 4: Market Distribution**

**Dataset:** `vw_market_analysis`

**Chart Type:** Treemap

**Configuration:**

- **Dimensions:** `market_code`
- **Metrics:** `SUM(total_tracks)`
- **Color Metric:** `AVG(avg_popularity)`
- **Limit:** 20

**Customize:**

- **Title:** "🌍 Market Distribution"
- **Color Scheme:** Red-Yellow-Green

---

### **Chart 5: Followers vs Popularity (Scatter)**

**Dataset:** `vw_artist_track_details`

**Chart Type:** Scatter Plot

**Configuration:**

- **X-Axis:** `artist_followers`
- **Y-Axis:** `artist_popularity`
- **Size:** `market_count`
- **Dimensions:** `artist_name`
- **Limit:** 50

**Customize:**

- **Title:** "🔥 Followers vs Popularity Analysis"
- **Log Scale:** X-axis (optional)
- **Show Labels:** Top 10

---

### **Chart 6: Top Artists by Year**

**Dataset:** `vw_timeline_analysis`

**Chart Type:** Pivot Table

**Configuration:**

- **Rows:** `year`
- **Columns:** Top 5 artists
- **Metrics:** `track_count`, `avg_popularity`
- **Sort:** Descending by popularity

**Customize:**

- **Title:** "📈 Top Artists by Year"
- **Conditional Formatting:** Heatmap colors

---

### **Chart 7: Genre-Market Heatmap**

**Dataset:** Custom SQL

```sql
SELECT
    m.market_code,
    a.primary_genres as genre,
    COUNT(DISTINCT f.track_id) as track_count,
    ROUND(AVG(f.popularity), 2) as avg_popularity
FROM fact_track_performance f
JOIN dim_market m ON f.market_id = m.market_id
JOIN dim_artist a ON f.artist_id = a.artist_id
WHERE a.primary_genres IS NOT NULL
GROUP BY m.market_code, a.primary_genres
```

**Chart Type:** Heatmap

**Configuration:**

- **X-Axis:** `market_code`
- **Y-Axis:** `genre`
- **Metrics:** `AVG(avg_popularity)`
- **Color Scheme:** Blue-White-Red

**Customize:**

- **Title:** "📊 Genre Popularity by Market"
- **Normalize:** By row or column

---

## 🎨 Bước 5: Tạo Dashboard

### **5.1. Create New Dashboard**

**Menu:** Dashboards → + Dashboard

**Dashboard Name:** `🎵 Spotify Gold Layer Analytics`

### **5.2. Add Charts**

**Layout Recommendation:**

```
┌─────────────────────────────────────────────┐
│      🎵 Spotify Gold Layer Analytics       │
├─────────────────────────────────────────────┤
│  Top 10 Artists        │  Genre Popularity  │
│  (Bar Chart)           │  (Bar Chart)       │
├────────────────────────┴────────────────────┤
│          Release Timeline (Line Chart)      │
├─────────────────────────────────────────────┤
│  Market Distribution   │  Followers vs Pop  │
│  (Treemap)             │  (Scatter Plot)    │
├─────────────────────────────────────────────┤
│          Genre-Market Heatmap               │
└─────────────────────────────────────────────┘
```

### **5.3. Dashboard Filters**

Add filters:

- **Year Filter** (from `dim_date.year`)
- **Genre Filter** (from `dim_genre.genre_name`)
- **Market Filter** (from `dim_market.market_code`)
- **Popularity Range** (slider)

### **5.4. Dashboard Settings**

- **Refresh Interval:** Auto (optional)
- **Color Scheme:** Consistent across charts
- **Export Options:** Enable PDF/CSV export

---

## 🎯 Tổng kết - 7 Charts Chính

| #   | Chart Name          | Type        | Dataset                 | Purpose               |
| --- | ------------------- | ----------- | ----------------------- | --------------------- |
| 1   | Top 10 Artists      | Bar (H)     | vw_top_artists          | Nghệ sĩ phổ biến nhất |
| 2   | Genre Popularity    | Bar (H)     | vw_genre_popularity     | Thể loại phổ biến     |
| 3   | Release Timeline    | Line        | vw_timeline_analysis    | Xu hướng phát hành    |
| 4   | Market Distribution | Treemap     | vw_market_analysis      | Phân bố thị trường    |
| 5   | Followers vs Pop    | Scatter     | vw_artist_track_details | Mối quan hệ           |
| 6   | Top by Year         | Pivot Table | vw_timeline_analysis    | Top theo năm          |
| 7   | Market Heatmap      | Heatmap     | Custom SQL              | Genre x Market        |

---

## 🔧 Troubleshooting

### **Lỗi: Database Connection Failed**

```bash
# Kiểm tra path
# Windows: sqlite:///C:/path/to/file.db
# Linux: sqlite:////absolute/path/to/file.db
```

### **Lỗi: Permission Denied**

```bash
# Cấp quyền đọc cho file .db
chmod 644 spotify_gold.db
```

### **Lỗi: No data displayed**

```sql
-- Test query trong SQL Lab
SELECT * FROM fact_track_performance LIMIT 10;
```

---

## 📚 Resources

- [Superset Documentation](https://superset.apache.org/docs/intro)
- [Chart Types Guide](https://superset.apache.org/docs/using-superset/exploring-data)
- [SQL Lab Guide](https://superset.apache.org/docs/using-superset/sql-lab)

---

## ✅ Checklist Hoàn thành

- [ ] Cài đặt Superset
- [ ] Kết nối SQLite database
- [ ] Tạo 10 datasets (6 dim + 1 fact + 3 agg)
- [ ] Tạo 5 virtual datasets (SQL views)
- [ ] Tạo 7 charts
- [ ] Tạo 1 dashboard tổng hợp
- [ ] Thêm filters
- [ ] Test và export dashboard

**Chúc bạn thành công! 🎉**
