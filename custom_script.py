#!/usr/bin/env python3
import numpy as np
import logging
import os.path
import pandas as pd
import yaml
import time
import sys


##### USER DEFINED GENERAL SETTINGS #####
f = open("custom_parameters.yaml")
config = yaml.safe_load(f)
f.close()

# If using the GUI for data visualization, do not change EXP_NAME!
# only change if you wish to have multiple data folders within a single
# directory for a set of scripts
EXP_NAME = config["experiment_settings"]["exp_name"]
CALIB_NAME = config["experiment_settings"]["calib_name"]
OPERATION_MODE = config["experiment_settings"]["operation_mode"]

if config["experiment_settings"]["stir_all"] is not None:
    stir = config["experiment_settings"]["stir_all"]
    STIR_INITIAL = [stir]*16

if config["experiment_settings"]["temp_all"] is not None:
    temp = config["experiment_settings"]["temp_all"]
    TEMP_INITIAL = [temp]*16

VIALS_TO_RUN = []
VOLUME = []
STARTOD = []
CHEMO_RATE = []
CHEMO_START_OD = []
CHEMO_START_TIME = []

for vial in config["experiment_settings"]["per_vial_settings"]:
    if vial["to_run"] is True:
        VIALS_TO_RUN.append(vial["vial"])
        VOLUME.append(vial["volume"])
        CHEMO_RATE.append(vial["chemo_rate"])
        CHEMO_START_OD.append(vial["chemo_start_od"])
        CHEMO_START_TIME.append(vial["chemo_start_time"])
    else:
        #VIALS_TO_RUN.append(0)
        VOLUME.append(vial["volume"])
        CHEMO_RATE.append(np.nan)
        CHEMO_START_OD.append(np.nan)
        CHEMO_START_TIME.append(np.nan)        
# Port for the eVOLVER connection. You should not need to change this unless you have multiple applications on a single RPi.
EVOLVER_PORT = 8081

# if using a different mode, name your function as the OPERATION_MODE variable

##### END OF USER DEFINED GENERAL SETTINGS #####


# logger setup
logger = logging.getLogger(__name__)

def bye(arg=None):
    if arg is not None:
        print(arg)
    sys.exit()

def at_target_GR(vial, averageGR, target_GR, targetcheck,
                 time, GRpass, GRcheck, file_name):
    SAVE_PATH = os.path.dirname(os.path.realpath(__file__))
    EXP_DIR = os.path.join(SAVE_PATH, EXP_NAME)
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

if "sleevecalib" in EXP_NAME:
    currentcalibs = list(sorted([f for f in os.listdir("./") if EXP_NAME in f]))
    if len(currentcalibs) > 0:
        calibnum = max([int(f.split("_")[1]) for f in currentcalibs])
        newcalib = calibnum + 1
    else:
        newcalib = 0

    EXP_NAME = f"{EXP_NAME}_{newcalib}"
    print(EXP_NAME)    

def growth_curve(eVOLVER, input_data, vials, elapsed_time):
    return

def growth_curve_stop_stir(eVOLVER, input_data, vials, elapsed_time):
    """
    Stir bar is turned on for STIR_SPACING minutes and then turned off for the same amount of time
    """
    STIR_SPACING = 2
    last_off = 0
    last_on = 0
    newstirrates = []

    for x in vials:
        file_name =  "vial{0}_stirrate.txt".format(x)
        stir_path = os.path.join(eVOLVER.exp_dir, EXP_NAME, 'stirrate', file_name)
        data = np.genfromtxt(stir_path, delimiter=',')
        oldstir = data[len(data)-1][2]
        oldstirtime = data[len(data)-1][1]
        newstir = None
        lowstir = 0
        highstir = 8
        if ((elapsed_time - oldstirtime)*60) >= STIR_SPACING:
            if oldstir == lowstir:
                newstir = highstir
            else:
                newstir = lowstir
            
            text_file = open(stir_path, "a+")
            text_file.write("{0},{1},{2}\n".format(elapsed_time,
                                                   elapsed_time,
                                                   newstir))
            text_file.close()
        else:
            newstir = oldstir
            text_file = open(stir_path, "a+")
            text_file.write("{0},{1},{2}\n".format(elapsed_time,
                                                   oldstirtime,
                                                   newstir))
        newstirrates.append(newstir)
    newstirrates = [str(d) for d in newstirrates]
    eVOLVER.update_stir_rate(newstirrates)
    return
     
