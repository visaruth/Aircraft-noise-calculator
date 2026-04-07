import pandas as pd
import numpy as np
import os
import gc
from src.scripts.util import get_operation, calculate_log_average, check_flight

def calculate_daily_metrics(df_noise, station_name):
    """
    Given a raw noise dataframe (with 'Period start' and 'Leq'),
    calculate daily Ld, Ln, Ldn, Leq24 metrics.
    """
    df_noise.columns = [c.strip() for c in df_noise.columns]
    
    if 'Period start' not in df_noise.columns:
        return None
        
    df_noise['datetime'] = pd.to_datetime(df_noise['Period start'], format='mixed')
    data = df_noise[['datetime', 'Leq']].copy()
    data['Power'] = np.power(10, data['Leq'] / 10.0)
    data['Date'] = data['datetime'].dt.date
    data['Hour'] = data['datetime'].dt.hour
    
    daily_metrics = []
    
    for date, group in data.groupby('Date'):
        # --- Ldn Specific (Day 07:00-22:00, Night 22:00-07:00) ---
        day_mask = (group['Hour'] >= 7) & (group['Hour'] < 22)
        day_data = group.loc[day_mask, 'Power']
        night_mask = ~day_mask
        night_data = group.loc[night_mask, 'Power']
        
        avg_p_day_ldn = day_data.mean() if len(day_data) > 0 else 0
        avg_p_night = night_data.mean() if len(night_data) > 0 else 0
        avg_p_24 = group['Power'].mean()
        
        # Unpenalized Ln and overall Ld (for backwards compatibility)
        Ld = 10 * np.log10(avg_p_day_ldn) if avg_p_day_ldn > 0 else np.nan
        Ln = 10 * np.log10(avg_p_night) if avg_p_night > 0 else np.nan
        Leq24 = 10 * np.log10(avg_p_24) if avg_p_24 > 0 else np.nan
        
        if avg_p_day_ldn > 0 and avg_p_night > 0:
            ldn_power = (15 * avg_p_day_ldn + 9 * avg_p_night * 10) / 24
            Ldn = 10 * np.log10(ldn_power)
        elif avg_p_day_ldn > 0:
             Ldn = Ld 
        else:
             Ldn = np.nan

        # --- Lden Specific (Day 07:00-19:00, Evening 19:00-22:00, Night 22:00-07:00) ---
        day_lden_mask = (group['Hour'] >= 7) & (group['Hour'] < 19)
        evening_mask = (group['Hour'] >= 19) & (group['Hour'] < 22)
        
        day_lden_data = group.loc[day_lden_mask, 'Power']
        evening_data = group.loc[evening_mask, 'Power']
        
        avg_p_day_lden = day_lden_data.mean() if len(day_lden_data) > 0 else 0
        avg_p_evening = evening_data.mean() if len(evening_data) > 0 else 0
        
        # Use existing avg_p_night for Lden's night block
        if avg_p_day_lden > 0 and avg_p_evening > 0 and avg_p_night > 0:
            lden_power = (12 * avg_p_day_lden + 3 * avg_p_evening * (10**(5/10)) + 9 * avg_p_night * 10) / 24
            Lden = 10 * np.log10(lden_power)
        else:
            Lden = np.nan

        daily_metrics.append({
            'Station': station_name,
            'Date': date,
            'Ld': round(Ld, 2) if not np.isnan(Ld) else np.nan,
            'Ln': round(Ln, 2) if not np.isnan(Ln) else np.nan,
            'Ldn': round(Ldn, 2) if not np.isnan(Ldn) else np.nan,
            'Lden': round(Lden, 2) if not np.isnan(Lden) else np.nan,
            'Leq24': round(Leq24, 2) if not np.isnan(Leq24) else np.nan
        })
        
    return pd.DataFrame(daily_metrics)


