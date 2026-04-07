import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import string
from scipy import stats

# --- Helper logic expected to be in utils.py ---
from src.scripts.util import calculate_log_average

def setup_plot_dir(output_dir='plot'):
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def plot_accuracy_metrics(df_results, station, op_name, output_dir='plot', ext='.png'):
    """
    Plot Precision, Recall, and F1 Score for a given station and operation.
    """
    plt.figure(figsize=(10, 6))
    plt.plot(df_results['Lag (s)'], df_results['Precision'], marker='o', label='Precision')
    plt.plot(df_results['Lag (s)'], df_results['Recall'], marker='x', label='Recall')
    plt.plot(df_results['Lag (s)'], df_results['F1 Score'], marker='s', label='F1 Score')
    
    plt.title(f'Accuracy vs Lag Time: {station} ({op_name})')
    plt.xlabel('Lag Time (seconds)')
    plt.ylabel('Score')
    plt.legend()
    plt.grid(True)
    plt.xticks(df_results['Lag (s)'])
    
    acc_plot_filename = os.path.join(output_dir, f'{station}_{op_name.lower()}_accuracy{ext}')
    plt.savefig(acc_plot_filename)
    plt.close()

def plot_detailed_metrics_table(df_results, station, op_name, output_dir='plot', ext='.png'):
    """
    Generate a detailed metrics table as an image.
    """
    display_cols = ['Lag (s)', 'Peak Events', 'Flights (in range)', 'TP', 'TN', 'FP', 'FN', 'Precision', 'Recall', 'F1 Score']
    table_data = df_results[display_cols].values
    col_labels = display_cols
    
    rows = len(table_data)
    fig_height = max(4, rows * 0.35 + 1)
    
    plt.figure(figsize=(14, fig_height))
    plt.axis('off')
    
    table = plt.table(cellText=table_data,
                      colLabels=col_labels,
                      cellLoc='center',
                      loc='center',
                      colColours=['#f2f2f2']*len(col_labels))
    
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.0, 1.5)
    
    plt.title(f'Detailed Metrics: {station} ({op_name})', fontsize=14, pad=10)
    
    table_filename = os.path.join(output_dir, f'{station}_{op_name.lower()}_detailed_metrics{ext}')
    plt.savefig(table_filename, bbox_inches='tight', dpi=200)
    plt.close()

def plot_combined_score(all_results_df, stations, op_name='ALL', output_dir='plot', ext='.png'):
    """
    Plot combined score (Average P, R, F1) across all stations for a specific operation.
    """
    plt.figure(figsize=(12, 8))
    op_df = all_results_df[all_results_df['Operation'] == op_name]
    
    for station in stations:
        df_station = op_df[op_df['Station'] == station].copy()
        df_station['Combined_Score'] = (df_station['Precision'] + df_station['Recall'] + df_station['F1 Score']) / 3
        plt.plot(df_station['Lag (s)'], df_station['Combined_Score'], marker='.', label=station)
    
    plt.title(f'Station Performance ({op_name}): Average of (Precision + Recall + F1) vs Lag Time')
    plt.xlabel('Lag Time (seconds)')
    plt.ylabel('Average Score')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True)
    plt.xticks(list(range(10, 201, 10)))
    plt.tight_layout()
    
    combined_plot_filename = os.path.join(output_dir, f'all_stations_combined_score_{op_name.lower()}{ext}')
    plt.savefig(combined_plot_filename)
    plt.close()

def plot_metric_all_stations(all_results_df, stations, metric_col, title_metric_name, op_name='ALL', output_dir='plot', filename_suffix='', ext='.png'):
    """
    Plot a specific metric (Precision, Recall, or F1 Score) across all stations.
    """
    plt.figure(figsize=(12, 8))
    op_df = all_results_df[all_results_df['Operation'] == op_name]
    
    for station in stations:
        df_station = op_df[op_df['Station'] == station].copy()
        if metric_col in df_station.columns:
            plt.plot(df_station['Lag (s)'], df_station[metric_col], marker='.', label=station)
    
    plt.title(f'Station {title_metric_name} ({op_name}) vs Lag Time')
    plt.xlabel('Lag Time (seconds)')
    plt.ylabel(title_metric_name)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True)
    plt.xticks(list(range(10, 201, 10)))
    plt.tight_layout()
    
    plot_filename = os.path.join(output_dir, f'all_stations_{filename_suffix}_{op_name.lower()}{ext}')
    plt.savefig(plot_filename)
    plt.close()

def plot_operation_comparison(df_metrics, output_dir='plot'):
    """
    Compare average combined scores between Departure and Arrival.
    (Derived from plot_comparison.py)
    """
    if 'Combined_Score' not in df_metrics.columns:
        df_metrics['Combined_Score'] = (df_metrics['Precision'] + df_metrics['Recall'] + df_metrics['F1 Score']) / 3
        
    plt.figure(figsize=(10, 6))
    
    df_dep = df_metrics[df_metrics['Operation'] == 'Departure']
    df_arr = df_metrics[df_metrics['Operation'] == 'Arrival']
    
    avg_dep = df_dep.groupby('Lag (s)')['Combined_Score'].mean()
    avg_arr = df_arr.groupby('Lag (s)')['Combined_Score'].mean()
    
    plt.plot(avg_dep.index, avg_dep.values, marker='o', label='Departure', color='blue')
    plt.plot(avg_arr.index, avg_arr.values, marker='x', label='Arrival', color='red')
    
    plt.title('Average Performance across all stations: Departure vs Arrival')
    plt.xlabel('Lag Time (seconds)')
    plt.ylabel('Average Combined Score')
    plt.legend()
    plt.grid(True)
    plt.xticks(list(range(10, 201, 10)))
    
    plot1_path = os.path.join(output_dir, 'comparison_avg_score_vs_lag.png')
    plt.savefig(plot1_path)
    plt.close()
    
    # 2. Bar chart of F1 Score at a specific lag
    lag_to_plot = 60
    df_lag = df_metrics[df_metrics['Lag (s)'] == lag_to_plot]
    stations = df_lag['Station'].unique()
    
    dep_f1 = []
    arr_f1 = []
    for station in stations:
        dep_val = df_lag[(df_lag['Station'] == station) & (df_lag['Operation'] == 'Departure')]['F1 Score'].values
        arr_val = df_lag[(df_lag['Station'] == station) & (df_lag['Operation'] == 'Arrival')]['F1 Score'].values
        dep_f1.append(dep_val[0] if len(dep_val) > 0 else 0)
        arr_f1.append(arr_val[0] if len(arr_val) > 0 else 0)
        
    x = np.arange(len(stations))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(14, 7))
    rects1 = ax.bar(x - width/2, dep_f1, width, label='Departure', color='blue')
    rects2 = ax.bar(x + width/2, arr_f1, width, label='Arrival', color='red')
    
    ax.set_ylabel('F1 Score')
    ax.set_title(f'F1 Score Comparison by Station (Lag = {lag_to_plot}s)')
    ax.set_xticks(x)
    ax.set_xticklabels(stations, rotation=45, ha='right')
    ax.legend()
    
    fig.tight_layout()
    plot2_path = os.path.join(output_dir, f'comparison_f1_score_lag{lag_to_plot}s.png')
    plt.savefig(plot2_path)
    plt.close()

