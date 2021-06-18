import pandas as pd
import networkx as nx
from .topic_analysis import addresses_of_interest

class GraphFactory():
    def __init__(self, txs_df, source_col, target_col):
        self.G = nx.from_pandas_edgelist(txs_df, source=source_col, target=target_col, edge_attr="timeStamp", create_using=nx.MultiDiGraph)
        
    def info(self):
        return self.G.number_of_nodes(), self.G.number_of_edges()
    
    def _time_filter(self, min_time, max_time):
        G = self.G
        check_min = (min_time != None)
        check_max = (max_time != None)
        if  check_min or check_max:
            selected = []
            for edge in G.edges(data=True):
                time_stamp = edge[2]["timeStamp"]
                valid = True
                if check_min:
                    valid = time_stamp >= min_time
                if check_max:
                    valid = valid and time_stamp <= max_time
                if valid:
                    selected.append((edge[0],edge[1], time_stamp))
            sub_graph = nx.MultiDiGraph()
            sub_graph.add_weighted_edges_from(selected, weight="timeStamp")
            print(sub_graph.number_of_edges() / G.number_of_edges())
            return sub_graph
        else:
            return G    
    
    def query_addresses(self, address_list, min_time, max_time):
        H = self._time_filter(min_time, max_time)
        in_links = pd.DataFrame(list(H.in_edges(address_list)), columns=["src","trg"])
        in_neighbors = dict(in_links.groupby("trg")["src"].apply(set))
        out_links = pd.DataFrame(list(H.out_edges(address_list)), columns=["src","trg"])
        out_neighbors = dict(out_links.groupby("src")["trg"].apply(set))
        return in_neighbors, out_neighbors

def dataframe_time_filter(df, min_time, max_time):
    check_min = (min_time != None)
    check_max = (max_time != None)
    if check_min or check_max:
        tmp = df.copy()
        if check_min:
            tmp = tmp[tmp["timeStamp"] >= min_time]
        if check_max:
            tmp = tmp[tmp["timeStamp"] <= max_time]
        return tmp
    return df
    
def filter_tx_df(df, api, address_filter, hash_to_remove=[]):
    addresses, ens_addresses, tornado_addresses, hd_addresses = addresses_of_interest(api, with_tornado=True, with_hd=True, verbose=False)
    if address_filter == "ens":
        keep_these = ens_addresses
    elif address_filter == "tornado":
        keep_these = tornado_addresses
    elif address_filter == "hd":
        keep_these = hd_addresses
    else:
        keep_these = addresses
    tmp_df = df[df["from"].isin(keep_these) | df["to"].isin(keep_these)]
    if len(hash_to_remove) > 0:
        tmp_df = tmp_df[~tmp_df["hash"].isin(hash_to_remove)]
        print("removed %i hashes" % len(hash_to_remove))
    return tmp_df
    
