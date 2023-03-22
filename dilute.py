import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")
import pandas as pd
import seaborn as sns
from itertools import product

experiment = "XA08-dilute"
dflist = []
vvolumes = [17.752, 17.27, 17.81, 18.52]
startod = [1.246, 1.302, 1.21, 1.214]
for sensor, vial in product(["90","135"], range(4)):
    df = pd.read_csv(f"./{experiment}/od_{sensor}_raw/vial{vial}_od_{sensor}_raw.txt",
                     header=None).iloc[1:,].astype(float)    
    stirdf = pd.read_csv(f"./{experiment}/stirrate/vial{vial}_stirrate.txt").iloc[1:]
    pumpdf = pd.read_csv(f"./{experiment}/pump_log/vial{vial}_pump_log.txt",
                         names=["time","pump"]).iloc[1:].astype(float)
    
    df["time"] = df[0]
    df["reading"] = df[1]
    df["estimated_od"] = 0
    df["vial"] = vial
    df["sensor"] = sensor
    df["stirrate"] = stirdf.stir_rate
    df["pump"] = 0
    num_pump_events = 20
    bolus = vvolumes[vial]*(1-(0.05/startod[vial])**(1/num_pump_events))/((0.05/startod[vial])**(1/num_pump_events))
    prevtime = 0
    for dil, (i, row) in enumerate(pumpdf.iterrows()):
        df.loc[df.time == row.time, "pump"] = row.pump
        df.loc[(df.time > prevtime) & (df.time <= row.time), "estimated_od"] = startod[vial]*(vvolumes[vial]/(vvolumes[vial] + bolus))**(dil)
        prevtime = row.time
    df = df[["time","reading","vial","sensor","stirrate","pump", "estimated_od"]]
    dflist.append(df)

fulldf = pd.concat(dflist)
g = sns.relplot(data=fulldf, x="time", y="reading",
            row="sensor",col="vial",hue="stirrate",
            facet_kws={"sharey":False})

axes = g.fig.axes
for sensor,axrow in zip(["90","135"],[axes[:4], axes[4:]]):
    for ax, vial in zip(axrow, list(range(4))):
        for i, (idx, row) in enumerate(fulldf[(fulldf.sensor == sensor) & (fulldf.vial == vial) & (fulldf.pump > 0)].iterrows()):
            ax.axvline(row.time, color="k", alpha=0.4)
            ax.text(row.time, fulldf[(fulldf.sensor == sensor) & (fulldf.vial == vial) & (fulldf.time < row.time)].reading.median(), str(i))

plt.savefig("xa08.png")

plt.close()


g = sns.relplot(data=fulldf, x="estimated_od", y="reading",
            row="sensor",col="vial",hue="stirrate",
            facet_kws={"sharey":False})
#g.set(xscale="log")
plt.savefig("xa08-od-calibration.png")
