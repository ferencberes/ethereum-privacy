#!/bin/bash
pushd scripts
python preprocess_data.py
python train_node_embedding.py netmf False 0