def calibration(eVOLVER, input_data, vials, elapsed_time):
    """
    Runs pumps for specified duration of time
    """

    ## First define pump action.
    ## Modify this section to increase the dilution size
    STIR_SPACING = 2
    last_off = 0
    last_on = 0
    newstirrates = []
    
    
    volume_per_step = [vtr*vsleeve*(1-(endOD/od)**(1/num_pump_events))/((endOD/od)**(1/num_pump_events)) if (od > 0) else 0 for vsleeve, od, vtr in zip(VOLUME, CHEMO_START_OD, VIALS_TO_RUN)]
    
    flow_rate = eVOLVER.get_flow_rate() #read from calibration file

    pump_run_duration = [volume_per_step[x]/flow_rate[x]
                         if flow_rate[x] != '' else 0 for x in vials] 
    MESSAGE = ["--"]*48
    pumplogs = [os.path.join(eVOLVER.exp_dir, EXP_NAME,
                                            "pump_log", f"vial{x}_pump_log.txt")
                for x in vials]
    odlogs = [os.path.join(eVOLVER.exp_dir, EXP_NAME,
                                            "od_90_raw", f"vial{x}_od_90_raw.txt")
                for x in vials]    
    pumpdata = pd.read_csv(pumplogs[0],
                           sep=",",names=["elapsed_time","last_pump"],
                           skiprows=[0])

    for x in vials:
        ## Stir control
        file_name =  "vial{0}_stirrate.txt".format(x)
        stir_path = os.path.join(eVOLVER.exp_dir, EXP_NAME, 'stirrate', file_name)
        data = np.genfromtxt(stir_path, delimiter=',')
        oldstir = data[len(data)-1][2]
        oldstirtime = data[len(data)-1][1]
        newstir = None
        lowstir = 0
        highstir = 8
        
        oddata = pd.read_csv(odlogs[x],
                               sep=",",names=["elapsed_time","od90"],
                               skiprows=[0])
        pumpdata = pd.read_csv(pumplogs[x],
                               sep=",",names=["elapsed_time","last_pump"],
                               skiprows=[0])
        print(pumpdata.shape)
        last_pump = pumpdata.iloc[-1,0]
        timein = 0
        oddata = oddata[oddata.elapsed_time > last_pump]
        if oddata.shape[0] == 9:                
            MESSAGE[x] = "--"
            if vials_to_run[x] == 1:
                MESSAGE[x+16] = str(15)
            else:
                MESSAGE[x+16] = "--"

        elif oddata.shape[0] == 10:
            if pumpdata.shape[0] > num_pump_events:
                print("Ending calibration. Please measure ODs next.")
                sys.exit()            
            timein = round(pump_run_duration[x],2)
            MESSAGE[x] = str(timein)
            MESSAGE[x + 16] = "--"
            
            with open(pumplogs[x], "a+") as outfile:
                outfile.write(f"{elapsed_time},{timein}\n")        
            
    if MESSAGE != ["--"]*48:
        eVOLVER.fluid_command(MESSAGE)

