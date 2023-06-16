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
if config["experiment_settings"]["operation"]["mode"] == "calibration":
    EXP_NAME = config["experiment_settings"]["exp_name"]
    num_pump_events = config["experiment_settings"]["operation"]["num_pump_events"]


    dflist = []

    startOD = []
    endOD = []
    VOLUME = []
    VIALS_TO_RUN = []
    for vial in config["experiment_settings"]["per_vial_settings"]:
        startOD.append(vial["calib_initial_od"])
        VOLUME.append(vial["volume"])
        if config["experiment_settings"]["operation"].get("fold_calibration", False):
            endOD.append(vial["calib_initial_od"]/config["experiment_settings"]["operation"]["fold_calibration"])

        else:
            endOD.append(vial["calib_end_od"])

        if vial["to_run"] is True:
            VIALS_TO_RUN.append(vial["vial"])
    try:
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
                        hue="sensor",col="vial",col_wrap=4,
                        facet_kws={"sharey":False})

        axes = g.fig.axes
        for ax, vial in zip(axes, list(range(16))):
            for i, (idx, row) in enumerate(fulldf[(fulldf.sensor == "90") & (fulldf.vial == vial) & (fulldf.pump > 0)].iterrows()):
                ax.axvline(row.time, color="k", alpha=0.4)
                ax.text(row.time, fulldf[(fulldf.sensor == "90") & (fulldf.vial == vial) & (fulldf.time < row.time)].reading.median(), str(i))    

        # for sensor,axrow in zip(["90","135"],[axes, axes]):
        #     for ax, vial in zip(axrow, list(range(16))):
        #         for i, (idx, row) in enumerate(fulldf[(fulldf.sensor == sensor) & (fulldf.vial == vial) & (fulldf.pump > 0)].iterrows()):
        #             ax.axvline(row.time, color="k", alpha=0.4)
        #             ax.text(row.time, fulldf[(fulldf.sensor == sensor) & (fulldf.vial == vial) & (fulldf.time < row.time)].reading.median(), str(i))

        plt.savefig(f"{EXP_NAME}-curves.png")

        plt.close()


        g = sns.relplot(data=fulldf, x="estimated_od", y="reading",
                        hue="sensor",col="vial",col_wrap=4,
                    facet_kws={"sharey":False})
        #g.set(xscale="log")
        plt.savefig(f"{EXP_NAME}.png")
    except:
        print("no files found")
