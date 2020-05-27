# ethereum-privacy (ethprivacy package)

Latest joint work of [Ferenc Béres](https://github.com/ferencberes), [István András Seres](https://github.com/seresistvanandras), András A. Benczúr and Mikerah Quintyne-Collins on Ethereum deanonymization. 

# Introduction

In this work we assess the privacy shortcomings of Ethereum's account-based model. We collect and analyze a wide source of Etherum related data, including [Ethereum name service](https://ens.domains/), [Etherscan](https://etherscan.io/) blockchain explorer, [Tornado Cash](https://tornado.cash/) mixer contracts, and Twitter. To the best of our knowledge, we are the first to propose and implement Ethereum user profiling techniques based on user quasi-identifiers. Using the learned representations we deanonymize Ethereum addresses that belong to the same user. 

In this repository publish our data and code for further research, in the from of a Python package **(ethprivacy)**.

## Cite

Our arxiv paper is coming soon.

# Requirements

- UNIX or macOS environment
    - For macOS users: you need to have wget (brew install wget) 
- This package was developed in Python 3.6 (conda environment)

# Installation

After cloning the repository you can install the simulator with `pip`.

```bash
git clone https://github.com/ferencberes/ethereum-privacy.git
cd ethereum-privacy
pip install .
```

# Data

**You must download our Ethereum data in order to use our code!**

You can choose from the commands below or just simply use this download [link](https://dms.sztaki.hu/~fberes/ln/ln_data_2019-10-29.zip).

### a.)From Linux
```bash
bash download_data.sh
ls data
```
### b.)From macOS
```bash
sh download_data.sh
ls data
```

# Experiments

- By running the following script you can check your setup.
```bash
bash run_tests.sh
```
- We also provide a [script](run_all.sh) to run every experiment from our paper.
- **A documentation for the *ethprivacy* package will be released in the upcoming weeks.**


# Acknowledgements

We thank Daniel A. Nagy, David Hai Gootvilig, Domokos M. Kelen and Kobi Gurkan for conversations and useful suggestions. Support from Project 2018-1.2.1-NKP-00008: Exploring the Mathematical Foundations of Artificial Intelligence and the “Big Data—–Momentum” grant of the Hungarian
Academy of Sciences.
