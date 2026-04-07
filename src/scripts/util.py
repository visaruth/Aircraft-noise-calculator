import numpy as np
import pandas as pd
import os

def calculate_log_average(series):
    """
    Calculate the equivalent continuous sound level (Leq) 
    using logarithmic averaging.
    """
    if len(series) == 0:
        return np.nan
    power = np.power(10, series / 10.0)
    avg_power = np.mean(power)
    if avg_power <= 0:
        return 0
    return 10 * np.log10(avg_power)

def get_operation(df_flights, start_time, end_time, time_col='datetime_th'):
    """
    Determine the primary operation type (Arrival or Departure) during a given time window.
    Assumes `df_flights` has an `APPDEPFLAG` column.
    """
    if df_flights.empty:
        return 'Unknown'
        
    mask = (df_flights[time_col] >= start_time) & (df_flights[time_col] <= end_time)
    relevant_flights = df_flights[mask]
    
    if relevant_flights.empty:
        return 'Unknown'
        
    ops = relevant_flights['APPDEPFLAG'].value_counts()
    if ops.empty:
        return 'Unknown'
        
    primary_op = ops.idxmax()
    return 'Arrival' if primary_op == 'A' else 'Departure'

def get_station_name(filepath):
    """
    Extract station name from a filename pattern like `..._noise_data.csv` or similar.
    """
    filename = os.path.basename(filepath)
    # Common replacements to isolate the station name
    name = filename.replace('_noise_data.csv', '')
    name = name.replace('Converted_Flight_Log_', '').replace('.xlsx', '')
    name = name.replace('complete_pipeline_', '').replace('.ipynb', '')
    return name

def merge_intervals(intervals):
    """
    Merge overlapping time intervals.
    intervals: list of tuples (start_datetime, end_datetime)
    Returns list of merged tuples.
    """
    if not intervals:
        return []
        
    sorted_intervals = sorted(intervals, key=lambda x: x[0])
    merged = [sorted_intervals[0]]
    
    for current in sorted_intervals[1:]:
        previous = merged[-1]
        
        # If the current interval overlaps with the previous one, merge them
        if current[0] <= previous[1]:
            merged[-1] = (previous[0], max(previous[1], current[1]))
        else:
            merged.append(current)
            
    return merged

def is_time_in_intervals(t, intervals):
    """
    Check if a given datetime `t` falls within any of the `intervals`.
    """
    for start, end in intervals:
        if start <= t <= end:
            return True
    return False

def check_flight(row, intervals, time_col='datetime_th'):
    """
    Helper function for DataFrame apply to check if a flight's time is within valid intervals.
    """
    t = row[time_col]
    if pd.isna(t):
         return False
    return is_time_in_intervals(t, intervals)

def get_optimal_max_workers():
    """
    Calculate max workers based on available CPU and RAM.
    Assumes each process might need ~4GB of RAM for safety.
    """
    import os
    import psutil
    cpu_count = os.cpu_count() or 1
    total_mem_gb = psutil.virtual_memory().total / (1024**3)
    # Limit workers so we don't exceed RAM or CPU
    mem_workers = max(1, int(total_mem_gb / 4.0)) 
    limit = min(cpu_count, mem_workers)
    # Hard cap at 8 to keep system responsive
    return max(1, min(limit, 8))

def determine_operation(pod, dest, airport='vtbs'):
    """
    Determine operation type (Landing/Take-off) based on origin/destination.
    """
    pod, dest = str(pod).upper(), str(dest).upper()
    airport_code = airport.upper()
    if pod == airport_code: return 'Take-off'
    elif dest == airport_code: return 'Landing'
    return 'Unknown'

def get_stations(df):
    """
    Get sorted list of unique stations from a DataFrame.
    """
    if df is not None and not df.empty and 'Station' in df.columns:
        return sorted(df['Station'].unique())
    return []
