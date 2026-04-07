import os
import argparse
import pandas as pd
from src.scripts.preparation import load_flight_logs, detect_metadata_from_path
from src.scripts.data_processing import run_unified_matching

def main():
    parser = argparse.ArgumentParser(description="Unified Aircraft Noise Matching Script (Modular).")
    parser.add_argument('-p', '--peak_file', required=True, help="Path to Combined_Peak_Data.csv")
    parser.add_argument('-f', '--flight_file', help="Path to flight log (e.g. Merged_Converted_Flight_Log.xlsx)")
    parser.add_argument('-ap', '--airport', help="Airport code name (Auto-detected if not provided)")
    parser.add_argument('-m', '--model', help="Model name (Auto-detected if not provided)")
    parser.add_argument('-mode', '--mode', choices=['12m', '121', '121e'], default='121e', 
                        help="Matching mode: 12m (Candidates), 121 (Peak-1to1, Reuse allowed), 121e (Exclusive 1to1, No reuse)")
    parser.add_argument('-lw', '--lag_width', type=int, default=300, help="Max lag width in seconds")
    parser.add_argument('-o', '--output_dir', help="Output directory")
    parser.add_argument('--filter-10db', action='store_true', help="Filter peaks using '10 dB down' validation flag")

    args = parser.parse_args()

    # 1. Detect Metadata via modular preparation script
    det_model, det_airport, k_value = detect_metadata_from_path(args.peak_file)
    model_name = args.model if args.model else det_model
    airport_name = (args.airport if args.airport else det_airport).lower()

    # 2. Setup Output Directory
    default_out = os.path.join('result', 'candidate' if args.mode == '12m' else 'matching')
    output_dir = args.output_dir or default_out
    os.makedirs(output_dir, exist_ok=True)

    # 3. Load Peak Data
    if not os.path.exists(args.peak_file):
        print(f"Error: {args.peak_file} not found.")
        return
    df_peaks = pd.read_csv(args.peak_file)
    
    if args.filter_10db:
        if 'Validated_10dB' in df_peaks.columns:
            initial_count = len(df_peaks)
            df_peaks = df_peaks[df_peaks['Validated_10dB'] == True].copy()
            removed = initial_count - len(df_peaks)
            print(f"Filtering: Removed {removed} peaks that failed '10 dB down' validation. Remaining: {len(df_peaks)}")
        else:
            print("Warning: --filter-10db requested but 'Validated_10dB' column not found in peaks CSV. Skipping filter.")

    # 4. Load Flight Data via modular preparation script
    flight_file = args.flight_file
    if not flight_file:
        potential_flight_log = f'Merged_Converted_Flight_Log_{airport_name.upper()}.xlsx'
        if os.path.exists(potential_flight_log):
            flight_file = potential_flight_log
        else:
            flight_file = 'Merged_Converted_Flight_Log.xlsx'

    print(f"Loading flights from {flight_file}...")
    df_flights = load_flight_logs(flight_file)

    if df_flights.empty:
        print(f"Error: Could not load flight log from {flight_file}")
        return

    # 5. Matching via unified modular function
    print(f"Starting Unified Matching (Mode: {args.mode}, Window: +/-{args.lag_width}s)...")
    df_out = run_unified_matching(df_peaks, df_flights, mode=args.mode, lag_width=args.lag_width)

    if df_out.empty:
        print("No matches found.")
        return

    # Add metadata to results
    df_out['Airport'] = airport_name
    df_out['Model'] = model_name

    # 6. Save results
    file_map = {'12m': 'candidates', '121': 'matched_121', '121e': 'matched_121e'}
    file_prefix = file_map.get(args.mode, 'matched')
    file_tag = f"{airport_name.lower()}_{model_name}"
    output_file = os.path.join(output_dir, f'{file_prefix}_{file_tag}.csv')
    df_out.to_csv(output_file, index=False)
    
    print(f"Success! Saved {len(df_out)} results to {output_file} (Mode: {args.mode})")

if __name__ == "__main__":
    main()