class EntityAPI():
    def __init__(self, data_dir, only_pos_tx=False, address_filter="aoi", hash_to_remove=[], verbose=False):
        self.verbose = verbose
        self.data_dir = data_dir
        self.address_filter = address_filter
        self.hash_to_remove = hash_to_remove
        self.only_pos_tx = only_pos_tx
        self.max_ens_per_address = 1
        self.ens_pairs = pd.read_csv("%s/all_ens_pairs.csv" % data_dir)
        if "Unnamed: 0" in self.ens_pairs.columns:
            self.ens_pairs.drop("Unnamed: 0", axis=1, inplace=True)
        self.normal_txs = pd.read_csv("%s/raw_normal_txs.csv" % data_dir)
        self.token_txs = pd.read_csv("%s/raw_token_txs.csv" % data_dir)
        self._clean()
        self.address2ens = dict(zip(self.ens_pairs["address"], self.ens_pairs["name"]))
        self._init_graphs()
        self.info()
        
    def info(self):
        """Show colleted data size"""
        print("ens_pairs", self.ens_pairs.shape)
        print("normal_txs", self.normal_txs.shape)
        print("token_txs", self.token_txs.shape)
        print("normal_graph", self.normal_graph.info())
        print("token_graph", self.token_graph.info())
        print("contract_graph", self.contract_graph.info())
        print("rev_contract_graph", self.rev_contract_graph.info())
        print("Number of unique ENS names:", len(self.ens_pairs["name"].unique()))
        print("Number of Etherscan events:", len(self.events))
        print("Number of unique tx hashes:", len(self.events["hash"].unique()))
        print("Number of accounts:", len(set(self.events["from"]).union(set(self.events["to"]))))
        print("min time", pd.to_datetime(self.events["timeStamp"].min(), unit='s'))
        print("max time", pd.to_datetime(self.events["timeStamp"].max(), unit='s'))
        
    def _clean(self):
        # lowercasing
        for col in ["name","address"]:
            self.ens_pairs[col] = self.ens_pairs[col].str.lower()
        for col in ["from","to"]:
            self.normal_txs[col] = self.normal_txs[col].str.lower()
            self.token_txs[col] = self.token_txs[col].str.lower()
        self.token_txs["contractAddress"] = self.token_txs["contractAddress"].str.lower()
        # exclude zero value txs
        if self.only_pos_tx:
            self.normal_txs = self.normal_txs[self.normal_txs["value"] > 0]
            self.token_txs = self.token_txs[self.token_txs["value"] > 0]
        # exclude addresses with multiple ENS names
        num_ens_for_addr = self.ens_pairs.groupby("address")["name"].nunique().sort_values(ascending=False).reset_index()
        excluded = list(num_ens_for_addr[num_ens_for_addr["name"] > self.max_ens_per_address]["address"])
        self.ens_pairs = self.ens_pairs[~self.ens_pairs["address"].isin(excluded)]
        if self.verbose:
            print("Number of addresses excluded from ens pairs: %i" % len(set(excluded)))
        old_normal_size = len(self.normal_txs)
        old_token_size = len(self.token_txs)
        self.normal_txs = filter_tx_df(self.normal_txs, self, self.address_filter, self.hash_to_remove)
        self.token_txs = filter_tx_df(self.token_txs, self, self.address_filter, self.hash_to_remove)
        if self.verbose:
            print("Normal", len(self.normal_txs) / old_normal_size, "Token", len(self.token_txs) / old_token_size)
        self.token_txs["tx_type"] = "token"
        cols = list(self.normal_txs.columns)
        cols.remove("isError")
        self.events = pd.concat([self.normal_txs[cols], self.token_txs[cols]]).sort_values("timeStamp")
            
    def _init_graphs(self):
        self.normal_graph = GraphFactory(self.normal_txs, "from", "to")
        self.token_graph = GraphFactory(self.token_txs, "from", "to")
        self.contract_graph = GraphFactory(self.token_txs, "from", "contractAddress")
        self.rev_contract_graph = GraphFactory(self.token_txs, "contractAddress", "to")
        
    def _mask(self, address_list):
        hits = set(address_list).intersection(set(self.address2ens.keys()))
        return set(self.address2ens[addr] for addr in hits)
        
    def _time_filter(self, min_time, max_time):
        return dataframe_time_filter(self.normal_txs, min_time, max_time), dataframe_time_filter(self.token_txs, min_time, max_time)
        
    def ens_addresses(self, ens_name):
        """Get every address that is related to the given ENS name"""
        return list(self.ens_pairs.query("name=='%s'" % str(ens_name).lower())["address"].unique())
    
    def ens_info(self, ens_name, min_time=None, max_time=None):
        """Get information about an ENS name"""
        ens_tmp = str(ens_name).lower()
        addr_list = self.ens_addresses(ens_tmp)
        records = [self.address_info(addr, min_time=min_time, max_time=max_time) for addr in addr_list]
        records_df = pd.DataFrame(records)
        records_df["num_ens"] = records_df["ens_names"].apply(len)
        return records_df
    
    def address_info(self, address_str, min_time=None, max_time=None):
        """Get information about an Ethereum address"""
        address = str(address_str).lower()
        normal_tmp, token_tmp = self._time_filter(min_time, max_time)
        ens_info = sorted(list(self.ens_pairs.query("address=='%s'" % address)["name"].unique())) if address in set(self.ens_pairs["address"]) else []
        has_normal_outbound_tx = address in set(normal_tmp["from"])
        has_normal_inbound_tx = address in set(normal_tmp["to"])
        has_token_outbound_tx = address in set(token_tmp["from"])
        has_token_inbound_tx = address in set(token_tmp["to"])
        is_contract = address in set(token_tmp["contractAddress"])
        return {
            "is_contract":is_contract, 
            "normal_in":has_normal_inbound_tx, 
            "normal_out":has_normal_outbound_tx, 
            "token_in":has_token_inbound_tx,
            "token_out":has_token_outbound_tx,
            "address":address,
            "ens_names":ens_info
        }
    
    def contract_info(self, address_str, min_time=None, max_time=None, ens_result=False):
        address = str(address_str).lower()
        _, token_tmp = self._time_filter(min_time, max_time)
        in_neigh = set(token_tmp[token_tmp["contractAddress"]==address]["from"])
        out_neigh = set(token_tmp[token_tmp["contractAddress"]==address]["to"])
        return {
            "address": address,
            "senders": self._mask(in_neigh) if ens_result else in_neigh,
            "receivers": self._mask(out_neigh) if ens_result else out_neigh
        }
    
    def address_txs(self, address_str, min_time=None, max_time=None):
        """Get every transaction related to an Ethereum address"""
        address = str(address_str).lower()
        normal_tmp, token_tmp = self._time_filter(min_time, max_time)
        normal = normal_tmp[(normal_tmp["from"]==address) | (normal_tmp["to"]==address)]
        normal["contractAddress"] = None
        normal["type"] = "normal"
        token = token_tmp[(token_tmp["from"]==address) | (token_tmp["to"]==address)]
        token["type"] = "token"
        common_cols = ["timeStamp","from","to","contractAddress","nonce","type"]
        txs = pd.concat([normal[common_cols], token[common_cols]])
        return txs.sort_values("timeStamp")
    
    def neighbors(self, address_list, min_time=None, max_time=None, ens_result=False):
        """Get transaction neighbors of an Ethereum address in the given time interval"""
        normal_in, normal_out = self.normal_graph.query_addresses(address_list, min_time, max_time)
        token_in, token_out = self.token_graph.query_addresses(address_list, min_time, max_time)
        _, to_contract = self.contract_graph.query_addresses(address_list, min_time, max_time)
        from_contract, _ = self.rev_contract_graph.query_addresses(address_list, min_time, max_time)
        res = {}
        for addr in address_list:
            res[addr] = {
                "normal_in":normal_in.get(addr, set()),
                "normal_out":normal_out.get(addr, set()),
                "token_in":token_in.get(addr, set()),
                "token_out":token_out.get(addr, set()),
                "to_contract":to_contract.get(addr, set()),
                "from_contract":from_contract.get(addr, set())
            }
            if ens_result:
                for key in res[addr]:
                    res[addr][key] = self._mask(res[addr][key])
        return res
    
    def topic_neighbors(self, address_list, selected_addr_info, result_type="topic"):
        """Get the topic of transaction neighbor addresses. More detailed output is given in case of result_type='name'."""
        topic_map = dict(zip(selected_addr_info["address"], selected_addr_info["topic"]))
        name_map = dict(zip(selected_addr_info["address"], selected_addr_info["name"]))
        neigh = self.neighbors(address_list)
        output = {}
        for node in address_list:
            res = {}
            for key in neigh[node]:
                res[key] = set([])
                for addr in neigh[node][key]:
                    if addr in topic_map:
                        if result_type == "name":
                            res[key].add((topic_map[addr], name_map[addr]))
                        else:
                            res[key].add(topic_map[addr])
            output[node] = res
        return output