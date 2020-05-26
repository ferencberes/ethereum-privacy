import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def get_deposit_indices(a2v_obj, tq, tup, f_id):
    """Extract the possible set of deposit address candidates for each heuristic record given different temporal filtering options"""
    if f_id == "day":
        d_addr_set = tq.get_possible_deposits(tup, 86400)
        anonymity_set_size = len(d_addr_set)
    elif f_id == "week":
        d_addr_set = tq.get_possible_deposits(tup, 7*86400)
        anonymity_set_size = len(d_addr_set)
    elif f_id == "past":
        d_addr_set = tq.get_possible_deposits(tup, None)
        anonymity_set_size = len(d_addr_set)
    else:
        d_addr_set = []
        anonymity_set_size = len(a2v_obj.addr_to_embedd)-1
    d_addr_idx = []
    for addr in d_addr_set:
        if addr in a2v_obj.addr2idx:
            d_addr_idx.append(a2v_obj.addr2idx[addr])
    return d_addr_idx, anonymity_set_size

def clean_heuristics(tornado_pairs, verbose):
    """Removing loops and Tornado contract addresses from the set of heuristics"""
    orig_size = len(tornado_pairs)
    # removing loops
    tornado_pairs = tornado_pairs[tornado_pairs["sender"]!=tornado_pairs["receiver"]]
    if verbose:
        print("Loops removed:", len(tornado_pairs) / orig_size)
    # removing Tornado cash 0.1ETH address    
    tornado_pairs = tornado_pairs[tornado_pairs["receiver"]!="0x12d66f87a04a9e220743712ce6d9bb1b5616b8fc"]
    if verbose:
        print("Tornado address removed:", len(tornado_pairs) / orig_size)
    return tornado_pairs

def temporal_filter(df, max_time):
    if max_time != None:
        return df[df["timeStamp"]<=max_time]
    else:
        return df
    
class TornadoQueries():
    def __init__(self, mixer_str_value="0.1", data_type="all", data_folder="../data", max_time=None, verbose=True):
        self.mixer_str_value = mixer_str_value
        self.data_type = data_type
        self.data_folder = data_folder
        self.max_time = max_time
        self.verbose = verbose
        self.history_df = temporal_filter(self._load_history(), self.max_time)
        self.tornado_pairs = temporal_filter(self._load_heuristics(), self.max_time)
        self.tornado_tuples = list(zip(self.tornado_pairs["sender"], self.tornado_pairs["receiver"], self.tornado_pairs["withdHash"], self.tornado_pairs["timeStamp"]))
        if self.verbose:
            print("history", self.history_df.shape)
            print("pairs", self.tornado_pairs.shape)      
    
    def _load_history(self):
        history_df = pd.read_csv("%s/tornadoFullHistoryMixer_%sETH.csv" % (self.data_folder, self.mixer_str_value))
        history_df = history_df.sort_values("timeStamp")
        history_df["contrib"] = history_df["action"].apply(lambda x: 1 if x == "d" else 0)
        history_df["num_deps"] = history_df["contrib"].cumsum()
        if "index" in history_df.columns:
            history_df = history_df.drop("index", axis=1)
        self.tornado_hash_time = dict(zip(history_df["txHash"],history_df["timeStamp"]))
        return history_df
    
    def _load_heuristics(self):
        if self.data_type == "heur2":
            tornado_pairs = pd.read_csv("%s/heuristic2Mixer_%sETH.csv" % (self.data_folder, self.mixer_str_value))
        elif self.data_type == "heur3":
            tornado_pairs = pd.read_csv("%s/heuristic3Mixer_%sETH.csv" % (self.data_folder, self.mixer_str_value))
        else:
            heur2 = pd.read_csv("%s/heuristic2Mixer_%sETH.csv" % (self.data_folder, self.mixer_str_value))
            heur3 = pd.read_csv("%s/heuristic3Mixer_%sETH.csv" % (self.data_folder, self.mixer_str_value))
            tornado_pairs = pd.concat([heur2,heur3])
        tornado_pairs = tornado_pairs.drop_duplicates()
        tornado_pairs["timeStamp"] = tornado_pairs["withdHash"].apply(lambda x: self.tornado_hash_time[x])
        tornado_pairs = clean_heuristics(tornado_pairs, self.verbose)
        if "Unnamed: 0" in tornado_pairs.columns:
            tornado_pairs = tornado_pairs.drop("Unnamed: 0", axis=1)
        return tornado_pairs
            
    def plot_num_deposits(self, show_heuristics=True, linew=3, msize=10):
        """Visualize the temporal distribution of the found withdraw-deposit address pairs (show_heuristics=True) or the number of active deposits (show_heuristics=False)"""
        df = self.history_df
        if show_heuristics:
            plt.plot(pd.to_datetime(self.tornado_pairs["timeStamp"], unit='s'), np.ones(len(self.tornado_pairs))*float(self.mixer_str_value),'x',label="%sETH" % self.mixer_str_value, linewidth=linew, markersize=msize)
        else:
            plt.plot(pd.to_datetime(df["timeStamp"], unit='s'),df["num_deps"], label="%sETH" % self.mixer_str_value, linewidth=linew, markersize=msize)
        plt.xticks(rotation=90)

    def get_possible_deposits(self, tornado_tuple, time_interval=None):
        """Get possible deposit address set for a withdraw transaction. Provide the 'time_interval' in seconds if you have some temporal assumption on the timestamp of the deposit."""
        d, w, h, time_bound  = tornado_tuple
        filtered_df = self.history_df[(self.history_df["action"]=="d") & (self.history_df["timeStamp"]<=time_bound)]
        if time_interval != None:
            filtered_df = filtered_df[filtered_df["timeStamp"] >= (time_bound-time_interval)]
        return list(filtered_df["account"].unique())