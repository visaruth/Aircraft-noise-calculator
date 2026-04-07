from sklearn.cluster import MeanShift
import pandas as pd
import numpy as np

def find_peaks_msa(data, time, bandwidth=None):
    """
    Find peaks using Mean Shift Algorithm with optimized parameters for speed.
    """
    if len(time) == 0:
        return pd.Series(dtype=int)
         
    # OPTIMIZATION: If bandwidth is None, set a safe default (150)
    # estimate_bandwidth is extremely slow
    if bandwidth is None:
        bandwidth = 150
        print(f"  Note: Bandwidth is not set. Using default value: {bandwidth}")
         
    # OPTIMIZATION 1: Downsampling for extremely large datasets
    # If we have more than 50,000 points, take every 5th point to speed up seeding
    # Mean Shift is O(n^2), so reducing n is the most effective way.
    original_time = time.copy()
    if len(time) > 50000:
        print(f"  Note: Large dataset detected ({len(time)} pts). Downsampling for seeding...")
        time_for_fit = time[::5]
    else:
        time_for_fit = time

    X_fit = time_for_fit.reshape(-1, 1)
    
    # OPTIMIZATION 2: bin_seeding=True is CRITICAL for large datasets in sklearn
    # It discretizes the points into a grid, making the number of seeds much smaller.
    ms = MeanShift(bandwidth=bandwidth, bin_seeding=True, min_bin_freq=5).fit(X_fit)
    
    # Map all original points to the found clusters
    X_all = original_time.reshape(-1, 1)
    labels = ms.predict(X_all)
    
    data_copy = data.loc[original_time].copy()
    data_copy["peak_group"] = labels
    
    return data_copy["peak_group"]