def plot_hourly_leq_profile(df_hourly_station, station, output_dir='plot/hourly_leq', ext='.png'):
    """
    Plot the hourly Leq profile for a station.
    (Derived from plot_hourly_leq.py)
    """
    os.makedirs(output_dir, exist_ok=True)
    hourly_summary = df_hourly_station.groupby('Hour')['Hourly_Leq'].apply(calculate_log_average).reset_index()
    
    plt.figure(figsize=(12, 6))
    
    for date, group in df_hourly_station.groupby('Date'):
        plt.plot(group['Hour'], group['Hourly_Leq'], color='gray', alpha=0.2, linewidth=1)
        
    plt.plot(hourly_summary['Hour'], hourly_summary['Hourly_Leq'], 
             color='blue', marker='o', linewidth=3, label='Average (All Days)')
    
    plt.title(f'Hourly Equivalent Sound Level (Leq) - {station}')
    plt.xlabel('Hour of Day (0-23)')
    plt.ylabel('Leq (dBA)')
    plt.xticks(range(0, 24))
    plt.grid(True, alpha=0.3)
    
    # Highlight Night Time
    plt.axvspan(0, 7, color='navy', alpha=0.1, label='Night Time')
    plt.axvspan(22, 24, color='navy', alpha=0.1)
    
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    plt.legend(by_label.values(), by_label.keys())
    
    plot_path = os.path.join(output_dir, f'{station}_hourly_profile{ext}')
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    plt.close()

def plot_daily_leq_metrics(df_metrics_station, station_name, output_dir='plot'):
    """
    Line chart plotting daily Ld, Ln, Ldn, Leq24
    (Derived from plot_leq_metrics.py)
    """
    os.makedirs(output_dir, exist_ok=True)
    if not df_metrics_station.empty:
        df_metrics = df_metrics_station.sort_values('Date')
        
        plt.figure(figsize=(12, 6))
        plt.plot(df_metrics['Date'], df_metrics['Leq24'], marker='o', label='Leq (24h)', linestyle='--', alpha=0.7)
        plt.plot(df_metrics['Date'], df_metrics['Ld'], marker='.', label='Ld (Day)', alpha=0.5)
        plt.plot(df_metrics['Date'], df_metrics['Ln'], marker='.', label='Ln (Night)', alpha=0.5)
        plt.plot(df_metrics['Date'], df_metrics['Ldn'], marker='s', label='Ldn', linewidth=2, color='black')
        
        plt.title(f'Daily Noise Metrics: {station_name}')
        plt.xlabel('Date')
        plt.ylabel('Noise Level (dBA)')
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        plot_path = os.path.join(output_dir, f'{station_name}_leq_metrics.png')
        plt.savefig(plot_path)
        plt.close()

