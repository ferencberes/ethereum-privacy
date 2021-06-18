import pandas as pd
import hashlib

fp = "../data/all_ens_pairs.csv"
df = pd.read_csv(fp)
if "Unnamed: 0" in df.columns:
    df.drop("Unnamed: 0", axis=1, inplace=True)
print(df.head())

ens_names = df["name"].unique()
print(len(ens_names))

digits = 10
hash_f = lambda x: hashlib.sha1(x.encode("UTF-8")).hexdigest()[:digits]
hashed_ens_names = list(map(hash_f, ens_names))
hash_map = dict(zip(ens_names, hashed_ens_names))
# check unique values
assert len(set(hashed_ens_names)) == len(ens_names)

df["name"] = df["name"].apply(lambda x: hash_map[x])
print(df.head())

df.to_csv(fp, index=False)
print("done")