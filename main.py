import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from scipy.optimize import minimize
import json
from tinydb import TinyDB, Query
import streamlit as st


class Gelenk:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def position(self):
        return np.array([self.x, self.y])


class Stab:
    def __init__(self, gelenk1, gelenk2):
        self.gelenk1 = gelenk1
        self.gelenk2 = gelenk2


class Mechanism:
    def __init__(self, gelenk, staebe, radius):
        self.gelenk = gelenk
        self.staebe = staebe

        self.fixed_gelenk_index = 0  # Der erste Punkt ist immer fixiert
        self.rotating_gelenk_index = 1  # Der zweite Punkt bewegt sich auf der Kreisbahn

        self.radius = radius
        self.theta_values = np.linspace(0, 2 * np.pi, 72)

        self.verbindungs_matrix = self.create_verbindungs_matrix()
        self.start_laengen = self.berechnet_laengen()

        self.trajectory1 = []

    def create_verbindungs_matrix(self):
        num_staebe = len(self.staebe)
        num_gelenk = len(self.gelenk)
        verbindungs_matrix = np.zeros((2 * num_staebe, 2 * num_gelenk))

        for i, stab in enumerate(self.staebe):
            p1_idx = self.gelenk.index(stab.gelenk1) * 2
            p2_idx = self.gelenk.index(stab.gelenk2) * 2

            verbindungs_matrix[2 * i, p1_idx] = 1
            verbindungs_matrix[2 * i, p2_idx] = -1
            verbindungs_matrix[2 * i + 1, p1_idx + 1] = 1
            verbindungs_matrix[2 * i + 1, p2_idx + 1] = -1

        return verbindungs_matrix

    def berechnet_laengen(self):
        gelenk_vektor = np.array([g.position() for g in self.gelenk]).flatten()
        stab_laenge = self.verbindungs_matrix @ gelenk_vektor
        laengen = np.linalg.norm(stab_laenge.reshape(-1, 2), axis=1)
        return laengen

    def fehlerfunktion(self, positions, rotationspunkt_neu):
        gelenk_vektor = np.hstack((
            [self.gelenk[self.fixed_gelenk_index].position()],
            [rotationspunkt_neu],
            [positions[i:i+2] for i in range(0, len(positions), 2)]
        )).flatten()

        current_laengen = self.verbindungs_matrix @ gelenk_vektor
        laengen = np.linalg.norm(current_laengen.reshape(-1, 2), axis=1)

        return np.sum((laengen - self.start_laengen) ** 2)

    def update_positions(self, theta):
        rotating_gelenk = self.gelenk[self.rotating_gelenk_index]
        rotationspunkt_neu = np.array([
            rotating_gelenk.x + self.radius * np.cos(theta),
            rotating_gelenk.y + self.radius * np.sin(theta)
        ])

        initial_guess = np.hstack([
            p.position()
            for i, p in enumerate(self.gelenk)
            if i not in [self.fixed_gelenk_index, self.rotating_gelenk_index]
        ]).flatten()

        result = minimize(
            self.fehlerfunktion,
            initial_guess,
            args=(rotationspunkt_neu,),
            method='BFGS'
        )

        optimized_positions = np.vstack((
            [self.gelenk[self.fixed_gelenk_index].position()],
            result.x.reshape(-1, 2).tolist(),
            [rotationspunkt_neu]
        ))

        return optimized_positions

    def animate_mechanism(self):
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.set_xlabel('X-Koordinate')
        ax.set_ylabel('Y-Koordinate')
        ax.set_title('Animation des Mechanismus')
        ax.grid(True)

        mechanik_plot, = ax.plot([], [], 'ro-', label='Mechanismus')
        rotating_gelenk_plot, = ax.plot(
            self.gelenk[self.rotating_gelenk_index].x,
            self.gelenk[self.rotating_gelenk_index].y,
            'bo',
            label='Rotierender Punkt'
        )

        circle = plt.Circle(
            (self.gelenk[self.rotating_gelenk_index].x, self.gelenk[self.rotating_gelenk_index].y),
            self.radius,
            color='b',
            fill=False,
            linestyle='--'
        )
        ax.add_patch(circle)

        trajectory1_plot, = ax.plot([], [], 'g-', label='Trajektorie Punkt 1')

        def update(frame):
            theta = self.theta_values[frame]
            optimized_positions = self.update_positions(theta)
            ax.set_xlim(-50, 40)
            ax.set_ylim(-20, 40)

            self.trajectory1.append(optimized_positions[1])

            mechanik_plot.set_data(optimized_positions[:, 0], optimized_positions[:, 1])
            trajectory1_plot.set_data(*zip(*self.trajectory1))

            return mechanik_plot, trajectory1_plot

        ani = animation.FuncAnimation(
            fig,
            update,
            frames=len(self.theta_values),
            interval=50,
            blit=False
        )
        plt.legend()
        plt.show()

db = TinyDB("mechanism_db.json")
mechanisms_table = db.table("mechanisms")

def save_mechanism_to_db(name, gelenke, staebe, radius):
    data = {
        "name": name,
        "gelenke": [{"x": g.x, "y": g.y} for g in gelenke],  # Speichert Gelenke als (x, y)-Werte
        "staebe": [[gelenke.index(s.gelenk1), gelenke.index(s.gelenk2)] for s in staebe],  # Indizes der verbundenen Gelenke
        "radius": radius
    }
    mechanisms_table.insert(data)  # Speichert den Mechanismus in der Datenbank
    st.success(f"Mechanismus '{name}' gespeichert!")



def load_mechanism(filename="mechanism.json"):
    with open(filename, "r") as f:
        data = json.load(f)

    gelenk = [Gelenk(x, y) for x, y in data["gelenke"]]
    staebe = [Stab(gelenk[i1], gelenk[i2]) for i1, i2 in data["staebe"]]
    
    return gelenk, staebe, data["radius"]


gelenk = [
    Gelenk(0, 0),
    Gelenk(-30, 0),
    Gelenk(10, 30)
]
radius = 10

staebe = [
    Stab(gelenk[0], gelenk[2]),
    Stab(gelenk[2], gelenk[1]),
    Stab(gelenk[0], gelenk[1])
]

def simulate_mechanism(gelenk, staebe, radius):
    
    mechanism = Mechanism(gelenk, staebe, radius)
    mechanism.animate_mechanism()



# Laden des Mechanismus und Simulation starten
geladene_gelenke, geladene_staebe, geladener_radius = load_mechanism()
simulate_mechanism(geladene_gelenke, geladene_staebe, geladener_radius)
