import pandas as pd
import os
import glob
import concurrent.futures
from tqdm import tqdm
import argparse

from src.scripts.data_processing import process_combined_data
from src.scripts.util import get_optimal_max_workers
from src.scripts.aircraft_calculate import calculate_station_peaks_worker

# --- (Local definitions of migrated functions removed - now imported from src/scripts/) ---

def calculate_peaks_if_needed(model='dbscan', eps=150, min_samples=10, bandwidth=None, airport='vtbs', output_combined='output/Combined_Peak_Data.csv', segment=False, K=100, mode='parallel', workers=None):
    """
    Finds all raw noise data files for the specific airport and calculates peaks using the specified model.
    Saves the result to output_combined.
    """
    airport_dir = os.path.join('raw_data', airport)
    noise_files = glob.glob(os.path.join(airport_dir, '*noise_data.csv'))
    print(f"Found {len(noise_files)} noise data files for {airport}.")
    all_peaks_list = []
    all_peaks_unfiltered_list = []
    all_timings = []
    
    if mode in ['p', 'parallel']:
        print(f"Calculating peaks using {model} for {len(noise_files)} files in PARALLEL (Airport: {airport})...")
        max_workers = workers if workers is not None else get_optimal_max_workers()
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(calculate_station_peaks_worker, f, model, eps, min_samples, bandwidth, segment=segment, K=K, mode=mode, airport=airport): f for f in noise_files}
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(noise_files), desc="Peak detection (Parallel)"):
                try:
                    res_dict = future.result()
                    if res_dict and 'peaks' in res_dict and res_dict['peaks'] is not None:
                        all_peaks_list.append(res_dict['peaks'])
                    if res_dict and 'peaks_unfiltered' in res_dict and res_dict['peaks_unfiltered'] is not None:
                        all_peaks_unfiltered_list.append(res_dict['peaks_unfiltered'])
                    if res_dict and 'timing' in res_dict and res_dict['timing'] is not None:
                        all_timings.append(res_dict['timing'])
                except Exception as e:
                    print(f"Error in peak worker: {e}")
    else:
        print(f"Calculating peaks using {model} for {len(noise_files)} files in SEQUENTIAL (Airport: {airport})...")
        for f in tqdm(noise_files, desc="Peak detection (Sequential)"):
            try:
                res_dict = calculate_station_peaks_worker(f, model, eps, min_samples, bandwidth, segment=segment, K=K, mode=mode, airport=airport)
                if res_dict and 'peaks' in res_dict and res_dict['peaks'] is not None:
                    all_peaks_list.append(res_dict['peaks'])
                if res_dict and 'peaks_unfiltered' in res_dict and res_dict['peaks_unfiltered'] is not None:
                    all_peaks_unfiltered_list.append(res_dict['peaks_unfiltered'])
                if res_dict and 'timing' in res_dict and res_dict['timing'] is not None:
                    all_timings.append(res_dict['timing'])
            except Exception as e:
                print(f"Error processing {f}: {e}")
    
    # Return both success status and the timing records for enrichment in main()
            
    if all_peaks_list:
        combined_df = pd.concat(all_peaks_list, ignore_index=True)
        found_stations = combined_df['Station'].unique()
        print(f"Successfully detected peaks for {len(found_stations)} stations: {found_stations}")
        
        # Ensure the directory exists before saving
        os.makedirs(os.path.dirname(output_combined), exist_ok=True)
        combined_df.to_csv(output_combined, index=False)
        print(f"Successfully generated peaks for all stations in {output_combined}")
        
        if all_peaks_unfiltered_list:
            combined_unf_df = pd.concat(all_peaks_unfiltered_list, ignore_index=True)
            out_unf_path = output_combined.replace('Combined_Peak_Data.csv', 'Combined_Peak_Data_Unfiltered.csv')
            combined_unf_df.to_csv(out_unf_path, index=False)
            print(f"Successfully saved unfiltered peaks to {out_unf_path}")
            
        return True, all_timings
    else:
        print("Error: No peaks were detected for any stations.")
    return False, []

