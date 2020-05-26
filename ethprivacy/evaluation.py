import os
import pandas as pd
import matplotlib.pyplot as plt

### Rank ###

def get_avg_rank(df, keys=["embedding_id", "filter"]):
    """Aggregate results for independent experiments"""
    target_cols = ["rank","set_size"]
    if "mixer" in df.columns and "mixer" not in keys:
        keys.append("mixer")
    for col in ["rank_ratio","auc"]:
        if col in df.columns:
            target_cols.append(col)
    # aggregate for independent experiments
    mean_result = df.groupby(["query_addr", "target_addr"]+keys)[target_cols].mean().reset_index()
    # aggregate for address pairs
    perf = mean_result.groupby(keys)[target_cols].mean().reset_index()
    return perf, mean_result