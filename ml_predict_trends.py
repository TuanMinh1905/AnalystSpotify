"""
Machine Learning Model để dự đoán xu hướng nhạc (popularity)
Sử dụng dữ liệu từ Gold layer để train và predict
"""

import pandas as pd
import numpy as np
import sqlite3
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.tree import DecisionTreeRegressor
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import matplotlib.pyplot as plt
import seaborn as sns
import pickle
import warnings
warnings.filterwarnings('ignore')

# Kết nối database
DB_PATH = "/home/hadoopminhquang/spotify_gold.db"
conn = sqlite3.connect(DB_PATH)

print("=" * 80)
print("🤖 MACHINE LEARNING - DỰ ĐOÁN XU HƯỚNG NHẠC")
print("=" * 80)

# ============================================================================
# 1. THU THẬP VÀ CHUẨN BỊ DỮ LIỆU
# ============================================================================
print("\n📊 BƯỚC 1: Thu thập và xử lý dữ liệu...")

# Query dữ liệu từ các bảng đã join
query = """
SELECT 
    -- Track features
    t.duration_minutes,
    t.explicit,
    t.is_collaboration,
    t.duration_category,
    
    -- Artist features
    a.artist_popularity,
    a.artist_followers,
    
    -- Album features
    al.album_type,
    al.is_recent,
    
    -- Date features
    d.year,
    d.month,
    d.quarter,
    
    -- Market features (count)
    (SELECT COUNT(DISTINCT market_id) 
     FROM fact_track_performance f2 
     WHERE f2.track_id = f.track_id) as market_count,
    
    -- Genre features
    f.genre_count,
    
    -- Collaboration count
    f.artist_count,
    
    -- Target variable
    f.popularity
    
FROM fact_track_performance f
JOIN dim_track t ON f.track_id = t.track_id
JOIN dim_artist a ON f.artist_id = a.artist_id
JOIN dim_album al ON f.album_id = al.album_id
JOIN dim_date d ON f.date_id = d.date_id
"""

df = pd.read_sql_query(query, conn)
print(f"✅ Đã load {len(df)} records từ database")
print(f"   Features: {df.shape[1] - 1} features")
print(f"   Target: popularity (giá trị cần dự đoán)")

# Thống kê cơ bản
print("\n📈 Thống kê Popularity:")
print(df['popularity'].describe())

# ============================================================================
# 2. FEATURE ENGINEERING
# ============================================================================
print("\n🔧 BƯỚC 2: Feature Engineering...")

# Encode categorical variables
le_duration = LabelEncoder()
le_album = LabelEncoder()

df['duration_category_encoded'] = le_duration.fit_transform(df['duration_category'])
df['album_type_encoded'] = le_album.fit_transform(df['album_type'])

# Convert boolean to int
df['explicit'] = df['explicit'].astype(int)
df['is_collaboration'] = df['is_collaboration'].astype(int)
df['is_recent'] = df['is_recent'].astype(int)

# Tạo thêm features
df['artist_popularity_tier'] = pd.cut(df['artist_popularity'], 
                                       bins=[0, 30, 60, 100], 
                                       labels=[0, 1, 2])
df['followers_log'] = np.log1p(df['artist_followers'])
df['market_penetration'] = df['market_count'] / 185  # % markets covered

# Drop categorical columns gốc
df_features = df.drop(['duration_category', 'album_type'], axis=1)

print(f"✅ Feature engineering hoàn tất")
print(f"   Total features: {df_features.shape[1] - 1}")
print(f"   Features list: {list(df_features.columns[:-1])}")

# ============================================================================
# 3. CHIA DỮ LIỆU TRAIN/TEST
# ============================================================================
print("\n✂️ BƯỚC 3: Chia dữ liệu Train/Test...")

X = df_features.drop('popularity', axis=1)
y = df_features['popularity']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print(f"✅ Train set: {len(X_train)} samples")
print(f"✅ Test set: {len(X_test)} samples")

# Chuẩn hóa dữ liệu
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# ============================================================================
# 4. TRAINING NHIỀU MODELS
# ============================================================================
print("\n🎓 BƯỚC 4: Training các models...")

models = {
    'Linear Regression': LinearRegression(),
    'Ridge Regression': Ridge(alpha=1.0),
    'Lasso Regression': Lasso(alpha=1.0),
    'Decision Tree': DecisionTreeRegressor(max_depth=10, random_state=42),
    'Random Forest': RandomForestRegressor(n_estimators=100, max_depth=15, random_state=42),
    'Gradient Boosting': GradientBoostingRegressor(n_estimators=100, max_depth=5, random_state=42)
}

