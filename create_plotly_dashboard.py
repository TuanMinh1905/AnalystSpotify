"""
Script tạo biểu đồ phân tích Spotify data từ Gold layer sử dụng Plotly
Thay thế cho Superset với visualizations đẹp và interactive
"""

import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import webbrowser
import os

# Đường dẫn database
DB_PATH = "/home/hadoopminhquang/spotify_gold.db"

print("=" * 80)
print("🎨 TẠO DASHBOARD PHÂN TÍCH SPOTIFY DATA")
print("="  * 80)

# Kết nối database
conn = sqlite3.connect(DB_PATH)

# ============================================================================
# 📊 CHART 1: Top 10 Artists by Average Popularity
# ============================================================================
print("\n📊 Tạo Chart 1: Top 10 Artists by Average Popularity...")

df_artists = pd.read_sql_query("""
    SELECT artist_name, avg_popularity, total_tracks, artist_followers
    FROM agg_artist_performance
    ORDER BY avg_popularity DESC
    LIMIT 10
""", conn)

fig1 = px.bar(
    df_artists,
    x='avg_popularity',
    y='artist_name',
    orientation='h',
    title='🎤 Top 10 Artists by Average Popularity',
    labels={'avg_popularity': 'Average Popularity', 'artist_name': 'Artist'},
    color='avg_popularity',
    color_continuous_scale='Viridis',
    text='avg_popularity'
)
fig1.update_traces(texttemplate='%{text:.1f}', textposition='outside')
fig1.update_layout(height=500, yaxis={'categoryorder':'total ascending'})
fig1.write_html("/home/hadoopminhquang/chart1_top_artists.html")
print("✅ Saved: chart1_top_artists.html")

# ============================================================================
# 🌍 CHART 2: Market Distribution (Top 15)
# ============================================================================
print("\n🌍 Tạo Chart 2: Track Distribution by Market...")

df_markets = pd.read_sql_query("""
    SELECT market_code, total_tracks, avg_popularity
    FROM agg_market_stats
    ORDER BY total_tracks DESC
    LIMIT 15
""", conn)

fig2 = px.pie(
    df_markets,
    values='total_tracks',
    names='market_code',
    title='🌍 Top 15 Markets by Track Count',
    hover_data=['avg_popularity'],
    color_discrete_sequence=px.colors.sequential.RdBu
)
fig2.update_traces(textposition='inside', textinfo='percent+label')
fig2.update_layout(height=600)
fig2.write_html("/home/hadoopminhquang/chart2_market_distribution.html")
print("✅ Saved: chart2_market_distribution.html")

# ============================================================================
# 🎵 CHART 3: Genre Popularity (Top 20)
# ============================================================================
print("\n🎵 Tạo Chart 3: Genre Popularity Distribution...")

df_genres = pd.read_sql_query("""
    SELECT genre_name as primary_genre, avg_popularity, total_tracks
    FROM agg_genre_popularity
    ORDER BY avg_popularity DESC
    LIMIT 20
""", conn)

fig3 = px.treemap(
    df_genres,
    path=['primary_genre'],
    values='total_tracks',
    color='avg_popularity',
    title='🎵 Top 20 Genres by Popularity & Track Count',
    color_continuous_scale='YlOrRd',
    hover_data={'avg_popularity': ':.1f', 'total_tracks': True}
)
fig3.update_layout(height=600)
fig3.write_html("/home/hadoopminhquang/chart3_genre_popularity.html")
print("✅ Saved: chart3_genre_popularity.html")

# ============================================================================
# 📅 CHART 4: Releases Over Time
# ============================================================================
print("\n📅 Tạo Chart 4: Releases Over Time...")

df_timeline = pd.read_sql_query("""
    SELECT 
        d.year,
        d.month,
        COUNT(DISTINCT f.track_id) as total_releases,
        AVG(f.popularity) as avg_popularity
    FROM fact_track_performance f
    JOIN dim_date d ON f.date_id = d.date_id
    GROUP BY d.year, d.month
    ORDER BY d.year, d.month
""", conn)

df_timeline['date'] = pd.to_datetime(df_timeline[['year', 'month']].assign(day=1))

fig4 = make_subplots(
    rows=2, cols=1,
    subplot_titles=('Total Releases Over Time', 'Average Popularity Trend'),
    vertical_spacing=0.12
)

