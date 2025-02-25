import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.animation import FuncAnimation, HTMLWriter, PillowWriter, FFMpegWriter
from tinydb import TinyDB, Query
from main import Mechanism, Gelenk, Stab, save_mechanism_to_db, load_mechanism_from_db
from io import BytesIO
import base64
import json
import tempfile
from streamlit_drawable_canvas import st_canvas

db = TinyDB("mechanism_db.json")
mechanisms_table = db.table("mechanisms")

st.title("Interaktive Mechanismus-Simulation")

st.session_state.setdefault("mechanism", None)

# Tabs
selected_tab = st.tabs(["💾 Erstellung", 
                        "📂 Laden/Darstellung", 
                        "📊 CSV download",
                        "📥⬆️ Mechanik-Export/Import", 
                        "🎞️ Animation"])

############################################################################################################################################################################

with selected_tab[0]:
    st.header("Mechanismus erstellen")

    radius = st.slider("Rotationsradius", 5, 20, 10)

    st.subheader("Gelenkpunkte")
    st.info("Hinweis: Das erste Gelenk ist immer das feste Gelenk, das zweite Gelenk immer das Drehgelenk, damit der Mechanismus in jeder Konfiguration einwandfrei funktioniert.")

    def create_gelenk_df(num_gelenke):
        data = {
            "Gelenk": [f"G{i}" for i in range(num_gelenke)],
            "X-Koordinate": [0 if i == 0 else 10 * i for i in range(num_gelenke)],
            "Y-Koordinate": [0 if i == 0 else 10 * i for i in range(num_gelenke)],
            "Fixiert": [i == 0 for i in range(num_gelenke)], 
            "Rotierend": [i == 1 for i in range(num_gelenke)],  
            "Trajektorie": [False for _ in range(num_gelenke)]
        }
        return pd.DataFrame(data)

    num_gelenke = st.number_input("Anzahl der Gelenkpunkte", min_value=2, max_value=100, value=4)
    gelenk_df = st.data_editor(create_gelenk_df(num_gelenke), num_rows="dynamic")

    if gelenk_df["Rotierend"].sum() > 1:
        st.error("Fehler: Es darf nur ein rotierendes Gelenk ausgewählt werden!")

    if gelenk_df["Fixiert"].sum() > 1:
        st.error("Fehler: Es darf nur ein fixiertes Gelenk ausgewählt werden!")

    # Extrahiere die Gelenkpunkte
    gelenke = []
    rotierendes_gelenk = None
    trajektorie_gelenke = []
    for _, row in gelenk_df.iterrows():
        gelenk = Gelenk(row["X-Koordinate"], row["Y-Koordinate"], row["Fixiert"], row["Rotierend"], row["Trajektorie"])
        gelenke.append(gelenk)
        if row["Rotierend"]:
            rotierendes_gelenk = gelenk
        if row["Trajektorie"]:
            trajektorie_gelenke.append(gelenk)

    st.subheader("Stäbe")

    num_staebe = max(1, 2 * num_gelenke - 4)

    def create_stab_df(num_staebe, num_gelenke):
        return pd.DataFrame({
            "Stab": [f"S{i}" for i in range(num_staebe)],
            "Gelenk 1": [i if i < num_gelenke else num_gelenke - 1 for i in range(num_staebe)],
            "Gelenk 2": [i + 1 if i + 1 < num_gelenke else 0 for i in range(num_staebe)]
        })

    stab_df = st.data_editor(create_stab_df(num_staebe, num_gelenke), num_rows="dynamic")
    staebe = [Stab(gelenke[row["Gelenk 1"]], gelenke[row["Gelenk 2"]]) for _, row in stab_df.iterrows()]

    # Mechanismus speichern
    mechanism_name = st.text_input("Mechanismusname eingeben", value="Mein Mechanismus")

    if st.button("💾 Speichern"):
        existing_names = [m["name"] for m in mechanisms_table.all()]
        if mechanism_name in existing_names:
            st.error("Fehler: Ein Mechanismus mit diesem Namen existiert bereits!")
        else:
            save_mechanism_to_db(mechanism_name, gelenke, staebe, radius)
            st.success(f"✅ Mechanismus '{mechanism_name}' gespeichert!")

    # Checkboxen für Anzeigen
    show_length_error = st.toggle("Prozentualen Längenfehler anzeigen")
    show_stab_lengths = st.toggle("Längen der Stäbe anzeigen")
    show_stab_angles = st.toggle("Winkel zwischen den Stäben anzeigen")

    if show_length_error and show_stab_lengths:
        st.warning("Warnung: Wenn sowohl 'Prozentualen Längenfehler anzeigen' als auch 'Längen der Stäbe anzeigen' aktiviert sind, können sich die Zahlen in der Visualisierung überlappen.")
   
   
    # Mechanismus visualisieren
    if rotierendes_gelenk is not None:
        if st.button("Simulation starten", key="start_simulation_tab0"):
            mechanism = Mechanism(gelenke, staebe, radius)

            trajectory_data = {i: [] for i in range(len(gelenke))}

            all_x = [g.x for g in mechanism.gelenk]
            all_y = [g.y for g in mechanism.gelenk]

            padding = 10
            x_min, x_max = min(all_x) - padding, max(all_x) + padding
            y_min, y_max = min(all_y) - padding, max(all_y) + padding

            x_range = x_max - x_min
            y_range = y_max - y_min

            max_range = max(x_range, y_range)

            x_center = (x_max + x_min) / 2
            y_center = (y_max + y_min) / 2

            x_min, x_max = x_center - max_range / 2, x_center + max_range / 2
            y_min, y_max = y_center - max_range / 2, y_center + max_range / 2

            fig, ax = plt.subplots()
            ax.set_xlim(x_min, x_max)
            ax.set_ylim(y_min, y_max)
            ax.set_aspect('equal')
            ax.set_title("Mechanismus Animation")
            ax.set_xlabel("X-Koordinate")
            ax.set_ylabel("Y-Koordinate")
            ax.grid(True)

            circle = plt.Circle((rotierendes_gelenk.x, rotierendes_gelenk.y), radius, color='b', fill=False, linestyle='dashed')
            ax.add_patch(circle)

            gelenk_points, = ax.plot([], [], 'ro')
            stab_plot, = ax.plot([], [], 'k-', lw=2)
            traj_plots = {i: ax.plot([], [], 'g-', lw=2)[0] for i, gelenk in enumerate(gelenke) if gelenk.is_tracked}

            text_annotations = []

            def calculate_length_error(mechanism, optimized_positions):
                current_lengths = mechanism.verbindungs_matrix @ optimized_positions.flatten()
                current_lengths = np.linalg.norm(current_lengths.reshape(-1, 2), axis=1)
                length_errors = (current_lengths - mechanism.start_laengen) / mechanism.start_laengen * 100
                return length_errors

            def calculate_stab_lengths(positions, staebe):
                lengths = []
                for stab in staebe:
                    p1, p2 = positions[gelenke.index(stab.gelenk1)], positions[gelenke.index(stab.gelenk2)]
                    length = np.linalg.norm(np.array(p2) - np.array(p1))
                    lengths.append(length)
                return lengths

            def calculate_stab_angles(positions, staebe):
                angles = []
                for gelenk in gelenke:
                    connected_stabs = [stab for stab in staebe if gelenk in [stab.gelenk1, stab.gelenk2]]
                    if len(connected_stabs) < 2:
                        continue

                    for i in range(len(connected_stabs) - 1):
                        stab1, stab2 = connected_stabs[i], connected_stabs[i + 1]
                        p1 = np.array(positions[gelenke.index(stab1.gelenk1 if stab1.gelenk1 != gelenk else stab1.gelenk2)])
                        p2 = np.array(positions[gelenke.index(gelenk)])
                        p3 = np.array(positions[gelenke.index(stab2.gelenk1 if stab2.gelenk1 != gelenk else stab2.gelenk2)])

                        v1 = p1 - p2
                        v2 = p3 - p2

                        if np.linalg.norm(v1) == 0 or np.linalg.norm(v2) == 0:
                            angle = 0
                        else:
                            cos_theta = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                            angle = np.arccos(np.clip(cos_theta, -1.0, 1.0)) * (180 / np.pi)

                        angles.append((gelenk, angle, p2[0], p2[1]))  
                return angles

            def update(frame):
                theta = np.linspace(0, 2 * np.pi, 50)[frame]
                optimized_positions = mechanism.update_positions(theta)
                gelenk_points.set_data(optimized_positions[:, 0], optimized_positions[:, 1])

                stab_x, stab_y = [], []
                length_errors = calculate_length_error(mechanism, optimized_positions)

                for text in text_annotations:
                    text.remove()
                text_annotations.clear()

                for i, stab in enumerate(mechanism.staebe):
                    p1, p2 = optimized_positions[mechanism.gelenk.index(stab.gelenk1)], optimized_positions[mechanism.gelenk.index(stab.gelenk2)]
                    stab_x.extend([p1[0], p2[0], None])
                    stab_y.extend([p1[1], p2[1], None])

                    if show_length_error:
                        mid_x, mid_y = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
                        text = ax.text(mid_x, mid_y, f"{length_errors[i]:.2f}%", color='red', fontsize=8, ha='center')
                        text_annotations.append(text)

                    if show_stab_lengths:
                        mid_x, mid_y = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
                        text = ax.text(mid_x, mid_y, f"{calculate_stab_lengths(optimized_positions, mechanism.staebe)[i]:.2f}", 
                                    color='blue', fontsize=8, ha='center')
                        text_annotations.append(text)

                stab_plot.set_data(stab_x, stab_y)

                for i, gelenk in enumerate(gelenke):
                    if gelenk.is_tracked:
                        traj_x, traj_y = traj_plots[i].get_data()
                        traj_plots[i].set_data(np.append(traj_x, optimized_positions[i, 0]), np.append(traj_y, optimized_positions[i, 1]))

                if show_stab_angles:
                    angles = calculate_stab_angles(optimized_positions, mechanism.staebe)
                    for idx, (gelenk, angle, mid_x, mid_y) in enumerate(angles):
                        # Verschiebe die Winkelanzeige leicht nach links und rechts, um Überlappung zu vermeiden
                        offset_x = 1.7 * np.cos(np.deg2rad(angle))
                        offset_y = 1.7 * np.sin(np.deg2rad(angle))
                        if idx % 2 == 0:
                            text = ax.text(mid_x + offset_x, mid_y + offset_y, f"{angle:.1f}°", color='green', fontsize=8, ha='center')
                        else:
                            text = ax.text(mid_x - offset_x, mid_y - offset_y, f"{angle:.1f}°", color='green', fontsize=8, ha='center')
                        text_annotations.append(text)


                return gelenk_points, stab_plot, *traj_plots.values()

            ani = FuncAnimation(fig, update, frames=50, interval=100)
            html_writer = HTMLWriter()
            anim_html = ani.to_jshtml()
            st.components.v1.html(anim_html, height=600)

    else:
        st.error("Fehler: Es muss ein rotierendes Gelenk definiert werden, um die Simulation zu starten.")


