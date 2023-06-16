# expname=`grep exp_name ./experiment_parameters.yaml | cut -f 2 -d: | cut -f 2 -d" "`
screen -dmS $(date +"%H%M_%m%y") ./doplot.sh
streamlit run visualize.py



