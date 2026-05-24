import yaml
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.patches import Rectangle
matplotlib.use("Agg")
import pandas as pd
import seaborn as sns
import numpy as np
from itertools import product
from scipy.signal import lfilter, medfilt

sns.set(style="ticks",
        font_scale=2)

def filter_noise(gdf, yvar):
    n = 200.
    b = [1./n]*int(n)
    a= [1]
    #gdf[yvar] = lfilter(b ,a, gdf[yvar].values)
    gdf[yvar] = medfilt(gdf[yvar].values, 21)
    return(gdf[[yvar, "time","vial"]])

def process_for_autocalib(_df,stirswitch):
    if stirswitch:
        return(_df.melt(id_vars=["time","vial","stir rate"],
                    value_vars=["od_plinear_90",
                                "od_plinear_135"],
                    var_name="sensor",
                    value_name="inferred OD").dropna())
    else:
        return(_df.melt(id_vars=["time","vial"],
                   value_vars=["od_plinear_90",
                               "od_plinear_135"],
                   var_name="sensor",
                   value_name="inferred OD").dropna())

def process_for_morbidostat(_df, pump):
    if stirswitch:
        return(_df.melt(id_vars=["time","vial","stir rate"],
                    value_vars=["od_plinear_90",
                                "od_plinear_135"],
                    var_name="sensor",
                    value_name="inferred OD").dropna())
    else:
        return(_df.melt(id_vars=["time","vial"],
                   value_vars=["od_plinear_90",
                               "od_plinear_135"],
                   var_name="sensor",
                   value_name="inferred OD").dropna())    
    
def plot_turbidostat_limits(config, g, _df):
    _df = _df[["vial","od_plinear_135"]].dropna()
    for ax, vialid in zip(g.axes.flatten(), _df["vial"].unique()):
        vialsettings = [vialset for vialset in config["experiment_settings"]["per_vial_settings"]\
                        if vialset["vial"] == vialid ][0]
        ax.axhline(vialsettings["turbidostat_high"], color="k")
        ax.axhline(vialsettings["turbidostat_low"], color="r")



def load_config():
    f = open("experiment_parameters.yaml")
    config = yaml.safe_load(f)
    f.close()
    print(f"EXPERIMENT: {config['experiment_settings']['exp_name']}")
    return(config)
TWINDOW = 150

# plotthese = {"od_90_raw":{"names":["time","od_90_raw"], "plot": True, "plotvar":"od_90_raw"},
#              "od_135_raw":{"names":["time","od_135_raw"], "plot": True, "plotvar":"od_135_raw"},
#              "OD":{"names":["time","OD"], "plot": True, "plotvar":"OD"},
#              "growthrate_fromOD":{"names":["time","gr"], "plot":True, "plotvar":"gr"},
#              "growthrate":{"names":["time","gr"], "plot":True, "plotvar":"gr"},             
#              "OD_autocalib":{"names":["time","od_plinear_90", "od_plinear_135"],
#                              "plot": True, "plotvar":"od_plinear_135"}}

def load_data(config):
    EXP_NAME = config["experiment_settings"]["exp_name"]
    dflist = []
    CALIB_NAME = config["experiment_settings"].get("calib_name", "")
    for vial in [v["vial"] for v in config["experiment_settings"]["per_vial_settings"] if v["to_run"]]:
        sensdf = []
        for sensor in ["od_90_raw","od_135_raw"]:
            _df = pd.read_csv(f"./{EXP_NAME}/{sensor}/vial{vial}_{sensor}.txt",
                             header=None).iloc[1:,].astype(float)
            _df["time"] = _df[0]
            _df["reading"] = _df[1]
            _df["vial"] = vial
            _df["sensor"] = sensor
            sensdf.append(_df[["time","reading","vial","sensor"]])
        sensordf = pd.concat(sensdf).reset_index(drop=True).pivot(index=["time","vial"],
                                                                  columns="sensor",
                                                                  values="reading").reset_index()
        
        #stirdf = pd.read_csv(f"./{EXP_NAME}/stirrate/vial{vial}_stirrate.txt").iloc[1:]
        #df = sensordf.merge(stirdf, on=["time","vial"])
        pumpdf = pd.read_csv(f"./{EXP_NAME}/pump_log/vial{vial}_pump_log.txt",
                             names=["time","pump"]).iloc[1:].astype(float)
        df = sensordf.merge(pumpdf, on=["time"],
                      how="left")

        oddf = pd.read_csv(f"./{EXP_NAME}/OD/vial{vial}_OD.txt",
                             names=["time","OD"]).iloc[1:].astype(float)
        df = df.merge(oddf, on=["time"],how="left")
        if CALIB_NAME != "":
            df_oac = pd.read_csv(f"./{EXP_NAME}/OD_autocalib/vial{vial}_OD_autocalib.txt",
                             names=["time","od_plinear_90","od_plinear_135"]).iloc[1:].astype(float)
            df = df.merge(df_oac, on="time", how="left")
        dflist.append(df)
    fulldf = pd.concat(dflist).reset_index(drop=True)
    return(fulldf)