############################################################################################################################################################################


with selected_tab[1]:
    st.header("Mechanismus laden")

    # Checkboxen für Anzeigen
    if "show_length_error_tab1" not in st.session_state:
        st.session_state["show_length_error_tab1"] = False
    if "show_stab_lengths_tab1" not in st.session_state:
        st.session_state["show_stab_lengths_tab1"] = False
    if "show_stab_angles_tab1" not in st.session_state:
        st.session_state["show_stab_angles_tab1"] = False

    
    saved_mechanisms = [m["name"] for m in mechanisms_table.all()]
    selected_mechanism = st.selectbox("🔽 Wähle einen gespeicherten Mechanismus", saved_mechanisms)

    show_length_error = st.toggle("Prozentualen Längenfehler anzeigen", key="show_length_error_tab1")
    show_stab_lengths = st.toggle("Längen der Stäbe anzeigen", key="show_stab_lengths_tab1")
    show_stab_angles = st.toggle("Winkel zwischen den Stäben anzeigen", key="show_stab_angles_tab1")

    if show_length_error and show_stab_lengths:
        st.warning("Warnung: Wenn sowohl 'Prozentualen Längenfehler anzeigen' als auch 'Längen der Stäbe anzeigen' aktiviert sind, können sich die Zahlen in der Visualisierung überlappen.")
   
    if st.button("📂 Laden"):
        result = load_mechanism_from_db(selected_mechanism)
        if result[0] is not None:
            gelenke, staebe, radius, fixed_gelenk_index, rotating_gelenk_index = result
            st.session_state["mechanism"] = Mechanism(gelenke, staebe, radius)
            st.success(f"✅ Mechanismus '{selected_mechanism}' geladen!")

            gelenk_data = pd.DataFrame({
                "Gelenk": [f"G{i}" for i in range(len(gelenke))],
                "X-Koordinate": [g.x for g in gelenke],
                "Y-Koordinate": [g.y for g in gelenke],
                "Fixiert": [g.is_static for g in gelenke],
                "Rotierend": [g.is_rotating for g in gelenke],
                "Trajektorie": [g.is_tracked for g in gelenke]
            })
            st.subheader("Gelenk-Daten")
            st.dataframe(gelenk_data)

            stab_data = pd.DataFrame({
                "Stab": [f"S{i}" for i in range(len(staebe))],
                "Gelenk 1": [gelenke.index(stab.gelenk1) for stab in staebe],
                "Gelenk 2": [gelenke.index(stab.gelenk2) for stab in staebe]
            })
            st.subheader("Stab-Daten")
            st.dataframe(stab_data)

            st.subheader("Rotationsradius")
            st.write(f"{radius}")

    if st.session_state["mechanism"] and st.button("▶ Mechanismus ausführen", key="run_loaded_mechanism_tab1"):
        mechanism = st.session_state["mechanism"]
        st.success(f"✅ Mechanismus '{selected_mechanism}' wird gestartet!")

        all_x = [g.x for g in mechanism.gelenk]
        all_y = [g.y for g in mechanism.gelenk]

        padding = 10
        x_min, x_max = min(all_x) - padding, max(all_x) + padding
        y_min, y_max = min(all_y) - padding, max(all_y) + padding

        x_range = x_max - x_min
        y_range = y_max - y_min

        max_range = max(x_range, y_range)

        x_center = (x_max + x_min) / 2
        y_center = (y_max + y_min) / 2

        x_min, x_max = x_center - max_range / 2, x_center + max_range / 2
        y_min, y_max = y_center - max_range / 2, y_center + max_range / 2

        fig, ax = plt.subplots()
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, y_max)
        ax.set_aspect('equal')
        ax.set_title("Mechanismus Animation")
        ax.set_xlabel("X-Koordinate")
        ax.set_ylabel("Y-Koordinate")
        ax.grid(True)

        circle = plt.Circle((mechanism.gelenk[mechanism.rotating_gelenk_index].x, mechanism.gelenk[mechanism.rotating_gelenk_index].y), radius, color='b', fill=False, linestyle='dashed')
        ax.add_patch(circle)

        gelenk_points, = ax.plot([], [], 'ro')
        stab_plot, = ax.plot([], [], 'k-', lw=2)
        traj_plots = {i: ax.plot([], [], 'g-', lw=2)[0] for i, gelenk in enumerate(mechanism.gelenk) if gelenk.is_tracked}

        text_annotations = []

        def calculate_length_error(mechanism, optimized_positions):
            current_lengths = mechanism.verbindungs_matrix @ optimized_positions.flatten()
            current_lengths = np.linalg.norm(current_lengths.reshape(-1, 2), axis=1)
            length_errors = (current_lengths - mechanism.start_laengen) / mechanism.start_laengen * 100
            return length_errors
        
        def calculate_stab_lengths(positions, staebe):
            lengths = []
            for stab in staebe:
                p1, p2 = positions[mechanism.gelenk.index(stab.gelenk1)], positions[mechanism.gelenk.index(stab.gelenk2)]
                length = np.linalg.norm(np.array(p2) - np.array(p1))
                lengths.append(length)
            return lengths

        def calculate_stab_angles(positions, staebe):
            angles = []
            for gelenk in mechanism.gelenk:
                connected_stabs = [stab for stab in staebe if gelenk in [stab.gelenk1, stab.gelenk2]]
                if len(connected_stabs) < 2:
                    continue

                for i in range(len(connected_stabs) - 1):
                    stab1, stab2 = connected_stabs[i], connected_stabs[i + 1]
                    p1 = np.array(positions[mechanism.gelenk.index(stab1.gelenk1 if stab1.gelenk1 != gelenk else stab1.gelenk2)])
                    p2 = np.array(positions[mechanism.gelenk.index(gelenk)])
                    p3 = np.array(positions[mechanism.gelenk.index(stab2.gelenk1 if stab2.gelenk1 != gelenk else stab2.gelenk2)])

                    v1 = p1 - p2
                    v2 = p3 - p2

                    if np.linalg.norm(v1) == 0 or np.linalg.norm(v2) == 0:
                        angle = 0
                    else:
                        cos_theta = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                        angle = np.arccos(np.clip(cos_theta, -1.0, 1.0)) * (180 / np.pi)

                    angles.append((gelenk, angle, p2[0], p2[1]))  
            return angles

        def update(frame):
            theta = np.linspace(0, 2 * np.pi, 50)[frame]
            optimized_positions = mechanism.update_positions(theta)
            gelenk_points.set_data(optimized_positions[:, 0], optimized_positions[:, 1])

            stab_x, stab_y = [], []
            length_errors = calculate_length_error(mechanism, optimized_positions)

            for text in text_annotations:
                text.remove()
            text_annotations.clear()

            for i, stab in enumerate(mechanism.staebe):
                p1, p2 = optimized_positions[mechanism.gelenk.index(stab.gelenk1)], optimized_positions[mechanism.gelenk.index(stab.gelenk2)]
                stab_x.extend([p1[0], p2[0], None])
                stab_y.extend([p1[1], p2[1], None])

                if st.session_state["show_length_error_tab1"]:
                    mid_x, mid_y = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
                    text = ax.text(mid_x, mid_y, f"{length_errors[i]:.2f}%", color='red', fontsize=8, ha='center')
                    text_annotations.append(text)

                if st.session_state["show_stab_lengths_tab1"]:
                    mid_x, mid_y = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
                    text = ax.text(mid_x, mid_y, f"{calculate_stab_lengths(optimized_positions, mechanism.staebe)[i]:.2f}", 
                                color='blue', fontsize=8, ha='center')
                    text_annotations.append(text)

            stab_plot.set_data(stab_x, stab_y)

            for i, gelenk in enumerate(mechanism.gelenk):
                if gelenk.is_tracked:
                    traj_x, traj_y = traj_plots[i].get_data()
                    traj_plots[i].set_data(np.append(traj_x, optimized_positions[i, 0]), np.append(traj_y, optimized_positions[i, 1]))

            if st.session_state["show_stab_angles_tab1"]:
                angles = calculate_stab_angles(optimized_positions, mechanism.staebe)
                for idx, (gelenk, angle, mid_x, mid_y) in enumerate(angles):
                    # Verschiebe die Winkelanzeige leicht nach links und rechts, um Überlappung zu vermeiden
                    offset_x = 1.7 * np.cos(np.deg2rad(angle))
                    offset_y = 1.7 * np.sin(np.deg2rad(angle))
                    if idx % 2 == 0:
                        text = ax.text(mid_x + offset_x, mid_y + offset_y, f"{angle:.1f}°", color='green', fontsize=8, ha='center')
                    else:
                        text = ax.text(mid_x - offset_x, mid_y - offset_y, f"{angle:.1f}°", color='green', fontsize=8, ha='center')
                    text_annotations.append(text)

            return gelenk_points, stab_plot, *traj_plots.values()

        ani = FuncAnimation(fig, update, frames=50, interval=100)
        html_writer = HTMLWriter()
        anim_html = ani.to_jshtml()
        st.components.v1.html(anim_html, height=600)


