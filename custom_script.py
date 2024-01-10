#!/usr/bin/env python3
import numpy as np
import logging
import os.path
import pandas as pd
import yaml
import time
import sys

def bye(arg=None):
    if arg is not None:
        print(arg)
    sys.exit()

class Settings():
    def __init__(self):
        f = open("experiment_parameters.yaml")
        config = yaml.safe_load(f)
        f.close()
        ### Validate:
        try:
            config.get("experiment_settings")
        except:
            bye("Required section `experiment_settings` missing. Exiting...")

        self.exp_name = config["experiment_settings"].get("exp_name", None)
        if self.exp_name is None:
            bye("Required variable `exp_name` missing")
            
        self.calib_name = config["experiment_settings"].get("calib_name", None)
        per_vial_dict = {vialsettings["vial"]:vialsettings\
                         for vialsettings in\
                         config["experiment_settings"].get("per_vial_settings", {})}
        if len(per_vial_dict) == 0:
            bye("Per vial settings may be needed for custom functions!")
        if len(per_vial_dict) < 16:
            print(f"Found settings for {len(per_vial_dict)} vials")
            print(f"Active vials are {self.fmt([vial if (vial in per_vial_dict.keys() and per_vial_dict[vial]['to_run'])  else '' for vial in range(16)])}")

        ## active_vials is the main entry point for overriding all other per vial settings.
        self.active_vials = []
        
        for vial, vialsettings in per_vial_dict.items():
            if vialsettings.get("to_run") is None:
                print(f"Should I run vial['vial']?")
            if vialsettings.get("to_run"):
                if type(vial) is int:
                    self.active_vials.append(vial)
                else:
                    bye(f"Which vial does this entry specify? Stuck at {vialsettings}.")
        
        # Global stir handling
        if config["experiment_settings"].get("stir_settings") is not None:
            self.stir_switch = config["experiment_settings"]["stir_settings"].get("stir_switch")            

            self.stir_on_rate = [0]*16
            for vidx in self.active_vials:
                self.stir_on_rate[vidx] = config["experiment_settings"]["stir_settings"]["stir_on_rate"]

            if (self.stir_switch is not None) and (self.stir_switch):
                self.stir_off_rate = [0]*16
                self.stir_on_duration = [0] * 16
                self.stir_off_duration = [0] * 16                
                for vidx in self.active_vials:
                    self.stir_on_rate[vidx] = per_vial_dict[vidx].get("stir_on_rate",
                                                                      config["experiment_settings"]["stir_settings"]["stir_on_rate"])
                    print(per_vial_dict[vidx])
                    self.stir_off_rate[vidx] = per_vial_dict[vidx].get("stir_off_rate",
                                                                       config["experiment_settings"]["stir_settings"]["stir_off_rate"])
                    
                    self.stir_on_duration[vidx] = per_vial_dict[vidx].get("stir_on_duration",
                                                                          config["experiment_settings"]["stir_settings"].get("stir_on_duration", 0))
                                                                          
                    self.stir_off_duration[vidx] = per_vial_dict[vidx].get("stir_off_duration",
                                                                           config["experiment_settings"]["stir_settings"].get("stir_off_duration", 0))
                
            
        # Global temperature handling
        if config["experiment_settings"].get("temp_all") is not None:
            temp = config["experiment_settings"]["temp_all"]
            self.temperature = [temp]*16

        if config["experiment_settings"].get("estimate_gr") is not None:
            self.estimate_gr = config["experiment_settings"].get("estimate_gr")

        
        self.operation_mode = config["experiment_settings"]["operation"].get("mode", None)
        if self.operation_mode is None:
            bye("Invalid operation mode specification")



        #for 
                    
        ## The following are variables that can be set per vial, but are not required
        ## for all operation modes.
        self.volume = [per_vial_dict[vidx].get("volume")\
                       if vidx in self.active_vials\
                       else 0
                       for vidx in range(16)]

        if self.operation_mode == "calibration":
            """
            Calibration requires three parameters:
            1. calibration initial od
            2. calibration final od 
            3. number of calibration steps DEFAULT 20
            """
            self.vials_to_run = [0]*16
            for vidx in self.active_vials:
                self.vials_to_run[vidx] = 1
            self.calibration_initial_od = [0.0]*16 ### TODO CHECK FOR BEHAVIOR
            self.calibration_end_od = [0.0]*16 ### TODO CHECK FOR BEHAVIOR
            self.calibration_fold_range = config["experiment_settings"]["operation"].get("fold_calibration", np.nan)
            self.calibration_measured_od = config["experiment_settings"]["operation"].get("measured_od")
            
            for vidx in self.active_vials:
                self.calibration_initial_od[vidx] = per_vial_dict[vidx].get("calib_initial_od")
                self.calibration_end_od[vidx] = per_vial_dict[vidx].get("calib_end_od", None)
                if self.calibration_end_od[vidx] is None and not np.isnan(self.calibration_fold_range):
                    self.calibration_end_od[vidx] = self.calibration_initial_od[vidx]/self.calibration_fold_range
                # if self.calibration_end_od is None:
                #     bye("Please specify global setting `end_od` in operation: calibration.")

            self.calibration_num_pump_events = config["experiment_settings"]["operation"].get("num_pump_events", 20)
            
        if self.operation_mode == "chemostat":
            """
            Chemostat operation:
            Required parameters:
            1. chemostat rate: per vial configuration
            Optional parameters:
            1. chemostat start OD DEFAULT 0
            2. chemostat start time DEFAULT 0
            3. chemostat growth rate responsive start DEFAULT 0
               This requires accurate growth rate estimation.
            """
            self.chemo_rate = [0]*16
            self.chemo_start_od = [0.]*16
            self.chemo_start_time = [0.] * 16
            self.chemo_growth_rate_responsive_start = config["experiment_settings"]["operation"].get("growth_rate_responsive_start", False)            
            for vidx in self.active_vials:
                for key in ["chemo_rate"]:
                    if key not in per_vial_dict[vidx].keys():
                        bye(f"Missing {key} specification for vial {vidx}")
                self.chemo_rate[vidx] = per_vial_dict[vidx].get("chemo_rate")

                self.chemo_start_od[vidx] = per_vial_dict[vidx].get("chemo_start_od", 0)
                self.chemo_start_time[vidx] = per_vial_dict[vidx].get("chemo_start_time", 0)

        if self.operation_mode == "turbidostat":
            """
            Turbidostat operation:
            Required parameters:
            1. turbidostat low threshold : per vial configuration
            2. turbidostat high threshold : per vial configuration
            """
            self.turbidostat_low = [9999]*16
            self.turbidostat_high = [9999]*16
            self.vials_to_run = [0]*16            
            for vidx in self.active_vials:
                self.vials_to_run[vidx] = 1                
                for key in ["turbidostat_low", "turbidostat_high"]:
                    if key not in per_vial_dict[vidx].keys():
                        bye(f"Missing {key} specification for vial {vidx}")
                self.turbidostat_low[vidx] = per_vial_dict[vidx].get("turbidostat_low")
                self.turbidostat_high[vidx] = per_vial_dict[vidx].get("turbidostat_high")                                

    def fmt(self, l, numtabs=0):
        sep = "".join(["\t"]*numtabs)
        s = "\n" + sep
        if type(l) is list:
            for idx, v in enumerate(l):
                s +=str(v).format('%.1f') + "\t"
                if (idx +1) % 4 == 0:
                    s += "\n" + sep
        else:
             s = str(l)       
        return(s)
            
    def __repr__(self):
        s = ""
        s += f'Experiment name: {self.exp_name}\n'
        if self.calib_name is None:
            s += f'Calib name: CURRENTLY UNSET\n'
        else:
            s += f'Calib name : {self.calib_name}\n'
        s += "--- GLOBAL ---\n"
        s += f"Estimate Growth Rate: {self.estimate_gr}\n"
        s += f"Temperature: {self.fmt(self.temperature)}\n"
        if self.stir_switch:
            s += f"Switch stir rate: Yes\n"
            s += f"Stir on rates: {self.fmt(self.stir_on_rate)}\n"
            s += f"Stir off rates: {self.fmt(self.stir_off_rate)}\n"
            s += f"Stir on durations: {self.fmt(self.stir_on_duration)}\n"
            s += f"Stir off durations: {self.fmt(self.stir_off_duration)}\n"             
        else:
            s += f"Switch stir rate: No\n"
            s += f"Stir rate: {self.stir_on_rate}\n"
        #s += f"Temperature: {self.temp_all}\n"                
        s += "--------------\n"        
        s += f'Vial Volumes : {self.fmt(self.volume)}\n'
        if self.operation_mode == "calibration":
            s += "Mode selection: calibration\n"
            s += f"\tInitial ODs: {self.fmt(self.calibration_initial_od, 1)}\n"
            s += f"\tFinal OD: {self.calibration_end_od}\n"
        if self.operation_mode == "chemostat":
            s += "Mode selection: chemostat\n"
            s += f"\tChemostat rate: {self.fmt(self.chemo_rate, 1)}\n"
            s += f"\tChemostat start od: {self.fmt(self.chemo_start_od,1)}\n"
            s += f"\tChemostat start time: {self.fmt(self.chemo_start_time,1)}\n"
            s += f"\tGrowth rate responsive start?: {self.chemo_growth_rate_responsive_start}\n"
        if self.operation_mode == "turbidostat":
            s += "Mode selection: turbidostat\n"
            s += f"\tTurbidostat low: {self.fmt(self.turbidostat_low, 1)}\n"
            s += f"\tTurbidostat high: {self.fmt(self.turbidostat_high, 1)}\n"            
        return(s)
        
        
