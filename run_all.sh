#!/bin/bash

echo "Warning: running this script would take a lot of time!"

pushd scripts

echo "### Preprocess ###"

python preprocess_data.py

echo "### ENS experiments ###"

# create time of day representation
python run_ens_experiment.py False 6 -1
# create gas price representation
python run_ens_experiment.py False -1 50

#for algo in {laplacian,netmf,role2vec,deepwalk,boostne,walklets,grarep,diff2vec,hope,nodesketch,nmfadmm,graphwave}; do
for algo in {role2vec,diff2vec}; do
# run for multiple samples
for i in {0..9}; do
echo $algo $i
# train model
python train_node_embedding.py $algo False $i;
# create representation
python run_ens_experiment.py True $algo $i;
done;
done;

echo "### Tornado experiments ###"

# create time of day representation
python run_tornado_experiment.py False 6 -1
# create gas price representation
python run_tornado_experiment.py False -1 50

# run for multiple samples
for i in {0..9}; do
echo $i
# train model
python train_node_embedding.py diff2vec True $i;
# create representation
python run_tornado_experiment.py True diff2vec $i;
done;

popd