############################################################################################################################################################################



with selected_tab[2]:  

    saved_mechanisms = [m["name"] for m in mechanisms_table.all()]
    selected_mechanism = st.selectbox("🔽 Wähle einen gespeicherten Mechanismus", saved_mechanisms, key="saved_mechanism_tab0")

    if st.button("📂 Laden", key="laden_tab2"):
        result = load_mechanism_from_db(selected_mechanism)
        if result[0] is not None:
            gelenke, staebe, radius, fixed_gelenk_index, rotating_gelenk_index = result
            st.session_state["mechanism"] = Mechanism(gelenke, staebe, radius)
            st.success(f"✅ Mechanismus '{selected_mechanism}' geladen!")

            gelenk_data = pd.DataFrame({
                "Gelenk": [f"G{i}" for i in range(len(gelenke))],
                "X-Koordinate": [round(g.x, 2) for g in gelenke],
                "Y-Koordinate": [round(g.y, 2) for g in gelenke],
                "Fixiert": [g.is_static for g in gelenke],
                "Rotierend": [g.is_rotating for g in gelenke],
                "Trajektorie": [g.is_tracked for g in gelenke]
            })
            
            st.subheader("Gelenk-Daten")
            st.dataframe(gelenk_data)

            stab_data = pd.DataFrame({
                "Stab": [f"S{i}" for i in range(len(staebe))],
                "Gelenk 1": [gelenke.index(stab.gelenk1) for stab in staebe],
                "Gelenk 2": [gelenke.index(stab.gelenk2) for stab in staebe]
            })
    
    if st.session_state["mechanism"]:
        export_option = st.toggle("CSV-Datei nur für ausgewählte Trajektorie", value=True)

        if st.button("CSV exportieren"):
            mechanism = st.session_state["mechanism"]
            theta_values = np.linspace(0, 2 * np.pi, 50)
            positions_over_time = [mechanism.update_positions(theta) for theta in theta_values]

            if export_option:
                tracked_positions = {i: [] for i, gelenk in enumerate(mechanism.gelenk) if gelenk.is_tracked}
                for theta, positions in zip(theta_values, positions_over_time):
                    for i, gelenk in enumerate(mechanism.gelenk):
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
                for i in range(len(mechanism.gelenk)):
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
                for i in range(len(mechanism.gelenk)):
                    columns.extend([f"X{i}", f"Y{i}"])

                df = pd.DataFrame(data, columns=columns)

            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 CSV herunterladen",
                data=csv,
                file_name="trajektorie.csv",
                mime="text/csv"
            )

