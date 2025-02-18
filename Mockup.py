import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from scipy.optimize import minimize
import json
from main import Gelenk, Stab, Mechanism, save_mechanism_to_db


st.title("Mechanismus-Simulation mit Streamlit")
st.markdown("Definiere Gelenke, verbinde sie mit Stäben und simuliere die Bewegung.")

# Gelenke definieren
gelenke = []
st.subheader("Gelenke definieren")
num_gelenke = st.slider("Anzahl der Gelenke", min_value=2, max_value=10, value=3)
for i in range(num_gelenke):
    cols = st.columns(2)
    x = cols[0].number_input(f"Gelenk {i+1} X-Koordinate", value=i * 10, step=1)
    y = cols[1].number_input(f"Gelenk {i+1} Y-Koordinate", value=0, step=1)
    gelenke.append(Gelenk(x, y))

# Stäbe definieren
st.subheader("Stäbe verbinden")
staebe = []
num_stabe = st.slider("Anzahl der Stäbe", min_value=1, max_value=num_gelenke*(num_gelenke-1)//2, value=num_gelenke-1)
for i in range(num_stabe):
    cols = st.columns(2)
    gelenk1 = cols[0].selectbox(f"Stab {i+1} - Gelenk 1", range(num_gelenke), key=f"g1_{i}")
    gelenk2 = cols[1].selectbox(f"Stab {i+1} - Gelenk 2", range(num_gelenke), key=f"g2_{i}")
    if gelenk1 != gelenk2:
        staebe.append(Stab(gelenke[gelenk1], gelenke[gelenk2]))

# Radius eingeben
st.subheader("Rotationsradius einstellen")
radius = st.slider("Rotationsradius", min_value=1, max_value=50, value=10)

# Mechanismus simulieren
if st.button("Simulation starten"):
    mechanism = Mechanism(gelenke, staebe, radius)
    mechanism.animate_mechanism()

mechanism_name = st.text_input("🔹 Mechanismus-Name", value="Mein Mechanismus")
if st.button("Speichern"):
    save_mechanism_to_db(mechanism_name, gelenke, staebe, radius)