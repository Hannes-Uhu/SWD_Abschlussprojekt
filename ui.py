import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from database import save_mechanism_to_db, load_mechanism_from_db
from mechanism import Mechanism, Gelenk, Stab
from animation import animate_mechanism
from tinydb import TinyDB, Query
import tempfile
import json

db = TinyDB("mechanism_db.json")
mechanisms_table = db.table("mechanisms")

st.title("Interaktive Mechanismus-Simulation")

# Initialize session state for mechanism
if "mechanism" not in st.session_state:
    st.session_state["mechanism"] = None

# Tabs
selected_tab = st.tabs(["💾 Erstellung", 
                        "📂 Laden/Darstellung", 
                        "📊 CSV download", 
                        "📥⬆️ Mechanik-Export/Import", 
                        "🎞️ Animation",
                        "📜 Stückliste"])

with selected_tab[0]:
    st.header("Mechanismus erstellen")
    radius = st.slider("Rotationsradius", 5, 20, 10)
    
    num_gelenke = st.number_input("Anzahl der Gelenkpunkte", min_value=2, max_value=100, value=4)
    gelenke_data = pd.DataFrame({
        "Gelenk": [f"G{i}" for i in range(num_gelenke)],
        "X-Koordinate": [0 if i == 0 else 10 * i for i in range(num_gelenke)],
        "Y-Koordinate": [0 if i == 0 else 10 * i for i in range(num_gelenke)],
        "Fixiert": [i == 0 for i in range(num_gelenke)], 
        "Rotierend": [i == 1 for i in range(num_gelenke)],  
        "Trajektorie": [False for _ in range(num_gelenke)]
    })
    gelenke_df = st.data_editor(gelenke_data, num_rows="dynamic")
    
    num_staebe = max(1, 2 * num_gelenke - 4)
    stab_data = pd.DataFrame({
        "Stab": [f"S{i}" for i in range(num_staebe)],
        "Gelenk 1": [i if i < num_gelenke else num_gelenke - 1 for i in range(num_staebe)],
        "Gelenk 2": [i + 1 if i + 1 < num_gelenke else 0 for i in range(num_staebe)]
    })
    stab_df = st.data_editor(stab_data, num_rows="dynamic")
    
    mechanism_name = st.text_input("Mechanismusname eingeben", value="Mein Mechanismus")
    
    if st.button("Speichern"):
        gelenke = [Gelenk(row["X-Koordinate"], row["Y-Koordinate"], row["Fixiert"], row["Rotierend"], row["Trajektorie"]) for _, row in gelenke_df.iterrows()]
        staebe = [Stab(gelenke[row["Gelenk 1"]], gelenke[row["Gelenk 2"]]) for _, row in stab_df.iterrows()]
        save_mechanism_to_db(mechanism_name, gelenke, staebe, radius)
        st.success(f"✅ Mechanismus '{mechanism_name}' gespeichert!")

    # Checkboxen für Anzeigen
    if "show_length_error_tab0" not in st.session_state:
        st.session_state["show_length_error_tab0"] = False
    if "show_stab_lengths_tab0" not in st.session_state:
        st.session_state["show_stab_lengths_tab0"] = False
    if "show_stab_angles_tab0" not in st.session_state:
        st.session_state["show_stab_angles_tab0"] = False

    show_length_error = st.toggle("Prozentualen Längenfehler anzeigen", key="show_length_error_tab0")
    show_stab_lengths = st.toggle("Längen der Stäbe anzeigen", key="show_stab_lengths_tab0")
    show_stab_angles = st.toggle("Winkel zwischen den Stäben anzeigen", key="show_stab_angles_tab0")

    if show_length_error and show_stab_lengths:
        st.warning("Warnung: Wenn sowohl 'Prozentualen Längenfehler anzeigen' als auch 'Längen der Stäbe anzeigen' aktiviert sind, können sich die Zahlen in der Visualisierung überlappen.")
   
    # Mechanismus visualisieren
    if st.button("Simulation starten", key="start_simulation_tab0"):
        mechanism = Mechanism(gelenke, staebe, radius)
        anim_html = animate_mechanism(mechanism, show_length_error, show_stab_lengths, show_stab_angles)
        st.components.v1.html(anim_html, height=600)