fig4.add_trace(
    go.Scatter(
        x=df_timeline['date'],
        y=df_timeline['total_releases'],
        mode='lines+markers',
        name='Total Releases',
        line=dict(color='royalblue', width=2),
        marker=dict(size=6)
    ),
    row=1, col=1
)

fig4.add_trace(
    go.Scatter(
        x=df_timeline['date'],
        y=df_timeline['avg_popularity'],
        mode='lines+markers',
        name='Avg Popularity',
        line=dict(color='tomato', width=2),
        marker=dict(size=6)
    ),
    row=2, col=1
)

fig4.update_xaxes(title_text="Date", row=2, col=1)
fig4.update_yaxes(title_text="Number of Releases", row=1, col=1)
fig4.update_yaxes(title_text="Popularity", row=2, col=1)
fig4.update_layout(height=700, title_text="📅 Music Releases Timeline Analysis", showlegend=False)
fig4.write_html("/home/hadoopminhquang/chart4_timeline.html")
print("✅ Saved: chart4_timeline.html")

# ============================================================================
# 🔥 CHART 5: Artist Followers vs Popularity Scatter
# ============================================================================
print("\n🔥 Tạo Chart 5: Artist Followers vs Popularity...")

df_scatter = pd.read_sql_query("""
    SELECT artist_name, avg_popularity, total_tracks, artist_followers
    FROM agg_artist_performance
    WHERE artist_followers > 0
    ORDER BY avg_popularity DESC
    LIMIT 30
""", conn)

fig5 = px.scatter(
    df_scatter,
    x='artist_followers',
    y='avg_popularity',
    size='total_tracks',
    color='avg_popularity',
    hover_name='artist_name',
    title='🔥 Artist Followers vs Popularity (Top 30)',
    labels={
        'artist_followers': 'Total Followers',
        'avg_popularity': 'Average Popularity',
        'total_tracks': 'Track Count'
    },
    color_continuous_scale='Plasma',
    size_max=30
)
fig5.update_layout(height=600)
fig5.write_html("/home/hadoopminhquang/chart5_scatter.html")
print("✅ Saved: chart5_scatter.html")

# ============================================================================
# 📈 CHART 6: Top 5 Artists by Year
# ============================================================================
print("\n📈 Tạo Chart 6: Top Artists by Year...")

df_by_year = pd.read_sql_query("""
    SELECT 
        d.year,
        a.artist_name,
        AVG(f.popularity) as avg_popularity,
        COUNT(f.track_id) as track_count
    FROM fact_track_performance f
    JOIN dim_artist a ON f.artist_id = a.artist_id
    JOIN dim_date d ON f.date_id = d.date_id
    GROUP BY d.year, a.artist_name
    ORDER BY d.year DESC, avg_popularity DESC
""", conn)

# Top 5 cho từng năm
top5_each_year = df_by_year.groupby('year').apply(
    lambda x: x.nlargest(5, 'avg_popularity')
).reset_index(drop=True)

fig6 = px.bar(
    top5_each_year,
    x='year',
    y='avg_popularity',
    color='artist_name',
    title='📈 Top 5 Artists by Year',
    labels={'avg_popularity': 'Average Popularity', 'year': 'Year'},
    text='artist_name',
    barmode='group',
    color_discrete_sequence=px.colors.qualitative.Set3
)
fig6.update_traces(textposition='outside', textangle=0)
fig6.update_layout(height=600, showlegend=True)
fig6.write_html("/home/hadoopminhquang/chart6_top_by_year.html")
print("✅ Saved: chart6_top_by_year.html")

# ============================================================================
# 📊 CHART 7: Market Performance Heatmap
# ============================================================================
print("\n📊 Tạo Chart 7: Market Performance Heatmap...")

df_market_genre = pd.read_sql_query("""
    SELECT 
        m.market_code,
        g.genre_name as primary_genre,
        AVG(f.popularity) as avg_popularity,
        COUNT(*) as track_count
    FROM fact_track_performance f
    JOIN dim_market m ON f.market_id = m.market_id
    JOIN bridge_track_genre b ON f.track_id = b.track_id
    JOIN dim_genre g ON b.genre_id = g.genre_id
    GROUP BY m.market_code, g.genre_name
    HAVING track_count > 5
""", conn)

