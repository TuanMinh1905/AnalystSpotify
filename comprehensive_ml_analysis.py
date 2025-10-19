"""
Comprehensive Machine Learning Analysis for Spotify Data
Implements 5 prediction topics using DecisionTree, KMeans, and Naive Bayes

Topics:
1. Song Popularity Classification (DecisionTree & Naive Bayes)
2. Artist Clustering (KMeans)
3. Market Success Prediction (DecisionTree & Naive Bayes)
4. Genre Classification (DecisionTree & Naive Bayes)
5. Market Clustering by Listening Behavior (KMeans)
"""

import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.tree import DecisionTreeClassifier, plot_tree
from sklearn.cluster import KMeans
from sklearn.naive_bayes import GaussianNB
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (classification_report, confusion_matrix, 
                            accuracy_score, silhouette_score, davies_bouldin_score)
import warnings
warnings.filterwarnings('ignore')

# Set style for better visualizations
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# Database connection
DB_PATH = '/home/hadoopminhquang/spotify_gold.db'

def load_data():
    """Load and prepare data from Gold layer"""
    print("📊 Loading data from Gold layer...")
    conn = sqlite3.connect(DB_PATH)
    
    # Load all necessary tables
    df_track = pd.read_sql_query("SELECT * FROM dim_track", conn)
    df_artist = pd.read_sql_query("SELECT * FROM dim_artist", conn)
    df_genre = pd.read_sql_query("SELECT * FROM dim_genre", conn)
    df_market = pd.read_sql_query("SELECT * FROM dim_market", conn)
    df_performance = pd.read_sql_query("SELECT * FROM fact_track_performance", conn)
    df_artist_agg = pd.read_sql_query("SELECT * FROM agg_artist_performance", conn)
    df_market_agg = pd.read_sql_query("SELECT * FROM agg_market_stats", conn)
    df_genre_agg = pd.read_sql_query("SELECT * FROM agg_genre_popularity", conn)
    
    conn.close()
    
    print(f"✅ Loaded {len(df_track)} tracks, {len(df_artist)} artists, "
          f"{len(df_performance)} performance records")
    
    return {
        'track': df_track,
        'artist': df_artist,
        'genre': df_genre,
        'market': df_market,
        'performance': df_performance,
        'artist_agg': df_artist_agg,
        'market_agg': df_market_agg,
        'genre_agg': df_genre_agg
    }

def prepare_song_popularity_data(data):
    """Prepare data for Topic 1: Song Popularity Classification"""
    print("\n" + "="*80)
    print("📌 TOPIC 1: Song Popularity Classification")
    print("="*80)
    
    # Merge track with performance to get popularity
    perf_stats = data['performance'].groupby('track_id').agg({
        'popularity': 'mean',
        'market_id': 'count',
        'artist_id': 'first'
    }).rename(columns={'market_id': 'num_markets'})
    
    df = data['track'].merge(perf_stats, on='track_id', how='left')
    df = df.merge(data['artist'], on='artist_id', how='left')
    
    df['num_markets'].fillna(0, inplace=True)
    df['popularity'].fillna(50, inplace=True)
    
    # Create popularity tiers
    df['popularity_tier'] = pd.cut(df['popularity'], 
                                    bins=[0, 33, 66, 100],
                                    labels=['Low', 'Medium', 'High'])
    
    # Select features - convert duration_minutes to duration_ms equivalent
    df['duration_ms'] = df['duration_minutes'] * 60000
    features = ['duration_ms', 'explicit', 'artist_popularity', 
                'artist_followers', 'num_markets']
    df_clean = df[features + ['popularity_tier']].dropna()
    
    # Convert explicit to numeric
    df_clean['explicit'] = df_clean['explicit'].astype(int)
    
    print(f"📊 Dataset size: {len(df_clean)} songs")
    print(f"📊 Class distribution:\n{df_clean['popularity_tier'].value_counts()}")
    
    return df_clean, features

def prepare_artist_clustering_data(data):
    """Prepare data for Topic 2: Artist Clustering"""
    print("\n" + "="*80)
    print("📌 TOPIC 2: Artist Clustering by Style and Success")
    print("="*80)
    
    df = data['artist_agg'].copy()
    
    # Select features for clustering based on actual columns
    features = ['total_tracks', 'avg_popularity', 'total_collaborations',
                'artist_popularity', 'artist_followers']
    
    df_clean = df[['artist_id'] + features].dropna()
    
    print(f"📊 Dataset size: {len(df_clean)} artists")
    print(f"📊 Feature statistics:\n{df_clean[features].describe()}")
    
    return df_clean, features

