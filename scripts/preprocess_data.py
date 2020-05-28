import matplotlib.pyplot as plt
import seaborn as sns
sns.set(font_scale = 2)
sns.set_style("whitegrid")
import os
import pandas as pd
import numpy as np
from tqdm import tqdm
from ethprivacy.entity_api import EntityAPI
from ethprivacy.topic_analysis import addresses_of_interest

data_dir = "../data"
output_dir = "../results"
export_figs = True

img_dir = "%s/figs" % output_dir
if export_figs and not os.path.exists(img_dir):
    os.makedirs(img_dir)

# # 1.) Initialize EntityAPI
api = EntityAPI(data_dir)

# # 2.) Preprocess data

# ## i.) Addresses of interest (ENS Twitter + Tornado + Humanity-Dao)
addresses, ens_addrs, tornado_addrs, hd_addrs = addresses_of_interest(api)

# ## ii.) Interaction data
cols = ["timeStamp","from","to","hash","gasPrice"]
part1 = api.normal_txs[cols+["tx_type"]]
part2 = api.token_txs[cols]
part2["tx_type"] = "token"

# ### Internal transactions has no gasPrice so use only NORMAL txs
part1 = part1[part1["tx_type"]=="normal"]
part1["gasPrice"].isnull().sum()

interactions = pd.concat([part1, part2])
print("interactions", interactions.shape)

# ## iii.) Timestamp transformations

interactions["day"] = interactions["timeStamp"] // 86400
interactions["hour"] = interactions["timeStamp"] % 86400

plt.figure(figsize=(6,4))
interactions["hour"].hist(bins=24)
plt.ylabel("Count")
plt.xlabel("Hour (GMT)")
hours = [0,4,8,12,16,20]
plt.xticks(np.array(hours)*3600, hours)
if export_figs:
    plt.savefig("%s/hour_distrib.pdf" % img_dir, format='pdf', bbox_inches='tight')

# ## iv.) Gasprice and Tx value transformations

# ### Average daily gas price (only for addresses of interest)

# #### a.) Daily average gasPrice based on all interactions
daily_avg = interactions.groupby("day")["gasPrice"].mean().reset_index()

# #### b.) Daily average gasPrice based on addresses of interest
addr_daily_avg = interactions[interactions["from"].isin(addresses)].groupby("day")["gasPrice"].mean().reset_index()
daily_avg = daily_avg.merge(addr_daily_avg, on="day", how="right", suffixes=("","_addr"))

# ### Gas normalization
filtered = interactions.merge(daily_avg.drop("gasPrice", axis=1), on="day", how="inner")
print("daily avg filter", len(filtered) / len(interactions))

# ### Keep only addresses of interest
filtered = filtered[filtered["from"].isin(addresses)]
print("addresses of interest", len(filtered) / len(interactions))
filtered["normalized_gas"] = filtered["gasPrice"] / filtered["gasPrice_addr"]

# ## v.) Outlier exclusion
print("Before outlier exclusion", len(filtered) / len(interactions))
filtered = filtered[(filtered["normalized_gas"] < 5)]
print("gas price outliers", len(filtered) / len(interactions))

plt.figure(figsize=(6,4))
filtered["normalized_gas"].hist(bins=50)
plt.ylabel("Count")
plt.xlabel("Normalized gas price")
plt.xticks([0,1,2,3,4])
if export_figs:
    plt.savefig("%s/gas_distrib.pdf" % img_dir, format='pdf', bbox_inches='tight')

# ### Logarithmic transformation
filtered["normalized_gas"] = np.log(1+filtered["normalized_gas"])

# # 3.) Address categories

# A transactions may have multiple recipients. In this case we count these transactions multiple times
addr_cnts = filtered.groupby("from")["hash"].count().reset_index()
addr_cnts["is_ens"] = addr_cnts["from"].apply(lambda x: x in ens_addrs).astype("int")
addr_cnts["is_tornado"] = addr_cnts["from"].apply(lambda x: x in tornado_addrs).astype("int")
addr_cnts["is_hd"] = addr_cnts["from"].apply(lambda x: x in hd_addrs).astype("int")

df = addr_cnts
print("All accounts")
print(df.shape)
print(df[["is_ens","is_tornado","is_hd"]].sum(axis=0))
print()

df = addr_cnts[addr_cnts["hash"]>=5]
print("Accounts with at least 5 sent transactions")
print(df.shape)
print(df[["is_ens","is_tornado","is_hd"]].sum(axis=0))

# # 4.) Export preprocessed data
filtered.to_csv("%s/filtered_data.csv" % output_dir, index=False)
print("Done")
