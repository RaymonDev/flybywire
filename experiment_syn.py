import numpy as np
import copy
import sys

from pathlib import Path

# Add repo folder to sys.path and import model
sys.path.insert(0, './Drosophila_brain_model')
from Drosophila_brain_model.model import run_exp, default_params

# === SPLIT POR SINAPSIS ===
lplc2_dorsal  = np.load('lplc2_dorsal_syn.npy',  allow_pickle=True).tolist()
lplc2_ventral = np.load('lplc2_ventral_syn.npy', allow_pickle=True).tolist()
lc4_dorsal    = np.load('lc4_dorsal_syn.npy',     allow_pickle=True).tolist()
lc4_ventral   = np.load('lc4_ventral_syn.npy',    allow_pickle=True).tolist()

path_res  = './results/experiment_syn'
path_comp = './Drosophila_brain_model/Completeness_783.csv'
path_con  = './Drosophila_brain_model/Connectivity_783.parquet'
Path(path_res).mkdir(parents=True, exist_ok=True)

params = copy.deepcopy(default_params)
params['n_run'] = 30

CONDITIONS = {
    'dorsal_only'  : lplc2_dorsal + lc4_dorsal,
    'ventral_only' : lplc2_ventral + lc4_ventral,
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
        n_proc          = 12,
        force_overwrite = True,
    )

print("\nExperimento con split por sinapsis completado.")