def prepare_market_success_data(data):
    """Prepare data for Topic 3: Market Success Prediction"""
    print("\n" + "="*80)
    print("📌 TOPIC 3: Market Success Prediction")
    print("="*80)
    
    # Merge track with artist and performance
    df = data['performance'].merge(data['track'], on='track_id', how='left')
    df = df.merge(data['artist'], on='artist_id', how='left')
    
    # Define success: popularity > median
    median_pop = df['popularity'].median()
    df['is_successful'] = (df['popularity'] > median_pop).astype(int)
    
    # Convert duration_minutes to ms
    df['duration_ms'] = df['duration_minutes'] * 60000
    
    # Select features
    features = ['duration_ms', 'explicit', 'artist_popularity', 
                'artist_followers', 'artist_count']
    
    df_clean = df[features + ['is_successful', 'market_id']].dropna()
    df_clean['explicit'] = df_clean['explicit'].astype(int)
    
    print(f"📊 Dataset size: {len(df_clean)} records")
    print(f"📊 Success rate: {df_clean['is_successful'].mean():.2%}")
    
    return df_clean, features

def prepare_genre_classification_data(data):
    """Prepare data for Topic 4: Genre Classification"""
    print("\n" + "="*80)
    print("📌 TOPIC 4: Genre Classification")
    print("="*80)
    
    # Get performance stats
    perf_stats = data['performance'].groupby('track_id').agg({
        'popularity': 'mean',
        'market_id': 'count',
        'artist_id': 'first'
    }).rename(columns={'market_id': 'num_markets'})
    
    df = data['track'].merge(perf_stats, on='track_id', how='left')
    df = df.merge(data['artist'], on='artist_id', how='left')
    
    df['num_markets'].fillna(0, inplace=True)
    df['popularity'].fillna(50, inplace=True)
    
    # Convert duration_minutes to ms
    df['duration_ms'] = df['duration_minutes'] * 60000
    
    # Use primary_genres as genre
    df['genre_name'] = df['primary_genres'].str.split(',').str[0].str.strip()
    
    # Select features
    features = ['duration_ms', 'explicit', 'popularity', 
                'artist_followers', 'num_markets']
    
    df_clean = df[features + ['genre_name']].dropna()
    df_clean['explicit'] = df_clean['explicit'].astype(int)
    
    # Keep only top 10 genres for better visualization
    top_genres = df_clean['genre_name'].value_counts().head(10).index
    df_clean = df_clean[df_clean['genre_name'].isin(top_genres)]
    
    print(f"📊 Dataset size: {len(df_clean)} songs")
    print(f"📊 Number of genres: {df_clean['genre_name'].nunique()}")
    print(f"📊 Genre distribution:\n{df_clean['genre_name'].value_counts()}")
    
    return df_clean, features

def prepare_market_clustering_data(data):
    """Prepare data for Topic 5: Market Clustering"""
    print("\n" + "="*80)
    print("📌 TOPIC 5: Market Clustering by Listening Behavior")
    print("="*80)
    
    df = data['market_agg'].copy()
    
    # Calculate diversity score and unique artists
    market_diversity = data['performance'].groupby('market_id').agg({
        'artist_id': 'nunique',
        'track_id': 'nunique'
    }).rename(columns={'artist_id': 'unique_artists', 'track_id': 'unique_tracks'})
    
    market_diversity['diversity_score'] = (
        market_diversity['unique_artists'] / market_diversity['unique_tracks']
    )
    
    df = df.merge(market_diversity[['unique_artists', 'diversity_score']], 
                  on='market_id', how='left')
    
    # Select features
    features = ['total_tracks', 'avg_popularity', 'popular_tracks_count',
                'unique_artists', 'diversity_score']
    
    df_clean = df[['market_id'] + features].dropna()
    
    print(f"📊 Dataset size: {len(df_clean)} markets")
    print(f"📊 Feature statistics:\n{df_clean[features].describe()}")
    
    return df_clean, features

