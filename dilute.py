import yaml
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")
import pandas as pd
import seaborn as sns
import numpy as np
from itertools import product

f = open("experiment_parameters.yaml")
config = yaml.safe_load(f)
f.close()
EXP_NAME = config["experiment_settings"]["exp_name"]

dflist = []

startOD = []
endOD = []
VOLUME = []
VIALS_TO_RUN = []
for vial in config["experiment_settings"]["per_vial_settings"]:
    startOD.append(vial["calib_initial_od"])
    VOLUME.append(vial["volume"])
    endOD.append(config["experiment_settings"]["operation"]["end_od"])
    if vial["to_run"] is True:
        VIALS_TO_RUN.append(vial["vial"])

for sensor, vial in product(["90","135"], VIALS_TO_RUN):
    df = pd.read_csv(f"./{EXP_NAME}/od_{sensor}_raw/vial{vial}_od_{sensor}_raw.txt",
                     header=None).iloc[1:,].astype(float)    
    stirdf = pd.read_csv(f"./{EXP_NAME}/stirrate/vial{vial}_stirrate.txt").iloc[1:]
    pumpdf = pd.read_csv(f"./{EXP_NAME}/pump_log/vial{vial}_pump_log.txt",
                         names=["time","pump"]).iloc[1:].astype(float)
    
    df["time"] = df[0]
    df["reading"] = df[1]
    df["estimated_od"] = np.nan
    df["vial"] = vial
    df["sensor"] = sensor
    df["stirrate"] = stirdf.stir_rate
    df["pump"] = np.nan
    num_pump_events = 20
    bolus = VOLUME[vial]*(1-(endOD[vial]/startOD[vial])**(1/num_pump_events))/((endOD[vial]/startOD[vial])**(1/num_pump_events))
    prevtime = 0
    for dil, (i, row) in enumerate(pumpdf.iterrows()):
        df.loc[df.time == row.time, "pump"] = row.pump
        df.loc[(df.time > prevtime) & (df.time <= row.time), "estimated_od"] = startOD[vial]*(VOLUME[vial]/(VOLUME[vial] + bolus))**(dil)
        prevtime = row.time
    df = df[["time","reading","vial","sensor","stirrate","pump", "estimated_od"]]
    dflist.append(df)

fulldf = pd.concat(dflist)
g = sns.relplot(data=fulldf, x="time", y="reading",
            row="sensor",col="vial",hue="stirrate",
            facet_kws={"sharey":False})

axes = g.fig.axes
for sensor,axrow in zip(["90","135"],[axes, axes]):
    for ax, vial in zip(axrow, list(range(16))):
        for i, (idx, row) in enumerate(fulldf[(fulldf.sensor == sensor) & (fulldf.vial == vial) & (fulldf.pump > 0)].iterrows()):
            ax.axvline(row.time, color="k", alpha=0.4)
            ax.text(row.time, fulldf[(fulldf.sensor == sensor) & (fulldf.vial == vial) & (fulldf.time < row.time)].reading.median(), str(i))

plt.savefig(f"{EXP_NAME}-curves.png")

plt.close()


g = sns.relplot(data=fulldf, x="estimated_od", y="reading",
                hue="sensor",col="vial",col_wrap=4,                
                facet_kws={"sharey":False})
#g.set(xscale="log")
plt.savefig(f"{EXP_NAME}.png")
