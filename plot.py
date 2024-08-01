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
    
def plot_turbidostat_limits(g, _df):
    for (i, ax), vialid in enumerate(g.axes.flatten(), _df["vial"].unique()):
        ax.axhline(config["experiment_settings"]["per_vial_settings"][vialid]["turbidostat_high"], color="k")
        ax.axhline(config["experiment_settings"]["per_vial_settings"][vialid]["turbidostat_low"], color="r")




f = open("experiment_parameters.yaml")
config = yaml.safe_load(f)
f.close()

print(f"PLOTTING: {config['experiment_settings']['exp_name']}")
TWINDOW = 150
sns.set(style="ticks",
        font_scale=2,
        # {'axes.grid' : True},
              )

plotthese = {"od_90_raw":{"names":["time","od_90_raw"], "plot": True, "plotvar":"od_90_raw"},
             "od_135_raw":{"names":["time","od_135_raw"], "plot": True, "plotvar":"od_135_raw"},
             "OD":{"names":["time","OD"], "plot": True, "plotvar":"OD"},
             "growthrate_fromOD":{"names":["time","gr"], "plot":True, "plotvar":"gr"},
             "growthrate":{"names":["time","gr"], "plot":True, "plotvar":"gr"},             
             "OD_autocalib":{"names":["time","od_plinear_90", "od_plinear_135"],
                             "plot": True, "plotvar":"od_plinear_135"}}


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
    isok = True
    EXP_NAME = config["experiment_settings"]["exp_name"]
    if "calib_name" in config["experiment_settings"].keys():
        CALIB_NAME = config["experiment_settings"]["calib_name"]
    else:
        CALIB_NAME = ""
    if config["experiment_settings"]["operation"]["mode"] == "turbidostat":
        plotthis = "ODset"
        dflist = []
        active_vials = [pvs for pvs in config["experiment_settings"]["per_vial_settings"]
                        if pvs["to_run"]]

        for vialconfig in active_vials:
            vial = vialconfig["vial"]
            tlow, thigh = vialconfig["turbidostat_low"], vialconfig["turbidostat_high"]
            _df = pd.read_csv(f"{EXP_NAME}/{plotthis}/vial{vial}_{plotthis}.txt",
                              names=["Time (hr)","ODset"],
                              skiprows=[0]).astype(float)
            _df = _df.assign(vial = vial,
                             datatype = plotthis,
                             turbidostat_low = tlow,
                             turbidostat_high = thigh)
            dflist.append(_df)
        df = pd.concat(dflist)
        df = df[df.turbidostat_low == df.ODset].reset_index(drop=True)
        straindf = pd.DataFrame({"vial":list(range(0,16)),
                                 "strain":[6,6,6,6,
                                           9,9,9,"b",
                                           "9-ctrl",6,6,9,
                                           9,"6-ctrl",9,"b"],
                                 "replicate":[1,2,3,4,
                                              1,2,3,1,
                                              1,1,2,1,
                                              2,1,4,2],
                                 "outgrowth":[0,0,0,0,
                                              0,0,0,0,
                                              0,1,1,1,
                                              1,0,0,0]})
        straindf["pregrowth"] = [f"{v}%" for v in straindf.outgrowth]
        df = df.merge(straindf, on="vial")
        df = df.assign(last_dilution = df.groupby("vial")["Time (hr)"].shift(1).reset_index()["Time (hr)"],
                       dilution_count = df.groupby("vial").cumcount())
        df = df.assign(num_generations = df.dilution_count*np.log2(df.turbidostat_high/df.turbidostat_low) + 1)
        df = df.assign(dilution_interval_h = df["Time (hr)"] - df.last_dilution)
        
        g = sns.relplot(data=df[df.dilution_interval_h < 7],
                    x="Time (hr)",y="dilution_interval_h",
                        hue="replicate",kind="line",marker="o",col="strain",
                        row="pregrowth",
                        palette="tab10",facet_kws={"sharey":False})

        plt.savefig(f"{EXP_NAME}-dilution-times.png")
        plt.close()
        #df.to_csv("temp.csv")

        g = sns.relplot(data=df,
                        x="Time (hr)",y="num_generations",col="strain",
                        row="outgrowth",
                        hue="replicate",kind="line",marker="o",
                        palette="tab10",facet_kws={"sharey":False}
                    )
        # annotate_media(g,ymax=df.num_generations.max())
        plt.savefig(f"{EXP_NAME}-generation-times.png")
        plt.close()
        
    if config["experiment_settings"]["operation"]["mode"] == "morbidostat":
        plotthis = "OD_autocalib"        
        active_vials = [pvs for pvs in config["experiment_settings"]["per_vial_settings"]
                        if pvs["to_run"]]
        dflist = []
        pumplist = []
        for vialconfig in active_vials:
            vial = vialconfig["vial"]
            _df = pd.read_csv(f"{EXP_NAME}/{plotthis}/vial{vial}_{plotthis}.txt",
                              names=["Time (hr)","od_plinear_90","od_plinear_135"],
                              skiprows=[0]).astype(float)
            pump = pd.read_csv(f"{EXP_NAME}/pump_log/vial{vial}_pump_log.txt",
                              names=["Time (hr)","timein","pump"],
                              skiprows=[0])
            _df = _df.assign(vial = vial,
                             datatype = plotthis)
            # _df = _df.merge(pump, on="Time (hr)",
            #                 how="left")
            _pump = pump.assign(vial = vial)
            dflist.append(_df)
            pumplist.append(_pump)
        df = pd.concat(dflist).reset_index(drop=True)
        pump = pd.concat(pumplist).reset_index(drop=True)
        df = df[df["Time (hr)"] > (df["Time (hr)"].max()-TWINDOW)]
        df["od_plinear_135"] = df.groupby(["vial"]).od_plinear_135.ffill()


        def get_salt_conc(gdf):
            gdf = gdf.assign(Salt_percent_wt = 0)                
            currsalt = 0
            STOCK = 1            
            for i,row in gdf.iterrows():
                if row.pump == "in2":
                    currsalt = (currsalt *22  + STOCK*1.1) / (22. + 1.1)
                    gdf.loc[i, "Salt_percent_wt"] = currsalt
                elif row.pump == "in1":
                    currsalt = (currsalt *22 ) / (22. + 1.1)
                    gdf.loc[i, "Salt_percent_wt"] = currsalt
                else:
                    gdf.loc[i, "Salt_percent_wt"] = currsalt
            return(gdf[["Salt_percent_wt","Time (hr)"]])
        concentrationdf = pump.merge(pump.groupby("vial").apply(get_salt_conc),
                                     on=["vial","Time (hr)"])
        concentrationdf = concentrationdf.assign(Log2_Salt_wtpc = np.log2(concentrationdf.Salt_percent_wt))
        
        # 0.14,
        calibdf = pd.read_csv(f"{config['experiment_settings']['calib_name']}.csv")

        g = sns.relplot(data=df, x="Time (hr)",
                        y="od_plinear_135",
                        s=50,edgecolor=None,alpha=0.05,
                        col="vial",col_wrap=4, palette="deep",
                        aspect=1.5,
                        facet_kws={"sharey":False })
        
        for ax, v in zip(g.axes.flatten(), df.vial.unique()):
            for p,c in zip(["in1", "in2"],["g","r"]):
                T = pump[(pump.vial == v) & (pump.pump == p)]["Time (hr)"]
                _df = df[(df.vial == v) & (df["Time (hr)"].isin(T))][["Time (hr)","od_plinear_135"]]
                ax.plot(_df["Time (hr)"],
                        _df.od_plinear_135,
                        f"{c}o", ms=5)
            ax.axhline(config["experiment_settings"]["per_vial_settings"][v]["morbidostat_setpoint"],
                       color="r",
                       alpha=0.5)
            ax2 = ax.twinx()
            saltdf = concentrationdf[concentrationdf.vial == v]
            ax2.plot(saltdf["Time (hr)"],
                     saltdf.Salt_percent_wt, 'r--')
            ax2.set_ylabel("NaCl (%wt/vol)")
            ax.add_artist(Rectangle((0,calibdf[calibdf.vial == v].estimated_od.min()), df["Time (hr)"].max(),calibdf[calibdf.vial == v].estimated_od.max() - calibdf[calibdf.vial == v].estimated_od.min(), alpha=0.1))
        plt.tight_layout()
        plt.savefig(f"{EXP_NAME}-morbidostat.png")
        plt.close()
        ### hardcoded
        volume = 1.1 # ml


        g = sns.relplot(data=concentrationdf,
                        x="Time (hr)", 
                        y = "Salt_percent_wt",
                        hue="pump",
                        col="vial", col_wrap=4, s=100)

        plt.savefig(f"{EXP_NAME}-salt.png")
        plt.close()
        
    stirswitch = config["experiment_settings"]["stir_settings"]["stir_switch"]
    active_vials = [pvs["vial"] for pvs in config["experiment_settings"]["per_vial_settings"]
                    if pvs["to_run"]]

    if stirswitch:
        plotthese["stirrate"] = {"names":["time","old stir time",
                                          "stir rate"],
                                 "plot": False, "plotvar":"stir rate"}
    dflist = []
    cdflist = []

    for vial, plotthis in product(active_vials, plotthese.keys()):
        _df = pd.read_csv(f"{EXP_NAME}/{plotthis}/vial{vial}_{plotthis}.txt",
                          names=plotthese[plotthis]["names"],
                          skiprows=[0]).astype(float)
        _df["vial"] = vial
        _df["datatype"] = plotthis
        dflist.append(_df)

    df = pd.concat(dflist).reset_index()

    df["vial"] = df.vial.astype("category")

    fig, axes = plt.subplots(int(np.ceil(len(active_vials)/4.)), 4,
                             figsize=(20, 5.* np.ceil(len(active_vials)/4.)))

    axes = axes.flatten()

    if CALIB_NAME !="":
        calibdf = pd.read_csv(f"{CALIB_NAME}.csv", index_col=0)
        calibdf = calibdf.assign(sensor = calibdf.sensor.astype(str))
    else:
        calibdf = None
    for vial, ax in enumerate(axes):
        if vial in active_vials:
            if CALIB_NAME != "":
                _calibdf = calibdf[calibdf.vial == vial][["estimated_od","sensor","reading"]]\
                    .pivot(index="estimated_od",values="reading",columns="sensor")                
                cdat = _calibdf
                ax.scatter(cdat["90"].values, cdat["135"].values, label="Calibration Median")
                # ax.scatter(cdat["90"].values,
                #            cdat["135"].values, c="r", alpha=0.1,label="Calibration Raw Values")    
            ddat = df[df.vial == vial]
            ax.scatter(ddat[ddat["datatype"] == "od_90_raw"].od_90_raw,
                    ddat[ddat["datatype"] == "od_135_raw"].od_135_raw,
                       c=ddat[ddat["datatype"] == "od_135_raw"].time.values,
                       s=3,
                       alpha=0.5, label="Timecourse")
            ax.set_xlabel("Sensor: 90")
            ax.set_ylabel("Sensor: 135")

            ax.set_title(f"Vial {vial}")
        if vial == active_vials[-1]:
            ax.legend()
        
    # for vial, ax in enumerate(axes):
    #     if vial in active_vials:
    #         if CALIB_NAME != "":            
    #             rawc90 = pd.read_csv(f"{CALIB_NAME}/od_90_raw/vial{vial}_od_90_raw.txt",
    #                                skiprows=[0],
    #                                names=["time","90"])
    #             rawc135 = pd.read_csv(f"{CALIB_NAME}/od_135_raw/vial{vial}_od_135_raw.txt",
    #                                skiprows=[0],
    #                                names=["time","135"])
    #             pump = pd.read_csv(f"{CALIB_NAME}/pump_log/vial{vial}_pump_log.txt",
    #                                skiprows=[0],
    #                                names=["time","pump_duration"])
    #             pump["pump_event"] = pump.index.astype(int)
    #             cdat = rawc90.merge(rawc135, on="time")
    #             cdat["pump_event"] = np.nan
    #             for i, prow in pump.iterrows():
    #                 cdat.loc[(cdat.time <= prow.time) & (np.isnan(cdat.pump_event)), "pump_event"] = prow.pump_event
    #             cdat["90_median"] = cdat.groupby("pump_event")["90"].median()
    #             cdat["135_median"] = cdat.groupby("pump_event")["135"].median()    

    #             ax.scatter(cdat["90_median"].values, cdat["135_median"].values, label="Calibration Median")
    #             ax.scatter(cdat["90"].values,
    #                        cdat["135"].values, c="r", alpha=0.1,label="Calibration Raw Values")    
    #         ddat = df[df.vial == vial]
    #         ax.scatter(ddat[ddat["datatype"] == "od_90_raw"].od_90_raw,
    #                 ddat[ddat["datatype"] == "od_135_raw"].od_135_raw,
    #                    c=ddat[ddat["datatype"] == "od_135_raw"].time.values,
    #                    s=3,
    #                    alpha=0.5, label="Timecourse")
    #         ax.set_xlabel("Sensor: 90")
    #         ax.set_ylabel("Sensor: 135")
    #         #ax.set_xlim(52000, 63500)

    #         ax.set_title(f"Vial {vial}")
    #     if vial == 15:
    #         ax.legend()

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
                    g = sns.relplot(data=_df[_df.sensor == yvar], x="time",
                                    y="inferred OD",style="stir rate",
                                    col="vial", col_wrap=4,
                                    hue="sensor", kind="line")
                    print(config["experiment_settings"]["operation"])
                    vials = [vts for vts in config["experiment_settings"]["per_vial_settings"] if vts['to_run']]
                    if config["experiment_settings"]["operation"]["mode"] == "turbidostat":
                        for i, ax in enumerate(g.axes.flatten()):
                            ax.axhline(vials[i]["turbidostat_high"], color="k")
                            ax.axhline(vials[i]["turbidostat_low"], color="r")                                            
                    plt.savefig(f"{EXP_NAME}-{plotthis}-linear.png")
                    plt.close()
                    g = sns.relplot(data=_df, x="time",
                                    y="inferred OD",style="stir rate",
                                    col="vial", col_wrap=4,
                                    hue="sensor", kind="line")
                    plt.yscale("log", base=2)
                    isok = True                    
                else:
                    _df = df[df.datatype == plotthis].melt(id_vars=["time","vial"],
                                                           value_vars=["od_plinear_90",
                                                                       "od_plinear_135"],
                                                           var_name="sensor",
                                                           value_name="inferred OD").dropna()

                    g = sns.relplot(data=_df, x="time",
                                    y="inferred OD",
                                    col="vial", col_wrap=4,
                                    hue="sensor", kind="line")
                    if config["experiment_settings"]["operation"]["mode"] == "turbidostat":
                        for i, ax in enumerate(g.axes.flatten()):
                            ax.axhline(config["experiment_settings"]["per_vial_settings"][i]["turbidostat_high"], color="k")
                            ax.axhline(config["experiment_settings"]["per_vial_settings"][i]["turbidostat_low"], color="r")                        
                    plt.savefig(f"{EXP_NAME}-{plotthis}-linear.png")
                    plt.close()
                    g = sns.relplot(data=_df, x="time",
                                    y="inferred OD",
                                    col="vial", col_wrap=4,
                                    hue="sensor", kind="line")
                    plt.yscale("log", base=2)                    
                    isok = True

            elif "growth" in plotthis:
                try:
                    if stirswitch:
                        _df = df[df.datatype == plotthis]\
                            [["time", yvar, "vial"]]\
                            .merge(df[df.datatype=="stirrate"]\
                                   [["time","stir rate","vial"]],
                                   on=["time","vial"])
                        if _df.shape[0] > 0:
                            _df = _df[(_df[yvar] < 3) & (_df[yvar] > 0 )]
                            _df["Doubling time (hr)"] = 1/_df[yvar]
                            _df = _df[_df["Doubling time (hr)"] < 50]
                            g = sns.relplot(data=_df, x="time",
                                            y="Doubling time (hr)",
                                            col="vial",col_wrap=4,edgecolor=None,
                                            style="stir rate", kind="line")            

                    else:
                        _df = df.fillna(0)
                        sns.set_style("whitegrid")
                        _df = _df[_df.time > _df.time.max() - 10.0]
                        g = sns.relplot(data=_df[(_df.datatype == plotthis) & (_df.gr > 0) & (_df.gr < 3)], x="time",
                                        y=yvar,aspect=0.75,facet_kws={"sharey":False},
                                        col="vial", col_wrap=4,edgecolor=None)
                              
                    isok = True
                except Exception:
                    print("Error in growth rate plotting")
                    isok = False
            else:
                if stirswitch:
                    _df = df[df.datatype == plotthis][["time", yvar, "vial"]].merge(df[df.datatype=="stirrate"][["time","stir rate","vial"]], on=["time","vial"])
                    if _df.shape[0] > 0:
                        g = sns.relplot(data=_df, x="time",
                                        y=yvar,
                                        col="vial", col_wrap=4,edgecolor=None,
                                        hue="stir rate", marker="o",facet_kws={"sharey":False})            

                else:
                    TWINDOW = 200
                    _df = df[(df.datatype == plotthis)\
                             & (df["time"] > (df["time"].max() - TWINDOW))]
                    g = _df.groupby(["vial"]).apply(filter_noise, yvar)
                    _df = _df.merge(g, on=["vial","time"],suffixes=["","_smooth"])
                    g = sns.relplot(data=_df, x="time",
                                    y=f"{yvar}_smooth",
                                    col="vial", col_wrap=4,
                                    kind="line",facet_kws={"sharey":False})                                                            
                    # g = sns.relplot(data=df[df.datatype == plotthis], x="time",
                    #                 y=yvar,
                    #                 col="vial", col_wrap=4,
                    #                 hue="vial", kind="line",facet_kws={"sharey":False})
            if isok:
                plt.savefig(f"{EXP_NAME}-{plotthis}.png")
    