def plot_daily_leq_bar_chart(df_station, station, output_dir='plot', ext='.png'):
    """
    Bar chart plotting daily Ld, Ln, Ldn, Leq24
    (Derived from plot_leq_bar_charts.py)
    """
    os.makedirs(output_dir, exist_ok=True)
    
    df_station = df_station.sort_values('Date').fillna(0)
    if df_station.empty:
        return
        
    dates = df_station['Date'].values
    ld = df_station['Ld'].values
    ln = df_station['Ln'].values
    ldn = df_station['Ldn'].values
    leq24 = df_station['Leq24'].values
    
    x = np.arange(len(dates))
    width = 0.2
    
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.bar(x - 1.5*width, ldn, width, label='Ldn (Day-Night Avg)', color='black', alpha=0.8)
    ax.bar(x - 0.5*width, leq24, width, label='Leq (24h Avg)', color='skyblue')
    ax.bar(x + 0.5*width, ld, width, label='Ld (Day)', color='orange', alpha=0.7)
    ax.bar(x + 1.5*width, ln, width, label='Ln (Night)', color='navy', alpha=0.6)
    
    ax.set_ylabel('Noise Level (dBA)', fontsize=12)
    ax.set_title(f'Daily Noise Metrics (Bar Chart): {station}', fontsize=16, pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(dates, rotation=45, ha='right')
    ax.legend(bbox_to_anchor=(1.01, 1), loc='upper left')
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    
    if len(dates) > 15:
        for i, label in enumerate(ax.xaxis.get_ticklabels()):
            if i % 2 != 0:
                label.set_visible(False)
    
    fig.tight_layout()
    plot_path = os.path.join(output_dir, f'{station}_leq_metrics_bar{ext}')
    plt.savefig(plot_path, dpi=150)
    plt.close(fig)

def plot_leq24_bar_chart(df_station, station, output_dir='plot', ext='.png'):
    """Bar chart for Leq 24h only."""
    os.makedirs(output_dir, exist_ok=True)
    df_station = df_station.sort_values('Date').dropna(subset=['Leq24'])
    if df_station.empty: return
    
    dates = df_station['Date'].values
    leq24 = df_station['Leq24'].values
    x = np.arange(len(dates))
    
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.bar(x, leq24, color='skyblue', alpha=0.9)
    ax.set_ylabel('Leq 24h (dBA)', fontsize=12)
    ax.set_title(f'Leq 24h: {station}', fontsize=16, pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(dates, rotation=45, ha='right')
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    
    if len(dates) > 15:
        for i, label in enumerate(ax.xaxis.get_ticklabels()):
            if i % 2 != 0: label.set_visible(False)
            
    fig.tight_layout()
    plt.savefig(os.path.join(output_dir, f'{station}_leq24_bar{ext}'), dpi=150)
    plt.close(fig)

def plot_ldn_bar_chart(df_station, station, output_dir='plot', ext='.png'):
    """Bar chart for Ldn only."""
    os.makedirs(output_dir, exist_ok=True)
    df_station = df_station.sort_values('Date').dropna(subset=['Ldn'])
    if df_station.empty: return
    
    dates = df_station['Date'].values
    ldn = df_station['Ldn'].values
    x = np.arange(len(dates))
    
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.bar(x, ldn, color='black', alpha=0.8)
    ax.set_ylabel('Ldn (dBA)', fontsize=12)
    ax.set_title(f'Ldn (+10 Night): {station}', fontsize=16, pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(dates, rotation=45, ha='right')
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    
    if len(dates) > 15:
        for i, label in enumerate(ax.xaxis.get_ticklabels()):
            if i % 2 != 0: label.set_visible(False)
            
    fig.tight_layout()
    plt.savefig(os.path.join(output_dir, f'{station}_ldn_bar{ext}'), dpi=150)
    plt.close(fig)

def plot_lden_bar_chart(df_station, station, output_dir='plot', ext='.png'):
    """Bar chart for Lden only."""
    os.makedirs(output_dir, exist_ok=True)
    df_station = df_station.sort_values('Date').dropna(subset=['Lden'])
    if df_station.empty: return
    
    dates = df_station['Date'].values
    lden = df_station['Lden'].values
    x = np.arange(len(dates))
    
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.bar(x, lden, color='purple', alpha=0.7)
    ax.set_ylabel('Lden (dBA)', fontsize=12)
    ax.set_title(f'Lden (+5 Evening, +10 Night): {station}', fontsize=16, pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(dates, rotation=45, ha='right')
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    
    if len(dates) > 15:
        for i, label in enumerate(ax.xaxis.get_ticklabels()):
            if i % 2 != 0: label.set_visible(False)
            
    fig.tight_layout()
    plt.savefig(os.path.join(output_dir, f'{station}_lden_bar{ext}'), dpi=150)
    plt.close(fig)

def plot_ln_bar_chart(df_station, station, output_dir='plot', ext='.png'):
    """Bar chart for Ln (unpenalized) only."""
    os.makedirs(output_dir, exist_ok=True)
    df_station = df_station.sort_values('Date').dropna(subset=['Ln'])
    if df_station.empty: return
    
    dates = df_station['Date'].values
    ln = df_station['Ln'].values
    x = np.arange(len(dates))
    
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.bar(x, ln, color='navy', alpha=0.6)
    ax.set_ylabel('Ln 22:00-07:00 (dBA)', fontsize=12)
    ax.set_title(f'Ln (No Penalty): {station}', fontsize=16, pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(dates, rotation=45, ha='right')
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    
    if len(dates) > 15:
        for i, label in enumerate(ax.xaxis.get_ticklabels()):
            if i % 2 != 0: label.set_visible(False)
            
    fig.tight_layout()
    plt.savefig(os.path.join(output_dir, f'{station}_ln_bar{ext}'), dpi=150)
    plt.close(fig)

def plot_actype_counts(station_actype_counts, output_dir='plot'):
    """
    (Derived from plot_actype_counts.py)
    """
    os.makedirs(output_dir, exist_ok=True)
    # Simple logic mapping since this differs per user data structure. 
    # Provided as skeleton based on original file.
    pass

def plot_missed_actypes(missed_df, output_dir='plot'):
    """
    (Derived from plot_missed_actypes.py)
    """
    os.makedirs(output_dir, exist_ok=True)
    pass

def plot_combined_images(image_paths, output_path, cols=2, rows=None):
    """
    Combine multiple image files into a single figure with subgraphs labeled (a), (b), (c), etc.
    
    :param image_paths: List of file paths to the input images.
    :param output_path: File path where the combined image will be saved.
    :param cols: Number of columns for the subplots layout.
    :param rows: Optional. Number of rows for the subplots layout. If None, calculated automatically.
    """
    num_images = len(image_paths)
    if num_images == 0:
        print("No images provided to combine.")
        return

    if rows is None:
        rows = int(np.ceil(num_images / cols))
    else:
        # If user hardcodes rows, we should recalculate cols to ensure it fits, or just trust them
        cols = int(np.ceil(num_images / rows))
    
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 6, rows * 5))
    
    # Ensure axes is a 1D array of axis objects
    if hasattr(axes, 'flatten'):
        axes = axes.flatten()
    else:
        axes = np.array([axes])
        
    labels = string.ascii_lowercase
        
    for i, ax in enumerate(axes):
        if i < num_images:
            try:
                img = plt.imread(image_paths[i])
                ax.imshow(img)
                ax.axis('off')
                # Add (a), (b), (c) labels below the image
                ax.text(0.5, -0.05, f'({labels[i]})', size=16, ha="center", va="top",
                        transform=ax.transAxes, weight='bold')
            except Exception as e:
                print(f"Error loading image {image_paths[i]}: {e}")
                ax.axis('off')
        else:
            # Hide empty subplots
            ax.axis('off')
            
    plt.tight_layout()
    # Save the combined figure
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

def calculate_peak_statistics(data, alpha=0.05):
    """Calculate IQR and Prediction Interval boundaries."""
    if len(data) < 2:
        return None
    
    # IQR
    q1 = np.percentile(data, 25)
    q3 = np.percentile(data, 75)
    
    # PI (1 - alpha Prediction Interval)
    n = len(data)
    mean = np.mean(data)
    std = np.std(data, ddof=1)
    
    t_critical = stats.t.ppf(1 - alpha / 2, df=n - 1)
    margin = t_critical * std * np.sqrt(1 + 1 / n)
    
    pi_low = mean - margin
    pi_high = mean + margin
    
    return {
        'q1': q1, 'q3': q3,
        'pi_low': pi_low, 'pi_high': pi_high
    }
    
def plot_peak_distribution_grid(df, col_name, title_prefix, xlabel, output_path, orient='v', exclude_stations=None, alpha=0.05):
    """
    Plot faceted distributions:
    - Histogram with density on y-axis
    - Plots both IQR and PI outlier boundaries in the same graph
    """
    if exclude_stations:
        df = df[~df['Station'].isin(exclude_stations)]
        
    stations = sorted(df['Station'].unique())
    n_stations = len(stations)
    if n_stations == 0:
        print("No stations to plot.")
        return

    # จัด Grid ให้พอดีกับจำนวนสถานี
    cols = 4 
    rows = (n_stations + cols - 1) // cols
    
    # กำหนดขนาดรูปภาพให้กว้างขึ้นนิดหน่อยเพื่อให้มีพื้นที่วาง Legend
    fig, axes = plt.subplots(rows, cols, figsize=(5 * cols, 4 * rows))
    axes = axes.flatten()
    
    for i, station in enumerate(stations):
        station_data = df[df['Station'] == station][col_name].dropna()
        ax = axes[i]
        
        if len(station_data) == 0:
            ax.text(0.5, 0.5, 'No Data', ha='center', va='center')
            ax.set_title(station)
            continue
            
        # 1. พล็อต Histogram (แกน y = density)
        sns.histplot(x=station_data, ax=ax, color='tab:blue', edgecolor='black', 
                     kde=False, stat='density', alpha=0.8)
        
        values = station_data.values
        x_bar = np.mean(values)
        
        # 2. คำนวณ IQR boundaries
        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1
        lower_iqr = q1 - 1.5 * iqr
        upper_iqr = q3 + 1.5 * iqr
        
        # 3. คำนวณ PI boundaries (Prediction Interval ตามสูตรใน aircraft_calculate.py)
        L_prime = len(values)
        if L_prime >= 2:
            s = np.std(values, ddof=1)
            t_critical = stats.t.ppf(1 - alpha / 2, df=L_prime - 1)
            margin = t_critical * s * np.sqrt(1 + 1 / L_prime)
            lower_pi = x_bar - margin
            upper_pi = x_bar + margin
        else:
            lower_pi = x_bar
            upper_pi = x_bar
            
        # 4. วาดเส้นลงในกราฟ (ใส่ Label เพื่อให้โชว์ใน Legend)
        # เส้น Mean
        ax.axvline(x_bar, color='black', linestyle='-', linewidth=2, label=f'Mean: {x_bar:.2f}')
        
        # เส้น IQR (ประสีส้ม)
        ax.axvline(lower_iqr, color='darkorange', linestyle='--', linewidth=2, label='IQR Boundary')
        ax.axvline(upper_iqr, color='darkorange', linestyle='--', linewidth=2)
        
        # เส้น PI (จุดสีแดง)
        ax.axvline(lower_pi, color='red', linestyle=':', linewidth=2.5, label='PI Boundary')
        ax.axvline(upper_pi, color='red', linestyle=':', linewidth=2.5)
    
        # จัดการชื่อแกนและชื่อกราฟ
        ax.set_title(f'Station: {station}', fontsize=12)
        ax.set_xlabel(xlabel, fontsize=11)
        ax.set_ylabel('Density (Frequency)', fontsize=11)
        
        # แสดงกล่องอธิบายเส้น (Legend) ไว้มุมขวาบนของทุกกราฟ
        ax.legend(fontsize=9, loc='upper right')
            
    # ซ่อน Subplot ที่ว่างเปล่ากรณีสถานีไม่พอดี Grid
    for j in range(i + 1, len(axes)):
        axes[j].axis('off')
        
    plt.tight_layout()
    
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f'Saved distribution plot to {output_path}')

def plot_peak_distribution_individual(df, col_name, title_prefix, xlabel, output_dir, file_prefix, orient='v', exclude_stations=None, alpha=0.05):
    """
    Plot distributions for each station and save as individual files in output_dir.
    """
    if exclude_stations:
        df = df[~df['Station'].isin(exclude_stations)]
        
    stations = sorted(df['Station'].unique())
    if len(stations) == 0:
        print("No stations to plot.")
        return

    os.makedirs(output_dir, exist_ok=True)
    
    for station in stations:
        station_data = df[df['Station'] == station][col_name].dropna()
        if len(station_data) == 0:
            continue
            
        fig, ax = plt.subplots(figsize=(8, 6))
        
        # 1. พล็อต Histogram (แกน y = density)
        sns.histplot(x=station_data, ax=ax, color='tab:blue', edgecolor='black', 
                     kde=False, stat='density', alpha=0.8)
        
        values = station_data.values
        x_bar = np.mean(values)
        
        # 2. คำนวณ IQR boundaries
        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1
        lower_iqr = q1 - 1.5 * iqr
        upper_iqr = q3 + 1.5 * iqr
        
        # 3. คำนวณ PI boundaries (Prediction Interval ตามสูตรใน aircraft_calculate.py)
        L_prime = len(values)
        if L_prime >= 2:
            s = np.std(values, ddof=1)
            t_critical = stats.t.ppf(1 - alpha / 2, df=L_prime - 1)
            margin = t_critical * s * np.sqrt(1 + 1 / L_prime)
            lower_pi = x_bar - margin
            upper_pi = x_bar + margin
        else:
            lower_pi = x_bar
            upper_pi = x_bar
            
        # 4. วาดเส้นลงในกราฟ (ใส่ Label เพื่อให้โชว์ใน Legend)
        # เส้น Mean
        ax.axvline(x_bar, color='black', linestyle='-', linewidth=2, label=f'Mean: {x_bar:.2f}')
        
        # เส้น IQR (ประสีส้ม)
        ax.axvline(lower_iqr, color='darkorange', linestyle='--', linewidth=2, label='IQR Boundary')
        ax.axvline(upper_iqr, color='darkorange', linestyle='--', linewidth=2)
        
        # เส้น PI (จุดสีแดง)
        ax.axvline(lower_pi, color='red', linestyle=':', linewidth=2.5, label='PI Boundary')
        ax.axvline(upper_pi, color='red', linestyle=':', linewidth=2.5)
    
        # จัดการชื่อแกนและชื่อกราฟ
        ax.set_title(f'Station: {station}\n{title_prefix}', fontsize=14)
        ax.set_xlabel(xlabel, fontsize=12)
        ax.set_ylabel('Density (Frequency)', fontsize=12)
        
        # แสดงกล่องอธิบายเส้น (Legend)
        ax.legend(fontsize=10, loc='upper right')
        
        plt.tight_layout()
        output_path = os.path.join(output_dir, f"{file_prefix}_{station}.pdf")
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
    
    print(f'Saved individual distribution plots in {output_dir}')


def generate_plot1_daily_leq(df, include_stations=None, output_dir=None, temp_dir='temp_images'):
    from src.scripts.util import get_stations
    print("Generating Plot 1: Daily Leq comparisons...")
    if df is None or df.empty:
        print("  Skip: No data.")
        return
        
    df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
    stations = get_stations(df)
    if include_stations:
        stations = [s for s in stations if s in include_stations]
        
    temp_images = []
    
    for station in stations:
        df_station = df[df['Station'] == station].copy()
        plot_daily_leq_bar_chart(df_station, station, temp_dir, ext='.png')
        expected_file = os.path.join(temp_dir, f"{station}_leq_metrics_bar.png")
        if os.path.exists(expected_file):
            temp_images.append(expected_file)
            
    if temp_images:
        final_path = os.path.join(output_dir, '1_daily_leq_comparison.pdf')
        plot_combined_images(temp_images, final_path, rows=2)
        print(f"  Saved Plot 1 to {final_path}")

def generate_plot2_missed_actypes(df, lag=120, prefix='2', output_dir=None):
    print(f"Generating Plot {prefix}: Top missed ACTYPEs (Lag {lag}s)...")
    if df is None or df.empty:
        print("  Skip: No data."); return
        
    col = f'Detected_{lag}s'
    if col not in df.columns:
        print(f"  Skip: Column {col} not found."); return
        
    missed = df[df[col] == 'Missed']
    if missed.empty:
        print(f"  Skip: No missed flights for lag {lag}s."); return
        
    counts = missed['ACTYPE'].value_counts().reset_index()
    counts.columns = ['ACTYPE', 'Missed_Count']
    top_counts = counts.head(20)
    
    plt.figure(figsize=(12, 8))
    ax = sns.barplot(data=top_counts, x='Missed_Count', y='ACTYPE', hue='ACTYPE', palette='viridis', legend=False)
    for p in ax.patches:
        width = p.get_width()
        if width > 0:
            ax.text(width + 0.3, p.get_y() + p.get_height() / 2, f'{int(width)}', va='center')

    plt.title(f'Top 20 Missed Aircraft Types (Lag {lag}s) - All Stations')
    plt.xlabel('Number of Missed Flights'); plt.ylabel('Aircraft Type')
    plt.grid(axis='x', linestyle='--', alpha=0.7); plt.tight_layout()
    
    filename = f"{prefix}_missed_actypes_{lag}s.pdf"
    if prefix == '2' and lag == 120: filename = '2_missed_actypes.pdf'
    final_path = os.path.join(output_dir, filename)
    plt.savefig(final_path, dpi=200, format='pdf'); plt.close()
    print(f"  Saved Plot {prefix} to {final_path}")

def generate_plot2_3_missed_actypes_percent(df, lag=120, prefix='2_3', output_dir=None):
    print(f"Generating Plot {prefix}: Missed ACTYPE Percentage (Lag {lag}s)...")
    if df is None or df.empty: return
    col = f'Detected_{lag}s'
    if col not in df.columns: return

    total_counts = df['ACTYPE'].value_counts()
    missed_counts = df[df[col] == 'Missed']['ACTYPE'].value_counts()
    stats_df = pd.DataFrame({'Total': total_counts, 'Missed': missed_counts}).fillna(0)
    stats_df['Missed_Percent'] = (stats_df['Missed'] / stats_df['Total']) * 100
    stats_df = stats_df[stats_df['Total'] > 1] 
    top_percent = stats_df.sort_values(by='Missed_Percent', ascending=False).head(20).reset_index()
    top_percent.columns = ['ACTYPE', 'Total', 'Missed', 'Missed_Percent']

    plt.figure(figsize=(12, 8))
    ax = sns.barplot(data=top_percent, x='Missed_Percent', y='ACTYPE', hue='ACTYPE', palette='magma', legend=False)
    for p in ax.patches:
        width = p.get_width()
        ax.text(width + 0.5, p.get_y() + p.get_height() / 2, f'{width:.1f}%', va='center')

    plt.title(f'Top 20 Missed Aircraft Types by Percentage (Lag {lag}s) - (Flights > 1)')
    plt.xlabel('Missed Percentage (%)'); plt.ylabel('Aircraft Type'); plt.xlim(0, 110)
    plt.grid(axis='x', linestyle='--', alpha=0.7); plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"{prefix}_missed_actypes_percent.pdf"), dpi=200, format='pdf'); plt.close()