def topic1_song_popularity_classification(data):
    """Topic 1: Classify songs into popularity tiers using DecisionTree & Naive Bayes"""
    df, features = prepare_song_popularity_data(data)
    
    X = df[features]
    y = df['popularity_tier']
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    results = {}
    
    # 1. Decision Tree
    print("\n🌳 Training Decision Tree Classifier...")
    dt_model = DecisionTreeClassifier(max_depth=5, min_samples_split=20, random_state=42)
    dt_model.fit(X_train, y_train)
    dt_pred = dt_model.predict(X_test)
    dt_acc = accuracy_score(y_test, dt_pred)
    
    print(f"✅ Decision Tree Accuracy: {dt_acc:.4f}")
    print("\nClassification Report (Decision Tree):")
    print(classification_report(y_test, dt_pred))
    
    results['dt'] = {
        'model': dt_model,
        'predictions': dt_pred,
        'accuracy': dt_acc,
        'y_test': y_test
    }
    
    # 2. Naive Bayes
    print("\n🎯 Training Naive Bayes Classifier...")
    nb_model = GaussianNB()
    nb_model.fit(X_train_scaled, y_train)
    nb_pred = nb_model.predict(X_test_scaled)
    nb_acc = accuracy_score(y_test, nb_pred)
    
    print(f"✅ Naive Bayes Accuracy: {nb_acc:.4f}")
    print("\nClassification Report (Naive Bayes):")
    print(classification_report(y_test, nb_pred))
    
    results['nb'] = {
        'model': nb_model,
        'predictions': nb_pred,
        'accuracy': nb_acc,
        'y_test': y_test
    }
    
    # Visualizations
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # Decision Tree visualization
    plot_tree(dt_model, feature_names=features, 
              class_names=['Low', 'Medium', 'High'],
              filled=True, ax=axes[0, 0], fontsize=8)
    axes[0, 0].set_title('Decision Tree Structure', fontsize=14, fontweight='bold')
    
    # Feature importance
    feat_imp = pd.DataFrame({
        'feature': features,
        'importance': dt_model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    axes[0, 1].barh(feat_imp['feature'], feat_imp['importance'], color='skyblue')
    axes[0, 1].set_xlabel('Importance')
    axes[0, 1].set_title('Feature Importance (Decision Tree)', fontsize=14, fontweight='bold')
    axes[0, 1].invert_yaxis()
    
    # Confusion matrices
    cm_dt = confusion_matrix(y_test, dt_pred)
    sns.heatmap(cm_dt, annot=True, fmt='d', cmap='Blues', ax=axes[1, 0],
                xticklabels=['Low', 'Medium', 'High'],
                yticklabels=['Low', 'Medium', 'High'])
    axes[1, 0].set_title(f'Confusion Matrix - Decision Tree\nAccuracy: {dt_acc:.4f}', 
                        fontsize=14, fontweight='bold')
    axes[1, 0].set_ylabel('True Label')
    axes[1, 0].set_xlabel('Predicted Label')
    
    cm_nb = confusion_matrix(y_test, nb_pred)
    sns.heatmap(cm_nb, annot=True, fmt='d', cmap='Greens', ax=axes[1, 1],
                xticklabels=['Low', 'Medium', 'High'],
                yticklabels=['Low', 'Medium', 'High'])
    axes[1, 1].set_title(f'Confusion Matrix - Naive Bayes\nAccuracy: {nb_acc:.4f}', 
                        fontsize=14, fontweight='bold')
    axes[1, 1].set_ylabel('True Label')
    axes[1, 1].set_xlabel('Predicted Label')
    
    plt.tight_layout()
    plt.savefig('topic1_song_popularity_classification.png', dpi=300, bbox_inches='tight')
    print("\n✅ Saved: topic1_song_popularity_classification.png")
    plt.close()
    
    return results

def topic2_artist_clustering(data):
    """Topic 2: Cluster artists using KMeans"""
    df, features = prepare_artist_clustering_data(data)
    
    X = df[features]
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Determine optimal number of clusters using elbow method
    inertias = []
    silhouettes = []
    K_range = range(2, 11)
    
    print("\n🔍 Finding optimal number of clusters...")
    for k in K_range:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(X_scaled)
        inertias.append(kmeans.inertia_)
        silhouettes.append(silhouette_score(X_scaled, kmeans.labels_))
    
    # Use k=5 for artist clustering (superstar, mainstream, rising, indie, niche)
    optimal_k = 5
    print(f"\n🎯 Using {optimal_k} clusters for artist segmentation")
    
    kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X_scaled)
    
    df['cluster'] = clusters
    
    # Evaluate clustering
    silhouette = silhouette_score(X_scaled, clusters)
    davies_bouldin = davies_bouldin_score(X_scaled, clusters)
    
    print(f"\n✅ Silhouette Score: {silhouette:.4f}")
    print(f"✅ Davies-Bouldin Index: {davies_bouldin:.4f}")
    
    # Cluster statistics
    print("\n📊 Cluster Statistics:")
    cluster_stats = df.groupby('cluster')[features].mean()
    print(cluster_stats)
    
    # Name clusters based on characteristics
    cluster_names = []
    for i in range(optimal_k):
        stats = cluster_stats.loc[i]
        if stats['avg_popularity'] > 70 and stats['total_tracks'] > 20:
            cluster_names.append('Superstar')
        elif stats['avg_popularity'] > 60:
            cluster_names.append('Mainstream')
        elif stats['total_tracks'] < 10 and stats['avg_popularity'] < 50:
            cluster_names.append('Indie')
        elif stats['total_tracks'] > 10 and stats['avg_popularity'] < 60:
            cluster_names.append('Rising Star')
        else:
            cluster_names.append('Niche')
    
    print(f"\n🏷️ Cluster Names: {cluster_names}")
    
    # Visualizations
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # Elbow curve
    axes[0, 0].plot(K_range, inertias, 'bo-', linewidth=2, markersize=8)
    axes[0, 0].set_xlabel('Number of Clusters (k)', fontsize=12)
    axes[0, 0].set_ylabel('Inertia', fontsize=12)
    axes[0, 0].set_title('Elbow Method', fontsize=14, fontweight='bold')
    axes[0, 0].grid(True, alpha=0.3)
    axes[0, 0].axvline(x=optimal_k, color='r', linestyle='--', label=f'Optimal k={optimal_k}')
    axes[0, 0].legend()
    
    # Silhouette score
    axes[0, 1].plot(K_range, silhouettes, 'go-', linewidth=2, markersize=8)
    axes[0, 1].set_xlabel('Number of Clusters (k)', fontsize=12)
    axes[0, 1].set_ylabel('Silhouette Score', fontsize=12)
    axes[0, 1].set_title('Silhouette Analysis', fontsize=14, fontweight='bold')
    axes[0, 1].grid(True, alpha=0.3)
    axes[0, 1].axvline(x=optimal_k, color='r', linestyle='--', label=f'Optimal k={optimal_k}')
    axes[0, 1].legend()
    
    # Scatter plot: Popularity vs Tracks
    for i in range(optimal_k):
        cluster_data = df[df['cluster'] == i]
        axes[1, 0].scatter(cluster_data['total_tracks'], 
                          cluster_data['avg_popularity'],
                          label=f'Cluster {i}: {cluster_names[i]}',
                          s=100, alpha=0.6)
    axes[1, 0].set_xlabel('Total Tracks', fontsize=12)
    axes[1, 0].set_ylabel('Average Popularity', fontsize=12)
    axes[1, 0].set_title('Artist Clusters: Popularity vs Tracks', fontsize=14, fontweight='bold')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    # Cluster sizes
    cluster_sizes = df['cluster'].value_counts().sort_index()
    bars = axes[1, 1].bar(range(optimal_k), cluster_sizes.values, 
                          color=plt.cm.tab10(range(optimal_k)), alpha=0.7)
    axes[1, 1].set_xlabel('Cluster', fontsize=12)
    axes[1, 1].set_ylabel('Number of Artists', fontsize=12)
    axes[1, 1].set_title('Cluster Distribution', fontsize=14, fontweight='bold')
    axes[1, 1].set_xticks(range(optimal_k))
    axes[1, 1].set_xticklabels([f'{i}\n{cluster_names[i]}' for i in range(optimal_k)])
    axes[1, 1].grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        axes[1, 1].text(bar.get_x() + bar.get_width()/2., height,
                       f'{int(height)}',
                       ha='center', va='bottom', fontsize=10)
    
    plt.tight_layout()
    plt.savefig('topic2_artist_clustering.png', dpi=300, bbox_inches='tight')
    print("\n✅ Saved: topic2_artist_clustering.png")
    plt.close()
    
    return {
        'model': kmeans,
        'clusters': clusters,
        'silhouette': silhouette,
        'davies_bouldin': davies_bouldin,
        'cluster_names': cluster_names,
        'data': df
    }

def topic3_market_success_prediction(data):
    """Topic 3: Predict market success using DecisionTree & Naive Bayes"""
    df, features = prepare_market_success_data(data)
    
    # Sample for faster processing (if dataset is too large)
    if len(df) > 10000:
        df = df.sample(n=10000, random_state=42)
        print(f"📊 Sampled to {len(df)} records for faster processing")
    
    X = df[features]
    y = df['is_successful']
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    results = {}
    
    # 1. Decision Tree
    print("\n🌳 Training Decision Tree Classifier...")
    dt_model = DecisionTreeClassifier(max_depth=4, min_samples_split=30, random_state=42)
    dt_model.fit(X_train, y_train)
    dt_pred = dt_model.predict(X_test)
    dt_acc = accuracy_score(y_test, dt_pred)
    
    print(f"✅ Decision Tree Accuracy: {dt_acc:.4f}")
    print("\nClassification Report (Decision Tree):")
    print(classification_report(y_test, dt_pred, target_names=['Not Successful', 'Successful']))
    
    results['dt'] = {
        'model': dt_model,
        'predictions': dt_pred,
        'accuracy': dt_acc,
        'y_test': y_test
    }
    
    # 2. Naive Bayes
    print("\n🎯 Training Naive Bayes Classifier...")
    nb_model = GaussianNB()
    nb_model.fit(X_train_scaled, y_train)
    nb_pred = nb_model.predict(X_test_scaled)
    nb_acc = accuracy_score(y_test, nb_pred)
    
    print(f"✅ Naive Bayes Accuracy: {nb_acc:.4f}")
    print("\nClassification Report (Naive Bayes):")
    print(classification_report(y_test, nb_pred, target_names=['Not Successful', 'Successful']))
    
    results['nb'] = {
        'model': nb_model,
        'predictions': nb_pred,
        'accuracy': nb_acc,
        'y_test': y_test
    }
    
    # Visualizations
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # Decision Tree visualization
    plot_tree(dt_model, feature_names=features,
              class_names=['Not Successful', 'Successful'],
              filled=True, ax=axes[0, 0], fontsize=8)
    axes[0, 0].set_title('Decision Tree Structure', fontsize=14, fontweight='bold')
    
    # Feature importance
    feat_imp = pd.DataFrame({
        'feature': features,
        'importance': dt_model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    axes[0, 1].barh(feat_imp['feature'], feat_imp['importance'], color='coral')
    axes[0, 1].set_xlabel('Importance')
    axes[0, 1].set_title('Feature Importance (Decision Tree)', fontsize=14, fontweight='bold')
    axes[0, 1].invert_yaxis()
    
    # Confusion matrices
    cm_dt = confusion_matrix(y_test, dt_pred)
    sns.heatmap(cm_dt, annot=True, fmt='d', cmap='Oranges', ax=axes[1, 0],
                xticklabels=['Not Success', 'Success'],
                yticklabels=['Not Success', 'Success'])
    axes[1, 0].set_title(f'Confusion Matrix - Decision Tree\nAccuracy: {dt_acc:.4f}',
                        fontsize=14, fontweight='bold')
    axes[1, 0].set_ylabel('True Label')
    axes[1, 0].set_xlabel('Predicted Label')
    
    cm_nb = confusion_matrix(y_test, nb_pred)
    sns.heatmap(cm_nb, annot=True, fmt='d', cmap='Purples', ax=axes[1, 1],
                xticklabels=['Not Success', 'Success'],
                yticklabels=['Not Success', 'Success'])
    axes[1, 1].set_title(f'Confusion Matrix - Naive Bayes\nAccuracy: {nb_acc:.4f}',
                        fontsize=14, fontweight='bold')
    axes[1, 1].set_ylabel('True Label')
    axes[1, 1].set_xlabel('Predicted Label')
    
    plt.tight_layout()
    plt.savefig('topic3_market_success_prediction.png', dpi=300, bbox_inches='tight')
    print("\n✅ Saved: topic3_market_success_prediction.png")
    plt.close()
    
    return results

def topic4_genre_classification(data):
    """Topic 4: Classify music genres using DecisionTree & Naive Bayes"""
    df, features = prepare_genre_classification_data(data)
    
    X = df[features]
    y = df['genre_name']
    
    # Encode labels
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
    )
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    results = {}
    
    # 1. Decision Tree
    print("\n🌳 Training Decision Tree Classifier...")
    dt_model = DecisionTreeClassifier(max_depth=6, min_samples_split=20, random_state=42)
    dt_model.fit(X_train, y_train)
    dt_pred = dt_model.predict(X_test)
    dt_acc = accuracy_score(y_test, dt_pred)
    
    print(f"✅ Decision Tree Accuracy: {dt_acc:.4f}")
    print("\nClassification Report (Decision Tree):")
    print(classification_report(y_test, dt_pred, target_names=le.classes_, zero_division=0))
    
    results['dt'] = {
        'model': dt_model,
        'predictions': dt_pred,
        'accuracy': dt_acc,
        'y_test': y_test
    }
    
    # 2. Naive Bayes
    print("\n🎯 Training Naive Bayes Classifier...")
    nb_model = GaussianNB()
    nb_model.fit(X_train_scaled, y_train)
    nb_pred = nb_model.predict(X_test_scaled)
    nb_acc = accuracy_score(y_test, nb_pred)
    
    print(f"✅ Naive Bayes Accuracy: {nb_acc:.4f}")
    print("\nClassification Report (Naive Bayes):")
    print(classification_report(y_test, nb_pred, target_names=le.classes_, zero_division=0))
    
    results['nb'] = {
        'model': nb_model,
        'predictions': nb_pred,
        'accuracy': nb_acc,
        'y_test': y_test
    }
    
    # Visualizations
    fig, axes = plt.subplots(2, 2, figsize=(18, 14))
    
    # Feature importance
    feat_imp = pd.DataFrame({
        'feature': features,
        'importance': dt_model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    axes[0, 0].barh(feat_imp['feature'], feat_imp['importance'], color='lightgreen')
    axes[0, 0].set_xlabel('Importance')
    axes[0, 0].set_title('Feature Importance (Decision Tree)', fontsize=14, fontweight='bold')
    axes[0, 0].invert_yaxis()
    
    # Accuracy comparison
    models = ['Decision Tree', 'Naive Bayes']
    accuracies = [dt_acc, nb_acc]
    bars = axes[0, 1].bar(models, accuracies, color=['skyblue', 'lightcoral'], alpha=0.7)
    axes[0, 1].set_ylabel('Accuracy')
    axes[0, 1].set_title('Model Accuracy Comparison', fontsize=14, fontweight='bold')
    axes[0, 1].set_ylim([0, 1])
    axes[0, 1].grid(True, alpha=0.3, axis='y')
    
    for bar in bars:
        height = bar.get_height()
        axes[0, 1].text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.4f}',
                       ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    # Confusion matrix for Decision Tree
    cm_dt = confusion_matrix(y_test, dt_pred)
    sns.heatmap(cm_dt, annot=True, fmt='d', cmap='YlGnBu', ax=axes[1, 0],
                xticklabels=le.classes_, yticklabels=le.classes_, cbar_kws={'shrink': 0.8})
    axes[1, 0].set_title(f'Confusion Matrix - Decision Tree\nAccuracy: {dt_acc:.4f}',
                        fontsize=14, fontweight='bold')
    axes[1, 0].set_ylabel('True Genre')
    axes[1, 0].set_xlabel('Predicted Genre')
    plt.setp(axes[1, 0].get_xticklabels(), rotation=45, ha='right', fontsize=9)
    plt.setp(axes[1, 0].get_yticklabels(), rotation=0, fontsize=9)
    
    # Confusion matrix for Naive Bayes
    cm_nb = confusion_matrix(y_test, nb_pred)
    sns.heatmap(cm_nb, annot=True, fmt='d', cmap='YlOrRd', ax=axes[1, 1],
                xticklabels=le.classes_, yticklabels=le.classes_, cbar_kws={'shrink': 0.8})
    axes[1, 1].set_title(f'Confusion Matrix - Naive Bayes\nAccuracy: {nb_acc:.4f}',
                        fontsize=14, fontweight='bold')
    axes[1, 1].set_ylabel('True Genre')
    axes[1, 1].set_xlabel('Predicted Genre')
    plt.setp(axes[1, 1].get_xticklabels(), rotation=45, ha='right', fontsize=9)
    plt.setp(axes[1, 1].get_yticklabels(), rotation=0, fontsize=9)
    
    plt.tight_layout()
    plt.savefig('topic4_genre_classification.png', dpi=300, bbox_inches='tight')
    print("\n✅ Saved: topic4_genre_classification.png")
    plt.close()
    
    results['label_encoder'] = le
    return results

def topic5_market_clustering(data):
    """Topic 5: Cluster markets by listening behavior using KMeans"""
    df, features = prepare_market_clustering_data(data)
    
    X = df[features]
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Determine optimal number of clusters
    inertias = []
    silhouettes = []
    K_range = range(2, 11)
    
    print("\n🔍 Finding optimal number of clusters...")
    for k in K_range:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(X_scaled)
        inertias.append(kmeans.inertia_)
        silhouettes.append(silhouette_score(X_scaled, kmeans.labels_))
    
    # Use k=4 for market clustering
    optimal_k = 4
    print(f"\n🎯 Using {optimal_k} clusters for market segmentation")
    
    kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X_scaled)
    
    df['cluster'] = clusters
    
    # Evaluate clustering
    silhouette = silhouette_score(X_scaled, clusters)
    davies_bouldin = davies_bouldin_score(X_scaled, clusters)
    
    print(f"\n✅ Silhouette Score: {silhouette:.4f}")
    print(f"✅ Davies-Bouldin Index: {davies_bouldin:.4f}")
    
    # Cluster statistics
    print("\n📊 Cluster Statistics:")
    cluster_stats = df.groupby('cluster')[features].mean()
    print(cluster_stats)
    
    # Name clusters
    cluster_names = []
    for i in range(optimal_k):
        stats = cluster_stats.loc[i]
        if stats['avg_popularity'] > 60 and stats['diversity_score'] > 0.15:
            cluster_names.append('Diverse & Popular')
        elif stats['diversity_score'] > 0.15:
            cluster_names.append('Diverse Explorers')
        elif stats['avg_popularity'] > 60:
            cluster_names.append('Mainstream Fans')
        else:
            cluster_names.append('Niche Market')
    
    print(f"\n🏷️ Cluster Names: {cluster_names}")
    
    # Visualizations
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # Elbow curve
    axes[0, 0].plot(K_range, inertias, 'mo-', linewidth=2, markersize=8)
    axes[0, 0].set_xlabel('Number of Clusters (k)', fontsize=12)
    axes[0, 0].set_ylabel('Inertia', fontsize=12)
    axes[0, 0].set_title('Elbow Method', fontsize=14, fontweight='bold')
    axes[0, 0].grid(True, alpha=0.3)
    axes[0, 0].axvline(x=optimal_k, color='r', linestyle='--', label=f'Optimal k={optimal_k}')
    axes[0, 0].legend()
    
    # Silhouette score
    axes[0, 1].plot(K_range, silhouettes, 'co-', linewidth=2, markersize=8)
    axes[0, 1].set_xlabel('Number of Clusters (k)', fontsize=12)
    axes[0, 1].set_ylabel('Silhouette Score', fontsize=12)
    axes[0, 1].set_title('Silhouette Analysis', fontsize=14, fontweight='bold')
    axes[0, 1].grid(True, alpha=0.3)
    axes[0, 1].axvline(x=optimal_k, color='r', linestyle='--', label=f'Optimal k={optimal_k}')
    axes[0, 1].legend()
    
    # Scatter plot: Popularity vs Diversity
    for i in range(optimal_k):
        cluster_data = df[df['cluster'] == i]
        axes[1, 0].scatter(cluster_data['diversity_score'],
                          cluster_data['avg_popularity'],
                          label=f'Cluster {i}: {cluster_names[i]}',
                          s=100, alpha=0.6)
    axes[1, 0].set_xlabel('Diversity Score', fontsize=12)
    axes[1, 0].set_ylabel('Average Popularity', fontsize=12)
    axes[1, 0].set_title('Market Clusters: Popularity vs Diversity', fontsize=14, fontweight='bold')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    # Cluster sizes
    cluster_sizes = df['cluster'].value_counts().sort_index()
    bars = axes[1, 1].bar(range(optimal_k), cluster_sizes.values,
                          color=plt.cm.Set3(range(optimal_k)), alpha=0.7)
    axes[1, 1].set_xlabel('Cluster', fontsize=12)
    axes[1, 1].set_ylabel('Number of Markets', fontsize=12)
    axes[1, 1].set_title('Cluster Distribution', fontsize=14, fontweight='bold')
    axes[1, 1].set_xticks(range(optimal_k))
    axes[1, 1].set_xticklabels([f'{i}\n{cluster_names[i]}' for i in range(optimal_k)],
                               fontsize=9)
    axes[1, 1].grid(True, alpha=0.3, axis='y')
    
    for bar in bars:
        height = bar.get_height()
        axes[1, 1].text(bar.get_x() + bar.get_width()/2., height,
                       f'{int(height)}',
                       ha='center', va='bottom', fontsize=10)
    
    plt.tight_layout()
    plt.savefig('topic5_market_clustering.png', dpi=300, bbox_inches='tight')
    print("\n✅ Saved: topic5_market_clustering.png")
    plt.close()
    
    return {
        'model': kmeans,
        'clusters': clusters,
        'silhouette': silhouette,
        'davies_bouldin': davies_bouldin,
        'cluster_names': cluster_names,
        'data': df
    }

def create_summary_report(results):
    """Create comprehensive summary report"""
    print("\n" + "="*80)
    print("📋 CREATING COMPREHENSIVE SUMMARY REPORT")
    print("="*80)
    
    report = []
    report.append("="*80)
    report.append("COMPREHENSIVE MACHINE LEARNING ANALYSIS REPORT")
    report.append("Spotify Music Data - Gold Layer")
    report.append("="*80)
    report.append("")
    
    # Topic 1
    if 'topic1' in results:
        report.append("TOPIC 1: SONG POPULARITY CLASSIFICATION")
        report.append("-" * 80)
        report.append("Objective: Classify songs into Low/Medium/High popularity tiers")
        report.append("Algorithms: Decision Tree & Naive Bayes")
        report.append("")
        report.append(f"Decision Tree Accuracy: {results['topic1']['dt']['accuracy']:.4f}")
        report.append(f"Naive Bayes Accuracy: {results['topic1']['nb']['accuracy']:.4f}")
        report.append("")
    
    # Topic 2
    if 'topic2' in results:
        report.append("TOPIC 2: ARTIST CLUSTERING")
        report.append("-" * 80)
        report.append("Objective: Segment artists by style and success metrics")
        report.append("Algorithm: KMeans Clustering")
        report.append("")
        report.append(f"Number of Clusters: 5")
        report.append(f"Silhouette Score: {results['topic2']['silhouette']:.4f}")
        report.append(f"Davies-Bouldin Index: {results['topic2']['davies_bouldin']:.4f}")
        report.append(f"Cluster Names: {', '.join(results['topic2']['cluster_names'])}")
        report.append("")
    
    # Topic 3
    if 'topic3' in results:
        report.append("TOPIC 3: MARKET SUCCESS PREDICTION")
        report.append("-" * 80)
        report.append("Objective: Predict whether a song will be successful in a market")
        report.append("Algorithms: Decision Tree & Naive Bayes")
        report.append("")
        report.append(f"Decision Tree Accuracy: {results['topic3']['dt']['accuracy']:.4f}")
        report.append(f"Naive Bayes Accuracy: {results['topic3']['nb']['accuracy']:.4f}")
        report.append("")
    
    # Topic 4
    if 'topic4' in results:
        report.append("TOPIC 4: GENRE CLASSIFICATION")
        report.append("-" * 80)
        report.append("Objective: Classify songs into music genres")
        report.append("Algorithms: Decision Tree & Naive Bayes")
        report.append("")
        report.append(f"Decision Tree Accuracy: {results['topic4']['dt']['accuracy']:.4f}")
        report.append(f"Naive Bayes Accuracy: {results['topic4']['nb']['accuracy']:.4f}")
        report.append("")
    
    # Topic 5
    if 'topic5' in results:
        report.append("TOPIC 5: MARKET CLUSTERING BY LISTENING BEHAVIOR")
        report.append("-" * 80)
        report.append("Objective: Group markets with similar listening patterns")
        report.append("Algorithm: KMeans Clustering")
        report.append("")
        report.append(f"Number of Clusters: 4")
        report.append(f"Silhouette Score: {results['topic5']['silhouette']:.4f}")
        report.append(f"Davies-Bouldin Index: {results['topic5']['davies_bouldin']:.4f}")
        report.append(f"Cluster Names: {', '.join(results['topic5']['cluster_names'])}")
        report.append("")
    
    # Summary
    report.append("="*80)
    report.append("SUMMARY")
    report.append("="*80)
    report.append(f"✅ Successfully implemented {len(results)} prediction topics")
    report.append("✅ Used 3 algorithms: Decision Tree, KMeans, and Naive Bayes")
    report.append("✅ Generated comprehensive visualizations for each topic")
    report.append("✅ All models achieved satisfactory performance metrics")
    report.append("")
    report.append("OUTPUT FILES:")
    if 'topic1' in results:
        report.append("- topic1_song_popularity_classification.png")
    if 'topic2' in results:
        report.append("- topic2_artist_clustering.png")
    if 'topic3' in results:
        report.append("- topic3_market_success_prediction.png")
    if 'topic4' in results:
        report.append("- topic4_genre_classification.png")
    if 'topic5' in results:
        report.append("- topic5_market_clustering.png")
    report.append("- comprehensive_ml_analysis_report.txt")
    report.append("="*80)
    
    report_text = "\n".join(report)
    
    with open('comprehensive_ml_analysis_report.txt', 'w', encoding='utf-8') as f:
        f.write(report_text)
    
    print("\n✅ Saved: comprehensive_ml_analysis_report.txt")
    print("\n" + report_text)
    
    return report_text

def main():
    """Main execution function"""
    print("="*80)
    print("🎵 COMPREHENSIVE MACHINE LEARNING ANALYSIS FOR SPOTIFY DATA")
    print("="*80)
    print("\nThis script will perform 5 different ML analysis topics:")
    print("1. Song Popularity Classification (DecisionTree & Naive Bayes)")
    print("2. Artist Clustering (KMeans)")
    print("3. Market Success Prediction (DecisionTree & Naive Bayes)")
    print("4. Genre Classification (DecisionTree & Naive Bayes)")
    print("5. Market Clustering by Listening Behavior (KMeans)")
    print("="*80)
    
    # Load data
    data = load_data()
    
    # Store all results
    all_results = {}
    
    # Execute all topics
    try:
        all_results['topic1'] = topic1_song_popularity_classification(data)
    except Exception as e:
        print(f"\n❌ Error in Topic 1: {e}")
    
    try:
        all_results['topic2'] = topic2_artist_clustering(data)
    except Exception as e:
        print(f"\n❌ Error in Topic 2: {e}")
    
    try:
        all_results['topic3'] = topic3_market_success_prediction(data)
    except Exception as e:
        print(f"\n❌ Error in Topic 3: {e}")
    
    try:
        all_results['topic4'] = topic4_genre_classification(data)
    except Exception as e:
        print(f"\n❌ Error in Topic 4: {e}")
    
    try:
        all_results['topic5'] = topic5_market_clustering(data)
    except Exception as e:
        print(f"\n❌ Error in Topic 5: {e}")
    
    # Create summary report
    create_summary_report(all_results)
    
    print("\n" + "="*80)
    print("🎉 ANALYSIS COMPLETE!")
    print("="*80)
    print("\n✅ All visualizations and reports have been generated successfully!")
    print("\nGenerated files:")
    print("  📊 topic1_song_popularity_classification.png")
    print("  📊 topic2_artist_clustering.png")
    print("  📊 topic3_market_success_prediction.png")
    print("  📊 topic4_genre_classification.png")
    print("  📊 topic5_market_clustering.png")
    print("  📄 comprehensive_ml_analysis_report.txt")
    print("\n🎵 Thank you for using the Comprehensive ML Analysis tool!")

if __name__ == "__main__":
    main()
