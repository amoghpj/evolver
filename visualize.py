import streamlit as st
from PIL import Image
import yaml
import glob
import os

if __name__ == '__main__':
    exps = [f for f in os.listdir("./") if (os.path.isdir(f) and f != "__pycache__")]
    page = st.sidebar.selectbox('Experiments..',exps)
    st.title(f"{page}")
    f = open("experiment_parameters.yaml","r")
    config = yaml.safe_load(f)
    f.close()
    try:
        calib = Image.open(f"{page}.png")
        st.image(calib, )
        curves = f"{page}-curves.png"
        st.image(curves)
    except:
        for suff in ["-od_135_raw",
                    "-od_90_raw",
                    "-OD",
                    "-OD_autocalib",
                    "_projection",
                    "-growthrate_fromOD"]:
            st.header(suff[1:])
            st.image(Image.open(f"{page}{suff}.png"))