def calculate_hourly_metrics(df_noise, station_name):
    """
    Calculate log average of Leq for each hour of each day.
    """
    df_noise.columns = [c.strip() for c in df_noise.columns]
    if 'Period start' not in df_noise.columns:
        return None
        
    df_noise['datetime'] = pd.to_datetime(df_noise['Period start'], format='mixed')
    data = df_noise[['datetime', 'Leq']].copy()
    data['Date'] = data['datetime'].dt.date
    data['Hour'] = data['datetime'].dt.hour
    
    hourly_data = data.groupby(['Date', 'Hour'])['Leq'].apply(calculate_log_average).reset_index()
    hourly_data['Station'] = station_name
    hourly_data['Hourly_Leq'] = hourly_data['Leq'].round(2)
    hourly_data = hourly_data.drop(columns=['Leq'])
    
    return hourly_data[['Station', 'Date', 'Hour', 'Hourly_Leq']]


def generate_accuracy_results(station_name, df_station_peaks, all_flight_times):
    """
    Compare peaks to flight times over various lag windows to compute Precision, Recall, F1.
    """
    from datetime import timedelta
    
    lag_times = list(range(10, 201, 10))
    results_data = []
    
    station_start = df_station_peaks['start_time'].min()
    station_end = df_station_peaks['end_time'].max()
    
    for lag in lag_times:
        window_starts = df_station_peaks['start_time'] - timedelta(seconds=lag)
        window_ends = df_station_peaks['end_time'] + timedelta(seconds=lag)
        
        start_indices = np.searchsorted(all_flight_times, window_starts.values, side='left')
        end_indices = np.searchsorted(all_flight_times, window_ends.values, side='right')
        
        matches = (end_indices > start_indices)
        tp_peaks = np.sum(matches)
        fp_peaks = len(df_station_peaks) - tp_peaks
        
        relevant_start = station_start - timedelta(seconds=lag)
        relevant_end = station_end + timedelta(seconds=lag)
        
        f_start_idx = np.searchsorted(all_flight_times, relevant_start.to_datetime64(), side='left')
        f_end_idx = np.searchsorted(all_flight_times, relevant_end.to_datetime64(), side='right')
        
        relevant_flight_times = all_flight_times[f_start_idx:f_end_idx]
        total_flights = len(relevant_flight_times)
        
        intervals = sorted(zip(window_starts, window_ends))
        merged = []
        if intervals:
            curr_start, curr_end = intervals[0]
            for next_start, next_end in intervals[1:]:
                if next_start <= curr_end:
                    curr_end = max(curr_end, next_end)
                else:
                    merged.append((curr_start, curr_end))
                    curr_start, curr_end = next_start, next_end
            merged.append((curr_start, curr_end))
            
        matched_flights_count = 0
        for start, end in merged:
            idx1 = np.searchsorted(relevant_flight_times, start.to_datetime64(), side='left')
            idx2 = np.searchsorted(relevant_flight_times, end.to_datetime64(), side='right')
            matched_flights_count += (idx2 - idx1)
            
        fn_flights = total_flights - matched_flights_count
        
        precision = tp_peaks / (tp_peaks + fp_peaks) if (tp_peaks + fp_peaks) > 0 else 0
        recall = matched_flights_count / total_flights if total_flights > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        results_data.append({
            'Station': station_name,
            'Lag (s)': lag,
            'Peak Events': len(df_station_peaks),
            'Flights (in range)': total_flights,
            'TP': tp_peaks,
            'TN': 0,
            'FP': fp_peaks,
            'FN': fn_flights,
            'Precision': round(precision, 4),
            'Recall': round(recall, 4),
            'F1 Score': round(f1, 4)
        })
        
    return pd.DataFrame(results_data)

