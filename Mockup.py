import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from scipy.optimize import minimize
from tinydb import TinyDB, Query
from main import Gelenk, Stab, Mechanism, save_mechanism_to_db, load_mechanism_from_db

# Datenbank einbinden
db = TinyDB("mechanism_db.json")
mechanisms_table = db.table("mechanisms")

st.title("Mechanismus-Simulation mit Streamlit")
st.markdown("Definiere Gelenke, verbinde sie mit Stäben und simuliere die Bewegung.")

# Tabs für die Benutzeroberfläche
tab1, tab2 = st.tabs(["🆕 Mechanismus erstellen", "📂 Gespeicherte Mechanismen laden"])

### **Tab 1: Mechanismus erstellen & speichern**
with tab1:
    st.subheader("Gelenke definieren")
    gelenke = []
    num_gelenke = st.slider("Anzahl der Gelenke", min_value=2, max_value=10, value=3)
    for i in range(num_gelenke):
        cols = st.columns(2)
        x = cols[0].number_input(f"Gelenk {i+1} X-Koordinate", value=i * 10, step=1)
        y = cols[1].number_input(f"Gelenk {i+1} Y-Koordinate", value=0, step=1)
        gelenke.append(Gelenk(x, y))

    # Anzahl der notwendigen Stäbe berechnen
    num_stabe_required = (3 * (num_gelenke - 1) - 1) // 2
    st.subheader("Stäbe verbinden")
    st.markdown(f"**Automatisch berechnete Anzahl an Stäben für F = 1: {num_stabe_required}**")
    
    staebe = []
    for i in range(num_stabe_required):
        cols = st.columns(2)
        gelenk1 = cols[0].selectbox(f"Stab {i+1} - Gelenk 1", range(num_gelenke), key=f"g1_{i}")
        gelenk2 = cols[1].selectbox(f"Stab {i+1} - Gelenk 2", range(num_gelenke), key=f"g2_{i}")
        if gelenk1 != gelenk2:
            staebe.append(Stab(gelenke[gelenk1], gelenke[gelenk2]))

    # Prüfen, ob alle Stäbe verwendet wurden
    if len(staebe) != num_stabe_required:
        st.error(f"Fehler: Es müssen genau {num_stabe_required} Stäbe verwendet werden, um F = 1 zu gewährleisten!")

    # Radius eingeben
    st.subheader("Rotationsradius einstellen")
    radius = st.slider("Rotationsradius", min_value=1, max_value=50, value=10)

    # Mechanismus simulieren
    if st.button("Simulation starten"):
        if len(staebe) == num_stabe_required:
            mechanism = Mechanism(gelenke, staebe, radius)
            mechanism.animate_mechanism()
        else:
            st.error("Simulation nicht möglich: Anzahl der Stäbe ist falsch.")

    # Mechanismus speichern
    mechanism_name = st.text_input("🔵 Mechanismus-Name", value="Mein Mechanismus")
    if st.button("Speichern"):
        if len(staebe) == num_stabe_required:
            save_mechanism_to_db(mechanism_name, gelenke, staebe, radius)
            st.success(f"Mechanismus '{mechanism_name}' gespeichert!")
        else:
            st.error("Speicherung nicht möglich: Anzahl der Stäbe ist falsch.")

### **Tab 2: Gespeicherte Mechanismen laden & anzeigen**
with tab2:
    st.subheader("Gespeicherte Mechanismen")

    # Gespeicherte Mechanismen aus der TinyDB abrufen
    saved_mechanisms = mechanisms_table.all()

    if saved_mechanisms:
        # Tabelle mit Mechanismen anzeigen
        mechanism_names = [m["name"] for m in saved_mechanisms]
        st.write("### Liste gespeicherter Mechanismen")
        st.table({"Name": mechanism_names, "Anzahl Gelenke": [len(m["gelenke"]) for m in saved_mechanisms]})

        # Auswahl eines Mechanismus zum Laden
        selected_mechanism = st.selectbox("🔽 Wähle einen Mechanismus zum Laden", mechanism_names)

        if st.button("Mechanismus laden und simulieren"):
            gelenke, staebe, radius = load_mechanism_from_db(selected_mechanism)
            if gelenke and staebe:
                st.success(f"Mechanismus '{selected_mechanism}' erfolgreich geladen!")
                mechanism = Mechanism(gelenke, staebe, radius)
                fig = mechanism.plot_mechanism()
                st.pyplot(fig)
            else:
                st.error("Fehler beim Laden des Mechanismus!")

    else:
        st.warning("Es sind noch keine Mechanismen gespeichert. Bitte erst einen Mechanismus im ersten Tab erstellen.")

