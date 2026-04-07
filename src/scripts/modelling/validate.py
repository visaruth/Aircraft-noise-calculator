import pandas as pd
import numpy as np

def validate_10db_down(noise_series, peak_index, drop_db=10, max_search_window=60):
    """
    Validates if a peak represents an aircraft noise event using the '10 dB down' method.
    The noise level must drop by at least `drop_db` (typically 10 dB) on both sides of the peak
    within a search window.

    :param noise_series: Pandas Series or NumPy array containing the continuous noise level data (e.g., Leq) over time.
    :param peak_index: The integer location (index position) of the peak in the noise_series.
    :param drop_db: The required dB drop to validate the event (default is 10 dB).
    :param max_search_window: Maximum number of data points (e.g., seconds if 1Hz data) to look forward and backward to find the 10 dB drop.
    :return: Boolean indicating whether it is a valid 10 dB down event.
    """
    # Convert Pandas Series to NumPy array for fast integer indexing
    if isinstance(noise_series, pd.Series):
        noise_data = noise_series.values
    else:
        noise_data = np.array(noise_series)
        
    if peak_index < 0 or peak_index >= len(noise_data):
        return False
        
    peak_value = noise_data[peak_index]
    target_value = peak_value - drop_db
    
    # Check left side (before the peak)
    left_valid = False
    left_bound = max(0, peak_index - max_search_window)
    for i in range(peak_index - 1, left_bound - 1, -1):
        if noise_data[i] <= target_value:
            left_valid = True
            break
            
    # Check right side (after the peak)
    right_valid = False
    right_bound = min(len(noise_data), peak_index + max_search_window + 1)
    for i in range(peak_index + 1, right_bound):
        if noise_data[i] <= target_value:
            right_valid = True
            break
            
    return left_valid and right_valid

def filter_peaks_10db_down(noise_series, peak_indices, drop_db=10, max_search_window=60):
    """
    Filters a list of peak indices, returning only those that pass the 10 dB down test.

    :param noise_series: Pandas Series or NumPy array containing the noise level data.
    :param peak_indices: List or array of integer peak indices.
    :param drop_db: The required dB drop.
    :param max_search_window: Search window length on each side.
    :return: List of valid peak indices.
    """
    valid_peaks = []
    for peak_idx in peak_indices:
        if validate_10db_down(noise_series, peak_idx, drop_db, max_search_window):
            valid_peaks.append(peak_idx)
    return valid_peaks

def apply_10db_down_validation(df, noise_column='Leq', peak_col='is_peak', drop_db=10, max_search_window=60):
    """
    Applies the 10 dB down validation on a DataFrame that already has identified peaks.

    :param df: DataFrame containing the noise data and peaks.
    :param noise_column: Column name containing the noise values.
    :param peak_col: Column name indicating if a row is a peak (boolean or 1/0).
    :param drop_db: Required drop in dB (default 10).
    :param max_search_window: Maximum number of rows to search before and after the peak.
    :return: DataFrame with a new column 'is_valid_event' indicating 10dB down valid events.
    """
    df_result = df.copy()
    
    # Get integer positions of the peaks
    peak_positions = np.where(df_result[peak_col] == True)[0]
    
    # Apply filter
    valid_positions = filter_peaks_10db_down(
        df_result[noise_column], 
        peak_positions, 
        drop_db=drop_db, 
        max_search_window=max_search_window
    )
    
    # Create the validation column
    df_result['is_valid_event'] = False
    df_result.iloc[valid_positions, df_result.columns.get_loc('is_valid_event')] = True
    
    return df_result
