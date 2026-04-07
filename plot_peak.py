import pandas as pd
import os
import sys
import argparse

# Add current directory to path to ensure src can be imported
sys.path.append(os.getcwd())
from src.scripts.plot import plot_peak_distribution_grid, plot_peak_distribution_individual
def parse_metadata_from_path(path):
    """
    Extract model/setup and airport from the file path.
    Example path: result/dbscan_eps_150_min_samples_10/vtbs/Combined_Peak_Data.csv
    Returns: ('dbscan_eps_150_min_samples_10', 'vtbs')
    """
    # Normalize path separators
    normalized_path = os.path.normpath(path)
    parts = normalized_path.split(os.sep)
    
    model = "unknown_model"
    airport = "unknown"
    
    if "result" in parts:
        idx = parts.index("result")
        if idx + 1 < len(parts):
            model = parts[idx + 1]
        if idx + 2 < len(parts):
            airport = parts[idx + 2]
    elif "output" in parts:
        idx = parts.index("output")
        if idx + 1 < len(parts):
            airport = parts[idx + 1]
    
    return model, airport

def main():
    parser = argparse.ArgumentParser(description="Plot Peak Distribution (Duration and Leq) across all stations.")
    parser.add_argument("-i", "--input", type=str, 
                        default=r"result\dbscan_eps_150_min_samples_10\vtbs\Combined_Peak_Data.csv",
                        help="Path to Combined_Peak_Data.csv")
    parser.add_argument("-o", "--output", type=str, default="plot",
                        help="Base output directory for plots (default: 'plot')")
    parser.add_argument("--orient", type=str, choices=['v', 'h'], default='v',
                        help="Orientation of the bars: 'v' (vertical) or 'h' (horizontal)")
    parser.add_argument("--exclude", nargs='*', default=[],
                        help="List of stations to exclude from the plot (space separated names)")
    parser.add_argument("--raw", action="store_true", help="Plot the raw/unfiltered peak data instead if available.")
    parser.add_argument("--separate", action="store_true", help="Plot distributions separately for each station.")
    
    args = parser.parse_args()
    data_path = args.input
    
    if args.raw and 'Combined_Peak_Data.csv' in data_path:
        raw_path = data_path.replace('Combined_Peak_Data.csv', 'Combined_Peak_Data_Unfiltered.csv')
        if os.path.exists(raw_path):
            data_path = raw_path
            print(f"Using RAW unfiltered peak data: {data_path}")
        else:
            print(f"Warning: --raw requested but {raw_path} not found. Falling back to filtered data.")
            
    if not os.path.exists(data_path):
        print(f"Error: {data_path} not found.")
        return

    # Metadata extraction
    model, airport = parse_metadata_from_path(data_path)
    print(f"Detected Model: {model}, Airport: {airport.upper()}")
    
    # Construct output directory: plot/<model>/<airport>/
    output_dir = os.path.join(args.output, model, airport)
    os.makedirs(output_dir, exist_ok=True)

    print(f"Loading data from {data_path}...")
    df = pd.read_csv(data_path)
    
    # Clean station names if they contain paths (e.g. 'output\peak_data_StationName')
    if 'Station' in df.columns:
        df['Station'] = df['Station'].apply(lambda x: os.path.basename(x).replace('peak_data_', '') if isinstance(x, str) else x)

    # Orientation suffix
    suffix = "_horiz" if args.orient == 'h' else ""
    if args.raw or 'Unfiltered' in data_path:
        suffix += "_raw"

    plot_func = plot_peak_distribution_individual if args.separate else plot_peak_distribution_grid
    
    # Group 1: Duration (interval) -> PDF
    if 'interval' in df.columns:
        # Filter duration outliers for visualization clarity
        df_duration = df[df['interval'] < 300].copy()
        
        if args.separate:
            dur_out_dir = os.path.join(output_dir, "duration")
            plot_func(
                df_duration, 'interval', f'Peak Duration ({airport.upper()})', 'Duration (seconds)', 
                dur_out_dir, f'peak_dur_{airport}_{model}{suffix}', orient=args.orient, exclude_stations=args.exclude
            )
        else:
            filename = f'peak_duration_distribution_{airport}_{model}{suffix}.pdf'
            duration_pdf = os.path.join(output_dir, filename)
            plot_func(
                df_duration, 'interval', f'Peak Duration Distribution ({airport.upper()})', 'Duration (seconds)', 
                duration_pdf, orient=args.orient, exclude_stations=args.exclude
            )
    
    # Group 2: Leq -> PDF
    if 'Leq' in df.columns:
        if args.separate:
            leq_out_dir = os.path.join(output_dir, "leq")
            plot_func(
                df, 'Leq', f'Peak Leq ({airport.upper()})', 'Leq (dBA)', 
                leq_out_dir, f'peak_leq_{airport}_{model}{suffix}', orient=args.orient, exclude_stations=args.exclude
            )
        else:
            filename = f'peak_leq_distribution_{airport}_{model}{suffix}.pdf'
            leq_pdf = os.path.join(output_dir, filename)
            plot_func(
                df, 'Leq', f'Peak Leq Distribution ({airport.upper()})', 'Leq (dBA)', 
                leq_pdf, orient=args.orient, exclude_stations=args.exclude
            )

if __name__ == "__main__":
    main()