settings = Settings()
print(settings)
#bye()
        
# Port for the eVOLVER connection. You should not need to change this unless you have multiple applications on a single RPi.
EVOLVER_PORT = 8081

# if using a different mode, name your function as the OPERATION_MODE variable

##### END OF USER DEFINED GENERAL SETTINGS #####


# logger setup
logger = logging.getLogger(__name__)


def at_target_GR(vial, averageGR, target_GR, targetcheck,
                 time, GRpass, GRcheck, file_name):
    SAVE_PATH = os.path.dirname(os.path.realpath(__file__))
    EXP_DIR = os.path.join(SAVE_PATH, settings.exp_name)
    gr_status_path = os.path.join(EXP_DIR, 'growthrate_status', file_name)
    TOLERANCE = 0.05
    if GRpass == 1:
        with open(gr_status_path, "a+") as outfile:
            outfile.write(f"{time[-1]},1,1\n")
        return True
    else:
        if GRcheck == 1:
            if abs(averageGR - target_GR) < TOLERANCE:
                file_name =  f"vial{vial}_growthrate_status.txt"
                with open(gr_status_path, "a+") as outfile:
                    outfile.write(f"{time[-1]},1,1\n")
                return True
            else:
                with open(gr_status_path, "a+") as outfile:
                    outfile.write(f"{time[-1]},0,1\n")            
                    return False
        else:
            if abs(averageGR - targetcheck) < TOLERANCE:
                file_name =  f"vial{vial}_growthrate_status.txt"
                with open(gr_status_path, "a+") as outfile:
                    outfile.write(f"{time[-1]},0,1\n")
                return False
            else:
                file_name =  f"vial{vial}_growthrate_status.txt"
                with open(gr_status_path, "a+") as outfile:
                    outfile.write(f"{time[-1]},0,0\n")
                return False           