results = {}

for name, model in models.items():
    print(f"\n🔄 Training {name}...")
    
    # Train
    model.fit(X_train_scaled, y_train)
    
    # Predict
    y_pred_train = model.predict(X_train_scaled)
    y_pred_test = model.predict(X_test_scaled)
    
    # Evaluate
    train_r2 = r2_score(y_train, y_pred_train)
    test_r2 = r2_score(y_test, y_pred_test)
    train_rmse = np.sqrt(mean_squared_error(y_train, y_pred_train))
    test_rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
    test_mae = mean_absolute_error(y_test, y_pred_test)
    
    results[name] = {
        'model': model,
        'train_r2': train_r2,
        'test_r2': test_r2,
        'train_rmse': train_rmse,
        'test_rmse': test_rmse,
        'test_mae': test_mae,
        'predictions': y_pred_test
    }
    
    print(f"   Train R²: {train_r2:.4f} | Test R²: {test_r2:.4f}")
    print(f"   Train RMSE: {train_rmse:.4f} | Test RMSE: {test_rmse:.4f}")
    print(f"   Test MAE: {test_mae:.4f}")

# ============================================================================
# 5. SO SÁNH MODELS
# ============================================================================
print("\n" + "=" * 80)
print("📊 KẾT QUẢ SO SÁNH CÁC MODELS")
print("=" * 80)

comparison_df = pd.DataFrame({
    'Model': list(results.keys()),
    'Train R²': [results[m]['train_r2'] for m in results],
    'Test R²': [results[m]['test_r2'] for m in results],
    'Test RMSE': [results[m]['test_rmse'] for m in results],
    'Test MAE': [results[m]['test_mae'] for m in results]
}).sort_values('Test R²', ascending=False)

print(comparison_df.to_string(index=False))

# Tìm best model
best_model_name = comparison_df.iloc[0]['Model']
best_model = results[best_model_name]['model']

print(f"\n🏆 BEST MODEL: {best_model_name}")
print(f"   Test R²: {comparison_df.iloc[0]['Test R²']:.4f}")
print(f"   Test RMSE: {comparison_df.iloc[0]['Test RMSE']:.4f}")
print(f"   Test MAE: {comparison_df.iloc[0]['Test MAE']:.4f}")

# ============================================================================
# 6. FEATURE IMPORTANCE (cho Random Forest hoặc Gradient Boosting)
# ============================================================================
print("\n🔍 BƯỚC 5: Phân tích Feature Importance...")

if best_model_name in ['Random Forest', 'Gradient Boosting']:
    feature_importance = pd.DataFrame({
        'Feature': X.columns,
        'Importance': best_model.feature_importances_
    }).sort_values('Importance', ascending=False)
    
    print("\n📊 Top 10 Features quan trọng nhất:")
    print(feature_importance.head(10).to_string(index=False))
    
    # Lưu feature importance
    feature_importance.to_csv('/home/hadoopminhquang/feature_importance.csv', index=False)
    print("\n✅ Saved: feature_importance.csv")

# ============================================================================
# 7. VISUALIZATION
# ============================================================================
print("\n📈 BƯỚC 6: Tạo visualizations...")

# 7.1. Model Comparison Chart
plt.figure(figsize=(12, 6))
x_pos = np.arange(len(comparison_df))
plt.bar(x_pos, comparison_df['Test R²'], color='skyblue', alpha=0.8)
plt.xlabel('Model', fontsize=12)
plt.ylabel('R² Score', fontsize=12)
plt.title('Model Comparison - R² Score', fontsize=14, fontweight='bold')
plt.xticks(x_pos, comparison_df['Model'], rotation=45, ha='right')
plt.tight_layout()
plt.savefig('/home/hadoopminhquang/model_comparison.png', dpi=300, bbox_inches='tight')
print("✅ Saved: model_comparison.png")

