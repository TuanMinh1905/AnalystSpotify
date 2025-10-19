"""
Script để vẽ lược đồ quan hệ (ERD) của Gold Layer
Hiển thị các bảng Dimension, Fact và Aggregate với các mối quan hệ
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.lines as mlines

# Định nghĩa schema cho các bảng
TABLE_SCHEMAS = {
    'dim_track': [
        ('track_id', 'STRING'),
        ('track_name', 'STRING'),
        ('duration_ms', 'BIGINT'),
        ('explicit', 'BOOLEAN'),
        ('is_collaboration', 'BOOLEAN'),
        ('popularity', 'BIGINT'),
        ('primary_genres', 'STRING'),
    ],
    'dim_artist': [
        ('artist_id', 'STRING'),
        ('artist_name', 'STRING'),
        ('artist_popularity', 'BIGINT'),
        ('artist_followers', 'BIGINT'),
        ('primary_genres', 'STRING'),
    ],
    'dim_album': [
        ('album_id', 'STRING'),
        ('album_name', 'STRING'),
        ('album_type', 'STRING'),
        ('release_date', 'DATE'),
        ('total_tracks', 'BIGINT'),
    ],
    'dim_market': [
        ('market_id', 'STRING'),
        ('market_code', 'STRING'),
    ],
    'dim_genre': [
        ('genre_id', 'BIGINT'),
        ('genre_name', 'STRING'),
    ],
    'dim_date': [
        ('date_id', 'STRING'),
        ('date', 'DATE'),
        ('year', 'INT'),
        ('month', 'INT'),
        ('day', 'INT'),
        ('quarter', 'INT'),
    ],
    'fact_track_performance': [
        ('track_id', 'STRING'),
        ('artist_id', 'STRING'),
        ('album_id', 'STRING'),
        ('market_id', 'STRING'),
        ('date_id', 'STRING'),
        ('popularity', 'BIGINT'),
        ('artist_count', 'BIGINT'),
        ('artist_followers', 'BIGINT'),
        ('total_appearances', 'BIGINT'),
        ('total_markets', 'BIGINT'),
    ],
    'agg_artist_performance': [
        ('artist_id', 'STRING'),
        ('artist_name', 'STRING'),
        ('total_tracks', 'BIGINT'),
        ('avg_popularity', 'DOUBLE'),
        ('max_popularity', 'BIGINT'),
        ('total_collaborations', 'BIGINT'),
        ('artist_followers', 'BIGINT'),
        ('primary_genres', 'STRING'),
    ],
    'agg_market_stats': [
        ('market_id', 'STRING'),
        ('market_code', 'STRING'),
        ('total_tracks', 'BIGINT'),
        ('avg_popularity', 'DOUBLE'),
        ('unique_artists', 'BIGINT'),
        ('market_rank', 'BIGINT'),
    ],
    'agg_genre_popularity': [
        ('genre_id', 'BIGINT'),
        ('genre_name', 'STRING'),
        ('total_tracks', 'BIGINT'),
        ('avg_popularity', 'DOUBLE'),
        ('genre_rank', 'BIGINT'),
    ],
}

def get_table_info(table_name):
    """Lấy thông tin cột của bảng từ schema đã định nghĩa"""
    return TABLE_SCHEMAS.get(table_name, [])

def draw_erd():
    """Vẽ ERD diagram cho Gold layer"""
    
    # Định nghĩa các bảng và vị trí
    tables = {
        # Dimension Tables (màu xanh dương)
        'dim_track': {'pos': (1, 8), 'color': '#E3F2FD', 'type': 'dimension'},
        'dim_artist': {'pos': (1, 6), 'color': '#E3F2FD', 'type': 'dimension'},
        'dim_album': {'pos': (1, 4), 'color': '#E3F2FD', 'type': 'dimension'},
        'dim_market': {'pos': (1, 2), 'color': '#E3F2FD', 'type': 'dimension'},
        'dim_genre': {'pos': (1, 0), 'color': '#E3F2FD', 'type': 'dimension'},
        'dim_date': {'pos': (5, 8), 'color': '#E3F2FD', 'type': 'dimension'},
        
        # Fact Table (màu đỏ)
        'fact_track_performance': {'pos': (5, 5), 'color': '#FFEBEE', 'type': 'fact'},
        
        # Aggregate Tables (màu xanh lá)
        'agg_artist_performance': {'pos': (9, 7), 'color': '#E8F5E9', 'type': 'aggregate'},
        'agg_market_stats': {'pos': (9, 5), 'color': '#E8F5E9', 'type': 'aggregate'},
        'agg_genre_popularity': {'pos': (9, 3), 'color': '#E8F5E9', 'type': 'aggregate'},
    }
    
    # Định nghĩa relationships
    relationships = [
        # Fact table relationships
        ('dim_track', 'fact_track_performance', 'track_id'),
        ('dim_artist', 'fact_track_performance', 'artist_id'),
        ('dim_album', 'fact_track_performance', 'album_id'),
        ('dim_market', 'fact_track_performance', 'market_id'),
        ('dim_date', 'fact_track_performance', 'date_id'),
        
        # Aggregate relationships
        ('fact_track_performance', 'agg_artist_performance', 'artist_id'),
        ('fact_track_performance', 'agg_market_stats', 'market_id'),
        ('fact_track_performance', 'agg_genre_popularity', 'genre'),
    ]
    
    # Tạo figure
    fig, ax = plt.subplots(figsize=(16, 12))
    ax.set_xlim(0, 12)
    ax.set_ylim(-1, 10)
    ax.axis('off')
    
    # Vẽ các bảng
    box_width = 2.2
    box_height_per_row = 0.2
    
    for table_name, info in tables.items():
        x, y = info['pos']
        color = info['color']
        table_type = info['type']
        
        # Lấy thông tin cột
        columns = get_table_info(table_name)
        
        # Tính chiều cao của box dựa trên số cột
        box_height = 0.4 + len(columns) * box_height_per_row
        
        # Vẽ box cho bảng
        if table_type == 'dimension':
            linewidth = 2
            edgecolor = '#1976D2'
        elif table_type == 'fact':
            linewidth = 3
            edgecolor = '#C62828'
        else:  # aggregate
            linewidth = 2
            edgecolor = '#388E3C'
        
        box = FancyBboxPatch((x, y), box_width, box_height,
                            boxstyle="round,pad=0.05",
                            facecolor=color,
                            edgecolor=edgecolor,
                            linewidth=linewidth,
                            zorder=2)
        ax.add_patch(box)
        
        # Vẽ header của bảng
        header_height = 0.3
        header = FancyBboxPatch((x, y + box_height - header_height), box_width, header_height,
                               boxstyle="round,pad=0.05",
                               facecolor=edgecolor,
                               edgecolor=edgecolor,
                               linewidth=linewidth,
                               zorder=3)
        ax.add_patch(header)
        
        # Tên bảng
        display_name = table_name.replace('_', '_\n') if len(table_name) > 15 else table_name
        ax.text(x + box_width/2, y + box_height - header_height/2,
               display_name,
               fontsize=9, fontweight='bold', ha='center', va='center',
               color='white', zorder=4)
        
        # Vẽ các cột
        y_offset = y + box_height - header_height - 0.15
        for col_name, col_type in columns[:8]:  # Chỉ hiển thị 8 cột đầu
            # Đánh dấu primary key
            if 'id' in col_name.lower() and col_name.endswith('_id'):
                col_text = f"🔑 {col_name}"
                fontweight = 'bold'
            else:
                col_text = f"   {col_name}"
                fontweight = 'normal'
            
            ax.text(x + 0.1, y_offset,
                   col_text,
                   fontsize=7, ha='left', va='center',
                   fontweight=fontweight,
                   zorder=4)
            y_offset -= box_height_per_row
        
        if len(columns) > 8:
            ax.text(x + 0.1, y_offset,
                   f"   ... (+{len(columns) - 8} more)",
                   fontsize=7, ha='left', va='center',
                   style='italic', color='gray',
                   zorder=4)
    
    # Vẽ các mối quan hệ
    for source, target, key in relationships:
        source_pos = tables[source]['pos']
        target_pos = tables[target]['pos']
        
        # Tính toán điểm bắt đầu và kết thúc
        source_x = source_pos[0] + box_width
        source_y = source_pos[1] + 0.3
        target_x = target_pos[0]
        target_y = target_pos[1] + 0.3
        
        # Màu sắc mũi tên dựa trên loại relationship
        if 'agg_' in target:
            arrow_color = '#388E3C'
            linestyle = 'dashed'
            alpha = 0.6
        else:
            arrow_color = '#C62828'
            linestyle = 'solid'
            alpha = 0.7
        
        # Vẽ mũi tên
        arrow = FancyArrowPatch((source_x, source_y), (target_x, target_y),
                               arrowstyle='->,head_width=0.3,head_length=0.3',
                               color=arrow_color,
                               linewidth=1.5,
                               linestyle=linestyle,
                               alpha=alpha,
                               zorder=1,
                               connectionstyle="arc3,rad=0.1")
        ax.add_patch(arrow)
        
        # Label cho relationship
        mid_x = (source_x + target_x) / 2
        mid_y = (source_y + target_y) / 2
        ax.text(mid_x, mid_y, key,
               fontsize=6, ha='center', va='bottom',
               bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                        edgecolor='gray', alpha=0.8),
               zorder=5)
    
    # Legend
    legend_elements = [
        mpatches.Patch(facecolor='#E3F2FD', edgecolor='#1976D2', linewidth=2, label='Dimension Tables'),
        mpatches.Patch(facecolor='#FFEBEE', edgecolor='#C62828', linewidth=3, label='Fact Table'),
        mpatches.Patch(facecolor='#E8F5E9', edgecolor='#388E3C', linewidth=2, label='Aggregate Tables'),
        mlines.Line2D([], [], color='#C62828', linestyle='solid', linewidth=1.5, label='Fact Relationships'),
        mlines.Line2D([], [], color='#388E3C', linestyle='dashed', linewidth=1.5, label='Aggregate Relationships'),
    ]
    ax.legend(handles=legend_elements, loc='lower center', ncol=5, fontsize=10,
             bbox_to_anchor=(0.5, -0.05), frameon=True, fancybox=True, shadow=True)
    
    plt.tight_layout()
    plt.savefig('gold_layer_erd.png', dpi=300, bbox_inches='tight', facecolor='white')
    print("✅ ERD diagram saved as: gold_layer_erd.png")
    
    print("\n✅ ERD Generation Complete!")

if __name__ == "__main__":
    print("="*80)
    print("🎨 GENERATING GOLD LAYER ERD DIAGRAM")
    print("="*80)
    draw_erd()
