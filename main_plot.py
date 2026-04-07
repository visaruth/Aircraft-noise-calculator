import os
import argparse
import pandas as pd
import glob
from src.scripts.preparation import load_precomputed_metrics
from src.scripts.plot import run_all_standard_plots
from src.scripts.util import get_stations

def main():
    parser = argparse.ArgumentParser(
        description="Aircraft Noise Main Plot Script (Modular) - Generates 12+ types of plots from a result directory.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Model configuration (should match main.py args)
    group_model = parser.add_argument_group('Model Configuration')
    group_model.add_argument('-m', '--model', type=str, default='dbscan', choices=['dbscan', 'msa'], 
                        help="Clustering model configuration used in main.py")
    group_model.add_argument('-eps', '-esp', type=int, default=150, help="EPS for DBSCAN")
    group_model.add_argument('-min_samples', type=int, default=10, help="min_samples for DBSCAN")
    group_model.add_argument('-bandwidth', type=float, default=150.0, help="bandwidth for MSA (default: 150.0)")
    group_model.add_argument('-ap', '--airport', type=str, default='vtbs', help="Airport code (default: vtbs)")
    group_model.add_argument('--segment', '-se', action='store_true', help="Enable signal segmentation subfolder logic")
    group_model.add_argument('-K', '--K', type=int, default=100, help="Number of segments if --segment is enabled")

    # Filtering options
    group_filter = parser.add_argument_group('Station Filtering')
    group_filter.add_argument('--exclude-accuracy', type=str, nargs='*', default=['silapakorn', 'habitia_ramindra'],
                        help="Stations to exclude from Accuracy/Metric plots (Group 3, 7, 8, 9-12)")
    group_filter.add_argument('--exclude-actype', type=str, nargs='*', default=['silapakorn', 'thana_place'],
                        help="Stations to exclude from ACTYPE distribution plots (Plot 6)")
    
    # Custom Input/Output for Matching Results
    group_custom = parser.add_argument_group('Custom Matching Results')
    group_custom.add_argument('--validation_file', type=str, help="Path to a custom matched CSV (e.g., matched_121_....csv)")
    group_custom.add_argument('--output_name', type=str, default='plots', help="Name of the subfolder for plots (default: 'plots')")

    args = parser.parse_args()
    
    # Construct base directory logic
    if args.model == 'dbscan':
        subfolder_name = f"dbscan_eps_{args.eps}_min_samples_{args.min_samples}"
    else:
        bw_str = f"{args.bandwidth}".replace('.', '_')
        subfolder_name = f"msa_bandwidth_{bw_str}"
        
    if args.segment:
        subfolder_name += f"_segmented_K{args.K}"
    
    airport = args.airport.lower()
    input_base_dir = os.path.join('result', subfolder_name, airport)
    
    # Fallback if the user didn't specify segment but a segmented folder exists
    if not args.segment and not os.path.exists(input_base_dir):
        potential_folders = glob.glob(os.path.join('result', f"{subfolder_name}_segmented_K*", airport))
        if potential_folders:
            input_base_dir = potential_folders[0]
            print(f"  Note: Found segmented results folder: {input_base_dir}")
    
    if not os.path.exists(input_base_dir):
        print(f"Error: Input directory {input_base_dir} does not exist.")
        return
    
    output_plot_dir = os.path.join(input_base_dir, args.output_name)
    os.makedirs(output_plot_dir, exist_ok=True)
    
    print(f"Starting Plotting Pipeline for Airport: {airport.upper()}")
    print(f"Input Directory: {input_base_dir}")
    print(f"Output Directory: {output_plot_dir}")

    # 1. Load data via modular preparation script
    data = load_precomputed_metrics(input_base_dir)
    
    # Custom Validation override if provided
    if args.validation_file:
        if os.path.exists(args.validation_file):
            print(f"Overriding validation data with: {args.validation_file}")
            data['validation'] = pd.read_csv(args.validation_file)
            # Ensure compatibility with match_flight outputs
            if 'lag time' in data['validation'].columns:
                for lag in [80, 100, 120]:
                    data['validation'][f'Detected_{lag}s'] = 'Detected'
        else:
            print(f"Warning: Custom validation file {args.validation_file} not found. Using default.")
    
    # 2. Determine stations to include
    all_stations = get_stations(data['metrics']) if data['metrics'] is not None else []
    include_accuracy = [s for s in all_stations if s not in args.exclude_accuracy]
    include_plot6 = [s for s in all_stations if s not in args.exclude_actype]

    # 3. Run all standard plots via modular plotting script
    run_all_standard_plots(
        data=data,
        output_plot_dir=output_plot_dir,
        include_accuracy=include_accuracy,
        include_plot6=include_plot6,
        temp_dir=os.path.join(input_base_dir, 'temp_images')
    )

    print("\nPlotting Pipeline Completed Successfully.")
    print(f"All plots saved in: {output_plot_dir}")

if __name__ == "__main__":
    main()
