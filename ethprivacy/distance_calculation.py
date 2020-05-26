import numpy as np
import pandas as pd

def euclidean_dist(a, b):
    return np.sqrt(np.sum(np.square(a-b)))

def nearest_neighbors(idx, X):
    if np.isnan(X).sum() > 0:
        raise RuntimeError("Representation matrix contains nans!")
    a = X[idx,:]
    indices = list(range(X.shape[0]))
    # exclude self distance
    indices.remove(idx)
    dist = np.array([euclidean_dist(a, X[i,:]) for i in indices])
    sorted_df = pd.DataFrame(list(zip(indices, dist)), columns=["idx","dist"]).sort_values("dist")
    return list(sorted_df["idx"]), list(sorted_df["dist"])

def get_neighbors(X, idx, include_idx_mask=[]):
    indices, distances = nearest_neighbors(idx, X)
    if len(include_idx_mask) > 0:
        # filter indices
        indices_tmp, distances_tmp = [], []
        for i, res_idx in enumerate(indices):
            if res_idx in include_idx_mask:
                indices_tmp.append(res_idx)
                distances_tmp.append(distances[i])
        indices = indices_tmp
        distances = distances_tmp
    return indices, distances 

def get_rank(X, query_idx, target_idx, include_idx_mask=[]):
    indices, distances = get_neighbors(X, query_idx, include_idx_mask)
    if len(indices) > 0 and target_idx in indices:
        trg_idx = indices.index(target_idx)
        return trg_idx+1, distances[trg_idx], len(indices)
    else:
        return None, None, len(indices)