def turbidostat_default(eVOLVER, input_data, vials, elapsed_time):
    OD_data = input_data['transformed']['od']

    ##### USER DEFINED VARIABLES #####

    turbidostat_vials = vials #vials is all 16, can set to different range (ex. [0,1,2,3]) to only trigger tstat on those vials
    stop_after_n_curves = np.inf #set to np.inf to never stop, or integer value to stop diluting after certain number of growth curves
    OD_values_to_average = 6  # Number of values to calculate the OD average

    lower_thresh = [0.05] * len(vials) #to set all vials to the same value, creates 16-value list
    upper_thresh = [0.3,0.3,0.3,
                    0.25,0.25,0.25,
                    10.,10.,0.2,
                    0.15,0.15,0.15,
                    0.2,0.2,0.3,
                    0.3] #to set all vials to the same value, creates 16-value list

    if eVOLVER.experiment_params is not None:
        lower_thresh = list(map(lambda x: x['lower'], eVOLVER.experiment_params['vial_configuration']))
        upper_thresh = list(map(lambda x: x['upper'], eVOLVER.experiment_params['vial_configuration']))

    #Alternatively, use 16 value list to set different thresholds, use 9999 for vials not being used
    #lower_thresh = [0.2, 0.2, 0.3, 0.3, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999]
    #upper_thresh = [0.4, 0.4, 0.4, 0.4, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999]


    ##### END OF USER DEFINED VARIABLES #####


    ##### Turbidostat Settings #####
    #Tunable settings for overflow protection, pump scheduling etc. Unlikely to change between expts

    time_out = 8 #(sec) additional amount of time to run efflux pump
    pump_wait = 3 # (min) minimum amount of time to wait between pump events

    ##### End of Turbidostat Settings #####

    flow_rate = eVOLVER.get_flow_rate() #read from calibration file

    ##### Turbidostat Control Code Below #####

    # fluidic message: initialized so that no change is sent
    MESSAGE = ['--'] * 48
    for x in turbidostat_vials: #main loop through each vial

        # Update turbidostat configuration files for each vial
        # initialize OD and find OD path

        file_name =  "vial{0}_ODset.txt".format(x)
        ODset_path = os.path.join(eVOLVER.exp_dir, EXP_NAME, 'ODset', file_name)
        data = np.genfromtxt(ODset_path, delimiter=',')
        ODset = data[len(data)-1][1]
        ODsettime = data[len(data)-1][0]
        num_curves=len(data)/2;

        file_name =  "vial{0}_OD.txt".format(x)
        OD_path = os.path.join(eVOLVER.exp_dir, EXP_NAME, 'OD', file_name)
        data = eVOLVER.tail_to_np(OD_path, OD_values_to_average)
        average_OD = 0

        # Determine whether turbidostat dilutions are needed
        #enough_ODdata = (len(data) > 7) #logical, checks to see if enough data points (couple minutes) for sliding window
        collecting_more_curves = (num_curves <= (stop_after_n_curves + 2)) #logical, checks to see if enough growth curves have happened

        if data.size != 0:
            # Take median to avoid outlier
            od_values_from_file = data[:,1]
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
            if (average_OD < (lower_thresh[x] + (upper_thresh[x] - lower_thresh[x]) / 3)) and (ODset != upper_thresh[x]):
                text_file = open(ODset_path, "a+")
                text_file.write("{0},{1}\n".format(elapsed_time, upper_thresh[x]))
                text_file.close()
                ODset = upper_thresh[x]

            #if need to dilute to lower threshold, then calculate amount of time to pump
            if average_OD > ODset and collecting_more_curves:

                time_in = - (np.log(lower_thresh[x]/average_OD)*VOLUME[vial])/flow_rate[x]

                if time_in > 20:
                    time_in = 20

                time_in = round(time_in, 2)

                file_name =  "vial{0}_pump_log.txt".format(x)
                file_path = os.path.join(eVOLVER.exp_dir, EXP_NAME,
                                         'pump_log', file_name)
                data = np.genfromtxt(file_path, delimiter=',')
                last_pump = data[len(data)-1][0]
                if ((elapsed_time - last_pump)*60) >= pump_wait: # if sufficient time since last pump, send command to Arduino
                    logger.info('turbidostat dilution for vial %d' % x)
                    # influx pump
                    MESSAGE[x] = str(time_in)
                    # efflux pump
                    MESSAGE[x + 16] = str(time_in + time_out)

                    file_name =  "vial{0}_pump_log.txt".format(x)
                    file_path = os.path.join(eVOLVER.exp_dir, EXP_NAME, 'pump_log', file_name)

                    text_file = open(file_path, "a+")
                    text_file.write("{0},{1}\n".format(elapsed_time, time_in))
                    text_file.close()
        else:
            logger.debug('not enough OD measurements for vial %d' % x)

    # send fluidic command only if we are actually turning on any of the pumps
    if MESSAGE != ['--'] * 48:
        eVOLVER.fluid_command(MESSAGE)

        # your_FB_function_here() #good spot to call feedback functions for dynamic temperature, stirring, etc for ind. vials
    # your_function_here() #good spot to call non-feedback functions for dynamic temperature, stirring, etc.

    # end of turbidostat() fxn