if "sleevecalib" in settings.exp_name:
    currentcalibs = list(sorted([f for f in os.listdir("./") if settings.exp_name in f]))
    if len(currentcalibs) > 0:
        calibnum = max([int(f.split("_")[1]) for f in currentcalibs])
        newcalib = calibnum + 1
    else:
        newcalib = 0

    EXP_NAME = f"{settings.exp_name}_{newcalib}"
    print(EXP_NAME)
    
def stir_rate_control(eVOLVER, vials, settings, elapsed_time):
    def update_stir_log(stir_path, t1,t2,s):
        text_file = open(stir_path, "a+")
        text_file.write("{0},{1},{2}\n".format(t1,
                                               t2,
                                               s))
        text_file.close()                

        
    newstirrates = [0]*16
    odlogs = [os.path.join(eVOLVER.exp_dir, settings.exp_name,
                                            "od_90_raw", f"vial{x}_od_90_raw.txt")
              for x in vials]
    for x in settings.active_vials:
        ################################################
        # Stir rate control
        file_name =  "vial{0}_stirrate.txt".format(x)
        stir_path = os.path.join(eVOLVER.exp_dir, settings.exp_name, 'stirrate', file_name)
        stirdata = np.genfromtxt(stir_path, delimiter=',')
        currstir = stirdata[len(stirdata)-1][2]
        currstirtime = stirdata[len(stirdata)-1][1]
        newstir = 0
        oddata = pd.read_csv(odlogs[x],
                               sep=",",names=["elapsed_time","od90"],
                               skiprows=[0])
              
        data = oddata[oddata.elapsed_time > currstirtime]
              

        if currstir == settings.stir_on_rate[x]:
            if data.shape[0] >= settings.stir_on_duration[x]:
                newstir = settings.stir_off_rate[x]
                update_stir_log(stir_path, elapsed_time, elapsed_time, newstir)
            else:
                newstir = settings.stir_on_rate[x]
                update_stir_log(stir_path, elapsed_time, currstirtime, settings.stir_on_rate[x])
        if currstir == settings.stir_off_rate[x]:
            if data.shape[0] >= settings.stir_off_duration[x]:
                newstir = settings.stir_on_rate[x]
                update_stir_log(stir_path, elapsed_time, elapsed_time, newstir)
            else:
                newstir = settings.stir_off_rate[x]                
                update_stir_log(stir_path, elapsed_time, currstirtime, settings.stir_off_rate[x])

        newstirrates[x] = newstir
        ################################################        
    eVOLVER.update_stir_rate(newstirrates)    
    
