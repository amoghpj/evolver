#import custom_script
import yaml
#from custom_script import EXP_NAME
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

INFLECTION_CORRECTION = 0

f = open("./experiment_parameters.yaml")
config = yaml.safe_load(f)
f.close()


# If using the GUI for data visualization, do not change EXP_NAME!
# only change if you wish to have multiple data folders within a single
# directory for a set of scripts
EXP_NAME = config["experiment_settings"]["exp_name"]
OPERATION_MODE = config["experiment_settings"]["operation"]["mode"]

VIALS_TO_RUN = []
VOLUME = []
CALIBRATION_INITIAL_OD = []
CALIBRATION_END_OD = []
CHEMO_RATE = []
CHEMO_START_OD = []
CHEMO_START_TIME = []


if config["experiment_settings"]["operation"]["mode"] == "calibration":
    settings = config["experiment_settings"]["operation"]
    for vial in config["experiment_settings"]["per_vial_settings"]:
        if vial["to_run"]:
            VIALS_TO_RUN.append(1)
        else:
            VIALS_TO_RUN.append(0)
        VOLUME.append(vial["volume"])
        if vial["to_run"] is True:    
            CALIBRATION_INITIAL_OD.append(vial["calib_initial_od"])
            CALIBRATION_END_OD.append(vial["calib_end_od"])            
        else:
            CALIBRATION_INITIAL_OD.append(0)
            CALIBRATION_END_OD.append(0)
    CALIBRATION_NUM_PUMP_EVENTS = settings["num_pump_events"]
    
num_pump_events= CALIBRATION_NUM_PUMP_EVENTS

# if type(CALIBRATION_END_OD) is float:
#     finalod = [CALIBRATION_END_OD]*16
# else:
    # finalod = [CALIBRATION_END_OD]
finalod  = CALIBRATION_END_OD    
# print(VOLUME)
# print(CALIBRATION_INITIAL_OD)
# print(finalod)
dflist = []
for sensor, vial in product(["90","135"], range(16)):
    if VIALS_TO_RUN[vial] == 1:
        df = pd.read_csv(f"./{EXP_NAME}/od_{sensor}_raw/vial{vial}_od_{sensor}_raw.txt",
                         header=None).iloc[1:,].astype(float)    
        pumpdf = pd.read_csv(f"./{EXP_NAME}/pump_log/vial{vial}_pump_log.txt",
                             names=["time","pump"],skiprows=[0]).astype(float)

        df["time"] = df[0]
        df["reading"] = df[1]
        df["estimated_od"] = np.nan
        df["vial"] = vial
        df["sensor"] = sensor
        df["pump"] = np.nan
        df["dilevent"] = 0
        bolus = VOLUME[vial]*((CALIBRATION_INITIAL_OD[vial]/finalod[vial])**(1/num_pump_events) - 1)
        prevtime = 0
        pumpdf = pumpdf.reset_index(drop=True)
        pumpeventidx = pumpdf.index.values
        for dil, (i, row) in enumerate(pumpdf.iterrows()):
            df.loc[df.time == row.time, "pump"] = row.pump
            if len(pumpeventidx) < dil + 2:
                df.loc[df.time > row.time, "dilevent"] = dil
                df.loc[df.time > row.time, "estimated_od"] = CALIBRATION_INITIAL_OD[vial]*(VOLUME[vial]/(VOLUME[vial] + bolus))**(dil)
            else:

                df.loc[(df.time > row.time) & (df.time <= pumpdf.loc[pumpeventidx[dil + 1], "time"]), "dilevent"] = dil
                df.loc[(df.time > row.time) & (df.time <= pumpdf.loc[pumpeventidx[dil + 1], "time"]), "estimated_od"] = CALIBRATION_INITIAL_OD[vial]*(VOLUME[vial]/(VOLUME[vial] + bolus))**(dil)
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
calibdf = calibdf.assign(is_monotonic = calibdf.reading - calibdf.prevreading)
calibdf = calibdf[calibdf.prevod > 0]
calibdf = calibdf.dropna()
calibdf.to_csv(f"{EXP_NAME}.csv")
