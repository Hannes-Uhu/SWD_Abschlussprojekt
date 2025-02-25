import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.animation import FuncAnimation, HTMLWriter
from mechanism import Mechanism
import streamlit as st

def animate_mechanism(mechanism: Mechanism, show_length_error=False, show_stab_lengths=False, show_stab_angles=False):
    fig, ax = plt.subplots()

    all_x = [g.x for g in mechanism.gelenke]
    all_y = [g.y for g in mechanism.gelenke]
    padding = 10
    x_min, x_max = min(all_x) - padding, max(all_x) + padding
    y_min, y_max = min(all_y) - padding, max(all_y) + padding
    max_range = max(x_max - x_min, y_max - y_min)
    x_center = (x_max + x_min) / 2
    y_center = (y_max + y_min) / 2
    x_min, x_max = x_center - max_range / 2, x_center + max_range / 2
    y_min, y_max = y_center - max_range / 2, y_center + max_range / 2

    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_aspect('equal')
    ax.set_title("Mechanismus Animation")
    ax.set_xlabel("X-Koordinate")
    ax.set_ylabel("Y-Koordinate")
    ax.grid(True)
    
    circle = plt.Circle((mechanism.gelenke[mechanism.rotating_gelenk_index].x, 
                         mechanism.gelenke[mechanism.rotating_gelenk_index].y), 
                         mechanism.radius, color='b', fill=False, linestyle='dashed')
    ax.add_patch(circle)
    
    gelenk_points, = ax.plot([], [], 'ro')
    stab_plot, = ax.plot([], [], 'k-', lw=2)
    traj_plots = {i: ax.plot([], [], 'g-', lw=2)[0] for i, gelenk in enumerate(mechanism.gelenke) if gelenk.is_tracked}
    text_annotations = []
    
    def calculate_length_error(mechanism, optimized_positions):
        current_lengths = mechanism.verbindungs_matrix @ optimized_positions.flatten()
        current_lengths = np.linalg.norm(current_lengths.reshape(-1, 2), axis=1)
        length_errors = (current_lengths - mechanism.start_laengen) / mechanism.start_laengen * 100
        return length_errors

    def calculate_stab_lengths(positions, staebe):
        lengths = []
        for stab in staebe:
            p1, p2 = positions[mechanism.gelenke.index(stab.gelenk1)], positions[mechanism.gelenke.index(stab.gelenk2)]
            length = np.linalg.norm(np.array(p2) - np.array(p1))
            lengths.append(length)
        return lengths

    def calculate_stab_angles(positions, staebe):
        angles = []
        for gelenk in mechanism.gelenke:
            connected_stabs = [stab for stab in staebe if gelenk in [stab.gelenk1, stab.gelenk2]]
            if len(connected_stabs) < 2:
                continue

            for i in range(len(connected_stabs) - 1):
                stab1, stab2 = connected_stabs[i], connected_stabs[i + 1]
                p1 = np.array(positions[mechanism.gelenke.index(stab1.gelenk1 if stab1.gelenk1 != gelenk else stab1.gelenk2)])
                p2 = np.array(positions[mechanism.gelenke.index(gelenk)])
                p3 = np.array(positions[mechanism.gelenke.index(stab2.gelenk1 if stab2.gelenk1 != gelenk else stab2.gelenk2)])

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
            p1, p2 = optimized_positions[mechanism.gelenke.index(stab.gelenk1)], optimized_positions[mechanism.gelenke.index(stab.gelenk2)]
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
        
        for i, gelenk in enumerate(mechanism.gelenke):
            if gelenk.is_tracked:
                traj_x, traj_y = traj_plots[i].get_data()
                traj_plots[i].set_data(np.append(traj_x, optimized_positions[i, 0]), np.append(traj_y, optimized_positions[i, 1]))

        if show_stab_angles:
            angles = calculate_stab_angles(optimized_positions, mechanism.staebe)
            for idx, (gelenk, angle, mid_x, mid_y) in enumerate(angles):
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
    return anim_html