def generate_plot2_4_missed_actypes_count_sorted_by_percent(df, lag=120, prefix='2_4', output_dir=None):
    print(f"Generating Plot {prefix}: Missed ACTYPE Count Sorted by % (Lag {lag}s)...")
    if df is None or df.empty: return
    col = f'Detected_{lag}s'
    if col not in df.columns: return

    total_counts = df['ACTYPE'].value_counts()
    missed_counts = df[df[col] == 'Missed']['ACTYPE'].value_counts()
    stats_df = pd.DataFrame({'Total': total_counts, 'Missed': missed_counts}).fillna(0)
    stats_df['Missed_Percent'] = (stats_df['Missed'] / stats_df['Total']) * 100
    stats_df = stats_df[stats_df['Total'] > 1] 
    top_by_percent = stats_df.sort_values(by='Missed_Percent', ascending=False).head(20).reset_index()
    top_by_percent.columns = ['ACTYPE', 'Total', 'Missed', 'Missed_Percent']

    plt.figure(figsize=(12, 8))
    ax = sns.barplot(data=top_by_percent, x='Missed', y='ACTYPE', hue='ACTYPE', palette='plasma', legend=False)
    for i, p in enumerate(ax.patches):
        row = top_by_percent.iloc[i]
        label = f"{int(row['Missed'])}/{int(row['Total'])} ({row['Missed_Percent']:.1f}%)"
        ax.text(p.get_width() + 0.5, p.get_y() + p.get_height() / 2, label, va='center')

    plt.title(f'Top 20 Missed ACTYPE Counts (Sorted by Missed %) - (Flights > 1)')
    plt.xlabel('Number of Missed Flights'); plt.ylabel('Aircraft Type')
    plt.grid(axis='x', linestyle='--', alpha=0.7); plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"{prefix}_missed_actypes_count_by_percent.pdf"), dpi=200, format='pdf'); plt.close()