with selected_tab[1]:
    st.header("Mechanismus laden")
    saved_mechanisms = [m["name"] for m in mechanisms_table.all()]
    selected_mechanism = st.selectbox("🔽 Wähle einen gespeicherten Mechanismus", saved_mechanisms)

    if st.button("📂 Laden"):
        result = load_mechanism_from_db(selected_mechanism)
        if result is not None:
            st.session_state["mechanism"] = result
            st.success(f"✅ Mechanismus '{selected_mechanism}' geladen!")

            gelenk_data = pd.DataFrame({
                "Gelenk": [f"G{i}" for i in range(len(result.gelenke))],
                "X-Koordinate": [g.x for g in result.gelenke],
                "Y-Koordinate": [g.y for g in result.gelenke],
                "Fixiert": [g.is_static for g in result.gelenke],
                "Rotierend": [g.is_rotating for g in result.gelenke],
                "Trajektorie": [g.is_tracked for g in result.gelenke]
            })
            st.subheader("Gelenk-Daten")
            st.dataframe(gelenk_data)

            stab_data = pd.DataFrame({
                "Stab": [f"S{i}" for i in range(len(result.staebe))],
                "Gelenk 1": [result.gelenke.index(stab.gelenk1) for stab in result.staebe],
                "Gelenk 2": [result.gelenke.index(stab.gelenk2) for stab in result.staebe]
            })
            st.subheader("Stab-Daten")
            st.dataframe(stab_data)

            st.subheader("Rotationsradius")
            st.write(f"{result.radius}")

    # Checkboxen für Anzeigen
    if "show_length_error_tab1" not in st.session_state:    
        st.session_state["show_length_error_tab1"] = False
    if "show_stab_lengths_tab1" not in st.session_state:
        st.session_state["show_stab_lengths_tab1"] = False
    if "show_stab_angles_tab1" not in st.session_state:
        st.session_state["show_stab_angles_tab1"] = False

    show_length_error = st.toggle("Prozentualen Längenfehler anzeigen", key="show_length_error_tab1")
    show_stab_lengths = st.toggle("Längen der Stäbe anzeigen", key="show_stab_lengths_tab1")
    show_stab_angles = st.toggle("Winkel zwischen den Stäben anzeigen", key="show_stab_angles_tab1")

    if show_length_error and show_stab_lengths:
        st.warning("Warnung: Wenn sowohl 'Prozentualen Längenfehler anzeigen' als auch 'Längen der Stäbe anzeigen' aktiviert sind, können sich die Zahlen in der Visualisierung überlappen.")
    
    if st.session_state["mechanism"] and st.button("▶ Mechanismus ausführen", key="run_loaded_mechanism_tab1"):
        mechanism = st.session_state["mechanism"]
        st.success(f"✅ Mechanismus '{selected_mechanism}' wird gestartet!")
        anim_html = animate_mechanism(mechanism, show_length_error, show_stab_lengths, show_stab_angles)
        st.components.v1.html(anim_html, height=600)
    
