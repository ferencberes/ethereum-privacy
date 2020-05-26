import pandas as pd
from tqdm import tqdm
import json

def load_address_topics(path_to_json, removed_topics=["News", "Security", "Heists", "Sports", "Investment", "Retail", "Real Estate"]):
    """Load relevant service categories from a prepared JSON file"""
    with open(path_to_json) as f:
        address_by_topic = json.load(f)
    # remove low activity topics
    for topic in removed_topics:
        del address_by_topic[topic]
    # merging health categories
    address_by_topic["Insurance/Healthcare"] = address_by_topic["Insurence"] + address_by_topic["Healthcare"]
    del address_by_topic["Insurence"]
    del address_by_topic["Healthcare"]
    # merging exchange categories
    address_by_topic["Exchange"] = address_by_topic["Exchange"] + address_by_topic["Poloniex"] + address_by_topic["Binance"] + address_by_topic["Kraken"] + address_by_topic["Gemini"] + address_by_topic["Bitfinex"] + address_by_topic["Okex"]
    for col in ["Poloniex","Binance","Kraken","Gemini","Bitfinex","Okex"]:
        del address_by_topic[col]
    # merging trading categories
    address_by_topic["Trading"] = address_by_topic["Trading"] + address_by_topic["Bittrex"]
    del address_by_topic["Bittrex"]
    # collect topic addresses
    topic_for_addr = {}
    name_for_addr = {}
    for topic in address_by_topic:
        print(topic)
        for item in address_by_topic[topic]:
            addr, name = item
            addr = str(addr).lower()
            if addr in topic_for_addr:
                print(addr, topic_for_addr[addr], topic)
            else:
                topic_for_addr[addr] = topic
                name_for_addr[addr] = name
    return topic_for_addr, name_for_addr

def get_in_out_connections_for_addr(entity_api, address, is_contract, is_ens_result=True):
    """Collect entities that were in connection to a given address"""
    interactions = list(entity_api.neighbors([address], ens_result=is_ens_result).values())
    if is_contract:
        interactions += [entity_api.contract_info(address, ens_result=is_ens_result)]
    inbound, outbound = set(), set()
    for record in interactions:
        for key in record:
            if "in" in key or "sender" in key:
                # sent tx to address or transfered this token
                inbound = inbound.union(record[key])
            elif "out" in key or "receiver" in key:
                # received tx from this account or got this token
                outbound = outbound.union(record[key])
    return inbound, outbound

def get_in_out_ens_connections(entity_api, selected_addr_info):
    """Collect entities that were in connection to the addresses of interest"""
    inbound, outbound = {}, {}
    indices = list(selected_addr_info.index)
    for idx in tqdm(indices):
        row = selected_addr_info.loc[idx]
        is_contract = row["is_contract"]
        topic = row["topic"]
        address = row["address"]
        name = row["name"]
        if not topic in inbound:
            inbound[topic] = {}
            outbound[topic] = {}
        if not name in inbound[topic]:
            inbound[topic][name] = set()
            outbound[topic][name] = set()
        in_, out_ = get_in_out_connections_for_addr(entity_api, address, is_contract, is_ens_result=True)
        inbound[topic][name] = inbound[topic][name].union(in_)
        outbound[topic][name] = outbound[topic][name].union(out_)
    return inbound, outbound

def calculate_ens_coverage(inbound, outbound, num_uniq_ens, result_type="name", connection_type="both"):
    """Calculate the fraction of ens names that interacted with given topics or addresses"""
    counts = []
    for topic in inbound:
        hits_set = set()
        for name in inbound[topic]:
            if connection_type == "inbound":
                hits = inbound[topic][name]
            elif connection_type == "outbound":
                hits = outbound[topic][name]
            else:
                hits = outbound[topic][name].union(inbound[topic][name])
            if result_type == "topic":
                hits_set = hits_set.union(hits)
            else:
                counts.append((topic, name, connection_type, len(hits), len(hits) / num_uniq_ens))
        if result_type == "topic":
            counts.append((topic, connection_type, len(hits_set), len(hits_set) / num_uniq_ens))
    if result_type == "topic":
        df = pd.DataFrame(counts, columns=["topic", "type", "cnt","frac"])
    else:
        df = pd.DataFrame(counts, columns=["topic", "name", "type", "cnt","frac"])
    return df[df["cnt"] > 0]

def addresses_of_interest(entity_api, with_tornado=True, with_hd=True, verbose=True):
    """Extract the list of addresses of interest from the data"""
    ens_addresses = set(entity_api.ens_pairs["address"].unique())
    if verbose:
        print("Number of ENS names:", len(entity_api.ens_pairs["name"].unique()))
        print("Number of ENS addresses:", len(ens_addresses))
    tornado_file_ids = ["0.1","1","10","100"]
    tornado_parts = [pd.read_csv("%s/tornadoFullHistoryMixer_%sETH.csv" % (entity_api.data_dir, part)) for part in tornado_file_ids]
    tornado_df = pd.concat(tornado_parts)
    tornado_deposits = set(tornado_df[tornado_df["action"]=="d"]["account"])
    tornado_withraws = set(tornado_df[tornado_df["action"]=="w"]["account"])
    tornado_addresses = list(tornado_deposits.union(tornado_withraws))
    if verbose:
        print("Number of Tornado addresses:", len(tornado_addresses))
    humanity_dao_addresses = set(pd.read_csv("%s/humanity_dao_addresses.csv" % entity_api.data_dir)["eth_address"])
    if verbose:
        print("Number of Humanity-Dao addresses:", len(humanity_dao_addresses))
    addresses = ens_addresses.copy()
    if with_tornado:
        addresses = addresses.union(tornado_addresses)
    if with_hd:
        addresses = addresses.union(humanity_dao_addresses)
    if verbose:
        print("Number of all addresses:", len(addresses))
    return list(addresses), ens_addresses, tornado_addresses, humanity_dao_addresses

def get_unlabeled_addresses(entity_api, event_type, addresses, selected_addr_info):
    """Find popular unlabeled addresses"""
    normal = entity_api.normal_txs[["from","to","hash","tx_type"]]
    if event_type == "outbound":
        key_col = "from"
        other_col = "to"
        token = entity_api.token_txs[[key_col,"contractAddress","hash"]].rename({"contractAddress":other_col}, axis=1)
    else:
        key_col = "to"
        other_col = "from"
        token = entity_api.token_txs[["contractAddress",key_col,"hash"]].rename({"contractAddress":other_col}, axis=1)
    token["tx_type"] = "token"
    txs = pd.concat([normal,token[["from","to","hash","tx_type"]]])
    txs = txs[txs[key_col].isin(addresses)]
    txs = txs.merge(selected_addr_info[["address","name","topic"]], left_on=other_col, right_on="address", how="left").drop("address", axis=1)
    return txs