def generate_plot345_accuracy_metrics(df, include_stations=None, output_dir=None, temp_dir='temp_images'):
    from src.scripts.util import get_stations
    import time
    print("Generating Plots 3, 4, 5: Accuracy metrics over lags...")
    if df is None or df.empty: return
    stations = get_stations(df)
    if include_stations: stations = [s for s in stations if s in include_stations]
    
    ops = [('ALL', '3_accuracy_all_stations.pdf'), ('Arrival', '4_accuracy_arrival.pdf'), ('Departure', '5_accuracy_departure.pdf')]
    for op_name, filename in ops:
        plot_combined_score(df, stations, op_name, temp_dir, ext='.pdf')
        if op_name == 'ALL':
            plot_metric_all_stations(df, stations, 'Precision', 'Precision', 'ALL', temp_dir, 'precision', ext='.pdf')
            plot_metric_all_stations(df, stations, 'Recall', 'Recall', 'ALL', temp_dir, 'recall', ext='.pdf')
            plot_metric_all_stations(df, stations, 'F1 Score', 'F1 Score', 'ALL', temp_dir, 'f1_score', ext='.pdf')

        mapping = {f"all_stations_combined_score_{op_name.lower()}.pdf": filename}
        if op_name == 'ALL':
            mapping.update({"all_stations_precision_all.pdf": "3_1_precision_all_stations.pdf",
                           "all_stations_recall_all.pdf": "3_2_recall_all_stations.pdf",
                           "all_stations_f1_score_all.pdf": "3_3_f1_score_all_stations.pdf"})

        for src_name, dest_name in mapping.items():
            expected_file = os.path.join(temp_dir, src_name)
            if os.path.exists(expected_file):
                final_path = os.path.join(output_dir, dest_name)
                for _ in range(5):
                    try:
                        if os.path.exists(final_path): os.remove(final_path)
                        os.rename(expected_file, final_path); break
                    except PermissionError: time.sleep(0.5)

