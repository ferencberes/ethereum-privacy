import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from tqdm import tqdm

from .distance_calculation import get_rank
from .tornado_mixer import get_deposit_indices

def show_patterns(events_df, addresses, gas_bins=50, hour_bins=24, figsize=(15,3), show_kde=False, log_gas=False):
    """Show side channels distribution of the given addresses"""
    if show_kde:
        fig, ax = plt.subplots(1,2, figsize=(15,3))
        for address in addresses:
            user_txs = events_df[events_df["from"]==address]
            print(address, len(user_txs))
        plt.subplot(1,2,1)
        try:
            for address in addresses:
                user_txs = events_df[events_df["from"]==address]
                user_txs["normalized_gas"].plot.kde()
            if log_gas:
                plt.xlim([0,np.log(1+5)])
            else:
                plt.xlim([0,5])
            plt.subplot(1,2,2)
            for address in addresses:
                user_txs = events_df[events_df["from"]==address]
                user_txs["hour"].plot.kde()
            plt.xlim([0,86400])
        except Exception as e:
            print(e)
    fig, ax = plt.subplots(1,2, figsize=(15,3))
    plt.subplot(1,2,1)
    for address in addresses:
        user_txs = events_df[events_df["from"]==address]
        user_txs["normalized_gas"].hist(bins=gas_bins, range=(0.0, events_df["normalized_gas"].max()), alpha=0.5)
    if log_gas:
        plt.xlim([0,np.log(1+5)])
    else:
        plt.xlim([0,5])
    plt.subplot(1,2,2)
    for address in addresses:
        user_txs = events_df[events_df["from"]==address]
        user_txs["hour"].hist(bins=hour_bins, range=(0,86400), alpha=0.5)

def preproc_node_embeddings(df, a2v_obj):
    """Reorder node representations and handle missing addresses according to the given Address2Vec object."""
    nodes = list(a2v_obj.addr_to_embedd)
    missing = set(nodes).difference(set(df["address"]))
    node_emb = df[df["address"].isin(nodes)]
    # handle missing addresses
    mean_repr = list(node_emb.mean())
    missing_df = pd.DataFrame([mean_repr for _ in range(len(missing))])
    missing_df["address"] = list(missing)
    missing_df.columns = node_emb.columns
    # concatenation
    augmented_df = pd.concat([node_emb, missing_df], ignore_index=True)
    augmented_df = augmented_df.set_index("address")
    augmented_df = augmented_df.loc[nodes,:]
    return augmented_df.values

