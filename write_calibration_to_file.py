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

experiment = "XA09-calib"
dflist = []
vvolumes = [17.64, 17.9, 18.49, 17.49,
              17.86, 17.41, 18.04, 18.16,
              17.61, 17.35, 18.21, 17.85, 
              17.88, 18.07, 17.99, 16.69]

finalod = [
    0.042, 0.029, 0.054, 0.046,
    0.058, 0.065, 0.051, 0.049,
    0.062, 0.057, 0.061, 0.052,
    0.176, 0.063, 0.068, 0.071]
startod = [1.0]*16

for sensor, vial in product(["90","135"], range(16)):
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
    for dil, (i, row) in enumerate(pumpdf[pumpdf.time > 0].iterrows()):
        df.loc[df.time == row.time, "pump"] = row.pump
        df.loc[(df.time > prevtime) & (df.time <= row.time), "estimated_od"] = startod[vial]*(vvolumes[vial]/(vvolumes[vial] + bolus))**(dil)
        prevtime = row.time
    df = df[["time","reading","vial","sensor","stirrate","pump", "estimated_od"]]
    dflist.append(df)

calibdf = pd.concat(dflist)
calibdf["readingtype"] = "calibration"
calibdf = calibdf.groupby(["vial", "sensor",
                           "stirrate",
                           "estimated_od"])\
                 .agg({"reading":"median","time":"median"}).reset_index()

calibdf = calibdf.merge(calibdf[calibdf.sensor == "135"]\
                        .groupby(["vial", "stirrate"])\
                        .reading.min()\
                        .reset_index()\
                        [["reading","vial","stirrate"]],
                  on=["vial", "stirrate"], suffixes=[None, "_inflection"])
calibdf = calibdf.merge(calibdf.loc[(calibdf.sensor == "135")\
                                 & (calibdf.reading == calibdf.reading_inflection),
                                 ["vial","stirrate","estimated_od"]],
                        on=["vial","stirrate"],suffixes = [None,"_inflection"])

calibdf["estimated_od_inflection"] = calibdf["estimated_od_inflection"] - INFLECTION_CORRECTION
calibdf["prevod"] = calibdf.groupby(["vial","stirrate","sensor"]).estimated_od.shift(1)
calibdf["prevreading"] = calibdf.groupby(["vial","stirrate","sensor"]).reading.shift(1)
calibdf = calibdf.dropna()
calibdf.to_csv(f"{experiment}-calibration.csv")
p
