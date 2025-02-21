import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from scipy.optimize import minimize
import json
from tinydb import TinyDB, Query
import streamlit as st

class Gelenk:
    def __init__(self, x, y, is_static=False, is_rotating=False, is_tracked=False):
        self.x = x
        self.y = y
        self.is_static = is_static
        self.is_rotating = is_rotating
        self.is_tracked = is_tracked

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

        self.fixed_gelenk_index = next((i for i, g in enumerate(gelenk) if g.is_static), 0)
        self.rotating_gelenk_index = next((i for i, g in enumerate(gelenk) if g.is_rotating), 1)

        self.radius = radius
        self.theta_values = np.linspace(0, 2 * np.pi, 72)

        self.verbindungs_matrix = self.create_verbindungs_matrix()
        self.start_laengen = self.berechnet_laengen()

        # Speichere Bahnkurven für alle Gelenke
        self.trajectories = {i: [] for i in range(len(self.gelenk))}
        self.selected_trajectory = next((i for i, g in enumerate(gelenk) if g.is_tracked), self.rotating_gelenk_index)

        # Speichert Werte in Trajektorie
        for theta in self.theta_values:
            positions = self.update_positions(theta)
            for i, pos in enumerate(positions):
                self.trajectories[i].append(tuple(pos))  


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
        gelenk_vektor = np.vstack((
            self.gelenk[self.fixed_gelenk_index].position().reshape(1, -1),
            rotationspunkt_neu.reshape(1, -1),
            np.array(positions).reshape(-1, 2)
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

        # Reihenfolge der Gelenke bleibt fix
        optimized_positions = np.zeros((len(self.gelenk), 2))
        
        optimized_positions[self.fixed_gelenk_index] = self.gelenk[self.fixed_gelenk_index].position()
        optimized_positions[self.rotating_gelenk_index] = rotationspunkt_neu
        remaining_indices = [i for i in range(len(self.gelenk)) if i not in [self.fixed_gelenk_index, self.rotating_gelenk_index]]
        
        optimized_positions[remaining_indices] = result.x.reshape(-1, 2)

        for i, pos in enumerate(optimized_positions):
            self.trajectories[i].append(tuple(pos))

        return optimized_positions

# TinyDB Datenbank
db = TinyDB("mechanism_db.json")
mechanisms_table = db.table("mechanisms")

def save_mechanism_to_db(name, gelenke, staebe, radius):
    data = {
        "name": name,
        "gelenke": [{
            "x": g.x, 
            "y": g.y, 
            "static": g.is_static, 
            "rotating": g.is_rotating, 
            "tracked": g.is_tracked
        } for g in gelenke],
        "staebe": [[gelenke.index(s.gelenk1), gelenke.index(s.gelenk2)] for s in staebe],
        "radius": radius
    }
    mechanisms_table.insert(data)
    st.success(f"✅ Mechanismus '{name}' gespeichert!")

def load_mechanism_from_db(name):
    MechanismQuery = Query()
    result = mechanisms_table.search(MechanismQuery.name == name)
    
    if not result:
        return None, None, None, None, None 
    
    data = result[0]
    gelenke = [Gelenk(g["x"], g["y"], g.get("static", False), g.get("rotating", False), g.get("tracked", False)) for g in data["gelenke"]]
    staebe = [Stab(gelenke[i1], gelenke[i2]) for i1, i2 in data["staebe"]]
    radius = data["radius"]
    fixed_gelenk_index = data.get("fixed_gelenk_index", None)
    rotating_gelenk_index = data.get("rotating_gelenk_index", None)

    return gelenke, staebe, radius, fixed_gelenk_index, rotating_gelenk_index