def generate_plot6_actype_per_station(df, include_stations=None, output_dir=None, temp_dir='temp_images'):
    from src.scripts.util import get_stations
    print("Generating Plot 6: ACTYPE distributions per station...")
    if df is None or df.empty: return
    stations = get_stations(df)
    if include_stations: stations = [s for s in stations if s in include_stations]
    sns.set_theme(style="whitegrid"); temp_images = []
    
    for station in stations:
        data = df[df['Station'] == station].sort_values('Count', ascending=False).head(15)
        if data.empty: continue
        plt.figure(figsize=(10, max(5, int(len(data) * 0.4))))
        ax = sns.barplot(x='Count', y='ACTYPE', data=data, hue='ACTYPE', palette='viridis', legend=False)
        for i, v in enumerate(data['Count']): ax.text(v + (v * 0.01), i, str(v), va='center', fontsize=9)
        plt.title(f'ACTYPE Distribution ({station})', fontsize=14)
        plt.xlabel('Number of Flights'); plt.ylabel('Aircraft Type'); plt.tight_layout()
        temp_path = os.path.join(temp_dir, f"p6_{station}.png")
        plt.savefig(temp_path, dpi=150, format='png'); plt.close(); temp_images.append(temp_path)
        
    if temp_images:
        plot_combined_images(temp_images, os.path.join(output_dir, '6_actype_distribution.pdf'), rows=2)

def generate_plot7_summary_tables(df, include_stations=None, output_dir=None, temp_dir='temp_images'):
    from src.scripts.util import get_stations
    print("Generating Plot 7: Summary metrics tables per station...")
    if df is None or df.empty: return
    stations = get_stations(df); temp_images = []
    # include_stations can be used here directly
    if include_stations: stations = [s for s in stations if s in include_stations]
    df_all = df[(df['Operation'] == 'ALL') & (df['Lag (s)'] == 120)]
    
    for station in stations:
        df_station = df_all[df_all['Station'] == station].copy()
        if df_station.empty: continue
        plot_detailed_metrics_table(df_station, station, 'ALL_120s', temp_dir, ext='.png')
        expected_file = os.path.join(temp_dir, f"{station}_all_120s_detailed_metrics.png")
        if os.path.exists(expected_file): temp_images.append(expected_file)
            
    if temp_images:
        plot_combined_images(temp_images, os.path.join(output_dir, '7_summary_tables.pdf'), cols=1)