def growth_curve(eVOLVER, input_data, vials, elapsed_time):
    if settings.stir_switch:
        stir_rate_control(eVOLVER, vials, settings, elapsed_time)
    values_to_average = 100
    WINSIZE = 50
    SAVE_PATH = os.path.dirname(os.path.realpath(__file__))
    EXP_DIR = os.path.join(SAVE_PATH, settings.exp_name)        
    for x in vials: #main loop through each vial
        # Update chemostat configuration files for each vial
        #initialize OD and find OD path
        if settings.calib_name is not None:
            file_name =  "vial{0}_OD_autocalib.txt".format(x)
            OD_path = os.path.join(EXP_DIR, 'OD_autocalib', file_name)            
        else:
            file_name =  "vial{0}_OD.txt".format(x)
            OD_path = os.path.join(EXP_DIR, 'OD', file_name)

        ## First read in the entire data set...
        ODdata_full = np.genfromtxt(OD_path, delimiter=',')
        ## ...then average the last few values
        ODdata = ODdata_full[-values_to_average:, :]
        if settings.estimate_gr:
            ODdata_forgr = ODdata_full[-WINSIZE:, 1]
            time = ODdata_full[-WINSIZE:,0]            
            eVOLVER.aj_growth_rate(x, time, ODdata_forgr)                
    return

    
def calibration(eVOLVER, input_data, vials, elapsed_time):
    """
    Runs pumps for specified duration of time
    """

    ## First define pump action.
    ## Modify this section to increase the dilution size
    #endOD = settings.calibration_end_od


    #######
    num_pump_events = settings.calibration_num_pump_events + 1 ##### VERY IMPORTANT LOGIC
    ## This is set to +1 because the pump log file is initialized with a zero time point line.
    ## This makes the logic a little messy.
    
    
    volume_per_step = [vtr*vsleeve*( (od/endod)**(1/num_pump_events) - 1)\
                       if (od > 0) else 0 for vsleeve, endod, od, vtr in zip(settings.volume,
                                                                             settings.calibration_end_od,
                                                                             settings.calibration_initial_od,
                                                                             settings.vials_to_run)]
    flow_rate = eVOLVER.get_flow_rate() #read from calibration file

    pump_run_duration = [volume_per_step[x]/flow_rate[x]
                         if flow_rate[x] != '' else 0 for x in vials] 
    MESSAGE = ["--"]*48
    pumplogs = [os.path.join(eVOLVER.exp_dir, settings.exp_name,
                                            "pump_log", f"vial{x}_pump_log.txt")
                for x in vials]
    odlogs = [os.path.join(eVOLVER.exp_dir, settings.exp_name,
                                            "od_90_raw", f"vial{x}_od_90_raw.txt")
                for x in vials]    
    pumpdata = pd.read_csv(pumplogs[0],
                           sep=",",names=["elapsed_time","last_pump"],
                           skiprows=[0])

    for x in vials:
        oddata = pd.read_csv(odlogs[x],
                               sep=",",names=["elapsed_time","od90"],
                               skiprows=[0])
        pumpdata = pd.read_csv(pumplogs[x],
                               sep=",",names=["elapsed_time","last_pump"],
                               skiprows=[0])
        last_pump = pumpdata.iloc[-1,0]
        timein = 0
        oddata = oddata[oddata.elapsed_time > last_pump]

        if (pumpdata.shape[0] == num_pump_events) and (not settings.calibration_measured_od):
            print("Ending calibration. Please insert tubes to measure ODs next.")            
            sys.exit()
        if (oddata.shape[0] == 10) and (settings.calibration_measured_od):
            print("Calibration done.")
            sys.exit()
            
        if oddata.shape[0] == 9:                
            MESSAGE[x] = "--"
            if settings.vials_to_run[x] == 1:
                MESSAGE[x+16] = str(15)
            else:
                MESSAGE[x+16] = "--"

            
        elif oddata.shape[0] == 10:
            timein = round(pump_run_duration[x],2)
            MESSAGE[x] = str(timein)
            MESSAGE[x + 16] = "--"
            
            with open(pumplogs[x], "a+") as outfile:
                outfile.write(f"{elapsed_time},{timein}\n")        
            
    if MESSAGE != ["--"]*48:
        eVOLVER.fluid_command(MESSAGE)

