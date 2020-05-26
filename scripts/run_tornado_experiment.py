from ethprivacy.entity_api import EntityAPI
from ethprivacy.address2vec import Address2Vec
from ethprivacy.evaluation import get_avg_rank
from ethprivacy.tornado_mixer import TornadoQueries
import pandas as pd
import numpy as np
import datetime as dt
import os, time, sys

data_dir = "../data"
results_dir = "../results"
filter_ids = ["past", "week", "day"]

def run(hour_bins, gas_bins, algo, sample_id):
    if not os.path.exists(results_dir + "/tornado"):
        os.makedirs(results_dir + "/tornado")

    use_stats = True
    use_distrib = True
    min_tx_cnt = 1

    use_hour = hour_bins != -1
    use_gas = gas_bins != -1

    # # Load data
    api = EntityAPI(data_dir)
    max_time = api.events["timeStamp"].max()
    
    tq0_1 = TornadoQueries(mixer_str_value="0.1", max_time=max_time)
    tq1 = TornadoQueries(mixer_str_value="1", max_time=max_time)
    tq10 = TornadoQueries(mixer_str_value="10", max_time=max_time)
    queries = [tq0_1, tq1, tq10]
    
    filtered = pd.read_csv("%s/filtered_data.csv" % results_dir)

    node_embs = {}
    if sample_id != None:
        node_emb_dir = results_dir + "/node_embeddings_exTrue/" + str(sample_id)
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

    # # Evaluate embeddings for Tornado withdraw-deposit address pairs
    pairs = []
    for tq in queries:
        pairs.append(tq.tornado_pairs[["sender","receiver"]])
    pairs = pd.concat(pairs).reset_index(drop=True)
    pairs = pairs.drop_duplicates()
    print("Evaluated withdraw-deposit:", pairs.shape)
    
    tornado_result = ae.run_tornado(queries, ae.id, filters=filter_ids)
    tornado_perf, _ = get_avg_rank(tornado_result)
    print(tornado_perf)

    # # Export
    while True:
        time_id = str(dt.datetime.now()).split(".")[0].replace(" ","_")
        experiment_id = "%s-%s" % (time_id, ae.id)
        output_file = "%s/tornado/%s.csv" % (results_dir, experiment_id)
        if os.path.exists(output_file):
            time.sleep(np.random.randint(1,10))
            continue
        else:
            tornado_result.to_csv(output_file, index=False)
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