import numpy as np
from scipy.optimize import minimize

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
    def __init__(self, gelenke, staebe, radius):
        self.gelenke = gelenke
        self.staebe = staebe
        self.radius = radius
        
        self.fixed_gelenk_index = next((i for i, g in enumerate(gelenke) if g.is_static), None)
        self.rotating_gelenk_index = next((i for i, g in enumerate(gelenke) if g.is_rotating), None)
        
        if self.fixed_gelenk_index is None or self.rotating_gelenk_index is None:
            raise ValueError("Fehler: Es muss genau ein fixiertes und ein rotierendes Gelenk geben!")
        
        self.theta_values = np.linspace(0, 2 * np.pi, 72)
        self.verbindungs_matrix = self.create_verbindungs_matrix()
        self.start_laengen = self.berechnet_laengen()
        self.trajectories = {i: [] for i in range(len(self.gelenke))}
        self.selected_trajectory = next((i for i, g in enumerate(gelenke) if g.is_tracked), self.rotating_gelenk_index)
        
        for theta in self.theta_values:
            positions = self.update_positions(theta)
            for i, pos in enumerate(positions):
                self.trajectories[i].append(tuple(pos))

    def create_verbindungs_matrix(self):
        num_staebe = len(self.staebe)
        num_gelenke = len(self.gelenke)
        verbindungs_matrix = np.zeros((2 * num_staebe, 2 * num_gelenke))

        for i, stab in enumerate(self.staebe):
            p1_idx = self.gelenke.index(stab.gelenk1) * 2
            p2_idx = self.gelenke.index(stab.gelenk2) * 2

            verbindungs_matrix[2 * i, p1_idx] = 1
            verbindungs_matrix[2 * i, p2_idx] = -1
            verbindungs_matrix[2 * i + 1, p1_idx + 1] = 1
            verbindungs_matrix[2 * i + 1, p2_idx + 1] = -1
        
        return verbindungs_matrix

    def berechnet_laengen(self):
        gelenk_vektor = np.array([g.position() for g in self.gelenke]).flatten()
        stab_laenge = self.verbindungs_matrix @ gelenk_vektor
        laengen = np.linalg.norm(stab_laenge.reshape(-1, 2), axis=1)
        return laengen
    
    def fehlerfunktion(self, positions, rotationspunkt_neu):
        gelenk_vektor = np.vstack((
            self.gelenke[self.fixed_gelenk_index].position().reshape(1, -1),
            rotationspunkt_neu.reshape(1, -1),
            np.array(positions).reshape(-1, 2)
        )).flatten()

        current_laengen = self.verbindungs_matrix @ gelenk_vektor
        laengen = np.linalg.norm(current_laengen.reshape(-1, 2), axis=1)
        return np.sum((laengen - self.start_laengen) ** 2)

    def update_positions(self, theta):
        rotating_gelenk = self.gelenke[self.rotating_gelenk_index]
        rotationspunkt_neu = np.array([
            rotating_gelenk.x + self.radius * np.cos(theta),
            rotating_gelenk.y + self.radius * np.sin(theta)
        ])
        
        initial_guess = np.hstack([
            p.position()
            for i, p in enumerate(self.gelenke)
            if i not in [self.fixed_gelenk_index, self.rotating_gelenk_index]
        ]).flatten()

        result = minimize(self.fehlerfunktion, initial_guess, args=(rotationspunkt_neu,), method='SLSQP')
        
        optimized_positions = np.zeros((len(self.gelenke), 2))
        optimized_positions[self.fixed_gelenk_index] = self.gelenke[self.fixed_gelenk_index].position()
        optimized_positions[self.rotating_gelenk_index] = rotationspunkt_neu
        remaining_indices = [i for i in range(len(self.gelenke)) if i not in [self.fixed_gelenk_index, self.rotating_gelenk_index]]
        optimized_positions[remaining_indices] = result.x.reshape(-1, 2)
        
        for i, pos in enumerate(optimized_positions):
            self.trajectories[i].append(tuple(pos))
        
        return optimized_positions