def process_station_worker(station, station_peaks, flight_df, airport='vtbs', match_algorithm='legacy'):
    """
    Worker function to process a single station's peak results, metrics, and flight matching.
    Designed for parallel execution in main.py.
    """
    import os
    import glob
    import numpy as np
    import pandas as pd
    from datetime import timedelta
    from src.scripts.data_processing import calculate_daily_metrics, calculate_hourly_metrics, generate_accuracy_results, run_unified_matching
    from src.scripts.modelling.validate import validate_10db_down
    from src.scripts.util import merge_intervals, is_time_in_intervals
    
    # Standard lags for accuracy benchmarking
    lags = [60, 80, 100, 120, 180]
    
    results = {
        'station': station,
        'hourly_leq': None,
        'daily_metrics': None,
        'validation_results': None,
        'actype_counts': None,
        'accuracy_metrics': [],
        'peak_results': []
    }

    # --- 1. Load Raw Noise Data for Metrics ---
    norm_station = station.lower().replace('-', '').replace('_', '')
    raw_noise_file = None
    for f in glob.glob(os.path.join('raw_data', airport, '*noise_data.csv')):
        # Normalize find filename
        norm_f = os.path.basename(f).lower().replace('-', '').replace('_', '').replace('noisedata.csv', '')
        if norm_station == norm_f or norm_station in norm_f or norm_f in norm_station:
            raw_noise_file = f
            break
            
    df_noise = pd.DataFrame()
    if raw_noise_file and os.path.exists(raw_noise_file):
        try:
            df_noise = pd.read_csv(raw_noise_file)
            time_col = next((c for c in df_noise.columns if 'time' in c.lower() or 'period start' in c.lower() or 'date' in c.lower()), None)
            if time_col:
                 df_noise['timestamp'] = pd.to_datetime(df_noise[time_col], errors='coerce', format='mixed')
            elif 'datetime' in df_noise.columns:
                 df_noise['timestamp'] = pd.to_datetime(df_noise['datetime'], errors='coerce')
                 
            if 'Leq' in df_noise.columns:
                 df_noise_copy = df_noise.copy()
                 if 'Period start' not in df_noise_copy.columns and time_col:
                     df_noise_copy = df_noise_copy.rename(columns={time_col: 'Period start'})
                 
                 results['hourly_leq'] = calculate_hourly_metrics(df_noise_copy, station)
                 results['daily_metrics'] = calculate_daily_metrics(df_noise_copy, station)
        except Exception as e:
            print(f"  Warning: Failed to read noise file {raw_noise_file}: {e}")

    # --- 2. Pre-calculate Flight Validation across lags ---
    station_start = station_peaks['start_time'].min()
    station_end = station_peaks['end_time'].max()
    
    if not flight_df.empty:
        buffer = timedelta(minutes=5)
        mask = (flight_df['datetime'] >= (station_start - buffer)) & (flight_df['datetime'] <= (station_end + buffer))
        df_station_flights = flight_df[mask].copy()
        
        if not df_station_flights.empty:
            df_station_flights['Station'] = station
            df_station_flights['datetime_th'] = df_station_flights['datetime']
            
            intervals_map = {}
            for lag in lags:
                starts = station_peaks['start_time'] - timedelta(seconds=lag)
                ends = station_peaks['end_time'] + timedelta(seconds=lag)
                # Use modular merge_intervals from util.py
                intervals_map[lag] = merge_intervals(list(zip(starts, ends)))

            for lag in lags:
                col_name = f'Detected_{lag}s'
                # Use modular is_time_in_intervals from util.py
                df_station_flights[col_name] = df_station_flights['datetime_th'].apply(
                    lambda t: is_time_in_intervals(t, intervals_map[lag])
                ).map({True: 'Detected', False: 'Missed'})
            
            final_cols = [c for c in ['Station', 'datetime_th', 'CALLSIGN', 'REGISTRATION', 'ACTYPE', 'POD', 'DEST', 'RWY', 'Operation'] + [f'Detected_{lag}s' for lag in lags] if c in df_station_flights.columns]
            results['validation_results'] = df_station_flights[final_cols]
            
            # Pre-calculate ACTYPE counts
            counts = results['validation_results']['ACTYPE'].astype(str).str.strip().value_counts().reset_index()
            counts.columns = ['ACTYPE', 'Count']
            counts['Station'] = station
            counts['Period_Start'] = station_start
            counts['Period_End'] = station_end
            results['actype_counts'] = counts[['Station', 'Period_Start', 'Period_End', 'ACTYPE', 'Count']]

    # --- 3. Accuracy metrics ---
    if not flight_df.empty:
        flight_times_dict = {
            'ALL': flight_df['datetime'].values,
            'Departure': flight_df[flight_df['Operation'].isin(['Departure', 'Take-off'])]['datetime'].values,
            'Arrival': flight_df[flight_df['Operation'].isin(['Arrival', 'Landing'])]['datetime'].values
        }
        for op_name, f_times in flight_times_dict.items():
             if len(f_times) > 0:
                 df_res = generate_accuracy_results(station, station_peaks, f_times)
                 df_res['Operation'] = op_name
                 results['accuracy_metrics'].append(df_res)
                 
    # --- 4. Advanced Flight Matching mapping and 10dB Validations ---
    # Legacy mode uses the full `matching_flight_with_peak` inside main.py, so we skip file-writing individual matches here
    # to avoid overwriting the legacy structure.
    if match_algorithm != 'legacy':
        if not df_noise.empty and 'timestamp' in df_noise.columns:
            ts_values = df_noise['timestamp'].values
            leq_values = df_noise['Leq'].values
        else:
            ts_values, leq_values = np.array([]), np.array([])
            
        matched_df = run_unified_matching(station_peaks, df_station_flights if not flight_df.empty else pd.DataFrame(), mode=match_algorithm, lag_width=200)
        
        for _, row in matched_df.iterrows():
            p_time = row['Peak_Start']
            is_10db_valid = False
            
            # Efficient vectorized 10dB verification
            if ts_values.size > 0:
                try:
                    p_time_np = pd.to_datetime(p_time).to_datetime64()
                    idx = np.searchsorted(ts_values, p_time_np)
                    if idx == 0: orig_idx = 0
                    elif idx == len(ts_values): orig_idx = len(ts_values) - 1
                    else: orig_idx = idx if abs(ts_values[idx] - p_time_np) < abs(ts_values[idx-1] - p_time_np) else idx - 1
                    # Since we removed duplicated 10dB checks via caching, only evaluate if strictly necessary
                    is_10db_valid = validate_10db_down(leq_values, orig_idx, drop_db=10)
                except: pass
                
            res = {
                'Station': station, 
                'Peak_Start': p_time, 
                'Peak_End': row['Peak_End'], 
                'Leq': row['Leq'], 
                'Validated_10dB': is_10db_valid, 
                'Matched_Flight': pd.notna(row.get('CALLSIGN')),
                'ACTYPE': row.get('ACTYPE'), 
                'REGISTRATION': row.get('REGISTRATION'), 
                'Callsign': row.get('CALLSIGN'), 
                'Operation': row.get('Operation'), 
                'Flight_Time': row.get('Flight_Time'),
                'direction_match': row.get('direction_match', 'Unknown'),
                'lag_time': row.get('lag time')
            }
            results['peak_results'].append(res)
            
    return results