else:
    EXP_NAME = config["experiment_settings"]["exp_name"]
    if "calib_name" in config["experiment_settings"].keys():
        CALIB_NAME = config["experiment_settings"]["calib_name"]
    else:
        CALIB_NAME = ""
    stirswitch = config["experiment_settings"]["stir_settings"]["stir_switch"]
    active_vials = [pvs["vial"] for pvs in config["experiment_settings"]["per_vial_settings"]]

    plotthese = {"od_90_raw":{"names":["time","od_90_raw"], "plot": True, "plotvar":"od_90_raw"},
                 "od_135_raw":{"names":["time","od_135_raw"], "plot": True, "plotvar":"od_135_raw"},
                 "OD":{"names":["time","OD"], "plot": True, "plotvar":"OD"},
                 "growthrate_fromOD":{"names":["time","gr"], "plot":True, "plotvar":"gr"},
                 "OD_autocalib":{"names":["time","od_plinear_90", "od_plinear_135"],
                                 "plot": True, "plotvar":"od_plinear_135"}}
    if stirswitch:
        plotthese["stirrate"] = {"names":["time","old stir time",
                                          "stir rate"],
                                 "plot": False, "plotvar":"stir rate"}
    dflist = []
    cdflist = []
    for vial, plotthis in product(list(range(16)), plotthese.keys()):
        _df = pd.read_csv(f"{EXP_NAME}/{plotthis}/vial{vial}_{plotthis}.txt",
                          names=plotthese[plotthis]["names"],
                          skiprows=[0]).astype(float)
        _df["vial"] = vial
        _df["datatype"] = plotthis
        dflist.append(_df)

    df = pd.concat(dflist).reset_index()

    df["vial"] = df.vial.astype("category")

    fig, axes = plt.subplots(4,4, figsize=(16,16))

    axes = axes.flatten()
    if CALIB_NAME != "":
        for vial, ax in enumerate(axes):
            if vial in active_vials:
                rawc90 = pd.read_csv(f"{CALIB_NAME}/od_90_raw/vial{vial}_od_90_raw.txt",
                                   skiprows=[0],
                                   names=["time","90"])
                rawc135 = pd.read_csv(f"{CALIB_NAME}/od_135_raw/vial{vial}_od_135_raw.txt",
                                   skiprows=[0],
                                   names=["time","135"])
                pump = pd.read_csv(f"{CALIB_NAME}/pump_log/vial{vial}_pump_log.txt",
                                   skiprows=[0],
                                   names=["time","pump_duration"])
                pump["pump_event"] = pump.index.astype(int)
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
                           alpha=0.5, label="Chemostat Timecourse")
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
        print(plotthis)
        if plotthese[plotthis]["plot"]:
            yvar = plotthese[plotthis]["plotvar"]
            if "autocalib" in plotthis:
                if stirswitch:
                    _df = df[df.datatype == plotthis]
                    stirdf = df[df.datatype == "stirrate"]
                    _df = _df[["time", "od_plinear_90","od_plinear_135", "vial"]].merge(stirdf[["time","stir rate","vial"]], on=["time","vial"])
                    _df = _df.melt(id_vars=["time","vial","stir rate"], value_vars=["od_plinear_90",
                                                                                    "od_plinear_135"],
                                                      var_name="sensor", value_name="inferred OD").dropna()
                    sns.set_style("ticks",{'axes.grid' : True})                
                    g = sns.relplot(data=_df[_df.sensor == yvar], x="time",
                                    y="inferred OD",style="stir rate",
                                    col="vial", col_wrap=4,
                                    hue="sensor", kind="line")
                    print(config["experiment_settings"]["operation"])
                    if config["experiment_settings"]["operation"]["mode"] == "turbidostat":
                        for i, ax in enumerate(g.axes.flatten()):
                            ax.axhline(config["experiment_settings"]["per_vial_settings"][i]["turbidostat_high"], color="k")
                            ax.axhline(config["experiment_settings"]["per_vial_settings"][i]["turbidostat_low"], color="r")                        
                    plt.savefig(f"{EXP_NAME}-{plotthis}-linear.png")
                    plt.close()
                    g = sns.relplot(data=_df, x="time",
                                    y="inferred OD",style="stir rate",
                                    col="vial", col_wrap=4,
                                    hue="sensor", kind="line")
                    plt.yscale("log", base=2)                
                else:
                    _df = df[df.datatype == plotthis].melt(id_vars=["time","vial"], value_vars=["od_plinear_90",
                                                                                  "od_plinear_135"],
                                                      var_name="sensor", value_name="inferred OD").dropna()
                    g = sns.relplot(data=_df, x="time",
                                    y="inferred OD",
                                    col="vial", col_wrap=4,
                                    hue="sensor", kind="line")            

            elif "growth" in plotthis:
                if stirswitch:
                    _df = df[df.datatype == plotthis][["time", yvar, "vial"]].merge(df[df.datatype=="stirrate"][["time","stir rate","vial"]], on=["time","vial"])
                    if _df.shape[0] > 0:
                        _df = _df[(_df[yvar] < 1) & (_df[yvar] > 0 )]
                        _df["Doubling time (hr)"] = 1/_df[yvar]
                        _df = _df[_df["Doubling time (hr)"] < 50]
                        g = sns.relplot(data=_df, x="time",
                                        y="Doubling time (hr)",
                                        hue="vial",
                                        style="stir rate", kind="line")            

                else:
                    g = sns.relplot(data=df[df.datatype == plotthis], x="time",
                                    y=yvar,
                                    col="vial", col_wrap=4,
                                    hue="vial", kind="line")                        

            else:
                if stirswitch:
                    _df = df[df.datatype == plotthis][["time", yvar, "vial"]].merge(df[df.datatype=="stirrate"][["time","stir rate","vial"]], on=["time","vial"])
                    if _df.shape[0] > 0:
                        g = sns.relplot(data=_df, x="time",
                                        y=yvar,
                                        col="vial", col_wrap=4,edgecolor=None,
                                        hue="stir rate", marker="o")            

                else:
                    g = sns.relplot(data=df[df.datatype == plotthis], x="time",
                                    y=yvar,
                                    col="vial", col_wrap=4,
                                    hue="vial", kind="line")            
            plt.savefig(f"{EXP_NAME}-{plotthis}.png")
    
