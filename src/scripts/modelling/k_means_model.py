from sklearn.cluster import KMeans
import kneed


def sound_clustering(X):
    sse = {}
    for k in range(1, 5):
        kmeans = KMeans(n_clusters=k, random_state=0).fit(X)
        sse[k] = kmeans.inertia_

    kn = kneed.KneeLocator(
        x=list(sse.keys()),
        y=list(sse.values()),
        curve="convex",
        direction="decreasing",
        S=0.0,
    )

    k = kn.knee
    kmeans_best = KMeans(n_clusters=k, random_state=0).fit(X)
    return kmeans_best