def process_combined_data(flight_log_file, combined_peak_csv, output_csv, airport='vtbs', match_algorithm='legacy'):
    """
    Parallel implementation of the processing workflow.
    Orchestrates flight loading, matching, and result saving.
    """
    import os
    import pandas as pd
    import concurrent.futures
    from tqdm import tqdm
    from src.scripts.preparation import load_flight_logs
    from src.scripts.util import get_optimal_max_workers, determine_operation
    from src.scripts.data_processing import process_station_worker

    flight_df = load_flight_logs(flight_log_file)
    if not flight_df.empty and 'POD' in flight_df.columns:
        flight_df['Operation'] = flight_df.apply(lambda row: determine_operation(row.get('POD',''), row.get('DEST',''), airport=airport), axis=1)
    else: flight_df['Operation'] = 'Unknown'

    print(f"Loading {combined_peak_csv}...")
    try:
        peaks_df = pd.read_csv(combined_peak_csv)
    except FileNotFoundError:
        print(f"File {combined_peak_csv} not found."); return pd.DataFrame()
        
    peaks_df['start_time'] = pd.to_datetime(peaks_df['start_time'], errors='coerce')
    peaks_df['end_time'] = pd.to_datetime(peaks_df['end_time'], errors='coerce')
    peaks_df = peaks_df.dropna(subset=['start_time'])

    stations = peaks_df['Station'].unique()
    print(f"Processing {len(stations)} stations in parallel...")
    all_hourly_leq, all_daily_metrics, all_accuracy_metrics, all_validation_results, all_actype_counts, all_peak_results = [], [], [], [], [], []

    max_workers = get_optimal_max_workers()
    print(f"Using {max_workers} worker processes based on system resources.")
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_station_worker, s, peaks_df[peaks_df['Station'] == s].copy(), flight_df, airport=airport, match_algorithm=match_algorithm): s for s in stations}
        
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(stations), desc="Processing stations"):
            try:
                res = future.result()
                if res['hourly_leq'] is not None: all_hourly_leq.append(res['hourly_leq'])
                if res['daily_metrics'] is not None: all_daily_metrics.append(res['daily_metrics'])
                if res['validation_results'] is not None: all_validation_results.append(res['validation_results'])
                if res['actype_counts'] is not None: all_actype_counts.append(res['actype_counts'])
                all_accuracy_metrics.extend(res['accuracy_metrics'])
                all_peak_results.extend(res['peak_results'])
            except Exception as e:
                station_name = futures[future]
                print(f"Error processing station {station_name}: {e}")

    # Save results
    if all_peak_results:
        final_df = pd.DataFrame(all_peak_results)
        final_df.to_csv(output_csv, index=False)
        print(f"Successfully processed {len(final_df)} peaks mapping flights to {output_csv}")
    
    base_out = os.path.dirname(output_csv)
    if all_hourly_leq: pd.concat(all_hourly_leq, ignore_index=True).to_csv(os.path.join(base_out, 'all_stations_hourly_leq.csv'), index=False)
    if all_daily_metrics: pd.concat(all_daily_metrics, ignore_index=True).to_csv(os.path.join(base_out, 'daily_leq_metrics.csv'), index=False)
    if all_accuracy_metrics: pd.concat(all_accuracy_metrics, ignore_index=True).to_csv(os.path.join(base_out, 'all_stations_metrics_detailed.csv'), index=False)
    if all_validation_results: pd.concat(all_validation_results, ignore_index=True).to_csv(os.path.join(base_out, 'Station_Flight_Validation.csv'), index=False)
    if all_actype_counts: pd.concat(all_actype_counts, ignore_index=True).to_csv(os.path.join(base_out, 'ACTYPE_Counts_Per_Site.csv'), index=False)
    
    if all_accuracy_metrics:
        return pd.concat(all_accuracy_metrics, ignore_index=True)
    return pd.DataFrame()