def main():
    parser = argparse.ArgumentParser(description="Aircraft Noise Calculation & Processing Script")
    parser.add_argument('-m', '--model', type=str, default='dbscan', choices=['dbscan', 'msa'], 
                        help="Clustering model: 'dbscan' (default) or 'msa'")
    parser.add_argument('-ma', '--match-algorithm', type=str, choices=['legacy', '121', '121e', '12m'], default='legacy', 
                        help="Matching algorithm: 'legacy' (matching_flight_with_peak), '121', '121e' (Exclusive), '12m' (Multiple).")
    parser.add_argument('-eps', '-esp', type=int, default=150, 
                        help="EPS for DBSCAN (default: 150)")
    parser.add_argument('-min_samples', type=int, default=10, 
                        help="min_samples for DBSCAN (default: 10)")
    parser.add_argument('-bandwidth', type=float, default=150.0, 
                        help="bandwidth for MSA (default: 150.0)")
    parser.add_argument('-ap', '--airport', type=str, default='vtbs', 
                        help="Airport code (default: vtbs)")
    parser.add_argument('--recalculate', '-r', action='store_true', 
                        help="Force recalculation of peaks even if Combined_Peak_Data.csv exists")
    parser.add_argument('--segment', '-se', action='store_true', help="Enable signal segmentation for more efficient clustering")
    parser.add_argument('-K', '--K', type=int, default=100, help="Number of segments if --segment is enabled (default: 100)")
    parser.add_argument('--mode', choices=['p', 'parallel', 's', 'sequential'], default='p', 
                        help="Processing mode: 'p'/'parallel' (default) or 's'/'sequential'")
    parser.add_argument('-w', '--workers', type=int, default=None,
                        help="Number of workers for parallel mode (default: auto)")

    args = parser.parse_args()
    airport = args.airport.lower()

    # Generate subfolder name in snake_case
    if args.model == 'dbscan':
        subfolder = f"dbscan_eps_{args.eps}_min_samples_{args.min_samples}"
    else:
        # Bandwidth is now always a number or manually set
        bw_str = f"{args.bandwidth}".replace('.', '_')
        subfolder = f"msa_bandwidth_{bw_str}"
    
    if args.segment:
        subfolder += f"_segmented_K{args.K}"
        
    subfolder += f"_ma_{args.match_algorithm}"
    
    # New directory structure: result/<subfolder>/<airport>
    output_base_dir = os.path.join('result', subfolder, airport)
    os.makedirs(output_base_dir, exist_ok=True)

    # Use airport-specific flight log if it exists, otherwise use default
    airport_flight_log = f'Merged_Converted_Flight_Log_{airport.upper()}.xlsx'
    if os.path.exists(airport_flight_log):
        flight_log_file = airport_flight_log
    else:
        flight_log_file = r'Merged_Converted_Flight_Log.xlsx'
        
    combined_peak_data = os.path.join(output_base_dir, 'Combined_Peak_Data.csv')
    output_result = os.path.join(output_base_dir, 'Validated_Peaks_With_Flights.csv')

    # 1. File doesn't exist
    # 2. Recalculate is forced (-r)
    # 3. Existing file is invalid (missing 'start_time')
    # Determine if peak calculation is needed
    should_recalculate = not os.path.exists(combined_peak_data) or args.recalculate
    if not should_recalculate:
        try:
            temp_df = pd.read_csv(combined_peak_data, nrows=1)
            if 'start_time' not in temp_df.columns:
                print(f"  Warning: Existing peak data at {combined_peak_data} is invalid. Recalculating...")
                should_recalculate = True
        except Exception:
            should_recalculate = True

    import time
    start_time = time.time()
    
    calc_done = False
    recent_timings = []
    if should_recalculate:
        calc_done, recent_timings = calculate_peaks_if_needed(model=args.model, eps=args.eps, min_samples=args.min_samples, 
                                              bandwidth=args.bandwidth, airport=airport, output_combined=combined_peak_data,
                                              segment=args.segment, K=args.K, mode=args.mode, workers=args.workers)
    else:
        print(f"Using existing peak data from {combined_peak_data}. Use --recalculate to force new calculation.")
        calc_done = True
        
    if calc_done:
        if args.match_algorithm == 'legacy':
            print(f"Running legacy matching_flight_with_peak for {combined_peak_data}...")
            from src.scripts.aircraft_calculate import NoiseCalculation
            import pandas as pd
            calc = NoiseCalculation(n_pts='week', rate=95, is_std=True, lag_width=200)
            legacy_df = calc.matching_flight_with_peak(flight_log_file, peaks_df=pd.read_csv(combined_peak_data))
            legacy_df.to_csv(output_result, index=False)
            print(f"Successfully processed {len(legacy_df)} peaks mapping flights to {output_result} using legacy algorithm.")
            
        # 2. Perform Metrics Calculation and/or alternative Flight Matching
        metrics_df = process_combined_data(flight_log_file, combined_peak_data, output_result, airport=airport, match_algorithm=args.match_algorithm)
        
        # Merge metrics into the JSON log if we just recalculated
        if should_recalculate and recent_timings and metrics_df is not None and not metrics_df.empty:
            import json
            for timing in recent_timings:
                st = timing.get('station')
                # Find metrics for this station, 'ALL' operation, and representative Lag (e.g., 120s)
                # We use Lag=120 as a stable benchmark point
                m = metrics_df[(metrics_df['Station'] == st) & 
                               (metrics_df['Operation'] == 'ALL') & 
                               (metrics_df['Lag (s)'] == 120)]
                               
                if not m.empty:
                    timing['precision'] = round(float(m['Precision'].iloc[0]), 4)
                    timing['recall'] = round(float(m['Recall'].iloc[0]), 4)
                    timing['f1'] = round(float(m['F1 Score'].iloc[0]), 4)
                else:
                    timing['precision'] = timing['recall'] = timing['f1'] = 0.0
            
            # Save enriched performance log to JSON
            log_file = os.path.join('result', 'execution_times.json')
            os.makedirs('result', exist_ok=True)
            current_data = []
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r') as f:
                        current_data = json.load(f)
                except:
                    current_data = []
            
            current_data.extend(recent_timings)
            with open(log_file, 'w') as f:
                json.dump(current_data, f, indent=4)
            print(f"  Performance & Accuracy log updated: {log_file}")
    
    # Generate main plots

if __name__ == '__main__':
    main()