# Top 15 markets và top 10 genres
top_markets = df_market_genre.groupby('market_code')['track_count'].sum().nlargest(15).index
top_genres = df_market_genre.groupby('primary_genre')['track_count'].sum().nlargest(10).index

df_heatmap = df_market_genre[
    (df_market_genre['market_code'].isin(top_markets)) &
    (df_market_genre['primary_genre'].isin(top_genres))
]

# Pivot cho heatmap
pivot_data = df_heatmap.pivot_table(
    index='primary_genre',
    columns='market_code',
    values='avg_popularity',
    aggfunc='mean'
)

fig7 = px.imshow(
    pivot_data,
    title='📊 Genre Popularity by Market (Heatmap)',
    labels=dict(x="Market", y="Genre", color="Avg Popularity"),
    color_continuous_scale='Turbo',
    aspect='auto'
)
fig7.update_layout(height=600)
fig7.write_html("/home/hadoopminhquang/chart7_heatmap.html")
print("✅ Saved: chart7_heatmap.html")

# ============================================================================
# 🎯 CHART 8: Summary Dashboard (Combined) - SIMPLIFIED
# ============================================================================
print("\n🎯 Tạo Dashboard tổng hợp...")

# Tạo dashboard đơn giản với các bar charts
fig_dashboard = make_subplots(
    rows=2, cols=2,
    subplot_titles=(
        'Top 5 Artists',
        'Top 10 Markets',
        'Top 10 Genres',
        'Timeline Trend'
    ),
    vertical_spacing=0.15,
    horizontal_spacing=0.12
)

# Top Artists
fig_dashboard.add_trace(
    go.Bar(
        x=df_artists['avg_popularity'][:5],
        y=df_artists['artist_name'][:5],
        orientation='h',
        marker=dict(color=df_artists['avg_popularity'][:5], colorscale='Viridis'),
        name='Artists',
        showlegend=False
    ),
    row=1, col=1
)

# Markets
fig_dashboard.add_trace(
    go.Bar(
        x=df_markets['market_code'][:10],
        y=df_markets['total_tracks'][:10],
        marker=dict(color=df_markets['total_tracks'][:10], colorscale='Blues'),
        name='Markets',
        showlegend=False
    ),
    row=1, col=2
)

# Genres
fig_dashboard.add_trace(
    go.Bar(
        x=df_genres['primary_genre'][:10],
        y=df_genres['avg_popularity'][:10],
        marker=dict(color=df_genres['avg_popularity'][:10], colorscale='YlOrRd'),
        name='Genres',
        showlegend=False
    ),
    row=2, col=1
)

# Timeline
fig_dashboard.add_trace(
    go.Scatter(
        x=df_timeline['date'],
        y=df_timeline['total_releases'],
        mode='lines',
        line=dict(color='royalblue', width=2),
        name='Releases',
        showlegend=False
    ),
    row=2, col=2
)

fig_dashboard.update_xaxes(title_text="Popularity", row=1, col=1)
fig_dashboard.update_yaxes(title_text="Artist", row=1, col=1)
fig_dashboard.update_xaxes(title_text="Market", row=1, col=2)
fig_dashboard.update_yaxes(title_text="Tracks", row=1, col=2)
fig_dashboard.update_xaxes(title_text="Genre", row=2, col=1, tickangle=45)
fig_dashboard.update_yaxes(title_text="Popularity", row=2, col=1)
fig_dashboard.update_xaxes(title_text="Date", row=2, col=2)
fig_dashboard.update_yaxes(title_text="Releases", row=2, col=2)

fig_dashboard.update_layout(
    height=900,
    title_text="🎯 Spotify Data Analytics Dashboard",
    showlegend=False
)
fig_dashboard.write_html("/home/hadoopminhquang/dashboard_combined.html")
print("✅ Saved: dashboard_combined.html")

# Đóng connection
conn.close()

# ============================================================================
# 📝 Tạo index HTML để dễ truy cập
# ============================================================================
print("\n📝 Tạo index page...")

