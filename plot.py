import yaml
import pandas as pd
import seaborn as sns
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from itertools import product

f = open("experiment_parameters.yaml")
config = yaml.safe_load(f)
f.close()
EXP_NAME = config["experiment_settings"]["exp_name"]

plotthese = {"od_90_raw":{"names":["time","od_90_raw"], "plot": True, "plotvar":"od_90_raw"},
             "od_135_raw":{"names":["time","od_135_raw"], "plot": True, "plotvar":"od_135_raw"},
             "OD":{"names":["time","OD"], "plot": True, "plotvar":"OD"},
             "OD_autocalib":{"names":["time","od_plinear_90", "od_plinear_135"], "plot": True, "plotvar":"od_plinear_135"}             
             }

dflist = []
for vial, plotthis in product(list(range(16)), plotthese.keys()):
    _df = pd.read_csv(f"{EXP_NAME}/{plotthis}/vial{vial}_{plotthis}.txt",names=plotthese[plotthis]["names"],
                      skiprows=[0]).astype(float)
    _df["vial"] = vial
    _df["datatype"] = plotthis
    dflist.append(_df)

df = pd.concat(dflist).reset_index()


df["vial"] = df.vial.astype("category")

for plotthis in plotthese.keys():
    print(plotthis)
    yvar = plotthese[plotthis]["plotvar"]
    if "autocalib" in plotthis:
        df = df[df.datatype == plotthis].melt(id_vars=["time","vial"], value_vars=["od_plinear_90",
                                                                          "od_plinear_135"],
                                              var_name="sensor", value_name="inferred OD")
        g = sns.relplot(data=df, x="time",
                        y="inferred OD",
                        col="vial", col_wrap=4,
                        hue="sensor", kind="line")
    else:
        g = sns.relplot(data=df[df.datatype == plotthis], x="time",
                        y=yvar,
                        col="vial", col_wrap=4,
                        hue="vial", kind="line")
    if "raw" not in plotthis:
        g.set(yscale="log")
    plt.savefig(f"{EXP_NAME}-{plotthis}.png")
