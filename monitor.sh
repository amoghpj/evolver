expname=`grep exp_name ./experiment_parameters.yaml | cut -f 2 -d: | cut -f 2 -d" "`
screen -dmS $expname ./doplot.sh
streamlit run visualize.py



