import os, sys
from ethprivacy.entity_api import EntityAPI
from ethprivacy.node_embeddings import *
from ethprivacy.tornado_mixer import TornadoQueries

data_dir = "../data"
output_dir = "../results"

if len(sys.argv) < 4:
    print("Usage:train_node_embedding.py <algo> <exclude_tornado> <sample_id> <workers>")
else:
    algo = sys.argv[1]#"netmf"
    exclude_tornado = sys.argv[2] == "True"
    sample_id = sys.argv[3]
    if len(sys.argv) > 4:
        workers = int(sys.argv[4])
    else:
        workers = 1
        
    DIM = 128
    NWALKS = 10
    output_dir += ("/node_embeddings_ex%s/%s" % (exclude_tornado,sample_id))

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if algo in ["deepwalk","diff2vec","role2vec","walklets"]:
        f_name = "%s_dim%i_nwalk%i.csv" % (algo, DIM, NWALKS)
    elif algo == "graphwave":
        f_name = "%s.csv" % algo
    else:
        f_name = "%s_dim%i.csv" % (algo, DIM)

    api = EntityAPI(data_dir)
    max_time = api.events["timeStamp"].max()

    edges_to_remove = []
    if exclude_tornado:
        tq0_1 = TornadoQueries(mixer_str_value="0.1", max_time=max_time)
        tq1 = TornadoQueries(mixer_str_value="1", max_time=max_time)
        tq10 = TornadoQueries(mixer_str_value="10", max_time=max_time)
        tq100 = TornadoQueries(mixer_str_value="100", max_time=max_time)
        for tq in [tq0_1, tq1, tq10, tq100]:
            src, trg, _, _ = zip(*tq.tornado_tuples)
            edges_to_remove += list(zip(src,trg))
        edges_to_remove = list(set(edges_to_remove))
    print(len(edges_to_remove))

    ne = NodeEmbedder(api, edges_to_remove=edges_to_remove)
    karate_obj = karate_factory(algo, DIM, NWALKS, workers)
    embedding = ne.fit(karate_obj)
    print(embedding.shape)
    embedding.to_csv("%s/%s" % (output_dir, f_name), index=False)
    print("done")