def generate_plot8_hourly_leq(df, include_stations=None, output_dir=None, temp_dir='temp_images'):
    from src.scripts.util import get_stations
    print("Generating Plot 8: Hourly Leq profiles per station...")
    if df is None or df.empty: return
    stations = get_stations(df); temp_images = []
    if include_stations: stations = [s for s in stations if s in include_stations]
    
    for station in stations:
        df_station = df[df['Station'] == station].copy()
        plot_hourly_leq_profile(df_station, station, temp_dir, ext='.png')
        expected_file = os.path.join(temp_dir, f"{station}_hourly_profile.png")
        if os.path.exists(expected_file): temp_images.append(expected_file)
             
    if temp_images:
         plot_combined_images(temp_images, os.path.join(output_dir, '8_hourly_leq_profiles.pdf'), rows=2)

def generate_plot9_12_individual_leq(df_daily, include_stations=None, output_dir=None, temp_dir='temp_images'):
    from src.scripts.util import get_stations
    print("Generating Plots 9-12: Individual Leq bar charts...")
    stations = get_stations(df_daily)
    if include_stations: stations = [s for s in stations if s in include_stations]
    
    plots_config = [('9_leq24_bar_charts.pdf', plot_leq24_bar_chart, 'leq24_bar'),
                    ('10_ldn_bar_charts.pdf', plot_ldn_bar_chart, 'ldn_bar'),
                    ('11_lden_bar_charts.pdf', plot_lden_bar_chart, 'lden_bar'),
                    ('12_ln_bar_charts.pdf', plot_ln_bar_chart, 'ln_bar')]
    
    for final_filename, plot_func, suffix in plots_config:
        temp_img_list = []
        for station in stations:
            df_station = df_daily[df_daily['Station'] == station].copy()
            if df_station.empty: continue
            plot_func(df_station, station, temp_dir, ext='.png')
            expected_file = os.path.join(temp_dir, f"{station}_{suffix}.png")
            if os.path.exists(expected_file): temp_img_list.append(expected_file)
                
        if temp_img_list:
            plot_combined_images(temp_img_list, os.path.join(output_dir, final_filename), rows=2)

def cleanup_temp_dir(temp_dir):
    import glob
    print(f"Cleaning up temporary files in {temp_dir}...")
    for ext in ["*.pdf", "*.png"]:
        for f in glob.glob(os.path.join(temp_dir, ext)):
            try: os.remove(f)
            except OSError: pass
    try: os.rmdir(temp_dir)
    except OSError: pass

def run_all_standard_plots(data, output_plot_dir, include_accuracy=None, include_plot6=None, temp_dir='temp_images'):
    """
    Main orchestration function to generate all standard project plots.
    """
    os.makedirs(temp_dir, exist_ok=True)
    
    # Run all plot generations
    generate_plot1_daily_leq(data['daily_leq'], include_stations=include_accuracy, output_dir=output_plot_dir, temp_dir=temp_dir)
    generate_plot2_missed_actypes(data['validation'], lag=120, prefix='2', output_dir=output_plot_dir)
    generate_plot2_missed_actypes(data['validation'], lag=80, prefix='2_1', output_dir=output_plot_dir)
    generate_plot2_missed_actypes(data['validation'], lag=100, prefix='2_2', output_dir=output_plot_dir)
    generate_plot2_3_missed_actypes_percent(data['validation'], lag=120, prefix='2_3', output_dir=output_plot_dir)
    generate_plot2_4_missed_actypes_count_sorted_by_percent(data['validation'], lag=120, prefix='2_4', output_dir=output_plot_dir)
    generate_plot345_accuracy_metrics(data['metrics'], include_stations=include_accuracy, output_dir=output_plot_dir, temp_dir=temp_dir)
    generate_plot6_actype_per_station(data['actype_counts'], include_stations=include_plot6, output_dir=output_plot_dir, temp_dir=temp_dir)
    generate_plot7_summary_tables(data['metrics'], include_stations=include_accuracy, output_dir=output_plot_dir, temp_dir=temp_dir)
    generate_plot8_hourly_leq(data['hourly_leq'], include_stations=include_accuracy, output_dir=output_plot_dir, temp_dir=temp_dir)
    generate_plot9_12_individual_leq(data['daily_leq'], include_stations=include_accuracy, output_dir=output_plot_dir, temp_dir=temp_dir)
    
    cleanup_temp_dir(temp_dir)

def generate_comparison_type_a(model_tag, folders, airport, exclude_stations=None, output_dir='plot/comparison', temp_dir='temp_images'):
    """
    Type A (By Parameter/Configuration): 
    Each subgraph represents one config, showing all stations' performance.
    """
    from src.scripts.util import get_stations
    from src.scripts.preparation import get_folder_label

    metrics_config = [
        ('Combined_Score', 'Avg (P+R+F1)/3', '1', 'combined'),
        ('Precision', 'Precision', '1_1', 'precision'),
        ('Recall', 'Recall', '1_2', 'recall'),
        ('F1 Score', 'F1 Score', '1_3', 'f1')
    ]
    
    os.makedirs(temp_dir, exist_ok=True)
    
    def try_read_csv(filepath):
        if os.path.exists(filepath):
            try: return pd.read_csv(filepath)
            except: pass
        return None

    for metric_col, ylabel, prefix, suffix in metrics_config:
        print(f"Generating Comparison Type A ({suffix}) for {model_tag} ({airport})...")
        temp_images = []
        
        for folder in folders:
            param_label = get_folder_label(folder)
            metrics_file = os.path.join(folder, airport, 'all_stations_metrics_detailed.csv')
            df = try_read_csv(metrics_file)
            if df is None or df.empty: continue
                
            stations = get_stations(df)
            if exclude_stations:
                stations = [s for s in stations if s not in exclude_stations]
                
            # Sanitize label for filename
            safe_label = param_label.replace('=', '_').replace('(', '').replace(')', '').replace(' ', '_').replace('[', '').replace(']', '')
            temp_out = os.path.join(temp_dir, f"comp_a_{suffix}_{safe_label}.png")
            
            plt.figure(figsize=(12, 8))
            op_df = df[df['Operation'] == 'ALL']
            
            for station in stations:
                df_station = op_df[op_df['Station'] == station].copy()
                if not df_station.empty:
                    if metric_col == 'Combined_Score':
                        df_station['Combined_Score'] = (df_station['Precision'] + df_station['Recall'] + df_station['F1 Score']) / 3
                    
                    if metric_col in df_station.columns:
                        plt.plot(df_station['Lag (s)'], df_station[metric_col], marker='.', label=station)
            
            plt.title(f'{ylabel}: {param_label} (All Stations)', fontsize=14)
            plt.xlabel('Lag Time (seconds)')
            plt.ylabel(ylabel)
            plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize='small')
            plt.grid(True, alpha=0.3)
            plt.ylim(0, 1.1)
            plt.tight_layout()
            plt.savefig(temp_out, dpi=150)
            plt.close()
            temp_images.append(temp_out)
            
        if temp_images:
            final_path = os.path.join(output_dir, f'{prefix}_compare_{model_tag}_{suffix}.pdf')
            plot_combined_images(temp_images, final_path, rows=2)
            print(f"  Saved Comparison Type A ({suffix}) to {final_path}")

