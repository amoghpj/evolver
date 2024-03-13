import streamlit as st
from PIL import Image
import yaml
import glob
import os
import pandas as pd
import shutil
import time
from subprocess import Popen, run

def write_config_to_file(config):
    cyaml = yaml.safe_dump(config)
    if os.path.exists("./experiment_parameters.yaml"):
        shutil.copyfile("./experiment_parameters.yaml",
                        f"./experiment_parameters.yaml.{time.time()}")
    with open("./experiment_parameters.yaml","w") as outfile:
        outfile.write(cyaml)

def load_config(path):
    f = open(path)
    config = yaml.safe_load(f)
    f.close()
    return(config)

OPERATION_MODES = ["calibration",
                  "growthcurve",
                  "chemostat",
                  "turbidostat"]

EVOLVER_NAMES = ["spongebob",
                 "gary",
                 "patrick",
                 "sandy",
                 "plankton",
                 "pearl",
                 "barnacleboy",
                 "mermaidman",
                 "squidward",
                 "krabs"]
ipdict = {"spongebob":"192.168.1.3",
          "gary":"192.168.1.6",
          "patrick":"192.168.1.4",
          "sandy":"192.168.1.5",
          "plankton":"192.168.1.14",
          "pearl": "192.168.1.11",
          "squidward":"192.168.1.10",
          "mermaidman":"192.168.1.8",
          "barnacleboy":"192.168.1.9",              
          "krabs":"192.168.1.7"}