def plot_calibration(config):
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
        for sensor, vial in product(["od_90_raw","od_135_raw"], VIALS_TO_RUN):
            df = pd.read_csv(f"./{EXP_NAME}/{sensor}/vial{vial}_{sensor}.txt",
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
        vials = [v for v in config["experiment_settings"]["per_vial_settings"] if v["to_run"]]
        
        for ax, vial in zip(axes, range(len(vials))):
            for i, (idx, row) in enumerate(fulldf[(fulldf.sensor == "90") &\
                                                  (fulldf.vial == vials[vial]["vial"]) &\
                                                  (fulldf.pump > 0)].iterrows()):
                ax.axvline(row.time, color="k", alpha=0.4)
                ax.text(row.time,
                        fulldf[(fulldf.sensor == "90") &\
                               (fulldf.vial == vials[vial]["vial"]) &\
                               (fulldf.time < row.time)].reading.median(),
                        str(i))    
        plt.savefig(f"{EXP_NAME}-curves.png")
        plt.close()
        g = sns.relplot(data=fulldf, x="estimated_od", y="reading",
                        hue="sensor",col="vial",col_wrap=4,
                    facet_kws={"sharey":False})
        plt.savefig(f"{EXP_NAME}.png")
    except Exception:
        print("no files found")
        raise
        
def plot_turbidostat(config, datdf):
    EXP_NAME = config["experiment_settings"]["exp_name"]
    if "calib_name" in config["experiment_settings"].keys():
        CALIB_NAME = config["experiment_settings"]["calib_name"]
        g = sns.relplot(data=datdf[["time","vial","od_plinear_135"]].dropna(),
                        x="time", y="od_plinear_135",
                        col="vial",col_wrap=4,
                        kind="line",marker="o")
        plot_turbidostat_limits(config, g, datdf)
        plt.savefig(f"{EXP_NAME}-dilutions.png")
        plt.close()

        ## Estimate doubling time based on pump action
        dflist = []
        for vialsetting in [pvs for pvs in\
                            config["experiment_settings"]["per_vial_settings"]
                            if pvs["to_run"]]:
            tlow, thigh = vialsetting["turbidostat_low"], vialsetting["turbidostat_high"]
            _df = pd.read_csv(f"{EXP_NAME}/ODset/vial{vialsetting['vial']}_ODset.txt",
                              names=["time","ODset"],
                              skiprows=[0]).astype(float)
            _df = _df.assign(vial = vialsetting["vial"],
                             turbidostat_low = tlow,
                             turbidostat_high = thigh)
            _df = _df[(_df.ODset == _df.turbidostat_low) | (_df.ODset == _df.turbidostat_high)]
            _df = _df.assign(growthwindow = _df.time.shift(-1),
                             growthod= _df.ODset.shift(-1))
            _df = _df[_df.ODset == _df.turbidostat_high] ## We are interested in the growth period
            dflist.append(_df[["time","growthwindow","growthod","vial","ODset"]])
        
        df = pd.concat(dflist).reset_index(drop=True)
        print(df)

        df = df.assign(GrowthRate = np.log(df.growthod/df.ODset)/(df.time - df.growthwindow))
        df = df.assign(DoublingTime = np.log(2)/df.GrowthRate)        
        
        sns.relplot(data=df,
                    x="time",
                    y="GrowthRate",col="vial",col_wrap=4)
        plt.savefig(f"{EXP_NAME}-growth-rate-estimates.png")
        plt.close("all")
        sns.relplot(data=df,
                    x="time",
                    y="DoublingTime",col="vial",col_wrap=4)
        plt.savefig(f"{EXP_NAME}-doubling-time.png")
        
    else:
        pass
    # dflist = []
    # active_vials = 

    # for vialconfig in active_vials:
    #     vial = vialconfig["vial"]
    #     tlow, thigh = vialconfig["turbidostat_low"], vialconfig["turbidostat_high"]
    #     _df = pd.read_csv(f"{EXP_NAME}/{plotthis}/vial{vial}_{plotthis}.txt",
    #                       names=["Time (hr)","ODset"],
    #                       skiprows=[0]).astype(float)
    #     _df = _df.assign(vial = vial,
    #                      datatype = plotthis,
    #                      turbidostat_low = tlow,
    #                      turbidostat_high = thigh)
    #     dflist.append(_df)
    # df = pd.concat(dflist)
    # df = df[df.turbidostat_low == df.ODset].reset_index(drop=True)
    # df = df.assign(last_dilution = df.groupby("vial")["Time (hr)"].shift(1).reset_index()["Time (hr)"],
    #                dilution_count = df.groupby("vial").cumcount())    
    # df = df.assign(dilution_interval_h = df["Time (hr)"] - df.last_dilution)

    # g = sns.relplot(data=df,
    #             x="Time (hr)",y="dilution_interval_h",
    #                 col="vial",kind="line",marker="o",
    #                 palette="tab10",facet_kws={"sharey":False})

    # plt.savefig(f"{EXP_NAME}-dilution-times.png")

def customplot(config):
    EXP_NAME = config["experiment_settings"]["exp_name"]
    active_vials = [pvs for pvs in config["experiment_settings"]["per_vial_settings"]
                    if pvs["to_run"]]
    dflist = []
    pumplist = []
    for vialconfig in active_vials:
        vial = vialconfig["vial"]
        pump = pd.read_csv(f"{EXP_NAME}/pump_log/vial{vial}_pump_log.txt",
                          names=["time","timein","pump"],
                          skiprows=[0])
        _pump = pump.assign(vial = vial)
        pumplist.append(_pump)
    pump = pd.concat(pumplist).reset_index(drop=True)
    def calculate_conc(gdf):
        Clist = [0]
        vvial = 22
        vadd = 1.1
        for i, row in gdf.iterrows():
            if row.pump == "in1":
                Clist.append( Clist[-1]*vvial/(vvial + vadd))
            elif row.pump == "in2":
                Clist.append((Clist[-1]*vvial + vadd*5)/(vvial+vadd))

        return(gdf.assign(Phloroglucinol_gL = Clist)[["time","Phloroglucinol_gL"]])
    concdf = pump.groupby(["vial"]).apply(calculate_conc).reset_index()
    print(concdf)
    sns.relplot(data=concdf,x="time",y="Phloroglucinol_gL",
                col="vial",col_wrap=4)
    plt.savefig(f"{EXP_NAME}-ph-conc.png")
    
def plot_morbidostat(config):
    EXP_NAME = config["experiment_settings"]["exp_name"]
    active_vials = [pvs for pvs in config["experiment_settings"]["per_vial_settings"]
                    if pvs["to_run"]]
    dflist = []
    pumplist = []
    for vialconfig in active_vials:
        vial = vialconfig["vial"]
        _df = pd.read_csv(f"{EXP_NAME}/OD_autocalib/vial{vial}_OD_autocalib.txt",
                          names=["time","od_plinear_90","od_plinear_135"],
                          skiprows=[0]).astype(float)
        pump = pd.read_csv(f"{EXP_NAME}/pump_log/vial{vial}_pump_log.txt",
                          names=["time","timein","pump"],
                          skiprows=[0])
        _df = _df.assign(vial = vial)
        _pump = pump.assign(vial = vial)
        dflist.append(_df)
        pumplist.append(_pump)
    df = pd.concat(dflist).reset_index(drop=True)
    pump = pd.concat(pumplist).reset_index(drop=True)
    df = df[df["time"] > (df["time"].max()-TWINDOW)]
    df["od_plinear_135"] = df.groupby(["vial"]).od_plinear_135.ffill()
    calibdf = pd.read_csv(f"{config['experiment_settings']['calib_name']}.csv")
    ## Plot overlay
    g = sns.relplot(data=df, x="time",
                    y="od_plinear_135",
                    s=50,
                    edgecolor=None,
                    alpha=0.1,
                    col="vial",
                    col_wrap=4, 
                    aspect=1.3,
                    facet_kws={"sharey":False })

    for ax, v in zip(g.axes.flatten(), df.vial.unique()):
        for p,c in zip(["in1", "in2"],["g","r"]):
            T = pump[(pump.vial == v) & (pump.pump == p)]["time"]
            _df = df[(df.vial == v) & (df["time"].isin(T))][["time","od_plinear_135"]]
            ax.plot(_df["time"],
                    _df.od_plinear_135,
                    f"{c}o", ms=19)
        ax.axhline(config["experiment_settings"]["per_vial_settings"][v]["morbidostat_setpoint"],
                   color="r",
                   alpha=0.5)
        ## Draw a band where OD readings fall in the calibration range.
        ax.add_artist(Rectangle((0,calibdf[calibdf.vial == v].estimated_od.min()),
                                df["time"].max(),
                                calibdf[calibdf.vial == v].estimated_od.max()\
                                - calibdf[calibdf.vial == v].estimated_od.min(),
                                alpha=0.1))
    plt.tight_layout()
    plt.savefig(f"{EXP_NAME}-morbidostat.png")
    plt.close()

    ## Plot overlay in the most recent 2 hours == 3*60*2 =360 readings
    plotdf = df.groupby("vial").tail(120).reset_index()
    g = sns.relplot(data=plotdf, x="time",
                    y="od_plinear_135",
                    s=50,
                    edgecolor=None,
                    alpha=0.1,
                    col="vial",
                    col_wrap=4, 
                    aspect=1.3,
                    facet_kws={"sharey":False })

    for ax, v in zip(g.axes.flatten(), plotdf.vial.unique()):
        for p,c in zip(["in1", "in2"],["g","r"]):
            T = pump[(pump.vial == v) & (pump.pump == p)]["time"]
            _df = plotdf[(plotdf.vial == v) & (plotdf["time"].isin(T))][["time","od_plinear_135"]]
            ax.plot(_df["time"],
                    _df.od_plinear_135,
                    f"{c}o", ms=19)
        ax.axhline(config["experiment_settings"]["per_vial_settings"][v]["morbidostat_setpoint"],
                   color="r",
                   alpha=0.5)
        ## Draw a band where OD readings fall in the calibration range.
        ax.add_artist(Rectangle((0,calibdf[calibdf.vial == v].estimated_od.min()),
                                df["time"].max(),
                                calibdf[calibdf.vial == v].estimated_od.max()\
                                - calibdf[calibdf.vial == v].estimated_od.min(),
                                alpha=0.1))
    plt.tight_layout()
    plt.savefig(f"{EXP_NAME}-morbidostat-zoom.png")
    plt.close()
    
    ### hardcoded
    # volume = 1.1 # ml
    # g = sns.relplot(data=concentrationdf,
    #                 x="Time (hr)", 
    #                 y = "Salt_percent_wt",
    #                 hue="pump",
    #                 col="vial", col_wrap=4, s=100)

    # plt.savefig(f"{EXP_NAME}-salt.png")
    # plt.close()
        
    # stirswitch = config["experiment_settings"]["stir_settings"]["stir_switch"]
    # active_vials = [pvs["vial"] for pvs in config["experiment_settings"]["per_vial_settings"]
    #                 if pvs["to_run"]]

    # if stirswitch:
    #     plotthese["stirrate"] = {"names":["time","old stir time",
    #                                       "stir rate"],
    #                              "plot": False, "plotvar":"stir rate"}
    # dflist = []
    # cdflist = []

    # for vial, plotthis in product(active_vials, plotthese.keys()):
    #     _df = pd.read_csv(f"{EXP_NAME}/{plotthis}/vial{vial}_{plotthis}.txt",
    #                       names=plotthese[plotthis]["names"],
    #                       skiprows=[0]).astype(float)
    #     _df["vial"] = vial
    #     _df["datatype"] = plotthis
    #     dflist.append(_df)

    # df = pd.concat(dflist).reset_index()

    # df["vial"] = df.vial.astype("category")
    
def plot_sensor_scatter(config, df):
    EXP_NAME = config["experiment_settings"]["exp_name"]
    if "calib_name" in config["experiment_settings"].keys():
        CALIB_NAME = config["experiment_settings"]["calib_name"]
    else:
        CALIB_NAME = ""
    active_vials = [pvs["vial"] for pvs in config["experiment_settings"]["per_vial_settings"]
                    if pvs["to_run"]]        
    fig, axes = plt.subplots(int(np.ceil(len(active_vials)/4.)), 4,
                             figsize=(20, 5.* np.ceil(len(active_vials)/4.)))

    axes = axes.flatten()

    if CALIB_NAME !="":
        calibdf = pd.read_csv(f"{CALIB_NAME}.csv", index_col=0)
        calibdf = calibdf.assign(sensor = calibdf.sensor.astype(str))
    else:
        calibdf = None
    for vial, ax in zip(active_vials, axes):
        if CALIB_NAME != "":
            _calibdf = calibdf[calibdf.vial == vial][["estimated_od","reading","sensor"]]\
                .pivot(index="estimated_od",values="reading",columns="sensor")                
            cdat = _calibdf
            ax.scatter(cdat["90"].values, cdat["135"].values, label="Calibration Median")
        ddat = df[df.vial == vial]
        ax.scatter(ddat["od_90_raw"],
                   ddat["od_135_raw"],
                   c=ddat.time.values,
                   s=3,
                   alpha=0.5, label="Timecourse")
        ax.set_xlabel("Sensor: 90")
        ax.set_ylabel("Sensor: 135")
        ax.set_title(f"Vial {vial}")
    if vial == active_vials[-1]:
        ax.legend()
        
    plt.tight_layout()    
    plt.savefig(f"{EXP_NAME}-projection.png")
    plt.close()

    ## Timecourses
    for sensor in ["od_90_raw","od_135_raw","OD","od_plinear_135"]:
        print(sensor)
        fig, axes = plt.subplots(int(np.ceil(len(active_vials)/4.)), 4,
                                 figsize=(20, 5.* np.ceil(len(active_vials)/4.)))

        axes = axes.flatten()
        for vial, ax in zip(active_vials, axes):
            ddat = df[(df.vial == vial)]
            ax.plot(ddat.time.values,
                       ddat[sensor],
                       alpha=0.5, label="Timecourse")
            ax.set_title(f"Vial{vial}")
            ax.set_xlabel("Time (h)")
            ax.set_ylabel(f"{sensor}")
        plt.tight_layout()
        plt.savefig(f"{EXP_NAME}-{sensor}.png")
        plt.close("all")
    

    # for plotthis in plotthese.keys():
    #     print(plotthis)
    #     if plotthese[plotthis]["plot"]:
    #         yvar = plotthese[plotthis]["plotvar"]
    #         if "autocalib" in plotthis:
    #             if stirswitch:
    #                 _df = df[df.datatype == plotthis]
    #                 stirdf = df[df.datatype == "stirrate"]
    #                 _df = _df[["time", "od_plinear_90","od_plinear_135", "vial"]].merge(stirdf[["time","stir rate","vial"]], on=["time","vial"])
    #                 _df = _df.melt(id_vars=["time","vial","stir rate"], value_vars=["od_plinear_90",
    #                                                                                 "od_plinear_135"],
    #                                                   var_name="sensor", value_name="inferred OD").dropna()
    #                 g = sns.relplot(data=_df, x="time",
    #                                 y="inferred OD",style="stir rate",
    #                                 col="vial", col_wrap=4,
    #                                 hue="sensor", kind="line")
    #                 plt.yscale("log", base=2)
    #                 isok = True                    
    #             else:
    #                 _df = df[df.datatype == plotthis].melt(id_vars=["time","vial"],
    #                                                        value_vars=["od_plinear_90",
    #                                                                    "od_plinear_135"],
    #                                                        var_name="sensor",
    #                                                        value_name="inferred OD").dropna()

    #                 g = sns.relplot(data=_df, x="time",
    #                                 y="inferred OD",
    #                                 col="vial", col_wrap=4,
    #                                 hue="sensor", kind="line")
    #                 if config["experiment_settings"]["operation"]["mode"] == "turbidostat":
    #                     for i, ax in enumerate(g.axes.flatten()):
    #                         ax.axhline(config["experiment_settings"]["per_vial_settings"][i]["turbidostat_high"], color="k")
    #                         ax.axhline(config["experiment_settings"]["per_vial_settings"][i]["turbidostat_low"], color="r")                        
    #                 plt.savefig(f"{EXP_NAME}-{plotthis}-linear.png")
    #                 plt.close()
    #                 g = sns.relplot(data=_df, x="time",
    #                                 y="inferred OD",
    #                                 col="vial", col_wrap=4,
    #                                 hue="sensor", kind="line")
    #                 plt.yscale("log", base=2)                    
    #                 isok = True

    #         elif "growth" in plotthis:
    #             try:
    #                 if stirswitch:
    #                     _df = df[df.datatype == plotthis]\
    #                         [["time", yvar, "vial"]]\
    #                         .merge(df[df.datatype=="stirrate"]\
    #                                [["time","stir rate","vial"]],
    #                                on=["time","vial"])
    #                     if _df.shape[0] > 0:
    #                         _df = _df[(_df[yvar] < 3) & (_df[yvar] > 0 )]
    #                         _df["Doubling time (hr)"] = 1/_df[yvar]
    #                         _df = _df[_df["Doubling time (hr)"] < 50]
    #                         g = sns.relplot(data=_df, x="time",
    #                                         y="Doubling time (hr)",
    #                                         col="vial",col_wrap=4,edgecolor=None,
    #                                         style="stir rate", kind="line")            

    #                 else:
    #                     _df = df.fillna(0)
    #                     sns.set_style("whitegrid")
    #                     _df = _df[_df.time > _df.time.max() - 10.0]
    #                     g = sns.relplot(data=_df[(_df.datatype == plotthis) & (_df.gr > 0) & (_df.gr < 3)], x="time",
    #                                     y=yvar,aspect=0.75,facet_kws={"sharey":False},
    #                                     col="vial", col_wrap=4,edgecolor=None)
                              
    #                 isok = True
    #             except Exception:
    #                 print("Error in growth rate plotting")
    #                 isok = False
    #         else:
    #             if stirswitch:
    #                 _df = df[df.datatype == plotthis][["time", yvar, "vial"]].merge(df[df.datatype=="stirrate"][["time","stir rate","vial"]], on=["time","vial"])
    #                 if _df.shape[0] > 0:
    #                     g = sns.relplot(data=_df, x="time",
    #                                     y=yvar,
    #                                     col="vial", col_wrap=4,edgecolor=None,
    #                                     hue="stir rate", marker="o",facet_kws={"sharey":False})            

    #             else:
    #                 TWINDOW = 200
    #                 _df = df[(df.datatype == plotthis)\
    #                          & (df["time"] > (df["time"].max() - TWINDOW))]
    #                 g = _df.groupby(["vial"]).apply(filter_noise, yvar)
    #                 _df = _df.merge(g, on=["vial","time"],suffixes=["","_smooth"])
    #                 g = sns.relplot(data=_df, x="time",
    #                                 y=f"{yvar}_smooth",
    #                                 col="vial", col_wrap=4,
    #                                 kind="line",facet_kws={"sharey":False})                                                            
    #                 # g = sns.relplot(data=df[df.datatype == plotthis], x="time",
    #                 #                 y=yvar,
    #                 #                 col="vial", col_wrap=4,
    #                 #                 hue="vial", kind="line",facet_kws={"sharey":False})
    #         if isok:
    #             plt.savefig(f"{EXP_NAME}-{plotthis}.png")
    
if __name__ == "__main__":
    config = load_config()
    df = load_data(config)
    if config["experiment_settings"]["operation"]["mode"] == "calibration":
        print("plotting calibration...")
        plot_calibration(config)
    CALIB_NAME = config["experiment_settings"].get("calib_name", "")
    if config["experiment_settings"]["operation"]["mode"] == "turbidostat":
        plot_turbidostat(config, df)
    if config["experiment_settings"]["operation"]["mode"] == "morbidostat":
        plot_morbidostat(config)

    ## Routine plots
    ## Projection of sensor data. Optionally plot calibration data
    plot_sensor_scatter(config, df)
    customplot(config)
