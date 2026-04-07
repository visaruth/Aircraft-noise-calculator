import pandas as pd
import os
import argparse
from src.scripts.preparation import load_flight_logs, detect_metadata_from_path
from src.scripts.data_processing import find_candidate_flights

def main():
    parser = argparse.ArgumentParser(description="Find candidate flight matches for noise peaks based on time lag (Modular).")
    parser.add_argument('-p', '--peak_file', required=True, help="Path to Combined_Peak_Data.csv")
    parser.add_argument('-f', '--flight_file', help="Path to flight log (e.g. Merged_Converted_Flight_Log.xlsx)")
    parser.add_argument('-ap', '--airport', help="Airport code name (Auto-detected if not provided)")
    parser.add_argument('-m', '--model', help="Model name (Auto-detected if not provided)")
    parser.add_argument('-lw', '--lag_width', type=int, default=300, help="Max lag width in seconds (default: 300)")
    parser.add_argument('-o', '--output_dir', default=os.path.join('result', 'candidate'), help="Output directory")

    args = parser.parse_args()

    # 1. Detect Metadata via modular preparation script
    det_model, det_airport, k_value = detect_metadata_from_path(args.peak_file)
    model_name = args.model if args.model else det_model
    airport_name = (args.airport if args.airport else det_airport).lower()

    # 2. Load Peak Data
    if not os.path.exists(args.peak_file):
        print(f"Error: Peak file {args.peak_file} not found.")
        return
    
    print(f"Loading peaks from {args.peak_file}...")
    df_peaks = pd.read_csv(args.peak_file)
    
    # 3. Load Flight Data via modular preparation script
    flight_file = args.flight_file
    if not flight_file:
        # Try airport-specific name
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

    # 4. Finding Candidates via modular data processing script
    print(f"Searching for candidate flights within +/-{args.lag_width}s lag...")
    df_candidates = find_candidate_flights(df_peaks, df_flights, lag_width=args.lag_width)

    if df_candidates.empty:
        print("No candidates found within the specified lag.")
        return

    # Add metadata to results
    df_candidates['Airport'] = airport_name
    df_candidates['Model'] = model_name

    # 5. Save results
    os.makedirs(args.output_dir, exist_ok=True)
    file_tag = f"{airport_name.lower()}_{model_name}"
    output_file = os.path.join(args.output_dir, f'candidates_{file_tag}.csv')
    df_candidates.to_csv(output_file, index=False)
    
    print(f"Successfully saved {len(df_candidates)} candidates to {output_file}")

if __name__ == "__main__":
    main()
