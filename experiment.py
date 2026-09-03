import numpy as np
import copy
import sys
from pathlib import Path
import winsound
import time

# Add repo folder to sys.path and import model
sys.path.insert(0, './Drosophila_brain_model')
from Drosophila_brain_model.model import run_exp, default_params

# === CARGA DE IDs ===
lplc2_dorsal  = np.load('lplc2_dorsal.npy',  allow_pickle=True).tolist()
lplc2_ventral = np.load('lplc2_ventral.npy', allow_pickle=True).tolist()
lc4_dorsal    = np.load('lc4_dorsal.npy',     allow_pickle=True).tolist()
lc4_ventral   = np.load('lc4_ventral.npy',    allow_pickle=True).tolist()

# === PATHS ===
path_res  = './results/experiment_lc4'
path_comp = './Drosophila_brain_model/Completeness_783.csv'
path_con  = './Drosophila_brain_model/Connectivity_783.parquet'
Path(path_res).mkdir(parents=True, exist_ok=True)

# === PARAMS ===
params = copy.deepcopy(default_params)
params['n_run'] = 10   # sube a 30 para el resultado final

# === CONDICIONES ===
# Cada amenaza combina LPLC2 + LC4 de la misma región,
# porque el circuito direccional necesita LC4 para activar DNp02/DNp11
CONDITIONS = {
    # Amenaza solo arriba (dorsal): LPLC2 + LC4 dorsales
    'dorsal_only'  : lplc2_dorsal + lc4_dorsal,
    # Amenaza solo abajo (ventral): LPLC2 + LC4 ventrales
    'ventral_only' : lplc2_ventral + lc4_ventral,
    # Amenaza simultánea arriba y abajo: todo
    'dual'         : lplc2_dorsal + lplc2_ventral + lc4_dorsal + lc4_ventral,
}

for name, neurons in CONDITIONS.items():
    run_exp(
        exp_name        = name,
        neu_exc         = neurons,
        path_res        = path_res,
        path_comp       = path_comp,
        path_con        = path_con,
        params          = params,
        force_overwrite = True,
    )

print("\nExperimento LC4 completado.")

# === SONIDO DE ALERTA AL TERMINAR ===
for freq in [600, 800, 1000, 1200, 1500, 1800, 2000]:
    try:
        winsound.Beep(freq, 250)
        time.sleep(0.05)
    except Exception:
        print('\a', end='', flush=True)