import networkx as nx
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from karateclub import DeepWalk, Walklets, Role2Vec, Diff2Vec, BoostNE, NodeSketch, NetMF, HOPE, GraRep, NMFADMM, GraphWave, LaplacianEigenmaps

def clean_graph(G):
    G_undir = G.to_undirected()
    G_tmp = nx.Graph()
    G_tmp.add_edges_from(G_undir.edges())
    G_tmp.remove_edges_from(nx.selfloop_edges(G_tmp))
    return G_tmp

def recode_graph(G):
    N = G.number_of_nodes()
    node_map = dict(zip(G.nodes(), range(N)))
    edges_addr = list(G.edges())
    edges_idx = [(node_map[src], node_map[trg]) for src, trg in edges_addr]
    G_tmp = nx.Graph()
    G_tmp.add_edges_from(edges_idx)
    return G_tmp, node_map

def show_embeddings(emb_df, address_mask=[]):
    if len(address_mask) > 0:
        row_sel = emb_df["address"].isin(address_mask)
        plt.scatter(emb_df.loc[row_sel,0], emb_df.loc[row_sel,1])
    else:
        plt.scatter(emb_df.loc[:,0], emb_df.loc[:,1])
        
def karate_factory(algo, dim, nwalks, workers):
    if algo == "walklets":
        karate_obj = Walklets(dimensions=int(dim/4), walk_number=nwalks, workers=workers)
    elif algo == "role2vec":
        karate_obj = Role2Vec(dimensions=dim, walk_number=nwalks, workers=workers)
    elif algo == "diff2vec":
        karate_obj = Diff2Vec(dimensions=dim, diffusion_number=nwalks, workers=workers)
    elif algo == "deepwalk":
        karate_obj = DeepWalk(dimensions=dim, walk_number=nwalks, workers=workers)
    elif algo == "boostne":
        karate_obj = BoostNE(dimensions=int(dim/17)+1)
    elif algo == "nodesketch":
        karate_obj = NodeSketch(dimensions=dim)
    elif algo == "netmf":
        karate_obj = NetMF(dimensions=dim)
    elif algo == "hope":
        karate_obj = HOPE(dimensions=dim)
    elif algo == "grarep":
        karate_obj = GraRep(dimensions=int(dim/5)+1)
    elif algo == "nmfadmm":
        karate_obj = NMFADMM(dimensions=int(dim/2))
    elif algo == "graphwave":
        karate_obj = GraphWave()
    elif algo == "laplacian":
        karate_obj = LaplacianEigenmaps(dimensions=dim)
    else:
        raise RuntimeError("Invalid model type: %s" % algo)
    return karate_obj

class NodeEmbedder():
    def __init__(self, api, use_normal=True, use_token=True, use_contract=False, core_number=2, edges_to_remove=[],  verbose=True):
        self.verbose = verbose
        self.normal_G = clean_graph(api.normal_graph.G)
        self.token_G = clean_graph(api.token_graph.G)
        self.to_contract = clean_graph(api.contract_graph.G)
        self.from_contract = clean_graph(api.rev_contract_graph.G)
        all_edges = []
        if use_normal:
            all_edges += list(self.normal_G.edges())
        if use_token:
            all_edges += list(self.token_G.edges())
        if use_contract:
            all_edges += list(self.to_contract.edges())
            all_edges += list(self.from_contract.edges())
        G = nx.Graph()
        G.add_edges_from(all_edges)
        for u, v in edges_to_remove:
            if G.has_edge(u,v):
                G.remove_edge(u,v)
        if self.verbose:
            print("%i edges were removed" % len(edges_to_remove))
        # remove node nan - transactions without endpoint (e.g. new contract creation)
        G.remove_node(np.nan)
        # remove low degree nodes
        G = nx.k_core(G, k=core_number)
        # component check
        if nx.number_connected_components(G) > 1:
            Gcc = sorted(nx.connected_components(G), key=len, reverse=True)
            G = G.subgraph(Gcc[0])
        # recode addresses to integers
        self.G, self.node_map = recode_graph(G)
        self.idx_map = dict(zip(self.node_map.values(),self.node_map.keys()))
        self.ordered_addresses = [self.idx_map[idx] for idx in range(len(self.node_map))]
        if self.verbose:
            print("Number of nodes:", self.G.number_of_nodes())
            print("Number of edges:", self.G.number_of_edges())
            
    def get_indices(self, addresses):
        indices = []
        for addr in addresses:
            if add in self.node_map:
                indices.append(self.node_map[addr])
        return indices
    
    def fit(self, karate_model):
        if self.verbose:
            print("Training process STARTED")
        karate_model.fit(self.G)
        embedding = karate_model.get_embedding()
        emb_df = pd.DataFrame(embedding)
        emb_df["address"] = self.ordered_addresses
        if self.verbose:
            print("Training process FINISHED")
        return emb_df