with selected_tab[2]:  
    st.header("CSV exportieren")
    saved_mechanisms = [m["name"] for m in mechanisms_table.all()]
    selected_mechanism = st.selectbox("🔽 Wähle einen gespeicherten Mechanismus", saved_mechanisms, key="saved_mechanism_tab0")

    if st.button("📂 Laden", key="laden_tab2"):
        mechanism = load_mechanism_from_db(selected_mechanism)
        if mechanism is not None:
            st.session_state["mechanism"] = mechanism
            st.success(f"✅ Mechanismus '{selected_mechanism}' geladen!")

            gelenk_data = pd.DataFrame({
                "Gelenk": [f"G{i}" for i in range(len(mechanism.gelenke))],
                "X-Koordinate": [round(g.x, 2) for g in mechanism.gelenke],
                "Y-Koordinate": [round(g.y, 2) for g in mechanism.gelenke],
                "Fixiert": [g.is_static for g in mechanism.gelenke],
                "Rotierend": [g.is_rotating for g in mechanism.gelenke],
                "Trajektorie": [g.is_tracked for g in mechanism.gelenke]
            })
            
            st.subheader("Gelenk-Daten")
            st.dataframe(gelenk_data)

            stab_data = pd.DataFrame({
                "Stab": [f"S{i}" for i in range(len(mechanism.staebe))],
                "Gelenk 1": [mechanism.gelenke.index(stab.gelenk1) for stab in mechanism.staebe],
                "Gelenk 2": [mechanism.gelenke.index(stab.gelenk2) for stab in mechanism.staebe]
            })
            st.subheader("Stab-Daten")
            st.dataframe(stab_data)

    if st.session_state["mechanism"]:
        export_option = st.toggle("CSV-Datei nur für ausgewählte Trajektorie", value=True)

        if st.button("CSV exportieren"):
            mechanism = st.session_state["mechanism"]
            theta_values = np.linspace(0, 2 * np.pi, 50)
            positions_over_time = [mechanism.update_positions(theta) for theta in theta_values]

            if export_option:
                tracked_positions = {i: [] for i, gelenk in enumerate(mechanism.gelenke) if gelenk.is_tracked}
                for theta, positions in zip(theta_values, positions_over_time):
                    for i, gelenk in enumerate(mechanism.gelenke):
                        if gelenk.is_tracked:
                            tracked_positions[i].append((theta, positions[i]))

                data = []
                for theta, positions in zip(theta_values, positions_over_time):
                    row = [round(np.degrees(theta), 2)]
                    for i, pos in enumerate(positions):
                        if i in tracked_positions:
                            row.extend([round(pos[0], 2), round(pos[1], 2)])
                    data.append(row)

                columns = ["Theta (Grad)"]
                for i in range(len(mechanism.gelenke)):
                    if i in tracked_positions:
                        columns.extend([f"X{i}", f"Y{i}"])

                df = pd.DataFrame(data, columns=columns)

            else:
                data = []
                for theta, positions in zip(theta_values, positions_over_time):
                    row = [round(np.degrees(theta), 2)]
                    for pos in positions:
                        row.extend([round(pos[0], 2), round(pos[1], 2)])
                    data.append(row)

                columns = ["Theta (Grad)"]
                for i in range(len(mechanism.gelenke)):
                    columns.extend([f"X{i}", f"Y{i}"])

                df = pd.DataFrame(data, columns=columns)

            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 CSV herunterladen",
                data=csv,
                file_name="trajektorie.csv",
                mime="text/csv"
            )