def chemostat_default(eVOLVER, input_data, vials, elapsed_time):
    OD_data = input_data['transformed']['od']

    ##### USER DEFINED VARIABLES #####
    # CHEMO_START_OD = [0] * 16 # ~OD600, set to 0 to start chemostate dilutions at any positive OD
    # CHEMO_START_TIME = [8] * 16 #hours, set 0 to start immediately
    # Note that script uses AND logic, so both start time and start OD must be surpassed

    OD_values_to_average = 6  # Number of values to calculate the OD average
    chemostat_vials = VIALS_TO_RUN  #vials is all 16, can set to different range (ex. [0,1,2,3]) to only trigger tstat on those vials

    #rate_config = [4.73] * 16 #to set all vials to the same value, creates 16-value list
    #stir = [8] * 16
    #UNITS of 1/hr, NOT mL/hr, rate = flowrate/volume, so dilution rate ~ growth rate, set to 0 for unused vials
    ##### END OF USER DEFINED VARIABLES #####


    ##### Chemostat Settings #####

    #Tunable settings for bolus, etc. Unlikely to change between expts
    bolus = 0.5 #mL, can be changed with great caution, 0.2 is absolute minimum

    ##### End of Chemostat Settings #####

    flow_rate = eVOLVER.get_flow_rate() #read from calibration file
    period_config = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0] #initialize array
    bolus_in_s = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0] #initialize array


    ##### Chemostat Control Code Below #####

    for x in chemostat_vials: #main loop through each vial

        # Update chemostat configuration files for each vial

        #initialize OD and find OD path
        file_name =  "vial{0}_OD.txt".format(x)
        OD_path = os.path.join(eVOLVER.exp_dir, EXP_NAME, 'OD', file_name)
        data = eVOLVER.tail_to_np(OD_path, OD_values_to_average)
        average_OD = 0
        #enough_ODdata = (len(data) > 7) #logical, checks to see if enough data points (couple minutes) for sliding window

        if data.size != 0: #waits for seven OD measurements (couple minutes) for sliding window

            #calculate median OD
            od_values_from_file = data[:,1]
            average_OD = float(np.median(od_values_from_file))

            # set chemostat config path and pull current state from file
            file_name =  "vial{0}_chemo_config.txt".format(x)
            chemoconfig_path = os.path.join(eVOLVER.exp_dir, EXP_NAME,
                                            'chemo_config', file_name)
            chemo_config = np.genfromtxt(chemoconfig_path, delimiter=',')
            last_chemoset = chemo_config[len(chemo_config)-1][0] #should t=0 initially, changes each time a new command is written to file
            last_chemophase = chemo_config[len(chemo_config)-1][1] #should be zero initially, changes each time a new command is written to file
            last_chemorate = chemo_config[len(chemo_config)-1][2] #should be 0 initially, then period in seconds after new commands are sent

            # once start time has passed and culture hits start OD, if no command has been written, write new chemostat command to file
            if ((elapsed_time > CHEMO_START_TIME[x]) and (average_OD > CHEMO_START_OD[x])):

                #calculate time needed to pump bolus for each pump
                bolus_in_s[x] = bolus/flow_rate[x]

                # calculate the period (i.e. frequency of dilution events) based on user specified growth rate and bolus size
                if CHEMO_RATE[x] > 0:
                    period_config[x] = (3600*bolus)/((CHEMO_RATE[x])*VOLUME) #scale dilution rate by bolus size and volume
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

