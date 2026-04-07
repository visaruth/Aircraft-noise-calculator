import numpy as np
import pandas as pd
import datetime as datetime
import math
import os.path
import streamlit as st

from sklearn.preprocessing import StandardScaler
from scipy.signal import butter, filtfilt

from src.scripts.modelling.k_means_model import sound_clustering
from src.scripts.modelling.dbscan_model import find_peaks as find_peaks_dbscan
from src.scripts.modelling.msa_model import find_peaks_msa
from src.scripts.transform_data import (
    to_date,
    to_time,
    phasedecide,
    call_airline_name,
    call_airport_name,
    call_airplane_name,
)
from src.scripts.matchingFlight import find_flight_peak, match_peak


def cutoff(r, data):
    r = (100 - r) / 1000
    b, a = butter(4, r)
    filtered = filtfilt(b, a, data)
    return filtered


def computeL_eq_t(data):
    if len(data) == 0:
        return 0
    sum_pow = np.sum(np.power(10, data / 10))
    x = 1 / len(data) * sum_pow
    return 10 * math.log(x, 10)


def SoundAddition(data):
    x = np.sum(np.power(10, data / 10))
    return 10 * math.log(x, 10)


def computeSEL(data):
    return computeL_eq_t(data) + 10 * math.log((len(data) * 100) / 1000)


def IQR_outlier(data, d_type):
    Q1 = np.percentile(data[d_type], 25)
    Q3 = np.percentile(data[d_type], 75)
    IQR = Q3 - Q1

    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR

    df_result_cleaned = data[
        ~((data[d_type] < lower_bound) | (data[d_type] > upper_bound))
    ]
    return df_result_cleaned


def split_by_energy(signal, K, window=500):
    """
    Split a long time-series signal into K sub-segments by finding energy minima.
    Useful for segmenting aircraft noise events into manageable chunks for clustering.
    """
    from scipy.signal import find_peaks
    import numpy as np

    N = len(signal)
    if N < window * 2:
        return [signal], []

    # compute short-time energy (using float64 to avoid overflow with signal**2)
    energy = np.convolve(signal.astype(np.float64)**2, np.ones(window)/window, mode='same')

    # find minima
    minima, _ = find_peaks(-energy)
    
    if len(minima) == 0:
        return [signal], []

    cuts = []
    # Divide signal into K target positions
    target_positions = np.linspace(0, N, K+1)[1:-1]

    for t in target_positions:
        # Find the energy minimum closest to the target position
        idx = minima[np.argmin(np.abs(minima - t))]
        if idx not in cuts:
            cuts.append(idx)

    cuts = sorted(cuts)
    segments = np.split(signal, cuts)

    return segments, cuts