def find_candidate_flights(df_peaks, df_flights, lag_width=300):
    """
    Matches noise peaks to candidate flights within a time lag window.
    """
    from datetime import timedelta
    import pandas as pd
    candidates = []
    
    # Ensure peaks have needed calculated fields
    df_peaks['start_time'] = pd.to_datetime(df_peaks['start_time'])
    df_peaks['end_time'] = pd.to_datetime(df_peaks['end_time'])
    df_peaks['peak_center'] = df_peaks['start_time'] + (df_peaks['end_time'] - df_peaks['start_time']) / 2
    
    for idx, peak in df_peaks.iterrows():
        p_center = peak['peak_center']
        station = peak['Station']
        
        # Filter flights within the lag window: [PeakCenter - lw, PeakCenter + lw]
        mask = (df_flights['datetime'] >= p_center - timedelta(seconds=lag_width)) & \
               (df_flights['datetime'] <= p_center + timedelta(seconds=lag_width))
        
        matched_flights = df_flights[mask].copy()
        
        for f_idx, flight in matched_flights.iterrows():
            lag_time = (p_center - flight['datetime']).total_seconds()
            
            res = {
                'Station': station,
                'Peak_Start': peak['start_time'],
                'Peak_End': peak['end_time'],
                'Peak_Center': p_center,
                'Leq': peak.get('Leq'),
                'CALLSIGN': flight.get('CALLSIGN'),
                'REGISTRATION': flight.get('REGISTRATION'),
                'ACTYPE': flight.get('ACTYPE'),
                'Operation': flight.get('Operation') or flight.get('APPDEPFLAG'),
                'Flight_Time': flight['datetime'],
                'lag time': round(lag_time, 2)
            }
            candidates.append(res)
            
    return pd.DataFrame(candidates)