class Address2Vec():
    def __init__(self, events_df=None, norm_type="ptp", min_tx_cnt=10, gas_bins=25, hour_bins=6, use_hour=True, use_gas=True, use_stats=True, use_distrib=True, aggregations=["mean","median","std"], node_emb=None, verbose=True):
        self.min_tx_cnt = min_tx_cnt
        self.gas_bins = gas_bins
        self.hour_bins = hour_bins
        self.use_hour = use_hour
        self.use_gas = use_gas
        self.use_stats = use_stats
        self.use_distrib = use_distrib
        self.aggregations = aggregations
        self.node_emb = node_emb
        self.verbose = verbose
        self.events = events_df
        if norm_type in [None,"normal","ptp"]:
            self.norm_type = norm_type
        else:
            raise RuntimeError("Invalid normalization!")
        self.X = None
        self.id = "h%s_g%s_s%s_d%s_hb%i_gb%i_tx%i_nt%s_%s" % (self.use_hour, self.use_gas, self.use_stats, self.use_distrib, self.hour_bins, self.gas_bins, self.min_tx_cnt, self.norm_type,  "_".join(aggregations))
        if not events_df is None:
            self._calculate_address_stats()
            self.X = self._preprocess()
      
    def _calculate_address_stats(self):
        """Calculate basic statistics for addresses based on side their side channels"""
        feature_cols = []
        if self.use_hour:
            feature_cols.append("hour")
        if self.use_gas:
            feature_cols.append("normalized_gas")
        self.feature_cols = feature_cols
        agg_map = {"hash":["count"]}
        for col in self.feature_cols:
            agg_map[col] = self.aggregations
        self.stats = self.events.groupby("from").agg(agg_map).reset_index()
        self.filtered_stats = self.stats[self.stats[("hash","count")] >= self.min_tx_cnt].reset_index(drop=True)
        self.addr_to_embedd = list(self.filtered_stats["from"])
        # mappings
        self.idx2addr = dict(self.filtered_stats["from"])
        self.addr2idx = dict(zip(self.idx2addr.values(), self.idx2addr.keys()))
        # filter
        self.events = self.events[self.events["from"].isin(self.addr_to_embedd)]
        # info
        if self.verbose:
            print("Number of embedded addresses:", len(self.addr_to_embedd))
            print("Ratio of embedded addresses: %.2f" % (len(self.addr_to_embedd) / len(self.stats)))
        
    def _stat_based_repr(self):
        """Prepare basic side channels statistics"""
        A = self.filtered_stats.drop("from",axis=1,level=0).drop(("hash","count"),axis=1).values
        if self.verbose:
            print("Statistics based representation dimensions:", A.shape)
        # replace missing values for std
        #print(A.shape)
        A = np.nan_to_num(A,nan=0.0)
        return A
    
    def _distribution_based_repr(self):
        """Prepare address representation based on side channel distribution"""
        max_gas_price = self.events["normalized_gas"].max()
        events_tmp = self.events.copy()
        cols = self.feature_cols.copy()
        events_tmp = events_tmp[["from","hash"]+cols]
        # discretization
        if self.use_gas and self.gas_bins > 0:
            norm_gas_interval = max_gas_price / self.gas_bins
            events_tmp["normalized_gas"] = (events_tmp["normalized_gas"] // norm_gas_interval).astype("int64")
        if self.use_gas and self.gas_bins == 0:
            cols.remove("normalized_gas")
        if self.use_hour and self.hour_bins > 0:
            hour_interval = 86400 / self.hour_bins
            events_tmp["hour"] = (events_tmp["hour"] // hour_interval).astype("int64")
        if self.use_hour and self.hour_bins == 0:
            cols.remove("hour")
        # extract distribution
        parts = []
        for col in cols:
            distrib = events_tmp.groupby(["from",col])["hash"].count().reset_index()
            pivot = distrib.pivot(index="from", columns=col, values="hash").fillna(0.0)
            parts.append(pivot)
        if len(parts) > 0:
            B = np.concatenate(parts, axis=1)
            # normalization
            tx_counts = np.array(self.filtered_stats[("hash","count")])
            B = B / tx_counts.reshape(-1,1)
        else:
            B = np.array([])
        if self.verbose:
            print("Distribution based representation dimensions:", B.shape)
        return B
    
    def _preprocess(self):
        """Concatenate and normalize multiple representations"""
        # concatenate features
        A = self._stat_based_repr()
        B = self._distribution_based_repr()
        X = None
        if self.use_stats and self.use_distrib:
            if B.shape[0] > 0:
                X = np.concatenate([A,B],axis=1)
            else:
                X = A
        elif self.use_stats and not self.use_distrib:
            X = A
        elif self.use_distrib and not self.use_stats:
            X = B
        # add node embedding
        if self.node_emb is not None:
            proc_node_emb = preproc_node_embeddings(self.node_emb, self)
            print("node embedding", proc_node_emb.shape)
            if X is None:
                X = proc_node_emb
            else:
                X = np.concatenate([X,proc_node_emb],axis=1)
        # normalization
        if self.norm_type == "normal":
            X = (X - X.mean(0)) / X.std(0)
        elif self.norm_type == "ptp":
            X = (X - X.min(0)) / X.ptp(0) 
        if self.verbose:
            print("Total dimensions:", X.shape)
        return X
    
    def get_idx_pairs(self, api, min_cnt=2, max_cnt=2, mirror=True):
        """Extract the indices of ENS address pairs for evaluation."""
        # extract ens names
        pairs = api.ens_pairs.copy()
        pairs = pairs[pairs["address"].isin(self.addr_to_embedd)]
        ens_counts = pairs["name"].value_counts()
        idx_pairs = []
        all_ens_names = []
        for cnt in range(min_cnt, max_cnt+1):
            ens_names = list(ens_counts[ens_counts == cnt].index)
            all_ens_names += ens_names
            # convert to indices
            for ename in ens_names:
                addrs = list(set(api.ens_addresses(ename)).intersection(set(self.addr_to_embedd)))
                for i in range(len(addrs)):
                    for j in range(i+1,len(addrs)):
                        addr1, addr2 = addrs[i], addrs[j]
                        idx1, idx2 = self.addr2idx[addr1], self.addr2idx[addr2]
                        idx_pairs.append([idx1,idx2])
                        if mirror:
                            idx_pairs.append([idx2,idx1])
        return idx_pairs, all_ens_names
        
    def run_ens(self, idx_pairs, model_id):
        """Evaluate representations for ENS address pairs"""
        pbar = tqdm(total=len(idx_pairs))
        records = []
        for pair in idx_pairs:
            rank, dist, num_set = get_rank(self.X, pair[1], pair[0])
            records.append((pair[1], pair[0], rank, dist, num_set, "none"))
            pbar.update(1)
        df = pd.DataFrame(records, columns=["query_idx", "target_idx", "rank", "dist", "set_size", "filter"])
        df["embedding_id"] = model_id
        df["query_addr"] = df["query_idx"].apply(lambda x: self.idx2addr[x])
        df["target_addr"] = df["target_idx"].apply(lambda x: self.idx2addr[x])
        return df.drop(["query_idx","target_idx"], axis=1)
    
    def run_tornado(self, query_objects, model_id, filters=["none", "past", "week", "day"]):
        """Evaluate representations for Tornado withdraw-deposit heuristics"""
        res = []
        pbar = tqdm(total=len(query_objects))
        for tq in query_objects:
            records = []
            for tup in tq.tornado_tuples:
                d_addr, w_addr = tup[0], tup[1]
                if d_addr in self.addr2idx and w_addr in self.addr2idx:
                    d_idx, w_idx = self.addr2idx[d_addr], self.addr2idx[w_addr] 
                    for f_id in filters:
                        # anonymity set size is needed without filters
                        d_set_idx, size_1 = get_deposit_indices(self, tq, tup, f_id)
                        rank, dist, size_2 = get_rank(self.X, w_idx, d_idx, d_set_idx)
                        num_set = max(size_1, size_2)
                        records.append((tup[3], w_idx, d_idx, rank, dist, num_set, f_id))
            df = pd.DataFrame(records, columns=["timestamp","query_idx","target_idx","rank","dist","set_size","filter"])
            df["embedding_id"] = model_id
            df["mixer"] = tq.mixer_str_value
            res.append(df)
            pbar.update(1)
        pbar.close()
        df = pd.concat(res)
        df["query_addr"] = df["query_idx"].apply(lambda x: self.idx2addr[x])
        df["target_addr"] = df["target_idx"].apply(lambda x: self.idx2addr[x])
        return df.drop(["query_idx","target_idx"], axis=1)
