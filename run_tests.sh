#!/bin/bash
pushd scripts

### Preprocess ###

python preprocess_data.py

### ENS experiments ###

# create time of day representation
python run_ens_experiment.py False 6 -1
# create gas price representation
python run_ens_experiment.py False -1 50

# train netmf (one of the fastest models to train)
python train_node_embedding.py netmf False 0
# create netmf representation
python run_ens_experiment.py True netmf 0
