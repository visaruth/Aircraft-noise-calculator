from sklearn.cluster import DBSCAN


def find_peaks(data, time, eps=150, min_samples=10):
    data_copy = data.copy()
    X = time.reshape(-1, 1)
    dbscan = DBSCAN(eps=eps, min_samples=min_samples).fit(X)

    data_copy = data_copy.loc[time]
    data_copy["peak_group"] = dbscan.labels_
    data_copy = data_copy[data_copy["peak_group"] != -1]
    return data_copy["peak_group"]