############################################################################################################################################################################

with selected_tab[3]:
    st.header("Mechanismus herunter- und hochladen")

    # Export-Funktion für JSON im gespeicherten Format
    st.subheader("Mechanismus exportieren")
    selected_mechanism = st.selectbox("🔽 Wähle einen gespeicherten Mechanismus zum Export", [m["name"] for m in mechanisms_table.all()], key="export_mechanism")

    result = load_mechanism_from_db(selected_mechanism)
    if result[0] is not None:
        gelenke, staebe, radius, _, _ = result

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

            gelenke = [Gelenk(joint["x"], joint["y"], joint.get("static", False), joint.get("rotating", False), joint.get("tracked", False)) for joint in mechanism_info["gelenke"]]
            staebe = [Stab(gelenke[s[0]], gelenke[s[1]]) for s in mechanism_info["staebe"]]
            radius = mechanism_info.get("radius", 10)

            # Speichern des Mechanismus in der Session
            st.session_state["mechanism"] = Mechanism(gelenke, staebe, radius)
            st.success(f"✅ Mechanismus '{mechanism_info['name']}' wurde erfolgreich geladen!")

            # Checkbox für Längenfehler anzeigen
            if "show_length_error" not in st.session_state:
                st.session_state.show_length_error = False

            st.session_state.show_length_error = st.checkbox("Prozentualen Längenfehler anzeigen", key="show_length_error_tab2")

            # Option zur Simulation des geladenen Mechanismus
            if st.session_state["mechanism"] and st.button("▶ Mechanik ausführen", key="run_loaded_mechanism_tab2"):
                mechanism = st.session_state["mechanism"]
                st.success(f"✅ Mechanismus '{selected_mechanism}' wird gestartet!")

                # Größe des Plots
                all_x = [g.x for g in mechanism.gelenk]
                all_y = [g.y for g in mechanism.gelenk]
                padding = 10
                x_min, x_max = min(all_x) - padding, max(all_x) + padding
                y_min, y_max = min(all_y) - padding, max(all_y) + padding
                x_range = x_max - x_min
                y_range = y_max - y_min
                max_range = max(x_range, y_range)
                x_center = (x_max + x_min) / 2
                y_center = (y_max + y_min) / 2
                x_min, x_max = x_center - max_range / 2, x_center + max_range / 2
                y_min, y_max = y_center - max_range / 2, y_center + max_range / 2

                fig, ax = plt.subplots()
                ax.set_xlim(x_min, x_max)
                ax.set_ylim(y_min, y_max)
                ax.set_aspect('equal')
                ax.set_title("Mechanismus Animation")
                ax.set_xlabel("X-Koordinate")
                ax.set_ylabel("Y-Koordinate")
                ax.grid(True)

                circle = plt.Circle((mechanism.gelenk[mechanism.rotating_gelenk_index].x, mechanism.gelenk[mechanism.rotating_gelenk_index].y), radius, color='b', fill=False, linestyle='dashed')
                ax.add_patch(circle)

                gelenk_points, = ax.plot([], [], 'ro')
                stab_plot, = ax.plot([], [], 'k-', lw=2)
                traj_plots = {i: ax.plot([], [], 'g-', lw=2)[0] for i, gelenk in enumerate(mechanism.gelenk) if gelenk.is_tracked}

                text_annotations = []

                def calculate_length_error(mechanism, optimized_positions):
                    current_lengths = mechanism.verbindungs_matrix @ optimized_positions.flatten()
                    current_lengths = np.linalg.norm(current_lengths.reshape(-1, 2), axis=1)
                    length_errors = (current_lengths - mechanism.start_laengen) / mechanism.start_laengen * 100
                    return length_errors

                def update(frame):
                    theta = np.linspace(0, 2 * np.pi, 50)[frame]
                    optimized_positions = mechanism.update_positions(theta)
                    gelenk_points.set_data(optimized_positions[:, 0], optimized_positions[:, 1])

                    stab_x, stab_y = [], []
                    length_errors = calculate_length_error(mechanism, optimized_positions)

                    for text in text_annotations:
                        text.remove()
                    text_annotations.clear()

                    for i, stab in enumerate(mechanism.staebe):
                        p1, p2 = optimized_positions[mechanism.gelenk.index(stab.gelenk1)], optimized_positions[mechanism.gelenk.index(stab.gelenk2)]
                        stab_x.extend([p1[0], p2[0], None])
                        stab_y.extend([p1[1], p2[1], None])

                        if st.session_state.show_length_error:
                            mid_x, mid_y = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
                            text = ax.text(mid_x, mid_y, f"{length_errors[i]:.2f}%", color='red', fontsize=8, ha='center')
                            text_annotations.append(text)

                    stab_plot.set_data(stab_x, stab_y)

                    for i, gelenk in enumerate(mechanism.gelenk):
                        if gelenk.is_tracked:
                            traj_x, traj_y = traj_plots[i].get_data()
                            traj_plots[i].set_data(np.append(traj_x, optimized_positions[i, 0]), np.append(traj_y, optimized_positions[i, 1]))

                    return gelenk_points, stab_plot, *traj_plots.values()

                ani = FuncAnimation(fig, update, frames=50, interval=100)
                html_writer = HTMLWriter()
                anim_html = ani.to_jshtml()
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