def turbidostat(eVOLVER, input_data, vials, elapsed_time):
    OD_data = input_data['transformed']['od']

    ##### USER DEFINED VARIABLES #####

    turbidostat_vials = vials #vials is all 16, can set to different range (ex. [0,1,2,3]) to only trigger tstat on those vials
    stop_after_n_curves = np.inf #set to np.inf to never stop, or integer value to stop diluting after certain number of growth curves
    OD_values_to_average = 50  # Number of values to calculate the OD average

    lower_thresh = settings.turbidostat_low #[0.2] * len(vials) #to set all vials to the same value, creates 16-value list
    upper_thresh = settings.turbidostat_high # [0.6] * 16

    ##### END OF USER DEFINED VARIABLES #####

    ##### Turbidostat Settings #####
    #Tunable settings for overflow protection, pump scheduling etc. Unlikely to change between expts

    time_out = 15 #(sec) additional amount of time to run efflux pump
    pump_wait = 3 # (min) minimum amount of time to wait between pump events

    ##### End of Turbidostat Settings #####

    flow_rate = eVOLVER.get_flow_rate() #read from calibration file

    ##### Turbidostat Control Code Below #####

    # fluidic message: initialized so that no change is sent
    MESSAGE = ['--'] * 48
    newstirrates = []

    num_pump_events = 20 # settings.calibration_num_pump_events

    pumplogs = [os.path.join(eVOLVER.exp_dir, settings.exp_name,
                                            "pump_log", f"vial{x}_pump_log.txt")
                for x in vials]    
    volume_per_step = [vtr*vsleeve*( (highod/lowod)**(1/num_pump_events) - 1)\
                       if (highod > 0) else 0 for vsleeve, lowod, highod, vtr in zip(settings.volume,
                                                                      settings.turbidostat_low,
                                                                      settings.turbidostat_high,
                                                                                     settings.vials_to_run)]

    
    if settings.calib_name is not None:
        calibration = pd.read_csv(os.path.join(eVOLVER.exp_dir, f"{settings.calib_name}.csv"))

    WINSIZE = 100        
    for x in turbidostat_vials: #main loop through each vial
        # Update turbidostat configuration files for each vial
        # initialize OD and find OD path

        if settings.stir_switch:
            stirdf = pd.read_csv(os.path.join(eVOLVER.exp_dir, settings.exp_name,
                                              'stirrate', f"vial{x}_stirrate.txt"),
                                 sep=",", )
        file_name =  "vial{0}_ODset.txt".format(x)
        
        ODset_path = os.path.join(eVOLVER.exp_dir, settings.exp_name, 'ODset', file_name)
        data = np.genfromtxt(ODset_path, delimiter=',')
        ODset = data[len(data)-1][1]
        ODsettime = data[len(data)-1][0]
        num_curves=len(data)/2;
        
        if settings.calib_name is not None:
            file_name =  "vial{0}_OD_autocalib.txt".format(x)
            OD_path = os.path.join(eVOLVER.exp_dir, settings.exp_name, 'OD_autocalib', file_name)
            data =  pd.read_csv(OD_path,sep=",",)
            inflectionpoint = calibration[calibration.vial == x].estimated_od_inflection.unique()[0]
            if inflectionpoint - np.median(data.od_plinear_135.values[-50:])  < 0.175:
                ## If we are close to the 135 inflection point, switch to 90
                sensor_to_use = "od_plinear_90"
                data["OD"] = data.od_plinear_90
            else:
                sensor_to_use = "od_plinear_135"
                data["OD"] = data.od_plinear_135
        else:
            file_name =  "vial{0}_OD.txt".format(x)
            OD_path = os.path.join(eVOLVER.exp_dir, settings.exp_name, 'OD', file_name)            
            data =  pd.read_csv(OD_path,sep=",", skiprows=[0],names=["time","OD"])
        try:
            if settings.estimate_gr and data.shape[0] > 2*WINSIZE:
                if settings.stir_switch:
                    grdata = data.merge(stirdf, left_on="time", right_on="Clock time")
                    grdata = grdata[grdata.stir_rate == 0]
                else:
                    grdata = data
                if settings.calib_name:
                    ODdata_forgr = grdata.loc[-WINSIZE:, sensor_to_use]
                    time = grdata.loc[-WINSIZE:,"time"]            
                else:
                    ODdata_forgr = grdata.loc[-WINSIZE:, 1]
                    time = grdata.loc[-WINSIZE:,0]            
                eVOLVER.aj_growth_rate(x, time, ODdata_forgr)
        except:
            print("Problem with growth rate estimation")
            
        ## Custom

        file_name =  "vial{0}_od_90_raw.txt".format(x)
        OD90_path = os.path.join(eVOLVER.exp_dir, settings.exp_name, 'od_90_raw', file_name)        

        sensordata = pd.read_csv(OD90_path,
                             sep=",",names=["elapsed_time","od"],
                                skiprows=[0]
                             ) 
        average_OD = 0
        # Determine whether turbidostat dilutions are needed
        #enough_ODdata = (len(data) > 7) #logical, checks to see if enough data points (couple minutes) for sliding window
        collecting_more_curves = (num_curves <= (stop_after_n_curves + 2)) #logical, checks to see if enough growth curves have happened

        if data.size != 0:
            # Take median to avoid outlier
            od_values_from_file = data.OD.values    # Use only od135 if using ODac
            average_OD = float(np.median(od_values_from_file))

            #if recently exceeded upper threshold, note end of growth curve in ODset, allow dilutions to occur and growthrate to be measured
            if (average_OD > upper_thresh[x]) and (ODset != lower_thresh[x]):
                text_file = open(ODset_path, "a+")
                text_file.write("{0},{1}\n".format(elapsed_time,
                                                   lower_thresh[x]))
                text_file.close()
                ODset = lower_thresh[x]
                # calculate growth rate
                eVOLVER.calc_growth_rate(x, ODsettime, elapsed_time)

            #if have approx. reached lower threshold, note start of growth curve in ODset
            # if (average_OD < (lower_thresh[x] + (upper_thresh[x] - lower_thresh[x]) / 3)) and (ODset != upper_thresh[x]):
            if (np.median(data.OD.tail(10)) <= lower_thresh[x] ) and (ODset != upper_thresh[x]):                
                text_file = open(ODset_path, "a+")
                text_file.write("{0},{1}\n".format(elapsed_time, upper_thresh[x]))
                text_file.close()
                ODset = upper_thresh[x]

            #if need to dilute to lower threshold, then calculate amount of time to pump
            if average_OD > ODset and collecting_more_curves:
                t_crossing = data[data.OD > ODset].time.values[0]
                
                # Old turbidostat logic
                # time_in = - (np.log(lower_thresh[x]/average_OD)*settings.volume[x])/flow_rate[x]

                # if time_in > 20:
                #     time_in = 20

                # time_in = round(time_in, 2)

                # file_name =  "vial{0}_pump_log.txt".format(x)
                # file_path = os.path.join(eVOLVER.exp_dir, settings.exp_name,
                #                          'pump_log', file_name)
                # data = np.genfromtxt(file_path, delimiter=',')
                # last_pump = data[len(data)-1][0]

                pumpdata = pd.read_csv(pumplogs[x],
                                       sep=",",names=["elapsed_time","last_pump"],
                                       skiprows=[0])
                last_pump = pumpdata.iloc[-1,0]
                oddata = data[data.elapsed_time > t_crossing]
                if oddata.shape[0] == 9:                
                    MESSAGE[x] = "--"
                    if settings.vials_to_run[x] == 1:
                        MESSAGE[x+16] = str(15)
                    else:
                        MESSAGE[x+16] = "--"

                elif oddata.shape[0] == 10:
                    timein = round(pump_run_duration[x],2)
                    MESSAGE[x] = str(timein)
                    MESSAGE[x + 16] = "--"

                    with open(pumplogs[x], "a+") as outfile:
                        outfile.write(f"{elapsed_time},{timein}\n")                        
                # if ((elapsed_time - last_pump)*60) >= pump_wait: # if sufficient time since last pump, send command to Arduino
                #     logger.info('turbidostat dilution for vial %d' % x)
                #     # influx pump
                #     MESSAGE[x] = str(time_in)
                #     # efflux pump
                #     MESSAGE[x + 16] = str(time_in + time_out)

                #     file_name =  "vial{0}_pump_log.txt".format(x)
                #     file_path = os.path.join(eVOLVER.exp_dir, settings.exp_name, 'pump_log', file_name)

                #     text_file = open(file_path, "a+")
                #     text_file.write("{0},{1}\n".format(elapsed_time, time_in))
                #     text_file.close()
        else:
            logger.debug('not enough OD measurements for vial %d' % x)

    # send fluidic command only if we are actually turning on any of the pumps
    if settings.stir_switch:
        stir_rate_control(eVOLVER, turbidostat_vials, settings, elapsed_time)    
    # print(newstirrates)
    # newstirrates = [str(d) for d in newstirrates]
    # eVOLVER.update_stir_rate(newstirrates)    
    if MESSAGE != ['--'] * 48:
        eVOLVER.fluid_command(MESSAGE)

        # your_FB_function_here() #good spot to call feedback functions for dynamic temperature, stirring, etc for ind. vials
    # your_function_here() #good spot to call non-feedback functions for dynamic temperature, stirring, etc.

    # end of turbidostat() fxn

