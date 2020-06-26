# ethereum-privacy (ethprivacy package)

[![Build Status](https://travis-ci.org/ferencberes/ethereum-privacy.svg?branch=master)](https://travis-ci.org/ferencberes/ethereum-privacy)

Latest joint work of [Ferenc Béres](https://github.com/ferencberes), [István András Seres](https://github.com/seresistvanandras), András A. Benczúr and Mikerah Quintyne-Collins on Ethereum user profiling and deanonymization. 

# Introduction

In this work we assess the privacy shortcomings of Ethereum's account-based model. We collect and analyze a wide source of Etherum related data, including [Ethereum name service](https://ens.domains/), [Etherscan](https://etherscan.io/) blockchain explorer, [Tornado Cash](https://tornado.cash/) mixer contracts, and Twitter. To the best of our knowledge, we are the first to propose and implement Ethereum user profiling techniques based on user quasi-identifiers. By learning Ethereum address representations we deanonymize accounts that belong to the same user. 

In this repository we publish our data and code for further research, in the from of a Python package **(ethprivacy)**.

## Cite

You can find our pre-print [paper](https://arxiv.org/pdf/2005.14051.pdf) on arXiv. Please cite our work if you use our code or the related data set.

```
@misc{beres2020blockchain,
    title={Blockchain is Watching You: Profiling and Deanonymizing Ethereum Users},
    author={Ferenc Béres and István András Seres and András A. Benczúr and Mikerah Quintyne-Collins},
    year={2020},
    eprint={2005.14051},
    archivePrefix={arXiv},
    primaryClass={cs.CR}
}
```

# Requirements

- UNIX environment
- This package was developed in Python 3.6 (conda environment)

# Installation

After cloning the repository you can install the **ethprivacy** package with `pip`.

```bash
git clone https://github.com/ferencberes/ethereum-privacy.git
cd ethereum-privacy
pip install .
```

# Data

**You must download our Ethereum data in order to use our code!**

You can choose to use our download script below or just simply use this [link](https://dms.sztaki.hu/~fberes/ln/ln_data_2019-10-29.zip).

```bash
bash download_data.sh
ls data
```

# Experiments

- By running the following script you can check your setup.
```bash
bash -e run_tests.sh
```
- We also provide a [script](run_all.sh) to run every experiment from our paper. *We recommend you to parallelize the tasks as it could take days to execute them on a single thread.*

# Acknowledgements

We thank Daniel A. Nagy, David Hai Gootvilig, Domokos M. Kelen and Kobi Gurkan for conversations and useful suggestions. Support from Project 2018-1.2.1-NKP-00008: Exploring the Mathematical Foundations of Artificial Intelligence and the “Big Data–Momentum” grant of the Hungarian
Academy of Sciences.