############################################################################################################################################################################


with selected_tab[4]:
    st.header("Mechanismusanimation (gif) downloaden")
    saved_mechanisms = [m["name"] for m in mechanisms_table.all()]
    selected_mechanism = st.selectbox("🔽 Wähle einen gespeicherten Mechanismus", saved_mechanisms, key="mechanism_tab3")

    # Checkboxen für Anzeigen
    if "show_length_error_tab3" not in st.session_state:
        st.session_state["show_length_error_tab3"] = False
    if "show_stab_lengths_tab3" not in st.session_state:
        st.session_state["show_stab_lengths_tab3"] = False
    if "show_stab_angles_tab3" not in st.session_state:
        st.session_state["show_stab_angles_tab3"] = False

    show_length_error = st.toggle("Prozentualen Längenfehler anzeigen", key="show_length_error_tab3")
    show_stab_lengths = st.toggle("Längen der Stäbe anzeigen", key="show_stab_lengths_tab3")
    show_stab_angles = st.toggle("Winkel zwischen den Stäben anzeigen", key="show_stab_angles_tab3")

    if show_length_error and show_stab_lengths:
        st.warning("Warnung: Wenn sowohl 'Prozentualen Längenfehler anzeigen' als auch 'Längen der Stäbe anzeigen' aktiviert sind, können sich die Zahlen in der Visualisierung überlappen.")
   
    if st.button("📂 Laden", key="laden_tab3"):
        result = load_mechanism_from_db(selected_mechanism)
        if result[0] is not None:
            gelenke, staebe, radius, fixed_gelenk_index, rotating_gelenk_index = result
            st.session_state["mechanism"] = Mechanism(gelenke, staebe, radius)
            st.success(f"✅ Mechanismus '{selected_mechanism}' wurde geladen und wird nun für den Download vorbereitet!")

            mechanism = st.session_state["mechanism"]
            theta_values = np.linspace(0, 2 * np.pi, 50)
            positions_over_time = [mechanism.update_positions(theta) for theta in theta_values]

            all_x = [pos[:, 0] for pos in positions_over_time]
            all_y = [pos[:, 1] for pos in positions_over_time]

            x_min, x_max = min(map(min, all_x)) - 10, max(map(max, all_x)) + 10
            y_min, y_max = min(map(min, all_y)) - 10, max(map(max, all_y)) + 10

            max_range = max(x_max - x_min, y_max - y_min)

            fig, ax = plt.subplots(figsize=(8, 8))  # Größere Darstellung
            ax.set_xlim((x_min + x_max) / 2 - max_range / 2, (x_min + x_max) / 2 + max_range / 2)
            ax.set_ylim((y_min + y_max) / 2 - max_range / 2, (y_min + y_max) / 2 + max_range / 2)
            ax.set_aspect('equal')
            ax.set_title("Mechanismus Animation")
            ax.set_xlabel("X-Koordinate")
            ax.set_ylabel("Y-Koordinate")
            ax.grid(True)

            circle = plt.Circle((mechanism.gelenk[mechanism.rotating_gelenk_index].x, mechanism.gelenk[mechanism.rotating_gelenk_index].y), radius, color='b', fill=False, linestyle='dashed')
            ax.add_patch(circle)

            gelenk_points, = ax.plot([], [], 'ro')
            stab_plot, = ax.plot([], [], 'k-', lw=2)
            traj_plots = {i: ax.plot([], [], 'g-', lw=2)[0] for i, gelenk in enumerate(gelenke) if gelenk.is_tracked}

            text_annotations = []

            def calculate_length_error(mechanism, optimized_positions):
                current_lengths = mechanism.verbindungs_matrix @ optimized_positions.flatten()
                current_lengths = np.linalg.norm(current_lengths.reshape(-1, 2), axis=1)
                length_errors = (current_lengths - mechanism.start_laengen) / mechanism.start_laengen * 100
                return length_errors

            def calculate_stab_lengths(positions, staebe):
                lengths = []
                for stab in staebe:
                    p1, p2 = positions[gelenke.index(stab.gelenk1)], positions[gelenke.index(stab.gelenk2)]
                    length = np.linalg.norm(np.array(p2) - np.array(p1))
                    lengths.append(length)
                return lengths

            def calculate_stab_angles(positions, staebe):
                angles = []
                for gelenk in gelenke:
                    connected_stabs = [stab for stab in staebe if gelenk in [stab.gelenk1, stab.gelenk2]]
                    if len(connected_stabs) < 2:
                        continue

                    for i in range(len(connected_stabs) - 1):
                        stab1, stab2 = connected_stabs[i], connected_stabs[i + 1]
                        p1 = np.array(positions[gelenke.index(stab1.gelenk1 if stab1.gelenk1 != gelenk else stab1.gelenk2)])
                        p2 = np.array(positions[gelenke.index(gelenk)])
                        p3 = np.array(positions[gelenke.index(stab2.gelenk1 if stab2.gelenk1 != gelenk else stab2.gelenk2)])

                        v1 = p1 - p2
                        v2 = p3 - p2

                        if np.linalg.norm(v1) == 0 or np.linalg.norm(v2) == 0:
                            angle = 0
                        else:
                            cos_theta = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                            angle = np.arccos(np.clip(cos_theta, -1.0, 1.0)) * (180 / np.pi)

                        angles.append((gelenk, angle, p2[0], p2[1]))  
                return angles
            
            def update(frame):
                theta = np.linspace(0, 2 * np.pi, 50)[frame]
                optimized_positions = mechanism.update_positions(theta)
                gelenk_points.set_data(optimized_positions[:, 0], optimized_positions[:, 1])

                stab_x, stab_y = [], []
                length_errors = calculate_length_error(mechanism, optimized_positions)

                for text in text_annotations:
                    text.remove()
                text_annotations.clear()

                for i, stab in enumerate(mechanism.staebe):
                    p1, p2 = optimized_positions[mechanism.gelenk.index(stab.gelenk1)], optimized_positions[mechanism.gelenk.index(stab.gelenk2)]
                    stab_x.extend([p1[0], p2[0], None])
                    stab_y.extend([p1[1], p2[1], None])

                    if st.session_state["show_length_error_tab3"]:
                        mid_x, mid_y = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
                        text = ax.text(mid_x, mid_y, f"{length_errors[i]:.2f}%", color='red', fontsize=8, ha='center')
                        text_annotations.append(text)

                    if st.session_state["show_stab_lengths_tab3"]:
                        mid_x, mid_y = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
                        text = ax.text(mid_x, mid_y, f"{calculate_stab_lengths(optimized_positions, mechanism.staebe)[i]:.2f}", 
                                    color='blue', fontsize=8, ha='center')
                        text_annotations.append(text)

                    if st.session_state["show_stab_angles_tab3"]:
                        angles = calculate_stab_angles(optimized_positions, mechanism.staebe)
                        for idx, (gelenk, angle, mid_x, mid_y) in enumerate(angles):
                            offset_x = 1.7 * np.cos(np.deg2rad(angle))
                            offset_y = 1.7 * np.sin(np.deg2rad(angle))
                            if idx % 2 == 0:
                                text = ax.text(mid_x + offset_x, mid_y + offset_y, f"{angle:.1f}°", color='green', fontsize=8, ha='center')
                            else:
                                text = ax.text(mid_x - offset_x, mid_y - offset_y, f"{angle:.1f}°", color='green', fontsize=8, ha='center')
                            text_annotations.append(text)

                stab_plot.set_data(stab_x, stab_y)

                for i, gelenk in enumerate(mechanism.gelenk):
                    if gelenk.is_tracked:
                        traj_x, traj_y = traj_plots[i].get_data()
                        traj_plots[i].set_data(np.append(traj_x, optimized_positions[i, 0]), np.append(traj_y, optimized_positions[i, 1]))

                return gelenk_points, stab_plot, *traj_plots.values()

            ani = FuncAnimation(fig, update, frames=len(theta_values), interval=100)

            # Speichern vom GIF
            with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as temp_gif:
                ani.save(temp_gif.name, writer=PillowWriter(fps=10))

                with open(temp_gif.name, "rb") as f:
                    gif_bytes = f.read()

            st.success("✅ Animation zum Download bereit.")

            # Download vom GIF
            st.download_button(
                label="📥 Download als GIF",
                data=gif_bytes,
                file_name=f"{selected_mechanism}.gif",
                mime="image/gif"
            )