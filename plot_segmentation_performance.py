import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os
import argparse

def main():
    parser = argparse.ArgumentParser(description="Plot segmentation performance results from JSON log.")
    parser.add_argument('-f', '--file', '--input_file', dest='input_file', default=os.path.join('result', 'execution_times.json'),
                        help="Input JSON file containing execution times and metrics (default: result/execution_times.json)")
    parser.add_argument('-o', '--output_dir', default=os.path.join('result', 'comparison'),
                        help="Directory where output plots will be saved (default: result/comparison)")
    parser.add_argument('-ap', '--airport', help="Filter by airport code (e.g. vtbs)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_file):
        print(f"Error: File {args.input_file} not found.")
        return

    # Load data
    with open(args.input_file, 'r') as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)
    
    if df.empty:
        print("Error: JSON file is empty.")
        return

    # 1. Filter by airport if specified
    if args.airport:
        airport_code = args.airport.lower()
        if 'airport' in df.columns:
            df = df[df['airport'].str.lower() == airport_code]
            if df.empty:
                print(f"Warning: No data found for airport '{airport_code}'. Available: {df['airport'].unique() if 'airport' in df.columns else 'None'}")
                return

    # 2. Handle missing model field for backward compatibility
    if 'model' not in df.columns:
        df['model'] = 'dbscan'
    else:
        df['model'] = df['model'].fillna('dbscan')
        
    # 3. Deduplicate: Keep only the latest run for each (airport, model, station, segment_used, K)
    # This ensures that if we rerun the same configuration, only the newest results are shown.
    if not df.empty:
        # Create a helper key for K to handle the segment_used=False case consistently
        df['segment_flag'] = df['segment_used'].astype(str)
        df['K_val'] = df['K'].fillna(0).astype(int)
        
        # Sort by index (usually chronological) and keep last
        df = df.sort_index().drop_duplicates(subset=['airport', 'model', 'station', 'segment_flag', 'K_val'], keep='last')

    # Prepare data for plotting
    # We treat segment_used=False as K=0 to show it as the baseline/starting point
    df['K_plot'] = df.apply(lambda row: 0 if not row['segment_used'] else int(row['K']), axis=1)
    df['Model_Station'] = df['model'].astype(str).str.upper() + " (" + df['station'].astype(str) + ")"
    
    # Sort by Model_Station and K_plot for correct line drawing
    df = df.sort_values(by=['Model_Station', 'K_plot'])
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Metrics to plot
    metrics = {
        'precision': 'Precision vs K (0=Original)',
        'recall': 'Recall vs K (0=Original)',
        'f1': 'F1-Score vs K (0=Original)',
        'duration_sec': 'Duration (sec) vs K (0=Original)'
    }

    sns.set_theme(style="whitegrid")
    plt.rcParams['font.family'] = 'sans-serif'

    # Create a 2x2 subplot figure
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    axes = axes.flatten()

    for i, (col, title) in enumerate(metrics.items()):
        ax = axes[i]
        
        # Plot lines (including K=0 baseline)
        sns.lineplot(data=df, x='K_plot', y=col, hue='Model_Station', marker='o', ax=ax, palette='viridis')
        
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel('K (0 = Original non-segmented)', fontsize=12)
        ax.set_ylabel(col.capitalize(), fontsize=12)
        
        # Shrink current axis by 20% for legend
        if i == 1 or i == 3: # Put legend only for some to avoid clutter, or handle separately
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0., title='Station', fontsize='small')
        else:
            ax.get_legend().remove()

    plt.tight_layout()
    output_path = os.path.join(args.output_dir, 'segmentation_performance_comparison.pdf')
    plt.savefig(output_path, bbox_inches='tight')
    print(f"Combined performance plot saved to: {output_path}")

    # Also save separate plots for clarity
    for col, title in metrics.items():
        plt.figure(figsize=(10, 6))
        sns.lineplot(data=df, x='K_plot', y=col, hue='Model_Station', marker='o', palette='tab10')
        plt.title(title, fontsize=14, fontweight='bold')
        plt.xlabel('K (0 = Original non-segmented)', fontsize=12)
        plt.ylabel(col.capitalize(), fontsize=12)
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', title='Station')
        plt.grid(True, linestyle='--', alpha=0.7)
        
        sep_path = os.path.join(args.output_dir, f'plot_K_vs_{col}.pdf')
        plt.savefig(sep_path, bbox_inches='tight')
        plt.close()
        print(f"Individual plot saved to: {sep_path}")

if __name__ == "__main__":
    main()
