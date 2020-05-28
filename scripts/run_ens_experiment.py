from ethprivacy.entity_api import EntityAPI
from ethprivacy.address2vec import Address2Vec
from ethprivacy.evaluation import get_avg_rank
import pandas as pd
import numpy as np
import datetime as dt
import os, time, sys

data_dir = "../data"
results_dir = "../results"

def run(hour_bins, gas_bins, algo, sample_id):
    if not os.path.exists(results_dir + "/ens"):
        os.makedirs(results_dir + "/ens")
    print("arguments:", hour_bins, gas_bins, algo, sample_id)
    use_stats = True
    use_distrib = True
    min_tx_cnt = 5

    use_hour = hour_bins != -1
    use_gas = gas_bins != -1

    # # Load data
    api = EntityAPI(data_dir)
    filtered = pd.read_csv("%s/filtered_data.csv" % results_dir)

    node_embs = {}
    if sample_id != None:
        node_emb_dir = results_dir + "/node_embeddings_exFalse/" + str(sample_id)
        files = os.listdir(node_emb_dir)
        for f in files:
            algo_id = f.split("_")[0]
            node_embs[algo_id] = pd.read_csv(node_emb_dir + "/" + f)
            print(algo, node_embs[algo_id].shape)

    # # Generate feature vectors
    if algo != None:
        ae = Address2Vec(filtered, norm_type=None, min_tx_cnt=min_tx_cnt, gas_bins=0, hour_bins=0, use_hour=False, use_gas=False, use_stats=False, use_distrib=False, node_emb=node_embs[algo])
        ae.id = algo
    else:
        ae = Address2Vec(filtered, min_tx_cnt=min_tx_cnt, gas_bins=gas_bins, hour_bins=hour_bins, use_hour=use_hour, use_gas=use_gas, use_stats=use_stats, use_distrib=use_distrib)

    print("Representation id:", ae.id)
    print("Representation shape:", ae.X.shape)

    # # Evaluate embeddings for ENS names
    idx_pairs, ens_names = ae.get_idx_pairs(api)
    print("Evaluated address pairs:", len(idx_pairs))
    ens_result = ae.run_ens(idx_pairs, ae.id)
    ens_perf, _ = get_avg_rank(ens_result)
    print(ens_perf)

    # # Export
    while True:
        time_id = str(dt.datetime.now()).split(".")[0].replace(" ","_")
        experiment_id = "%s-%s" % (time_id, ae.id)
        output_file = "%s/ens/%s.csv" % (results_dir, experiment_id)
        if os.path.exists(output_file):
            time.sleep(np.random.randint(1,10))
            continue
        else:
            ens_result.to_csv(output_file, index=False)
            break
    
if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage:")
        print("run_ens_experiment.py False <hour_bins> <gas_bins>")
        print("OR")
        print("run_ens_experiment.py True <algo> <sample_id>")
    else:
        is_node_emb = sys.argv[1] == "True"
        if is_node_emb:
            algo = sys.argv[2]
            sample_id = sys.argv[3]
            hour_bins = None
            gas_bins = None
            run(hour_bins, gas_bins, algo, sample_id)
        else:
            hour_bins = int(sys.argv[2])
            gas_bins = int(sys.argv[3])
            run(hour_bins, gas_bins, None, None)
        print("done")