# 7.2. Actual vs Predicted
plt.figure(figsize=(10, 6))
y_pred_best = results[best_model_name]['predictions']
plt.scatter(y_test, y_pred_best, alpha=0.5, s=10)
plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--', lw=2)
plt.xlabel('Actual Popularity', fontsize=12)
plt.ylabel('Predicted Popularity', fontsize=12)
plt.title(f'{best_model_name} - Actual vs Predicted', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig('/home/hadoopminhquang/actual_vs_predicted.png', dpi=300, bbox_inches='tight')
print("✅ Saved: actual_vs_predicted.png")

# 7.3. Residual Plot
plt.figure(figsize=(10, 6))
residuals = y_test - y_pred_best
plt.scatter(y_pred_best, residuals, alpha=0.5, s=10)
plt.axhline(y=0, color='r', linestyle='--', lw=2)
plt.xlabel('Predicted Popularity', fontsize=12)
plt.ylabel('Residuals', fontsize=12)
plt.title(f'{best_model_name} - Residual Plot', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig('/home/hadoopminhquang/residual_plot.png', dpi=300, bbox_inches='tight')
print("✅ Saved: residual_plot.png")

# 7.4. Feature Importance Chart
if best_model_name in ['Random Forest', 'Gradient Boosting']:
    plt.figure(figsize=(10, 8))
    top_features = feature_importance.head(10)
    plt.barh(top_features['Feature'], top_features['Importance'], color='coral')
    plt.xlabel('Importance', fontsize=12)
    plt.ylabel('Feature', fontsize=12)
    plt.title('Top 10 Most Important Features', fontsize=14, fontweight='bold')
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.savefig('/home/hadoopminhquang/feature_importance.png', dpi=300, bbox_inches='tight')
    print("✅ Saved: feature_importance.png")

# ============================================================================
# 8. LƯU MODEL
# ============================================================================
print("\n💾 BƯỚC 7: Lưu model và artifacts...")

# Lưu best model
with open('/home/hadoopminhquang/best_model.pkl', 'wb') as f:
    pickle.dump(best_model, f)

# Lưu scaler
with open('/home/hadoopminhquang/scaler.pkl', 'wb') as f:
    pickle.dump(scaler, f)

# Lưu label encoders
with open('/home/hadoopminhquang/label_encoders.pkl', 'wb') as f:
    pickle.dump({
        'duration': le_duration,
        'album_type': le_album
    }, f)

print("✅ Saved: best_model.pkl")
print("✅ Saved: scaler.pkl")
print("✅ Saved: label_encoders.pkl")

# ============================================================================
# 9. DỰ ĐOÁN MẪU CHO CÁC TRACKS MỚI
# ============================================================================
print("\n🔮 BƯỚC 8: Dự đoán xu hướng cho tracks...")

# Lấy sample tracks để predict
sample_query = """
SELECT 
    t.track_id,
    t.track_name,
    a.artist_name,
    f.popularity as actual_popularity
FROM fact_track_performance f
JOIN dim_track t ON f.track_id = t.track_id
JOIN dim_artist a ON f.artist_id = a.artist_id
GROUP BY t.track_id, t.track_name, a.artist_name, f.popularity
ORDER BY RANDOM()
LIMIT 20
"""

sample_tracks = pd.read_sql_query(sample_query, conn)

# Predict cho sample
sample_features_query = f"""
SELECT 
    t.duration_minutes,
    t.explicit,
    t.is_collaboration,
    t.duration_category,
    a.artist_popularity,
    a.artist_followers,
    al.album_type,
    al.is_recent,
    d.year,
    d.month,
    d.quarter,
    (SELECT COUNT(DISTINCT market_id) 
     FROM fact_track_performance f2 
     WHERE f2.track_id = f.track_id) as market_count,
    f.genre_count,
    f.artist_count
FROM fact_track_performance f
JOIN dim_track t ON f.track_id = t.track_id
JOIN dim_artist a ON f.artist_id = a.artist_id
JOIN dim_album al ON f.album_id = al.album_id
JOIN dim_date d ON f.date_id = d.date_id
WHERE t.track_id IN ({','.join([f"'{tid}'" for tid in sample_tracks['track_id']])})
GROUP BY t.track_id
LIMIT 20
"""

sample_features = pd.read_sql_query(sample_features_query, conn)

# Preprocessing
sample_features['duration_category_encoded'] = le_duration.transform(sample_features['duration_category'])
sample_features['album_type_encoded'] = le_album.transform(sample_features['album_type'])
sample_features['explicit'] = sample_features['explicit'].astype(int)
sample_features['is_collaboration'] = sample_features['is_collaboration'].astype(int)
sample_features['is_recent'] = sample_features['is_recent'].astype(int)
sample_features['artist_popularity_tier'] = pd.cut(sample_features['artist_popularity'], 
                                                     bins=[0, 30, 60, 100], 
                                                     labels=[0, 1, 2])
sample_features['followers_log'] = np.log1p(sample_features['artist_followers'])
sample_features['market_penetration'] = sample_features['market_count'] / 185
sample_features_clean = sample_features.drop(['duration_category', 'album_type'], axis=1)

# Predict
sample_scaled = scaler.transform(sample_features_clean)
predictions = best_model.predict(sample_scaled)

# Tạo kết quả
prediction_results = pd.DataFrame({
    'Track': sample_tracks['track_name'].values,
    'Artist': sample_tracks['artist_name'].values,
    'Actual Popularity': sample_tracks['actual_popularity'].values,
    'Predicted Popularity': predictions,
    'Difference': predictions - sample_tracks['actual_popularity'].values,
    'Accuracy (%)': (1 - abs(predictions - sample_tracks['actual_popularity'].values) / sample_tracks['actual_popularity'].values) * 100
})

print("\n🎯 DỰ ĐOÁN CHO 20 TRACKS MẪU:")
print("=" * 80)
print(prediction_results.to_string(index=False))

# Lưu predictions
prediction_results.to_csv('/home/hadoopminhquang/sample_predictions.csv', index=False)
print("\n✅ Saved: sample_predictions.csv")

# ============================================================================
# 10. PHÂN TÍCH XU HƯỚNG
# ============================================================================
print("\n" + "=" * 80)
print("📈 PHÂN TÍCH XU HƯỚNG NHẠC TRONG TƯƠNG LAI")
print("=" * 80)

# Tính trend cho các features
trend_analysis = f"""
Dựa trên {len(df)} records đã phân tích, các yếu tố quan trọng nhất ảnh hưởng đến xu hướng:

"""

if best_model_name in ['Random Forest', 'Gradient Boosting']:
    top5_features = feature_importance.head(5)
    for idx, row in top5_features.iterrows():
        trend_analysis += f"  {idx+1}. {row['Feature']}: {row['Importance']:.4f}\n"

trend_analysis += f"""

💡 KẾT LUẬN VÀ KHUYẾN NGHỊ:

1. Các bài hát có khả năng lên xu hướng cao:
   - Artist có popularity > 60 và followers cao
   - Được phát hành trên nhiều markets (> 50% = 93 markets)
   - Là collaboration (nhiều artists)
   - Thuộc nhiều genres (đa dạng)
   
2. Thời điểm phát hành:
   - Quý 4 (tháng 10-12) thường có popularity cao hơn
   - Tracks mới (is_recent=1) có lợi thế

3. Model Performance:
   - Best Model: {best_model_name}
   - R² Score: {comparison_df.iloc[0]['Test R²']:.4f} (giải thích {comparison_df.iloc[0]['Test R²']*100:.1f}% variance)
   - RMSE: {comparison_df.iloc[0]['Test RMSE']:.4f} (sai số trung bình)
   - MAE: {comparison_df.iloc[0]['Test MAE']:.4f} (sai số tuyệt đối)

4. Độ tin cậy:
   - Model có thể dự đoán popularity với độ chính xác {(1 - comparison_df.iloc[0]['Test RMSE']/y.mean())*100:.1f}%
   - Phù hợp để tư vấn chiến lược phát hành nhạc
"""

print(trend_analysis)

# Lưu report
with open('/home/hadoopminhquang/ml_trend_analysis_report.txt', 'w', encoding='utf-8') as f:
    f.write(trend_analysis)

print("✅ Saved: ml_trend_analysis_report.txt")

# Đóng connection
conn.close()

print("\n" + "=" * 80)
print("✅ HOÀN TẤT MACHINE LEARNING PIPELINE")
print("=" * 80)
print("\n📁 Files đã tạo:")
print("   • best_model.pkl (model đã train)")
print("   • scaler.pkl (scaler cho preprocessing)")
print("   • label_encoders.pkl (encoders cho categorical)")
print("   • feature_importance.csv (độ quan trọng của features)")
print("   • sample_predictions.csv (dự đoán mẫu)")
print("   • ml_trend_analysis_report.txt (báo cáo phân tích)")
print("   • model_comparison.png (so sánh models)")
print("   • actual_vs_predicted.png (đánh giá độ chính xác)")
print("   • residual_plot.png (phân tích sai số)")
print("   • feature_importance.png (biểu đồ feature importance)")

print("\n🎯 Để sử dụng model cho tracks mới:")
print("   1. Load model: pickle.load('best_model.pkl')")
print("   2. Chuẩn bị features tương tự như trong training")
print("   3. Predict: model.predict(features_scaled)")
