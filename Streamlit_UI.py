import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.animation import FuncAnimation, HTMLWriter
from tinydb import TinyDB, Query
from main import Mechanism, Gelenk, Stab, save_mechanism_to_db, load_mechanism_from_db
from io import BytesIO
import base64


db = TinyDB("mechanism_db.json")
mechanisms_table = db.table("mechanisms")

st.title("Interaktive Mechanismus-Simulation")

st.session_state.setdefault("mechanism", None)

#Tabs
selected_tab = st.tabs(["Mechanismus erstellen", "Mechaniken laden"])




with selected_tab[0]:
    st.header("Mechanismus erstellen")
    

    radius = st.slider("Rotationsradius", 5, 20, 10)

    st.subheader("Gelenkpunkte")
    def create_gelenk_df(num_gelenke):
        return pd.DataFrame({
            "Gelenk": [f"G{i}" for i in range(num_gelenke)],
            "X-Koordinate": [0 if i == 0 else 10 * i for i in range(num_gelenke)],
            "Y-Koordinate": [0 if i == 0 else 10 * i for i in range(num_gelenke)],
            "Fixiert": [False for _ in range(num_gelenke)],
            "Rotierend": [False for _ in range(num_gelenke)],
            "Trajektorie": [False for _ in range(num_gelenke)]
        })

    num_gelenke = st.number_input("Anzahl der Gelenkpunkte", min_value=2, max_value=100, value=4)
    gelenk_df = st.data_editor(create_gelenk_df(num_gelenke), num_rows="dynamic")

    if gelenk_df["Rotierend"].sum() > 1:
        st.error("Fehler: Es darf nur ein rotierendes Gelenk ausgewählt werden!")

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


    # Mechanismus visualisieren
    if rotierendes_gelenk is not None:
        if st.button("Simulation starten"):
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

            def update(frame):
                theta = np.linspace(0, 2 * np.pi, 50)[frame]
                optimized_positions = mechanism.update_positions(theta)
                gelenk_points.set_data(optimized_positions[:, 0], optimized_positions[:, 1])

                stab_x = []
                stab_y = []
                for stab in staebe:
                    p1_index = gelenke.index(stab.gelenk1)
                    p2_index = gelenke.index(stab.gelenk2)
                    p1 = optimized_positions[p1_index]
                    p2 = optimized_positions[p2_index]
                    stab_x.extend([p1[0], p2[0], None])
                    stab_y.extend([p1[1], p2[1], None])

                stab_plot.set_data(stab_x, stab_y)

                for i, gelenk in enumerate(gelenke):
                    if gelenk.is_tracked:
                        traj_x, traj_y = traj_plots[i].get_data()
                        traj_plots[i].set_data(np.append(traj_x, optimized_positions[i, 0]), np.append(traj_y, optimized_positions[i, 1]))

                return gelenk_points, stab_plot, *traj_plots.values()

            ani = FuncAnimation(fig, update, frames=50, interval=100)
            html_writer = HTMLWriter()
            anim_html = ani.to_jshtml()
            st.components.v1.html(anim_html, height=600)

    else:
        st.error("Fehler: Es muss ein rotierendes Gelenk definiert werden, um die Simulation zu starten.")
    



        



with selected_tab[1]:
    st.header("Mechaniken laden")
    saved_mechanisms = [m["name"] for m in mechanisms_table.all()]
    selected_mechanism = st.selectbox("🔽 Wähle einen gespeicherten Mechanismus", saved_mechanisms)
    
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


    if st.session_state["mechanism"] and st.button("▶ Mechanik ausführen"):
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
        
        def update(frame):
            theta = np.linspace(0, 2 * np.pi, 50)[frame]
            optimized_positions = mechanism.update_positions(theta)
            gelenk_points.set_data(optimized_positions[:, 0], optimized_positions[:, 1])
            
            stab_x, stab_y = [], []
            for stab in mechanism.staebe:
                p1, p2 = optimized_positions[mechanism.gelenk.index(stab.gelenk1)], optimized_positions[mechanism.gelenk.index(stab.gelenk2)]
                stab_x.extend([p1[0], p2[0], None])
                stab_y.extend([p1[1], p2[1], None])
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

    if st.session_state["mechanism"]:
        mechanism = st.session_state["mechanism"]

        save_mode = st.toggle("Nur verfolgte Gelenke speichern")

        if st.button("⬇️ Bahnkurve als CSV speichern"):
            data = []
            tracked_indices = [i for i, g in enumerate(mechanism.gelenk) if g.is_tracked]
            selected_indices = range(len(mechanism.gelenk)) if save_mode == "Alle Gelenke" else tracked_indices
            
            for i in range(len(mechanism.theta_values)):
                theta = np.degrees(mechanism.theta_values[i]) 
                row = [round(theta, 2)] 
                

                for j in selected_indices:
                    if j in mechanism.trajectories and len(mechanism.trajectories[j]) > i:
                        pos = mechanism.trajectories[j][i]
                    else:
                        pos = (None, None)  
                    row.extend([round(p, 2) if p is not None else None for p in pos])
                
                data.append(row)
            
            columns = ["Winkel (Theta) [°]"]
            for i in selected_indices:
                columns.extend([f"X-Koordinate Gelenk {i}", f"Y-Koordinate Gelenk {i}"])
            
            df = pd.DataFrame(data, columns=columns)
            csv = df.to_csv(index=False, sep=",") 
            st.download_button(
                label="📥 CSV herunterladen",
                data=csv,
                file_name="bahnkurve.csv",
                mime="text/csv"
            )
