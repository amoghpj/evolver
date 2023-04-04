import custom_script
from custom_script import EXP_NAME
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from itertools import product
from sklearn.linear_model import LinearRegression
import numpy as np
import time
import seaborn as sns
import sys 
from tqdm import tqdm
def bye():
    sys.exit()
# def growth_rate(time, od,winsize):
#     intercepts = []
#     slopes = []
#     midpoint = []
#     time = time.reshape(-1,1)
#     for i in range(len(time)-winsize):
#         model = LinearRegression()
#         model.fit(time[i:i+winsize], np.log2(od[i:i+winsize]))
#         intercepts.append(model.intercept_)
#         slopes.append(model.coef_[0])
#         midpoint.append(np.median(time[i:i+winsize]))
#     return(intercepts, slopes,midpoint)
INFLECTION_CORRECTION = 0
experiment = "NCB-turbidostat-calibration"
dflist = []
vvolumes = [21.47, 22.29, 21.81, 21.39,
           21.76,21.13, 21.55, 21.53,
           20.95, 21.83, 22.05, 21.46,
           21.21, 21.35, 21.66, 21.81]
startod = [0.892,0.892,0.892,0.892,
           0.918,0.918,0.918,0.918,
           0.711,0.711,0.711,0.711,
           0.677,0.677,0.677,0.677]
finalod = []


for sensor, vial in product(["90","135"], range(16)):
    df = pd.read_csv(f"./{experiment}/od_{sensor}_raw/vial{vial}_od_{sensor}_raw.txt",
                     header=None).iloc[1:,].astype(float)    
    pumpdf = pd.read_csv(f"./{experiment}/pump_log/vial{vial}_pump_log.txt",
                         names=["time","pump"]).iloc[1:].astype(float)
    
    df["time"] = df[0]
    df["reading"] = df[1]
    df["estimated_od"] = np.nan
    df["vial"] = vial
    df["sensor"] = sensor
    df["pump"] = np.nan
    df["dilevent"] = 0
    num_pump_events = 10

    bolus = vvolumes[vial]*(1-(finalod[vial]/startod[vial])**(1/num_pump_events))/((finalod[vial]/startod[vial])**(1/num_pump_events))

    prevtime = 0
    pumpdf = pumpdf.reset_index(drop=True)
    pumpeventidx = pumpdf.index.values
    for dil, (i, row) in enumerate(pumpdf.iterrows()):
        df.loc[df.time == row.time, "pump"] = row.pump
        if len(pumpeventidx) < dil + 2:
            print("here")
            df.loc[df.time > row.time, "dilevent"] = dil
            df.loc[df.time > row.time, "estimated_od"] = startod[vial]*(vvolumes[vial]/(vvolumes[vial] + bolus))**(dil)
        else:
            
            df.loc[(df.time > row.time) & (df.time <= pumpdf.loc[pumpeventidx[dil + 1], "time"]), "dilevent"] = dil
            df.loc[(df.time > row.time) & (df.time <= pumpdf.loc[pumpeventidx[dil + 1], "time"]), "estimated_od"] = startod[vial]*(vvolumes[vial]/(vvolumes[vial] + bolus))**(dil)
        prevtime = row.time
    df = df[["time","reading","vial","sensor","pump", "estimated_od", "dilevent"]]
    dflist.append(df)

calibdf = pd.concat(dflist)
#calibdf = calibdf[calibdf.dilevent <= 9]

calibdf["readingtype"] = "calibration"
calibdf = calibdf.groupby(["vial", "sensor",
                           "estimated_od","dilevent"])\
                 .agg({"reading":"median","time":"median"}).reset_index()

calibdf = calibdf.merge(calibdf[calibdf.sensor == "135"]\
                        .groupby(["vial", ])\
                        .reading.min()\
                        .reset_index()\
                        [["reading","vial",]],
                  on=["vial", ], suffixes=[None, "_inflection"])
calibdf = calibdf.merge(calibdf.loc[(calibdf.sensor == "135")\
                                 & (calibdf.reading == calibdf.reading_inflection),
                                 ["vial","estimated_od"]],
                        on=["vial",],suffixes = [None,"_inflection"])

calibdf["estimated_od_inflection"] = calibdf["estimated_od_inflection"] - INFLECTION_CORRECTION
calibdf["prevod"] = calibdf.groupby(["vial","sensor"]).estimated_od.shift(1)
calibdf["prevreading"] = calibdf.groupby(["vial","sensor"]).reading.shift(1)
# calibdf = calibdf[calibdf.prevod > 0]
# calibdf = calibdf.dropna()
calibdf.to_csv(f"{experiment}-calibration.csv")