def match_1to1_exclusive(df_peaks, df_flights, lag_width=300):
    """
    Performs exclusive 1-to-1 matching based on min lag and directional priority.
    Peaks are prioritized by Leq descending.
    """
    from datetime import timedelta
    import pandas as pd
    
    matched_results = []
    used_flight_indices = set()
    
    # Pre-calculate peak center if missing
    if 'peak_center' not in df_peaks.columns:
        df_peaks['start_time'] = pd.to_datetime(df_peaks['start_time'])
        df_peaks['end_time'] = pd.to_datetime(df_peaks['end_time'])
        df_peaks['peak_center'] = df_peaks['start_time'] + (df_peaks['end_time'] - df_peaks['start_time']) / 2
    else:
        df_peaks['peak_center'] = pd.to_datetime(df_peaks['peak_center'])
        
    df_peaks['start_time'] = pd.to_datetime(df_peaks['start_time'])
    df_peaks['end_time'] = pd.to_datetime(df_peaks['end_time'])
    
    # Sort peaks by Leq descending to prioritize matching "stronger" peaks first
    df_peaks_sorted = df_peaks.sort_values('Leq', ascending=False)
    
    for idx, peak in df_peaks_sorted.iterrows():
        p_center = peak['peak_center']
        mask = (df_flights['datetime'] >= p_center - timedelta(seconds=lag_width)) & \
               (df_flights['datetime'] <= p_center + timedelta(seconds=lag_width))
        
        candidates = df_flights[mask].copy()
        candidates = candidates[~candidates.index.isin(used_flight_indices)]
        
        if not candidates.empty:
            candidates['lag_time'] = (p_center - candidates['datetime']).dt.total_seconds()
            candidates['abs_lag'] = candidates['lag_time'].abs()
            
            def is_correct_direction(row):
                op = str(row.get('Operation', '')).lower() or str(row.get('APPDEPFLAG', '')).lower()
                lag = row['lag_time']
                if 'land' in op or 'arr' in op: return 1 if lag < 0 else 0
                if 'take' in op or 'dep' in op: return 1 if lag > 0 else 0
                return 0

            candidates['is_direction_correct'] = candidates.apply(is_correct_direction, axis=1)
            best_candidates = candidates.sort_values(['is_direction_correct', 'abs_lag'], ascending=[False, True])
            best_flight = best_candidates.iloc[0]
            used_flight_indices.add(best_flight.name)
            
            res = {
                'Station': peak['Station'],
                'Peak_Start': peak['start_time'],
                'Peak_End': peak['end_time'],
                'Peak_Center': p_center,
                'Leq': peak['Leq'],
                'CALLSIGN': best_flight.get('CALLSIGN'),
                'REGISTRATION': best_flight.get('REGISTRATION'),
                'ACTYPE': best_flight.get('ACTYPE'),
                'Operation': best_flight.get('Operation') or best_flight.get('APPDEPFLAG'),
                'Flight_Time': best_flight['datetime'],
                'lag time': round(best_flight['lag_time'], 2),
                'direction_match': 'Yes' if best_flight['is_direction_correct'] == 1 else 'No'
            }
            matched_results.append(res)
            
    return pd.DataFrame(matched_results)

