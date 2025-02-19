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

st.title("🔧 Planarer Mechanismus-Simulator")
st.markdown("Definiere Gelenke, verbinde sie mit Stäben und simuliere die Bewegung.")

# Tabs für die Benutzeroberfläche
tab1, tab2 = st.tabs(["🆕 Mechanismus erstellen", "📂 Gespeicherte Mechanismen laden"])

### **Tab 1: Mechanismus erstellen & speichern**
with tab1:
    st.subheader("🔹 Setup")
    st.info("Bitte gebe die Details des Mechanismus ein. Falls du die Seite aktualisierst, wird der Standardmechanismus geladen.")
    mechanism_name = st.text_input("📝 Modellname", value="Mein Mechanismus")
    
    st.subheader("📍 Gelenke definieren")
    gelenke = []
    num_gelenke = st.slider("Anzahl der Gelenke", min_value=2, max_value=10, value=3)
    num_staebe_required = (3 * (num_gelenke - 1) - 1) // 2  # Berechnung nach Kutzbach-Gleichung
    
    node_table = []
    for i in range(num_gelenke):
        cols = st.columns(3)
        x = cols[0].number_input(f"X-Koordinate für Gelenk {i}", value=i * 10, step=1)
        y = cols[1].number_input(f"Y-Koordinate für Gelenk {i}", value=0, step=1)
        is_static = cols[2].checkbox(f"Fixiert", key=f"static_{i}")
        gelenke.append(Gelenk(x, y))
        gelenke[-1].is_static = is_static  # Speichere den Static-Status im Gelenk-Objekt
        node_table.append({"Node": f"p{i}", "X": x, "Y": y, "Static": is_static})
    
    st.table(node_table)
    
    st.subheader(f"🔗 Stäbe verbinden (Benötigt: {num_staebe_required})")
    edge_table = []
    staebe = []
    for i in range(num_staebe_required):
        cols = st.columns(2)
        gelenk1 = cols[0].selectbox(f"Stab {i+1} - Gelenk 1", range(num_gelenke), key=f"g1_{i}")
        gelenk2 = cols[1].selectbox(f"Stab {i+1} - Gelenk 2", range(num_gelenke), key=f"g2_{i}")
        if gelenk1 != gelenk2:
            staebe.append(Stab(gelenke[gelenk1], gelenke[gelenk2]))
            edge_table.append({"Edge": f"p{gelenk1}-p{gelenk2}"})
    st.table(edge_table)
    
    # Überprüfung der Anzahl der Stäbe
    if len(staebe) != num_staebe_required:
        st.error(f"❌ Fehler: Es müssen genau {num_staebe_required} Stäbe verwendet werden, um F = 1 zu gewährleisten!")
    
    st.subheader("🔄 Dynamische Verschiebung")
    rotating_gelenk = st.selectbox("Wähle ein Gelenk für die Kreisbewegung", range(num_gelenke))
    center_x = st.number_input("X-Zentrum", value=0)
    center_y = st.number_input("Y-Zentrum", value=0)
    radius = st.slider("Rotationsradius", min_value=1, max_value=50, value=10)
    
    if st.button("🚀 Simulation starten"):
        if len(staebe) == num_staebe_required:
            mechanism = Mechanism(gelenke, staebe, radius)
            fig = mechanism.plot_mechanism()
            st.pyplot(fig)
        else:
            st.error("❌ Simulation nicht möglich: Falsche Anzahl an Stäben!")
    
    if st.button("💾 Speichern"):
        if len(staebe) == num_staebe_required:
            save_mechanism_to_db(mechanism_name, gelenke, staebe, radius)
            st.success(f"✅ Mechanismus '{mechanism_name}' gespeichert!")
        else:
            st.error("❌ Speicherung nicht möglich: Falsche Anzahl an Stäben!")

### **Tab 2: Gespeicherte Mechanismen laden & anzeigen**
with tab2:
    st.subheader("📂 Gespeicherte Mechanismen")
    saved_mechanisms = mechanisms_table.all()
    
    if saved_mechanisms:
        mechanism_names = [m["name"] for m in saved_mechanisms]
        selected_mechanism = st.selectbox("🔽 Wähle einen Mechanismus", mechanism_names)
        
        if st.button("📂 Laden & Simulieren"):
            gelenke, staebe, radius = load_mechanism_from_db(selected_mechanism)
            if gelenke and staebe:
                st.success(f"✅ '{selected_mechanism}' geladen!")
                node_table = [{"Node": f"p{i}", "X": g.x, "Y": g.y, "Static": g.is_static} for i, g in enumerate(gelenke)]
                st.table(node_table)
                mechanism = Mechanism(gelenke, staebe, radius)
                fig = mechanism.plot_mechanism()
                st.pyplot(fig)
            else:
                st.error("❌ Fehler beim Laden des Mechanismus!")
    else:
        st.warning("⚠️ Noch keine gespeicherten Mechanismen gefunden.")
