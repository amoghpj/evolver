import pandas as pd
import seaborn as sns
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
experiment = "NC-turbostat"
dflist = []
for i in range(16):
    _df = pd.read_csv(f"NC-turbidostat/OD_autocalib/vial{i}_OD_autocalib.txt",names=["time","OD90","OD135"], skiprows=[0]).astype(float)
    _df["vial"] = i
    dflist.append(_df)

df = pd.concat(dflist)
df = df[["time", "OD90","vial"]]
df = df.dropna()
df["Log2(OD)"] = np.log2(df.OD90)
df = df[df.time > 2].reset_index(drop=True)
df["vial"] = df.vial.astype("category")

sns.relplot(data=df, x="time",
            y="Log2(OD)",
            hue="vial", kind="line")
plt.savefig("NC-timecourse.png")
