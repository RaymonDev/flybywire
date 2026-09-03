import pandas as pd
import numpy as np
import copy
import time
import sys
from pathlib import Path

# Add repo folder to sys.path and import model
sys.path.insert(0, './Drosophila_brain_model')
from Drosophila_brain_model.model import run_exp, default_params

# Usa el subcircuito de 440 ya recortado por validate_subcircuit.py
comp_path = 'subcircuit_model/Completeness_sub.csv'
con_path  = 'subcircuit_model/Connectivity_sub.parquet'

# Inputs dorsales (los que sobrevivieron)
sub_ids = set(np.load('subcircuit_440.npy', allow_pickle=True).tolist())
lplc2_d = [i for i in np.load('lplc2_dorsal_syn.npy', allow_pickle=True).tolist() if i in sub_ids]
lc4_d   = [i for i in np.load('lc4_dorsal_syn.npy', allow_pickle=True).tolist() if i in sub_ids]
stim = lplc2_d + lc4_d

# Simula ventanas cortas y mide el tiempo de reloj
Path('./results/speedtest').mkdir(parents=True, exist_ok=True)

for t_ms in [50, 100, 200]:
    params = copy.deepcopy(default_params)
    params['n_run'] = 1
    from brian2 import ms
    params['t_run'] = t_ms * ms

    start = time.time()
    run_exp(
        exp_name=f'speed_{t_ms}', neu_exc=stim,
        path_res='./results/speedtest', path_comp=comp_path, path_con=con_path,
        params=params, n_proc=1, force_overwrite=True,
    )
    wall = time.time() - start
    ratio = (t_ms/1000) / wall
    print(f"\n>>> Simular {t_ms}ms biológicos tardó {wall:.3f}s de reloj")
    print(f"    Ratio tiempo-real: {ratio:.2f}x "
          f"({'TIEMPO REAL OK' if ratio >= 1 else 'más lento que tiempo real'})")