def run_unified_matching(df_peaks, df_flights, mode='121e', lag_width=300):
    """
    Unified matching orchestration.
    Modes:
      '12m': Candidate discovery (1-to-many, keep all within window)
      '121': Peak-side unique 1-to-1 (reuse flights allowed)
      '121e': Exclusive 1-to-1 (priority Leq descending, no reuse)
    """
    from datetime import timedelta
    import pandas as pd
    
    results = []
    
    # 1. Pre-processing
    if 'peak_center' not in df_peaks.columns:
        df_peaks['start_time'] = pd.to_datetime(df_peaks['start_time'])
        df_peaks['end_time'] = pd.to_datetime(df_peaks['end_time'])
        df_peaks['peak_center'] = df_peaks['start_time'] + (df_peaks['end_time'] - df_peaks['start_time']) / 2
    else:
        df_peaks['peak_center'] = pd.to_datetime(df_peaks['peak_center'])
        
    df_peaks['start_time'] = pd.to_datetime(df_peaks['start_time'])
    df_peaks['end_time'] = pd.to_datetime(df_peaks['end_time'])
    
    if mode == '121e':
        df_peaks_proc = df_peaks.sort_values('Leq', ascending=False)
        used_flight_indices = set()
    else:
        df_peaks_proc = df_peaks
        
    # Helper to normalize operation
    def get_op_sign(row):
        op = str(row.get('Operation', '')).lower() or str(row.get('APPDEPFLAG', '')).lower()
        if 'land' in op or 'arr' in op: return 'Landing'
        if 'take' in op or 'dep' in op: return 'Take-off'
        return 'Unknown'
    
    # 2. Iteration
    for idx, peak in df_peaks_proc.iterrows():
        p_center = peak['peak_center']
        mask = (df_flights['datetime'] >= p_center - timedelta(seconds=lag_width)) & \
               (df_flights['datetime'] <= p_center + timedelta(seconds=lag_width))
        
        candidates = df_flights[mask].copy()
        
        if mode == '121e' and not candidates.empty:
            candidates = candidates[~candidates.index.isin(used_flight_indices)]
            
        if candidates.empty: continue
        
        candidates['lag_time'] = (p_center - candidates['datetime']).dt.total_seconds()
        
        if mode in ['121', '121e']:
            def is_correct_direction(row):
                op = get_op_sign(row)
                lag = row['lag_time']
                if op == 'Landing': return 1 if lag < 0 else 0
                if op == 'Take-off': return 1 if lag > 0 else 0
                return 0
            
            candidates['is_direction_correct'] = candidates.apply(is_correct_direction, axis=1)
            candidates['abs_lag'] = candidates['lag_time'].abs()
            
            best = candidates.sort_values(['is_direction_correct', 'abs_lag'], ascending=[False, True]).iloc[0]
            if mode == '121e':
                used_flight_indices.add(best.name)
            match_list = [best]
        else:
            # Mode 12m: All
            match_list = [row for _, row in candidates.iterrows()]
            
        for flight in match_list:
            res = {
                'Station': peak['Station'],
                'Peak_Start': peak['start_time'],
                'Peak_End': peak['end_time'],
                'Peak_Center': p_center,
                'Leq': peak['Leq'],
                'CALLSIGN': flight.get('CALLSIGN'),
                'REGISTRATION': flight.get('REGISTRATION'),
                'ACTYPE': flight.get('ACTYPE'),
                'Operation': get_op_sign(flight),
                'Flight_Time': flight['datetime'],
                'lag time': round(flight['lag_time'], 2)
            }
            if mode in ['121', '121e']:
                res['direction_match'] = 'Yes' if flight.get('is_direction_correct') == 1 else 'No'
            results.append(res)
            
    return pd.DataFrame(results)