with selected_tab[3]:
    st.header("Mechanismus herunter- und hochladen")

    # Export-Funktion für JSON im gespeicherten Format
    st.subheader("Mechanismus exportieren")
    selected_mechanism = st.selectbox("🔽 Wähle einen gespeicherten Mechanismus zum Export", [m["name"] for m in mechanisms_table.all()], key="export_mechanism")

    mechanism = load_mechanism_from_db(selected_mechanism)
    if mechanism is not None:
        gelenke, staebe, radius = mechanism.gelenke, mechanism.staebe, mechanism.radius

        mechanism_data = {
            "mechanisms": {
                "1": {
                    "name": selected_mechanism,
                    "gelenke": [
                        {
                            "x": g.x,
                            "y": g.y,
                            "static": g.is_static,      
                            "rotating": g.is_rotating, 
                            "tracked": g.is_tracked     
                        } for g in gelenke
                    ],
                    "staebe": [[gelenke.index(s.gelenk1), gelenke.index(s.gelenk2)] for s in staebe],
                    "radius": radius
                }
            }
        }

        json_data = json.dumps(mechanism_data, indent=4)
        st.download_button(
            label="📥 JSON herunterladen",
            data=json_data,
            file_name=f"{selected_mechanism}.json",
            mime="application/json"
        )

        # Option zum Löschen
        if st.button("🗑️ Mechanismus aus Datenbank löschen"):
            mechanisms_table.remove(Query().name == selected_mechanism)
            st.success(f"✅ Mechanismus '{selected_mechanism}' wurde aus der Datenbank gelöscht!")

    # Import-Funktion für JSON mit neuer Formatierung
    st.subheader("Mechanismus importieren")
    uploaded_file = st.file_uploader("Lade eine JSON-Datei hoch", type=["json"])

    if uploaded_file is not None:
        try:
            json_data = json.load(uploaded_file)
            mechanism_key = list(json_data["mechanisms"].keys())[0]
            mechanism_info = json_data["mechanisms"][mechanism_key]

            gelenke = [Gelenk(joint["x"], 
                             joint["y"], 
                             joint.get("static", False),  # Änderung von is_static zu static
                             joint.get("rotating", False), # Änderung von is_rotating zu rotating 
                             joint.get("tracked", False)   # Änderung von is_tracked zu tracked
                             ) for joint in mechanism_info["gelenke"]]
            staebe = [Stab(gelenke[s[0]], gelenke[s[1]]) for s in mechanism_info["staebe"]]
            radius = mechanism_info.get("radius", 10)

            # Speichern des Mechanismus in der Session
            st.session_state["mechanism"] = Mechanism(gelenke, staebe, radius)
            st.success(f"✅ Mechanismus '{mechanism_info['name']}' wurde erfolgreich geladen!")

            # Checkboxen für Anzeigen
            if "show_length_error_tab1" not in st.session_state:
                st.session_state["show_length_error_tab3"] = False  
            if "show_stab_lengths_tab1" not in st.session_state:
                st.session_state["show_stab_lengths_tab3"] = False
            if "show_stab_angles_tab1" not in st.session_state:
                st.session_state["show_stab_angles_tab3"] = False
            
            show_length_error = st.toggle("Prozentualen Längenfehler anzeigen", key="show_length_error_tab3")
            show_stab_lengths = st.toggle("Längen der Stäbe anzeigen", key="show_stab_lengths_tab3")
            show_stab_angles = st.toggle("Winkel zwischen den Stäben anzeigen", key="show_stab_angles_tab3")

            if show_length_error and show_stab_lengths:
                st.warning("Warnung: Wenn sowohl 'Prozentualen Längenfehler anzeigen' als auch 'Längen der Stäbe anzeigen' aktiviert sind, können sich die Zahlen in der Visualisierung überlappen.")

            # Option zur Simulation des geladenen Mechanismus
            if st.session_state["mechanism"] and st.button("▶ Mechanik ausführen", key="run_loaded_mechanism_tab2"):
                mechanism = st.session_state["mechanism"]
                st.success(f"✅ Mechanismus '{selected_mechanism}' wird gestartet!")
                
                anim_html = animate_mechanism(mechanism, show_length_error, show_stab_lengths, show_stab_angles)
                st.components.v1.html(anim_html, height=600)

            # Option zum Speichern des Mechanismus nach dem Laden
            if st.button("💾 Mechanismus in Datenbank speichern"):
                if not mechanisms_table.search(Query().name == mechanism_info['name']):
                    save_mechanism_to_db(mechanism_info['name'], gelenke, staebe, radius)
                    st.success(f"✅ Mechanismus '{mechanism_info['name']}' wurde erfolgreich in der Datenbank gespeichert!")
                else:
                    st.warning(f"⚠️ Mechanismus '{mechanism_info['name']}' existiert bereits in der Datenbank!")

        except Exception as e:
            st.error(f"Fehler beim Laden der Datei: {e}")