def turbidostat(eVOLVER, input_data, vials, elapsed_time):
    OD_data = input_data['transformed']['od']

    ##### USER DEFINED VARIABLES #####

    turbidostat_vials = vials #vials is all 16, can set to different range (ex. [0,1,2,3]) to only trigger tstat on those vials
    stop_after_n_curves = np.inf #set to np.inf to never stop, or integer value to stop diluting after certain number of growth curves
    OD_values_to_average = 6  # Number of values to calculate the OD average

    lower_thresh = [0.2] * len(vials) #to set all vials to the same value, creates 16-value list
    upper_thresh = [0.6] * 16

    if eVOLVER.experiment_params is not None:
        lower_thresh = list(map(lambda x: x['lower'], eVOLVER.experiment_params['vial_configuration']))
        upper_thresh = list(map(lambda x: x['upper'], eVOLVER.experiment_params['vial_configuration']))

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
    for x in turbidostat_vials: #main loop through each vial
        # Update turbidostat configuration files for each vial
        # initialize OD and find OD path

        file_name =  "vial{0}_ODset.txt".format(x)
        ODset_path = os.path.join(eVOLVER.exp_dir, EXP_NAME, 'ODset', file_name)
        data = np.genfromtxt(ODset_path, delimiter=',')
        ODset = data[len(data)-1][1]
        ODsettime = data[len(data)-1][0]
        num_curves=len(data)/2;

        # file_name =  "vial{0}_OD.txt".format(x)
        # OD_path = os.path.join(eVOLVER.exp_dir, EXP_NAME, 'OD', file_name)
        # data = eVOLVER.tail_to_np(OD_path, OD_values_to_average)

        ## Custom
        file_name =  "vial{0}_OD_autocalib.txt".format(x)
        ODac_path = os.path.join(eVOLVER.exp_dir, EXP_NAME, 'OD_autocalib', file_name)
        data = eVOLVER.tail_to_np(ODac_path, OD_values_to_average)        
        average_OD = 0

        # Determine whether turbidostat dilutions are needed
        #enough_ODdata = (len(data) > 7) #logical, checks to see if enough data points (couple minutes) for sliding window
        collecting_more_curves = (num_curves <= (stop_after_n_curves + 2)) #logical, checks to see if enough growth curves have happened

        if data.size != 0:
            # Take median to avoid outlier
            od_values_from_file = data[:,1]    # Use only od90 if using ODac
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
            if (average_OD < (lower_thresh[x] + (upper_thresh[x] - lower_thresh[x]) / 3)) and (ODset != upper_thresh[x]):
                text_file = open(ODset_path, "a+")
                text_file.write("{0},{1}\n".format(elapsed_time, upper_thresh[x]))
                text_file.close()
                ODset = upper_thresh[x]

            #if need to dilute to lower threshold, then calculate amount of time to pump
            if average_OD > ODset and collecting_more_curves:

                time_in = - (np.log(lower_thresh[x]/average_OD)*VOLUME[x])/flow_rate[x]

                if time_in > 20:
                    time_in = 20

                time_in = round(time_in, 2)

                file_name =  "vial{0}_pump_log.txt".format(x)
                file_path = os.path.join(eVOLVER.exp_dir, EXP_NAME,
                                         'pump_log', file_name)
                data = np.genfromtxt(file_path, delimiter=',')
                last_pump = data[len(data)-1][0]
                if ((elapsed_time - last_pump)*60) >= pump_wait: # if sufficient time since last pump, send command to Arduino
                    logger.info('turbidostat dilution for vial %d' % x)
                    # influx pump
                    MESSAGE[x] = str(time_in)
                    # efflux pump
                    MESSAGE[x + 16] = str(time_in + time_out)

                    file_name =  "vial{0}_pump_log.txt".format(x)
                    file_path = os.path.join(eVOLVER.exp_dir, EXP_NAME, 'pump_log', file_name)

                    text_file = open(file_path, "a+")
                    text_file.write("{0},{1}\n".format(elapsed_time, time_in))
                    text_file.close()
        else:
            logger.debug('not enough OD measurements for vial %d' % x)

    # send fluidic command only if we are actually turning on any of the pumps
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
    # start_OD = [0] * 16 # ~OD600, set to 0 to start chemostate dilutions at any positive OD
    # start_time = [8] * 16 #hours, set 0 to start immediately
    # Note that script uses AND logic, so both start time and start OD must be surpassed

    values_to_average = 6  # Number of values to calculate the OD average
    gr_values_to_average = 6   # Number of values to calculate the OD average
    
    chemostat_vials = vials #vials is all 16, can set to different range (ex. [0,1,2,3]) to only trigger tstat on those vials
    #UNITS of 1/hr, NOT mL/hr, rate = flowrate/volume, so dilution rate ~ growth rate, set to 0 for unused vials
    target_GR = list(rate_config)
    targetcheck = 0.2                                ## Cross this growth rate first
    flow_rate = eVOLVER.get_flow_rate() #read from calibration file
    
    period_config = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0] #initialize array
    bolus_in_s = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0] #initialize array


    ##### Chemostat Control Code Below #####

    for x in chemostat_vials: #main loop through each vial

        # Update chemostat configuration files for each vial

        #initialize OD and find OD path
        file_name =  "vial{0}_OD_autocalib.txt".format(x)
        SAVE_PATH = os.path.dirname(os.path.realpath(__file__))
        EXP_DIR = os.path.join(SAVE_PATH, EXP_NAME)
        OD_path = os.path.join(EXP_DIR, 'OD_autocalib', file_name)
        ODdata_full = np.genfromtxt(OD_path, delimiter=',')
        ODdata = ODdata_full[-values_to_average:, :]

        ###
        ODdata_forgr = ODdata_full[-WINSIZE:, 1]
        time = ODdata_full[-WINSIZE:,0]
        ## Estimate growth rate
        eVOLVER.aj_growth_rate(x, time, ODdata_forgr)        
        ###
        average_OD = 0
        #initialize GR and find GR path
        file_name =  "vial{0}_growthrate_fromOD.txt".format(x)
        GR_path = os.path.join(eVOLVER.exp_dir, EXP_NAME, 'growthrate_fromOD', file_name)
        GRdata = eVOLVER.tail_to_np(GR_path, gr_values_to_average)

        file_name =  "vial{0}_growthrate_status.txt".format(x)        
        GRstatus_path = os.path.join(eVOLVER.exp_dir, EXP_NAME, 'growthrate_status', file_name)
        GRstatus = pd.read_csv(GRstatus_path)
        GRpass = GRstatus.iloc[-1]["GRstatus"]
        GRcheck = GRstatus.iloc[-1]["GRcheck"]

        average_GR = 0

        #enough_ODdata = (len(data) > 7) #logical, checks to see if enough data points (couple minutes) for sliding window

        if (ODdata.size != 0) and (GRdata.size !=0): #waits for seven OD measurements (couple minutes) for sliding window
            #calculate median OD
            od_values_from_file = ODdata[:,1]
            average_OD = float(np.median(od_values_from_file))

            gr_values_from_file = GRdata[:,1]
            average_GR = float(np.median(gr_values_from_file))

            # set chemostat config path and pull current state from file
            file_name =  "vial{0}_chemo_config.txt".format(x)
            chemoconfig_path = os.path.join(eVOLVER.exp_dir, EXP_NAME,
                                            'chemo_config', file_name)
            chemo_config = np.genfromtxt(chemoconfig_path, delimiter=',')
            last_chemoset = chemo_config[len(chemo_config)-1][0] #should t=0 initially, changes each time a new command is written to file
            last_chemophase = chemo_config[len(chemo_config)-1][1] #should be zero initially, changes each time a new command is written to file
            last_chemorate = chemo_config[len(chemo_config)-1][2] #should be 0 initially, then period in seconds after new commands are sent

            ## once start time has passed and culture hits start OD, 
            ## if no command has been written, write new chemostat command to file
            ## This condition is also growth rate responsive. 
            ## 1. If growth rate has already been passed, continue chemostat
            ## 2. Else, compute growth rate and store status, 0 is fail, 1 is pass 
            
            if ((elapsed_time > CHEMO_START_TIME[x])\
                and (average_OD > CHEMO_START_OD[x])):
                # and (at_target_GR(x, average_GR, target_GR[x], targetcheck,
                #                   time, GRpass, GRcheck, f"vial{x}_growthrate_status.txt")):
                #calculate time needed to pump bolus for each pump
                bolus_in_s[x] = bolus/flow_rate[x]
                
                # calculate the period (i.e. frequency of dilution events) based on user specified growth rate and bolus size
                if CHEMO_RATE[x] > 0:
                    period_config[x] = (3600*bolus)/((CHEMO_RATE[x])*VOLUME[x]) #scale dilution rate by bolus size and volume
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