class NoiseCalculation(object):
    def __init__(self, n_pts, rate, is_std, lag_width):
        self.n_pts = n_pts
        self.rate = rate
        self.is_std = is_std
        self.lag_width = lag_width

    def _process_segment(self, df_copy, model, esp, min_samples, bandwidth):
        """
        Helper to run clustering and peak detection on a single segment of data.
        """
        def standardization(X):
            if self.is_std:
                X = X.reshape(-1, 1)
                scaler = StandardScaler()
                X_norm = scaler.fit_transform(X)
                return X_norm
            else:
                return X.reshape(-1, 1)

        X = np.array(df_copy["Leq_filtered"])
        X = standardization(X)

        X_kmeans = sound_clustering(X)
        df_copy["cluster"] = X_kmeans.labels_

        avg_cluster = [
            df_copy[df_copy["cluster"] == i]["Leq_filtered"].mean()
            for i in range(len(np.unique(X_kmeans.labels_)))
        ]
        max_cluster = np.array(avg_cluster).argmax()

        time_on_max_clusters = np.array(
            df_copy[df_copy["cluster"] == max_cluster].index
        )
        
        if model.lower() == 'dbscan':
            df_peaks = find_peaks_dbscan(df_copy, time_on_max_clusters, eps=esp, min_samples=min_samples)
        elif model.lower() == 'msa':
            df_peaks = find_peaks_msa(df_copy, time_on_max_clusters, bandwidth=bandwidth)
        else:
            df_peaks = find_peaks_dbscan(df_copy, time_on_max_clusters, eps=esp, min_samples=min_samples)
            
        return df_peaks

    def find_localpeak_alternative(self, data, model='dbscan', esp=150, min_samples=10, bandwidth=None, segment=False, K=100):
        pts = 36000
        pts_period = (
            (data.iloc[1]["Period start"] - data.iloc[0]["Period start"])
            / np.timedelta64(1, "s")
        ) * 10
        self.pts_result = int(pts / pts_period)

        def time_slice(d, n_pts):
            n_pts_dict = {
                "half_day": self.pts_result * 12,
                "day": self.pts_result * 24,
                "week": self.pts_result * (24 * 7),
            }
            return d[: n_pts_dict[n_pts] + 1]

        def filterize(rate, d):
            sound_cutoff = cutoff(rate, d)
            return sound_cutoff

        ##### Main #####

        sound_data = time_slice(data, self.n_pts)

        print("filtering data...")
        sound_cutoff = filterize(self.rate, sound_data["Leq"])
        df_filtered = sound_data.assign(Leq_filtered=sound_cutoff)

        print("filterize done")
        print()

        print("##### find local peaks #####")
        
        if not segment:
            df_copy = df_filtered.copy()
            df_peaks = self._process_segment(df_copy, model, esp, min_samples, bandwidth)
            self.df_result = pd.concat([df_copy, df_peaks], axis=1)
            self.df_result["peak_group"] = self.df_result["peak_group"].fillna(-1)
        else:
            print(f"Segmenting signal into {K} parts for efficiency...")
            leq_signal = df_filtered["Leq_filtered"].values
            segments_data, cuts = split_by_energy(leq_signal, K)
            
            all_processed_dfs = []
            current_idx = 0
            group_offset = 0
            
            from tqdm import tqdm
            for i, seg_leq in enumerate(tqdm(segments_data, desc="Processing Segments")):
                seg_len = len(seg_leq)
                if seg_len == 0: continue
                
                seg_df = df_filtered.iloc[current_idx : current_idx + seg_len].copy()
                
                df_peaks = self._process_segment(seg_df, model, esp, min_samples, bandwidth)
                
                if not df_peaks.empty:
                    # Increment group IDs to avoid collisions between segments
                    # df_peaks is a Series returned by _process_segment
                    valid_mask = df_peaks != -1
                    if valid_mask.any():
                        df_peaks.loc[valid_mask] = df_peaks.loc[valid_mask] + group_offset
                        group_offset = df_peaks.max() + 1
                
                combined_seg = pd.concat([seg_df, df_peaks], axis=1)
                all_processed_dfs.append(combined_seg)
                current_idx += seg_len
            
            self.df_result = pd.concat(all_processed_dfs)
            self.df_result["peak_group"] = self.df_result["peak_group"].fillna(-1)

        print("finding sound peaks done")
        print("finding local peaks complete")
        print()

        self.len_data = len(self.df_result)

        return self.df_result

    def calculate_sound(self, df, station_name=None, return_unfiltered=False):
        print("Calculating sound metrics...")
        if "peak_group" not in df.columns:
            return (pd.DataFrame(), pd.DataFrame()) if return_unfiltered else pd.DataFrame()

        # OPTIMIZATION: Use groupby instead of filtering the whole dataframe in a loop
        # This is critical for performance when there are millions of rows and hundreds of peaks.
        df_valid = df[df["peak_group"] != -1]
        if df_valid.empty:
            return (pd.DataFrame(), pd.DataFrame()) if return_unfiltered else pd.DataFrame()

        groups = df_valid.groupby("peak_group")
        
        # Calculate medians efficiently
        # peak_median_series will have peak_group as index
        peak_median_series = groups.apply(lambda g: np.median(g.index), include_groups=False)
        
        unix_time = np.array(df["Period start"])
        results = []

        # Iterate through the pre-grouped data
        for c, group_data in groups:
            # group_data is a slice of the dataframe for this group
            indices = group_data.index
            min_t, max_t = indices.min(), indices.max()
            peak_t = int(peak_median_series[c])

            in_which_hour = min_t // self.pts_result

            raw = group_data["Leq"].values
            Leq = computeL_eq_t(raw)
            LAE = computeSEL(raw)

            r = {
                "hours": in_which_hour,
                "start_time": unix_time[min_t],
                "end_time": unix_time[max_t],
                "peak_time": peak_t,
                "interval": unix_time[max_t] - unix_time[min_t],
                "median": peak_median_series[c],
                "Leq": Leq,
                "Lae": LAE,
            }

            results.append(r)

        df_result = pd.DataFrame(results)
        df_result["interval"] = df_result["interval"] / np.timedelta64(1, "s")

        # STEP 1: IQR Filtering
        df_result_cleaned = IQR_outlier(df_result, "interval")
        df_result_cleaned = IQR_outlier(df_result_cleaned, "Leq")
        
        # STEP 2: PI Filtering
        def PI_outlier(data, d_type, alpha=0.05):
            if data.empty or len(data) < 2:
                return data
            
            values = data[d_type].values
            L_prime = len(values)
            x_bar = np.mean(values)
            s = np.std(values, ddof=1)
            
            from scipy import stats
            t_critical = stats.t.ppf(1 - alpha / 2, df=L_prime - 1)
            margin = t_critical * s * np.sqrt(1 + 1 / L_prime)
            
            lower_bound = x_bar - margin
            upper_bound = x_bar + margin
            return data[(data[d_type] >= lower_bound) & (data[d_type] <= upper_bound)]
            
        df_result_cleaned = PI_outlier(df_result_cleaned, "interval")
        df_result_cleaned = PI_outlier(df_result_cleaned, "Leq")

        if station_name:
            out_path = f"./Processed-data/output_{station_name}.csv"
            os.makedirs("./Processed-data", exist_ok=True)
            df_result_cleaned[
                ["hours", "start_time", "end_time", "peak_time", "interval", "Leq"]
            ].to_csv(out_path, index=False)
        else:
            # Maintain legacy output.csv only for single-process usage
            os.makedirs("./Processed-data", exist_ok=True)
            df_result_cleaned[
                ["hours", "start_time", "end_time", "peak_time", "interval", "Leq"]
            ].to_csv("./Processed-data/output.csv", index=False)
        print("Calculate Complete")

        if return_unfiltered:
            return df_result_cleaned, df_result
        return df_result_cleaned


    def find_aircraft(self, df):
        def count_aircraft(f, df):
            for i in range(self.len_data // self.pts_result):
                hours_data = df[df["hours"] == i]
                Lae_in_this_hour = np.array(hours_data["Lae"])
                Leq_in_this_hour = np.array(hours_data["Leq"])

                if len(Lae_in_this_hour) == 0 and len(Leq_in_this_hour) == 0:
                    f.write("Hour#%d no aircraft.\n" % (i + 1))
                else:
                    Leq = SoundAddition(Leq_in_this_hour)
                    Lae = SoundAddition(Lae_in_this_hour)

                    f.write(
                        "Hour#%d has %d aircraft(s) and sum of Leq of those aircraft(s) is %f and Lae is %f.\n"
                        % ((i + 1), len(hours_data), Leq, Lae)
                    )
                f.write("\n")

        log_file = "./logs/num_aircraft_log.txt"

        print("Counting aircraft...")
        if os.path.isfile(log_file):
            f = open(log_file, "r+")
            f.truncate(0)
            f.seek(0)
            data = f.read(100)

            if len(data) > 0:
                f.write("\n")

            count_aircraft(f, df)
            f.close()
        else:
            with open(log_file, "a+") as f:
                f.seek(0)
                data = f.read(100)

                if len(data) > 0:
                    f.write("\n")

                count_aircraft(f, df)
                f.close()
        print("Counting complete")
        print()

    def matching_flight_with_peak(self, flights_file, peaks_df=None):
        if peaks_df is not None:
            peaks = peaks_df.copy()
        else:
            peaks = pd.read_csv("./Processed-data/output.csv")

        print("loading flight files...")
        if ".xlsx" in flights_file:
            xl = pd.ExcelFile(flights_file)
            sheet_list = xl.sheet_names

            if len(sheet_list) > 1:
                index = [
                    idx
                    for idx, s in enumerate(sheet_list)
                    if "Billing" in s or "billing" in s
                ]
                if len(index) >= 1:
                    # Read and concatenate all matching sheets
                    billing_sheets = [pd.read_excel(xl, sheet_name=sheet_list[i]) for i in index]
                    flights = pd.concat(billing_sheets, ignore_index=True)
                else:
                    sheet_dict = pd.read_excel(xl, sheet_name=None)
                    flights = pd.concat(sheet_dict.values(), ignore_index=True)
            else:
                flights = pd.read_excel(xl)

            if "LOCAL DATE.1" in flights.columns:
                flights.rename(columns={"LOCAL DATE.1": "LOCAL TIME"}, inplace=True)

            for col in flights.columns:
                if col in ["LOCAL DATE", "Local Date"]:
                    flights.rename(columns={col: "local_date"}, inplace=True)
                    flights["local_date"] = flights["local_date"].astype("str")
                    flights["local_date"] = flights["local_date"].apply(
                        lambda a: to_date(a)
                    )

                if col in ["LOCAL TIME", "Local Time"]:
                    flights.rename(columns={col: "local_time"}, inplace=True)
                    flights["local_time"] = flights["local_time"].astype("str")
                    flights["local_time"] = flights["local_time"].apply(
                        lambda a: to_time(a)
                    )

            flights["datetime"] = pd.to_datetime(
                flights["local_date"].astype("str")
                + " "
                + flights["local_time"].astype("str"),
                format='mixed'
            )
            flights["phase"] = flights["datetime"].apply(lambda a: phasedecide(a))

            print("Reading Flight File Successfully.")

            peaks["start_time"], peaks["end_time"] = pd.to_datetime(
                peaks["start_time"], format='mixed'
            ), pd.to_datetime(peaks["end_time"], format='mixed')

            print("matching filght...")
            flights = find_flight_peak(flights, peaks)
            flights_matched = match_peak(flights, peaks, self.lag_width)
            print("matching complete")

            for col in flights_matched.columns:
                if col in ["CALLSIGN", "ID"]:
                    flights_matched["airline_name"] = flights_matched[col].apply(
                        lambda a: call_airline_name(a)
                    )

                if col in ["POD", "FROM"]:
                    flights_matched["pod_name"] = flights_matched[col].apply(
                        lambda a: call_airport_name(a)
                    )

                if col in ["DEST", "TO"]:
                    flights_matched["dest_name"] = flights_matched[col].apply(
                        lambda a: call_airport_name(a)
                    )

            if "WTC" not in flights_matched.columns:
                for col in flights_matched.columns:
                    if col in ["AIRCRAFT TYPE", "ACTYPE"]:
                        flights_matched["WTC"] = flights_matched[col].apply(
                            lambda a: call_airplane_name(a)
                        )

            col_data = list(flights_matched.columns)

            if col_data.count("pod_name") + col_data.count("dest_name") == 2:
                flights_matched["pod_to_dest"] = (
                    flights_matched["pod_name"] + "➔" + flights_matched["dest_name"]
                )

            return flights_matched

def calculate_station_peaks_worker(raw_file, model, eps, min_samples, bandwidth, segment=False, K=100, mode='parallel', airport='unknown'):
    """
    Worker function to calculate peaks for a single station.
    Integrates clustering (DBSCAN/MSA) and 10dB Down validation.
    """
    import os
    import time
    import pandas as pd
    import numpy as np
    from src.scripts.aircraft_calculate import NoiseCalculation
    from src.scripts.modelling.validate import validate_10db_down
    
    start_time = time.time()
    res = {'peaks': None, 'timing': None}
    station_name = os.path.basename(raw_file).split('_noise_data.csv')[0]
    
    # Timing Metadata
    timing_data = {
        'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
        'airport': airport,
        'station': station_name,
        'mode': mode,
        'segment_used': bool(segment),
        'K': int(K) if segment else None,
        'duration_sec': 0.0,
        'model': model
    }
    try:
        df_noise = pd.read_csv(raw_file)
        # Robust timestamp conversion to avoid str - str errors
        if 'Period start' in df_noise.columns:
            df_noise['Period start'] = pd.to_datetime(df_noise['Period start'], errors='coerce', format='mixed')
        else:
            time_col = next((c for c in df_noise.columns if 'time' in c.lower() or 'period start' in c.lower() or 'date' in c.lower()), None)
            if time_col:
                df_noise['Period start'] = pd.to_datetime(df_noise[time_col], errors='coerce', format='mixed')
        
        if 'Period start' not in df_noise.columns or df_noise['Period start'].isnull().all():
            return None
        
        if 'Leq' not in df_noise.columns: return None
        
        calc = NoiseCalculation(n_pts='week', rate=95, is_std=True, lag_width=200)
        df_noise_with_groups = calc.find_localpeak_alternative(df_noise, model=model, esp=eps, min_samples=min_samples, bandwidth=bandwidth, segment=segment, K=K)
        df_peaks, df_peaks_unfiltered = calc.calculate_sound(df_noise_with_groups, station_name=station_name, return_unfiltered=True)
        
        if df_peaks_unfiltered is not None and not df_peaks_unfiltered.empty:
            df_peaks_unfiltered = df_peaks_unfiltered.reset_index(drop=True)
            df_peaks_unfiltered['Station'] = station_name
            res['peaks_unfiltered'] = df_peaks_unfiltered
        
        if df_peaks is not None and not df_peaks.empty:
            df_peaks = df_peaks.reset_index(drop=True)
            df_peaks['Station'] = station_name
            
            # --- Inline 10dB Down Validation ---
            # We need the original noise data context
            leq_values = df_noise['Leq'].values
            ts_values = df_noise['Period start'].values
            
            validated_flags = []
            for _, peak_row in df_peaks.iterrows():
                p_time = peak_row['start_time']
                is_valid = False
                try:
                    p_time_np = pd.to_datetime(p_time).to_datetime64()
                    idx_pos = np.searchsorted(ts_values, p_time_np)
                    # Find closest index
                    if idx_pos == 0: orig_idx = 0
                    elif idx_pos == len(ts_values): orig_idx = len(ts_values) - 1
                    else: orig_idx = idx_pos if abs(ts_values[idx_pos] - p_time_np) < abs(ts_values[idx_pos-1] - p_time_np) else idx_pos - 1
                    
                    is_valid = validate_10db_down(leq_values, orig_idx, drop_db=10)
                except: pass
                validated_flags.append(is_valid)
            
            df_peaks['Validated_10dB'] = validated_flags
            res['peaks'] = df_peaks
            
        duration = time.time() - start_time
        timing_data['duration_sec'] = round(duration, 2)
        res['timing'] = timing_data
        
        return res
    except Exception as e:
        print(f"Error calculating peaks for {station_name}: {e}")
        return res
