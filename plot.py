#!/usr/bin/env python
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from itertools import product
import seaborn as sns
import time
import os

startingv = 20000
calibs = [f for f in os.listdir("./") if "sleevecalib" in f]
dflist = []
vspikedin = 75
vialvolumes = [17.75, 17.27, 17.81, 18.52]
for cfile,sensor, sleeve in product(calibs, ["90", "135"], list(range(4))):
    cnum= int(cfile.split("_")[1])
    vial = cfile.split("_")[0].replace("sleevecalib","")
    df = pd.read_csv(f"./{cfile}/od_{sensor}_raw/vial{sleeve}_od_{sensor}_raw.txt",
                     header=None).iloc[1:,].astype(float)
    stirdf = pd.read_csv(f"./{cfile}/stirrate/vial{sleeve}_stirrate.txt").iloc[1:]
    df["time"] = df[0]
    df["reading"] = df[1]
    vialv = vialvolumes[sleeve]
    df["odactual"] = (cnum*vspikedin*34)/(vialv*1000+cnum*vspikedin)
    df["calibnum"] = cnum
    df["cjitter"] = np.random.normal(cnum,0.01,size=df.shape[0])
    df["sleeve"] = sleeve
    df["vial"] = vial
    df["sensor"] = sensor
    if "pump" in stirdf.columns:
        df["stirrate"] = stirdf["pump"]
    else:
        df["stirrate"] = stirdf["stir_rate"]
    df = df[["time","reading","calibnum","vial","sensor",
             "sleeve","cjitter","odactual","stirrate"]]
    dflist.append(df)

fulldf = pd.concat(dflist)
sns.relplot(data=fulldf, x="odactual", y ="reading",
            row="sensor",col="sleeve",
            hue="stirrate",
            facet_kws={"sharey":False})

plt.savefig("calib.png")

plt.close()


sns.relplot(data=fulldf,x="time",y="reading",col="sleeve",
            col_wrap=4,hue="sensor")
plt.savefig("monitor.png")

plt.close()

# df = df.join(df.groupby(["sleeve","vial","calibnum"]).reading.median().reset_index(), rsuffix="_median")
# df = df[(df.reading < 57500) & (df.sensor == 90)]



### 1-0: 0.57
### 1-2: 0.552
### 2-0: 0.569
### 2-1: 0.571
