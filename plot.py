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
CALIB_NAME = config["experiment_settings"].get("calib_name", None)


plotthese = {"od_90_raw":{"names":["time","od_90_raw"], "plot": True, "plotvar":"od_90_raw"},
             "od_135_raw":{"names":["time","od_135_raw"], "plot": True, "plotvar":"od_135_raw"},
             "OD":{"names":["time","OD"], "plot": True, "plotvar":"OD"},
             "OD_autocalib":{"names":["time","od_plinear_90", "od_plinear_135"], "plot": True, "plotvar":"od_plinear_135"}                       }

dflist = []
cdflist = []
failed = []
for vial, plotthis in product(list(range(16)), plotthese.keys()):
    try:
        _df = pd.read_csv(f"{EXP_NAME}/{plotthis}/vial{vial}_{plotthis}.txt",names=plotthese[plotthis]["names"],
                          skiprows=[0]).astype(float)
        _df["vial"] = vial
        _df["datatype"] = plotthis
        _df = _df.dropna()
        if _df.shape[0] == 0:
            failed.append(plotthis)
        dflist.append(_df)
    except:
        failed.append(plotthis)
        print(f"Error reading files for: {plotthis} ")

df = pd.concat(dflist).reset_index()


df["vial"] = df.vial.astype("category")

fig, axes = plt.subplots(4,4, figsize=(16,16))

axes = axes.flatten()

for vial, ax in enumerate(axes):
    if CALIB_NAME is not None:
        pump = pd.read_csv(f"{CALIB_NAME}/pump_log/vial{vial}_pump_log.txt",
                           skiprows=[0],
                           names=["time","pump_duration"])    
        pump["pump_event"] = pump.index.astype(int)            
        rawc90 = pd.read_csv(f"{CALIB_NAME}/od_90_raw/vial{vial}_od_90_raw.txt",
                             skiprows=[0],
                             names=["time","90"])
        rawc135 = pd.read_csv(f"{CALIB_NAME}/od_135_raw/vial{vial}_od_135_raw.txt",
                              skiprows=[0],
                              names=["time","135"])
        cdat = rawc90.merge(rawc135, on="time")
        cdat["pump_event"] = np.nan
        for i, prow in pump.iterrows():
            cdat.loc[(cdat.time <= prow.time) & (np.isnan(cdat.pump_event)), "pump_event"] = prow.pump_event
        cdat["90_median"] = cdat.groupby("pump_event")["90"].median()
        cdat["135_median"] = cdat.groupby("pump_event")["135"].median()    

        ax.scatter(cdat["90_median"].values, cdat["135_median"].values, label="Calibration Median")
        ax.scatter(cdat["90"].values,
                   cdat["135"].values, c="r", alpha=0.1,label="Calibration Raw Values")    
    ddat = df[df.vial == vial]
    ax.scatter(ddat[ddat["datatype"] == "od_90_raw"].od_90_raw,
            ddat[ddat["datatype"] == "od_135_raw"].od_135_raw,
               c=ddat[ddat["datatype"] == "od_135_raw"].time.values,
               s=3,
               alpha=0.5, label="Timecourse")
    ax.set_xlabel("Sensor: 90")
    ax.set_ylabel("Sensor: 135")
    #ax.set_xlim(52000, 63500)
    ax.set_title(f"Vial {vial}")
    if vial == 15:
        ax.legend()
    
plt.tight_layout()    
plt.savefig(f"{EXP_NAME}_projection.png")


plt.close()

for plotthis in plotthese.keys():
    if plotthis not in failed:
        print(plotthis)
        yvar = plotthese[plotthis]["plotvar"]
        if "autocalib" in plotthis:
            print(plotthis)
            _df = df[df.datatype == plotthis].melt(id_vars=["time","vial"], value_vars=["od_plinear_90",
                                                                              "od_plinear_135"],
                                                  var_name="sensor", value_name="inferred OD").dropna()

            g = sns.relplot(data=_df, x="time",
                            y="inferred OD",
                            col="vial", col_wrap=4,
                            hue="sensor", kind="line")
        else:
            g = sns.relplot(data=df[df.datatype == plotthis], x="time",
                            y=yvar,
                            col="vial", col_wrap=4,
                            hue="vial", kind="line")
        # if "raw" not in plotthis:
        #     g.set(yscale="log")
        plt.savefig(f"{EXP_NAME}-{plotthis}.png")