def chemostat(eVOLVER, input_data, vials, elapsed_time):
    OD_data = input_data['transformed']['od']
    WINSIZE = 100
    bolus = 0.5 #mL, can be changed with great caution, 0.2 is absolute minimum    
    ##### USER DEFINED VARIABLES #####

    # Note that script uses AND logic, so both start time and start OD must be surpassed
    values_to_average = 6  # Number of values to calculate the OD average
    gr_values_to_average = 6   # Number of values to calculate the OD average
    
    chemostat_vials = vials #vials is all 16, can set to different range (ex. [0,1,2,3]) to only trigger tstat on those vials
    #UNITS of 1/hr, NOT mL/hr, rate = flowrate/volume, so dilution rate ~ growth rate, set to 0 for unused vials
    target_GR = list(settings.chemo_rate)
    targetcheck = 0.2                                ## Cross this growth rate first
    flow_rate = eVOLVER.get_flow_rate() #read from calibration file
    
    period_config = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0] #initialize array
    bolus_in_s = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0] #initialize array


    ##### Chemostat Control Code Below #####
    SAVE_PATH = os.path.dirname(os.path.realpath(__file__))
    EXP_DIR = os.path.join(SAVE_PATH, settings.exp_name)
    
    for x in chemostat_vials: #main loop through each vial
        # Update chemostat configuration files for each vial

        #initialize OD and find OD path
        if settings.calib_name is not None:
            file_name =  "vial{0}_OD_autocalib.txt".format(x)
            OD_path = os.path.join(EXP_DIR, 'OD_autocalib', file_name)            
        else:
            file_name =  "vial{0}_OD.txt".format(x)
            OD_path = os.path.join(EXP_DIR, 'OD', file_name)

        ## First read in the entire data set...
        ODdata_full = np.genfromtxt(OD_path, delimiter=',')
        ## ...then average the last few values
        ODdata = ODdata_full[-values_to_average:, :]

        ## Estimate growth rate
        if settings.estimate_gr:
            ODdata_forgr = ODdata_full[-WINSIZE:, 1]
            time = ODdata_full[-WINSIZE:,0]            
            eVOLVER.aj_growth_rate(x, time, ODdata_forgr)        
        ###
        
        average_OD = 0

        dataSizeSatisfied = (ODdata.size != 0 )        
        if settings.chemo_growth_rate_responsive_start:
            #initialize GR and find GR path
            file_name =  "vial{0}_growthrate_fromOD.txt".format(x)
            GR_path = os.path.join(eVOLVER.exp_dir, settings.exp_name, 'growthrate_fromOD', file_name)
            GRdata = eVOLVER.tail_to_np(GR_path, gr_values_to_average)

            file_name =  "vial{0}_growthrate_status.txt".format(x)        
            GRstatus_path = os.path.join(eVOLVER.exp_dir, settings.exp_name, 'growthrate_status', file_name)
            GRstatus = pd.read_csv(GRstatus_path)
            GRpass = GRstatus.iloc[-1]["GRstatus"]
            GRcheck = GRstatus.iloc[-1]["GRcheck"]

            average_GR = 0

            dataSizeSatisfied = (ODdata.size != 0 ) and (GRdata.size != 0)

        #enough_ODdata = (len(data) > 7) #logical, checks to see if enough data points (couple minutes) for sliding window

        if dataSizeSatisfied: #waits for seven OD measurements (couple minutes) for sliding window
            #calculate median OD
            od_values_from_file = ODdata[:,1]
            average_OD = float(np.median(od_values_from_file))

            # set chemostat config path and pull current state from file
            file_name =  "vial{0}_chemo_config.txt".format(x)
            chemoconfig_path = os.path.join(eVOLVER.exp_dir, settings.exp_name,
                                            'chemo_config', file_name)
            chemo_config = np.genfromtxt(chemoconfig_path, delimiter=',')
            last_chemoset = chemo_config[len(chemo_config)-1][0] #should t=0 initially, changes each time a new command is written to file
            last_chemophase = chemo_config[len(chemo_config)-1][1] #should be zero initially, changes each time a new command is written to file
            last_chemorate = chemo_config[len(chemo_config)-1][2] #should be 0 initially, then period in seconds after new commands are sent

            chemophaseSatisfied = ((elapsed_time > settings.chemo_start_time[x])\
                                   and (average_OD > settings.chemo_start_od[x]))
            
            if settings.chemo_growth_rate_responsive_start: 
                gr_values_from_file = GRdata[:,1]
                average_GR = float(np.median(gr_values_from_file))
                chemophaseSatisfied = ((elapsed_time > settings.chemo_start_time[x])\
                                       and (average_OD > settings.chemo_start_od[x]))\
                                       and (at_target_GR(x, average_GR, target_GR[x], targetcheck,
                                                         time, GRpass, GRcheck, f"vial{x}_growthrate_status.txt"))


            ## once start time has passed and culture hits start OD, 
            ## if no command has been written, write new chemostat command to file
            ## This condition is also growth rate responsive. 
            ## 1. If growth rate has already been passed, continue chemostat
            ## 2. Else, compute growth rate and store status, 0 is fail, 1 is pass 
            if chemophaseSatisfied:
                #calculate time needed to pump bolus for each pump
                bolus_in_s[x] = bolus/flow_rate[x]
                
                # calculate the period (i.e. frequency of dilution events) based on user specified growth rate and bolus size
                if settings.chemo_rate[x] > 0:
                    period_config[x] = (3600*bolus)/((settings.chemo_rate[x])*settings.volume[x]) #scale dilution rate by bolus size and volume
                else: # if no dilutions needed, then just loops with no dilutions
                    period_config[x] = 0

                if  (last_chemorate != period_config[x]):
                    print('Chemostat updated in vial {0}'.format(x))
                    logger.info('chemostat initiated for vial %d, period %.2f'
                                % (x, period_config[x]))
                    # writes command to chemo_config file, for storage
                    text_file = open(chemoconfig_path, "a+")
                    text_file.write("{0},{1},{2}\n".format(elapsed_time,
                                                           (last_chemophase+1),
                                                           period_config[x])) #note that this changes chemophase
                    text_file.close()
        else:
            logger.debug('not enough OD measurements for vial %d' % x)

        # your_FB_function_here() #good spot to call feedback functions for dynamic temperature, stirring, etc for ind. vials
    # your_function_here() #good spot to call non-feedback functions for dynamic temperature, stirring, etc.

    eVOLVER.update_chemo(input_data, chemostat_vials, bolus_in_s, period_config) #compares computed chemostat config to the remote one
    # end of chemostat() fxn

# def your_function_here(): # good spot to define modular functions for dynamics or feedback

if __name__ == '__main__':
    print('Please run eVOLVER.py instead')
    logger.info('Please run eVOLVER.py instead')