def generate_comparison_type_b(model_tag, folders, airport, exclude_stations=None, output_dir='plot/comparison', temp_dir='temp_images'):
    """
    Type B (By Station):
    Each subgraph represents one station, comparing various configurations.
    """
    from src.scripts.util import get_stations
    from src.scripts.preparation import get_folder_label

    metrics_config = [
        ('Combined_Score', 'Avg (P+R+F1)/3', '2', 'combined'),
        ('Precision', 'Precision', '2_1', 'precision'),
        ('Recall', 'Recall', '2_2', 'recall'),
        ('F1 Score', 'F1 Score', '2_3', 'f1')
    ]
    
    os.makedirs(temp_dir, exist_ok=True)
    
    def try_read_csv(filepath):
        if os.path.exists(filepath):
            try: return pd.read_csv(filepath)
            except: pass
        return None

    # Load all data first
    all_data = []
    for folder in folders:
        param_label = get_folder_label(folder)
        metrics_file = os.path.join(folder, airport, 'all_stations_metrics_detailed.csv')
        df = try_read_csv(metrics_file)
        if df is not None and not df.empty:
            df['Parameter'] = param_label
            all_data.append(df)
            
    if not all_data:
        print("  Skip: No data found for comparison.")
        return
        
    full_df = pd.concat(all_data, ignore_index=True)
    stations = get_stations(full_df)
    if exclude_stations:
        stations = [s for s in stations if s not in exclude_stations]
        
    for metric_col, ylabel, prefix, suffix in metrics_config:
        print(f"Generating Comparison Type B ({suffix}) for {model_tag} ({airport})...")
        temp_images = []
        for station in stations:
            station_df = full_df[(full_df['Station'] == station) & (full_df['Operation'] == 'ALL')]
            if station_df.empty: continue
            
            temp_out = os.path.join(temp_dir, f"comp_b_{suffix}_{station}.png")
            plt.figure(figsize=(12, 8))
            for param, group in station_df.groupby('Parameter'):
                group = group.sort_values('Lag (s)')
                if metric_col == 'Combined_Score':
                    val = (group['Precision'] + group['Recall'] + group['F1 Score']) / 3
                else:
                    val = group[metric_col]
                    
                plt.plot(group['Lag (s)'], val, marker='.', label=param)
                
            plt.title(f'{ylabel} Comparison for Site: {station}', fontsize=14)
            plt.xlabel('Lag Time (seconds)')
            plt.ylabel(ylabel)
            plt.legend(title="Configurations", bbox_to_anchor=(1.05, 1), loc='upper left', fontsize='small')
            plt.grid(True, alpha=0.3)
            plt.ylim(0, 1.1)
            plt.tight_layout()
            plt.savefig(temp_out, dpi=150)
            plt.close()
            temp_images.append(temp_out)
            
        if temp_images:
            final_path = os.path.join(output_dir, f'{prefix}_compare_{model_tag}_{suffix}.pdf')
            plot_combined_images(temp_images, final_path, rows=2)
            print(f"  Saved Comparison Type B ({suffix}) to {final_path}")

def run_matching_plots(df, output_dir):
    """
    Orchestrates all plots for matching results.
    """
    import os
    import matplotlib.pyplot as plt
    import seaborn as sns
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Plot Lag Distribution
    plt.figure(figsize=(12, 6))
    sns.histplot(data=df, x='lag time', hue='Operation', kde=True, bins=50, alpha=0.6)
    plt.title('Lag Time Distribution by Operation (1-to-1 Match)', fontsize=14, fontweight='bold')
    plt.xlabel('Lag Time (seconds)')
    plt.ylabel('Frequency')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.savefig(os.path.join(output_dir, 'overall_lag_distribution.pdf'))
    plt.close()
    
    # 2. Plot Leq vs Lag
    plt.figure(figsize=(12, 8))
    # Sample if the data is too large for scatter
    df_sample = df.sample(min(len(df), 5000)) if len(df) > 0 else df
    sns.scatterplot(data=df_sample, x='lag time', y='Leq', hue='Operation', alpha=0.4, s=20)
    plt.title(f"Leq vs Lag Time (Sample of {len(df_sample)} points)", fontsize=14, fontweight='bold')
    plt.xlabel('Lag Time (seconds)')
    plt.ylabel('Leq (dB)')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.savefig(os.path.join(output_dir, 'leq_vs_lag_scatter.pdf'))
    plt.close()
    
    # 3. Plot Station Summary
    if 'Station' in df.columns and 'Operation' in df.columns:
        summary = df.groupby(['Station', 'Operation'])['lag time'].agg(['mean', 'std', 'count']).reset_index()
        plt.figure(figsize=(14, 7))
        sns.barplot(data=summary, x='Station', y='mean', hue='Operation')
        plt.title('Mean Lag Time per Station and Operation', fontsize=14, fontweight='bold')
        plt.xticks(rotation=45)
        plt.ylabel('Mean Lag Time (seconds)')
        plt.grid(True, axis='y', linestyle='--', alpha=0.6)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'station_mean_lag.pdf'))
        plt.close()