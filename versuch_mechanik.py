import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from scipy.optimize import minimize

# Fixe Gelenkpunkte
C_start = np.array([-30, 0])  
radius = 10  
P0 = np.array([0, 0])
P1 = np.array([10, 30])
theta_values = np.linspace(0, 2 * np.pi, 72)  # 72 Schritte für 360°

# Dynamische Berechnung der Stablängen
def berechne_laenge(a_matrix, positions_matrix):  # Definition der Funktion zur Berechnung der Längen
    result_matrix = np.dot(a_matrix, positions_matrix)  # Matrixmultiplikation
    num_rows_result = result_matrix.shape[0] // 2  # Anzahl der Zeilen im Ergebnis durch 2 teilen
    pos_matrix_2_x_n = result_matrix.reshape(num_rows_result, 2)  # Umformen der Matrix in 2 Spalten
    return np.linalg.norm(pos_matrix_2_x_n, axis=1).reshape(-1, 1)  # Berechnung der euklidischen Norm und Umformen in Spaltenvektor

# Matrix für Verbindungen
a_matrix = np.array([
    [1, 0, -1, 0, 0, 0],  
    [0, 1, 0, -1, 0, 0],  
    [0, 0, 1, 0, -1, 0],  
    [0, 0, 0, 1, 0, -1]   
])

# Berechnung der Startlängen
P2_start = np.array([C_start[0] + radius * np.cos(theta_values[0]), 
                     C_start[1] + radius * np.sin(theta_values[0])])

positionen_punkte = [P0, P1, P2_start]

positions_matrix_start = np.vstack((positionen_punkte)).flatten().reshape(-1, 1)
start_laengen = berechne_laenge(a_matrix, positions_matrix_start)

# Minimierungsfunktion
def fehlerfunktion(positions, P2_new):
    positions_matrix = np.vstack((P0, positions.reshape(-1, 2), P2_new)).flatten().reshape(-1, 1)
    current_lengths = berechne_laenge(a_matrix, positions_matrix)
    return np.sum((current_lengths - start_laengen) ** 2)


############################################################################################

## Animation des Mechanismus ##

fig, ax = plt.subplots(figsize=(8, 6))
ax.set_xlabel('X-Koordinate')
ax.set_ylabel('Y-Koordinate')
ax.set_title('Animation des Mechanismus')
ax.grid(True)


# Linien und Punkte für die Animation
mechanismus, = ax.plot([], [], 'ro-', label='Mechanismus')
fixed_point, = ax.plot(C_start[0], C_start[1], 'bo', label='Fixpunkt C')
circle = plt.Circle(C_start, radius, color='b', fill=False, linestyle='--')
ax.add_patch(circle)


def update(frame):
    theta_new = theta_values[frame]

    # Berechnung der neuen Position von P2
    P2_new = np.array([C_start[0] + radius * np.cos(theta_new), 
                        C_start[1] + radius * np.sin(theta_new)])

    # Optimierung von P1
    initial_guess = P1.flatten()
    result = minimize(fehlerfunktion, initial_guess, args=(P2_new,), method='BFGS')
    optimized_positions = np.vstack((P0, result.x.reshape(-1, 2), P2_new))

    # Fenstergröße
    ax.set_xlim(-50, 20)
    ax.set_ylim(-20, 40)

    # Aktualisierung
    mechanismus.set_data(optimized_positions[:, 0], optimized_positions[:, 1])
    return mechanismus


animation_mechanik = animation.FuncAnimation(fig, update, frames=len(theta_values), interval=50, blit=False)


plt.legend()
plt.show()