if __name__ == '__main__':
    if os.path.exists("experiment_parameters.yaml"):
        currentconfig = load_config("experiment_parameters.yaml")
        expname = currentconfig\
            .get("experiment_settings", dict())\
            .get("exp_name", "")
        exps = [expname]
    else:
        currentconfig = dict()
        exps = []
        expname = ""

    exps.extend([f for f in os.listdir("./") if (os.path.isdir(f) and f not in  ["__pycache__", "img",".git",expname])])
    exps.append("Setup")
    exps.append("Current Experiment")    
    page = st.sidebar.selectbox('Experiments..',exps)
    st.title(f"{page}")

    revipdict = {str(v):k for k, v in ipdict.items()}

    config = {"experiment_settings":
              {"stir_settings":{
                  "stir_on_rate":4.0,
                  "stir_switch":False,
                  "stir_on_duration":6,
                  "stir_off_duration":6,
                  "stir_off_rate":0},
               "operation":{
                   "mode":"",},
               "per_vial_settings":[]
               }
              }

    if page == "Setup":
        with st.form("global_setup"):
            st.header("Global settings")
            exp_name = st.text_input("Experiment name",
                                     value=currentconfig\
                                     .get("experiment_settings", dict())\
                                     .get("exp_name", ""))
            ip = st.selectbox("IP address", EVOLVER_NAMES,
                              index = EVOLVER_NAMES.index(
                                  revipdict[currentconfig\
                                            .get("experiment_settings", dict())\
                                            .get("ip", "192.168.1.3")]))

            calib = st.text_input("Calibration name",
                                  value = currentconfig\
                                     .get("experiment_settings", dict())\
                                     .get("calib_name", ""))
            operation = st.selectbox("Operation mode", OPERATION_MODES,
                                     index = OPERATION_MODES.index(currentconfig\
                                                                   .get("experiment_settings", dict())\
                                                                   .get("operation", dict())\
                                                                   .get("mode","growthcurve")))
            temperature = st.number_input("Temperature",
                                          value = currentconfig\
                                     .get("experiment_settings", dict())\
                                     .get("temp_all", 25))
            stir_on_rate = st.number_input("Stir on rate",
                                           value = currentconfig\
                                           .get("experiment_settings", dict())\
                                           .get("stir_settings", dict())\
                                           .get("stir_on_rate", 8))
            stir_switch = st.checkbox("Stir rate switch?",
                                      value = currentconfig\
                                           .get("experiment_settings", dict())\
                                           .get("stir_settings", dict())\
                                           .get("stir_switch", False))
            stir_off_rate = st.number_input("Stir off rate",
                                            value = currentconfig\
                                           .get("experiment_settings", dict())\
                                           .get("stir_settings", dict())\
                                           .get("stir_off_rate", 0))
            stir_on_duration = st.number_input("Stir on duration (recommended: 6)",
                                               value = currentconfig\
                                           .get("experiment_settings", dict())\
                                           .get("stir_settings", dict())\
                                           .get("stir_on_duration", 6))
            stir_off_duration = st.number_input("Stir off duration (recommended: 6)", 
                                                value = currentconfig\
                                           .get("experiment_settings", dict())\
                                           .get("stir_settings", dict())\
                                           .get("stir_off_duration", 0))
            estimate_gr = st.checkbox("Estimate Growth Rate?",
                                      value = currentconfig\
                                           .get("experiment_settings", dict())\
                                           .get("estimate_gr", False))
            st.form_submit_button()
        config["experiment_settings"]["ip"] = ipdict[ip]
        config["experiment_settings"]["exp_name"] = str(exp_name)
        config["experiment_settings"]["temp_all"] = temperature
        if calib != "":
            config["experiment_settings"]["calib_name"] = calib

        config["experiment_settings"]["stir_settings"]["stir_on_rate"] = stir_on_rate
        config["experiment_settings"]["stir_settings"]["stir_switch"] = stir_switch
        config["experiment_settings"]["stir_settings"]["stir_off_rate"] = stir_off_rate
        config["experiment_settings"]["stir_settings"]["stir_on_duration"] = stir_on_duration
        config["experiment_settings"]["stir_settings"]["stir_off_duration"] = stir_off_duration
        
        config["experiment_settings"]["estimate_gr"] = estimate_gr
        ##############################
        ## Global settings for Turbidostat and Calibration
        ##############################
        with st.form("global_details"):
            st.header("Mode specific settings")
            with st.expander("Calibration settings"):
                num_pump_events = st.number_input("Number of calibration steps",20)
            # with st.expander("Chemostat settings"):
            #     chemoset = st.number_input("Chemo set")
            with st.expander("Turbidostat settings"):
                turbset = st.number_input("turbo_set")
            st.form_submit_button()
            
        config["experiment_settings"]["operation"]["mode"] = operation
        
        if operation == "calibration":
            config["experiment_settings"]["operation"]["num_pump_events"] = num_pump_events
            
        # if operation == "chemostat":
        #     config["experiment_settings"]["operation"]["chemo_rate"] = chemoset

        if len(currentconfig) > 0:
            viallist = []
            for pvc in currentconfig.get("experiment_settings", dict())\
                .get("per_vial_settings", []):
                viallist.append(pvc)
            df = pd.DataFrame(viallist)
        else:
            df = pd.DataFrame(
                [
                    {"vial": f"{vial}", "to_run": True, "volume":20., 
                     "calib_initial_od":0.,"calib_end_od":0.,
                     "turbidostat_low":0.,"turbidostat_high":0.,
                     "chemo_start_od":0.0, "chemo_start_time":0.0,
                     "chemo_rate":0.0}
                    for vial in range(16)
                ]
            )

        editeddf = st.experimental_data_editor(df, use_container_width=True)
        for i, row in editeddf.iterrows():
            if operation == "calibration":
                if row.calib_end_od == 0:
                    calib_end_od = row.calib_initial_od/10
                else:
                    calib_end_od = row.calib_end_od
            else:
                calib_end_od = row.calib_end_od                
            config["experiment_settings"]["per_vial_settings"].append(
                {"vial":int(row.vial),
                 "to_run":row.to_run,
                 "volume":row.volume,
                 "calib_initial_od":row.calib_initial_od,
                 "calib_end_od":calib_end_od,
                 "turbidostat_low":row.turbidostat_low,
                 "turbidostat_high":row.turbidostat_high,
                 "chemo_start_od":row.chemo_start_od,
                 "chemo_start_time":row.chemo_start_time,
                 "chemo_rate":row.chemo_rate,
                 })
        write_config = False
        write_config = st.button("Write configuration to file")
        if write_config:
            write_config_to_file(config)
            
        if operation == "calibration":
            st.markdown("If the calibration is complete and the calibration end ODs have been updated, write the calibration to file.")
            write_calibration = st.button("Write calibration to file")
            run(["python", "write_calibration_to_file.py"])

    elif page == "Current Experiment":
        if os.path.exists("experiment_parameters.yaml"):
            f = open("experiment_parameters.yaml","r")
            config = yaml.safe_load(f)
            f.close()
            with open('experiment_parameters.yaml') as f:
                print(f.readline())
        else:
            st.text(f"No currently defined experiment available.")
    else:
        try:
            calib = Image.open(f"{page}.png")
            st.image(calib, )
            curves = f"{page}-curves.png"
            st.image(curves)
        except:
            for suff in ["-od_135_raw",
                        "-od_90_raw",
                        "-OD",
                        "_projection",                         
                        "-OD_autocalib",
                        "-OD_autocalib-linear",
                        #"-growthrate",
                        "-growthrate_fromOD"
                         ]:
                st.header(suff[1:])
                if os.path.exists(f"{page}{suff}.png"):
                    st.image(Image.open(f"{page}{suff}.png"))
                else:
                    st.text(f"{page}{suff}.png Not found")