index_html = """
<!DOCTYPE html>
<html>
<head>
    <title>🎵 Spotify Analytics Dashboard</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255,255,255,0.1);
            padding: 30px;
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }
        h1 {
            text-align: center;
            font-size: 42px;
            margin-bottom: 10px;
        }
        .subtitle {
            text-align: center;
            font-size: 18px;
            margin-bottom: 40px;
            opacity: 0.9;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }
        .card {
            background: rgba(255,255,255,0.15);
            padding: 25px;
            border-radius: 12px;
            text-align: center;
            transition: transform 0.3s, box-shadow 0.3s;
            border: 2px solid rgba(255,255,255,0.2);
        }
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        .card h3 {
            margin-top: 0;
            font-size: 24px;
        }
        .card a {
            display: inline-block;
            margin-top: 15px;
            padding: 12px 30px;
            background: white;
            color: #667eea;
            text-decoration: none;
            border-radius: 25px;
            font-weight: bold;
            transition: background 0.3s;
        }
        .card a:hover {
            background: #f0f0f0;
        }
        .icon {
            font-size: 48px;
            margin-bottom: 15px;
        }
        .dashboard-card {
            grid-column: 1 / -1;
            background: linear-gradient(135deg, rgba(255,107,107,0.3), rgba(255,168,1,0.3));
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎵 Spotify Data Analytics Dashboard</h1>
        <p class="subtitle">Phân tích dữ liệu từ Gold Layer - Powered by Python & Plotly</p>
        
        <div class="grid">
            <div class="card dashboard-card">
                <div class="icon">🎯</div>
                <h3>Combined Dashboard</h3>
                <p>Tổng quan tất cả charts trong một trang</p>
                <a href="dashboard_combined.html" target="_blank">Xem Dashboard</a>
            </div>
            
            <div class="card">
                <div class="icon">🎤</div>
                <h3>Top Artists</h3>
                <p>10 nghệ sĩ có popularity cao nhất</p>
                <a href="chart1_top_artists.html" target="_blank">Xem Chi tiết</a>
            </div>
            
            <div class="card">
                <div class="icon">🌍</div>
                <h3>Market Distribution</h3>
                <p>Phân bổ tracks theo thị trường</p>
                <a href="chart2_market_distribution.html" target="_blank">Xem Chi tiết</a>
            </div>
            
            <div class="card">
                <div class="icon">🎵</div>
                <h3>Genre Popularity</h3>
                <p>Thể loại nhạc phổ biến nhất</p>
                <a href="chart3_genre_popularity.html" target="_blank">Xem Chi tiết</a>
            </div>
            
            <div class="card">
                <div class="icon">📅</div>
                <h3>Timeline Analysis</h3>
                <p>Xu hướng phát hành theo thời gian</p>
                <a href="chart4_timeline.html" target="_blank">Xem Chi tiết</a>
            </div>
            
            <div class="card">
                <div class="icon">🔥</div>
                <h3>Followers vs Popularity</h3>
                <p>Phân tích mối quan hệ followers & popularity</p>
                <a href="chart5_scatter.html" target="_blank">Xem Chi tiết</a>
            </div>
            
            <div class="card">
                <div class="icon">📈</div>
                <h3>Top by Year</h3>
                <p>Top 5 nghệ sĩ theo từng năm</p>
                <a href="chart6_top_by_year.html" target="_blank">Xem Chi tiết</a>
            </div>
            
            <div class="card">
                <div class="icon">📊</div>
                <h3>Market Heatmap</h3>
                <p>Genre popularity theo market</p>
                <a href="chart7_heatmap.html" target="_blank">Xem Chi tiết</a>
            </div>
        </div>
    </div>
</body>
</html>
"""

with open("/home/hadoopminhquang/index.html", "w", encoding="utf-8") as f:
    f.write(index_html)

print("✅ Saved: index.html")

print("\n" + "=" * 80)
print("✅ TẤT CẢ BIỂU ĐỒ ĐÃ ĐƯỢC TẠO THÀNH CÔNG!")
print("=" * 80)
print("\n📁 Các file đã tạo:")
print("   • index.html (trang chính)")
print("   • dashboard_combined.html")
print("   • chart1_top_artists.html")
print("   • chart2_market_distribution.html")
print("   • chart3_genre_popularity.html")
print("   • chart4_timeline.html")
print("   • chart5_scatter.html")
print("   • chart6_top_by_year.html")
print("   • chart7_heatmap.html")
print("\n🌐 Để xem dashboard, mở file index.html trong browser")
print("   Hoặc chạy: python3 -m http.server 8088")
print("   Sau đó truy cập: http://localhost:8088/index.html")