with selected_tab[4]:
    st.header("Mechanismusanimation (gif) downloaden")
    saved_mechanisms = [m["name"] for m in mechanisms_table.all()]
    selected_mechanism = st.selectbox("🔽 Wähle einen gespeicherten Mechanismus", saved_mechanisms, key="mechanism_tab3")

    # Checkboxen für Anzeigen
    if "show_length_error_tab4" not in st.session_state:
        st.session_state["show_length_error_tab4"] = False
    if "show_stab_lengths_tab4" not in st.session_state:
        st.session_state["show_stab_lengths_tab4"] = False
    if "show_stab_angles_tab4" not in st.session_state:
        st.session_state["show_stab_angles_tab4"] = False

    show_length_error = st.toggle("Prozentualen Längenfehler anzeigen", key="show_length_error_tab4")
    show_stab_lengths = st.toggle("Längen der Stäbe anzeigen", key="show_stab_lengths_tab4")
    show_stab_angles = st.toggle("Winkel zwischen den Stäben anzeigen", key="show_stab_angles_tab4")

    if show_length_error and show_stab_lengths:
        st.warning("Warnung: Wenn sowohl 'Prozentualen Längenfehler anzeigen' als auch 'Längen der Stäbe anzeigen' aktiviert sind, können sich die Zahlen in der Visualisierung überlappen.")
   
    if st.button("📂 Laden", key="laden_tab3"):
        mechanism = load_mechanism_from_db(selected_mechanism)
        if mechanism is not None:
            st.session_state["mechanism"] = mechanism
            st.success(f"✅ Mechanismus '{selected_mechanism}' wurde geladen und wird nun für den Download vorbereitet!")
            
            ani = animate_mechanism(mechanism, show_length_error, show_stab_lengths, show_stab_angles)
            # Speichern vom GIF
            with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as temp_gif:
                ani.save(temp_gif.name, writer=PillowWriter(fps=10))
                with open(temp_gif.name, "rb") as f:
                    gif_bytes = f.read()

            st.success("✅ Animation zum Download bereit.")
            st.download_button(
                label="📥 Download als GIF",
                data=gif_bytes,
                file_name=f"{selected_mechanism}.gif",
                mime="image/gif"
            )

with selected_tab[5]:
    st.header("Stückliste erstellen")

    if st.session_state["mechanism"]:
        mechanism = st.session_state["mechanism"]

        # Gelenke auswählen
        st.subheader("Gelenke auswählen")
        selected_gelenke = st.multiselect(
            "Wähle Gelenke aus",
            [f"G{i}" for i in range(len(mechanism.gelenke))],
            default=[f"G{i}" for i in range(len(mechanism.gelenke))]
        )

        # Stäbe auswählen
        st.subheader("Stäbe auswählen")
        selected_staebe = st.multiselect(
            "Wähle Stäbe aus",
            [f"S{i}" for i in range(len(mechanism.staebe))],
            default=[f"S{i}" for i in range(len(mechanism.staebe))]
        )

        # Antriebe auswählen
        st.subheader("Antriebe auswählen")
        selected_antriebe = st.multiselect(
            "Wähle Antriebe aus",
            [f"A{i}" for i in range(len(mechanism.gelenke)) if mechanism.gelenke[i].is_rotating],
            default=[f"A{i}" for i in range(len(mechanism.gelenke)) if mechanism.gelenke[i].is_rotating]
        )

        # Stückliste erstellen
        st.subheader("Stückliste")
        stueckliste_data = {
            "Typ": ["Gelenk"] * len(selected_gelenke) + ["Stab"] * len(selected_staebe) + ["Antrieb"] * len(selected_antriebe),
            "Name": selected_gelenke + selected_staebe + selected_antriebe
        }
        stueckliste_df = pd.DataFrame(stueckliste_data)
        st.dataframe(stueckliste_df)

        # Stückliste als CSV herunterladen
        csv = stueckliste_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Stückliste als CSV herunterladen",
            data=csv,
            file_name='stueckliste.csv',
            mime='text/csv'
        )
    else:
        st.warning("Bitte lade oder erstelle zuerst einen Mechanismus.")