import numpy as np

# --- Anclas del mapeo (declaradas explícitamente, ver README) ---
# El umbral de tamaño angular publicado (~40°) se mapea a 150 Hz,
# la tasa usada en todos los experimentos validados.
THETA_REF = 40.0     # grados
FREQ_MAX  = 150.0    # Hz
FREQ_REF  = 150.0    # Hz a THETA_REF


def angular_size(segment_height, distance):
    """Ángulo subtendido (grados) por un segmento de pared a cierta distancia."""
    if distance <= 1:
        distance = 1
    return np.degrees(2 * np.arctan((segment_height / 2) / distance))


def theta_to_freq(theta):
    """Convierte tamaño angular a frecuencia de estimulación (Hz).
    Lineal hasta el umbral, saturando en FREQ_MAX."""
    freq = FREQ_REF * (theta / THETA_REF)
    return float(np.clip(freq, 0, FREQ_MAX))


def game_state_to_stimulation(game):
    pipe = game.nearest_pipe()
    if pipe is None:
        return 0.0, 0.0

    gap_top    = pipe['gap_center'] - game.gap/2   # borde inferior del tubo de arriba
    gap_bottom = pipe['gap_center'] + game.gap/2   # borde superior del tubo de abajo

    # distancia del fly a cada pared real
    dist_to_upper_wall = game.fly_y - gap_top      # si <0, está metido en zona segura arriba
    dist_to_lower_wall = gap_bottom - game.fly_y

    # amenaza dorsal: crece cuanto más cerca (o dentro) de la pared de arriba
    # amenaza ventral: crece cuanto más cerca de la pared de abajo
    def threat(dist):
        # dist grande = pared lejos = poca amenaza; dist pequeña/negativa = mucha
        return float(np.clip((80 - dist) / 80, 0, 1)) * 150

    freq_dorsal  = threat(dist_to_upper_wall)   # cerca de pared arriba → baja
    freq_ventral = threat(dist_to_lower_wall)   # cerca de pared abajo → sube

    return freq_dorsal, freq_ventral


def _proximity_weight(dist, H):
    """Peso 1 si el fly está pegado al segmento, decae con la distancia."""
    return float(np.clip(1.0 - dist / (H / 2), 0.1, 1.0))


def dn_response_to_force(rates, gain=0.13, max_force=3.5):
    dnp11 = rates.get('DNp11', 0)
    dnp02 = rates.get('DNp02', 0)

    # normaliza cada uno por su máximo real observado
    d11_norm = dnp11 / 110.0   # DNp11 llega alto
    d02_norm = dnp02 / 90.0    # DNp02 llega más bajo

    force = gain * (d11_norm - d02_norm) * 100
    # limita la fuerza para evitar saltos bruscos
    force = float(np.clip(force, -max_force, max_force))
    return force