import numpy as np
import pandas as pd
import copy
import sys

from pathlib import Path

# Add repo folder to sys.path and import model
sys.path.insert(0, './Drosophila_brain_model')
from Drosophila_brain_model.model import run_exp, default_params

# === CARGA ===
lplc2_dorsal  = np.load('lplc2_dorsal_syn.npy',  allow_pickle=True).tolist()
lplc2_ventral = np.load('lplc2_ventral_syn.npy', allow_pickle=True).tolist()
lc4_dorsal    = np.load('lc4_dorsal_syn.npy',     allow_pickle=True).tolist()
lc4_ventral   = np.load('lc4_ventral_syn.npy',    allow_pickle=True).tolist()
output_ids    = np.load('output_ids.npy', allow_pickle=True).item()

path_comp = 'Drosophila_brain_model/Completeness_783.csv'
path_con  = 'Drosophila_brain_model/Connectivity_783.parquet'

# ============================================================
# CONTROL 3 (primero, porque es rápido y no simula):
# Verificar conectividad estructural LPLC2/LC4 → DNp11 en el connectoma
# ============================================================
print("=" * 60)
print("CONTROL DE CONECTIVIDAD ESTRUCTURAL")
print("=" * 60)

df_comp = pd.read_csv(path_comp, index_col=0)
df_con  = pd.read_parquet(path_con)

# Mapeo flywire id -> brian index
flyid2i = {j: i for i, j in enumerate(df_comp.index)}

def count_synapses(source_ids, target_ids, label):
    """Cuenta sinapsis de source_ids -> target_ids en el connectoma."""
    src_idx = set(flyid2i[i] for i in source_ids if i in flyid2i)
    tgt_idx = set(flyid2i[i] for i in target_ids if i in flyid2i)

    mask = (df_con['Presynaptic_Index'].isin(src_idx) &
            df_con['Postsynaptic_Index'].isin(tgt_idx))
    sub = df_con[mask]
    n_syn = sub['Connectivity'].sum() if 'Connectivity' in sub.columns else len(sub)
    print(f"{label}: {len(sub)} conexiones, peso total = {n_syn:.0f}")
    return n_syn

dnp11 = output_ids['DNp11']
dnp04 = output_ids['DNp04']
dnp02 = output_ids['DNp02']

print("\n--- Proyección a DNp11 ---")
d11 = count_synapses(lplc2_dorsal + lc4_dorsal,  dnp11, "Dorsal  -> DNp11")
v11 = count_synapses(lplc2_ventral + lc4_ventral, dnp11, "Ventral -> DNp11")
print(f"Ratio dorsal/ventral hacia DNp11: {d11/max(v11,1):.2f}")

print("\n--- Proyección a DNp04 ---")
count_synapses(lplc2_dorsal + lc4_dorsal,  dnp04, "Dorsal  -> DNp04")
count_synapses(lplc2_ventral + lc4_ventral, dnp04, "Ventral -> DNp04")

print("\n--- Proyección a DNp02 ---")
count_synapses(lplc2_dorsal + lc4_dorsal,  dnp02, "Dorsal  -> DNp02")
count_synapses(lplc2_ventral + lc4_ventral, dnp02, "Ventral -> DNp02")

print("\nInterpretación: si dorsal->DNp11 tiene bastante más peso que")
print("ventral->DNp11, la asimetría funcional tiene base estructural real.")

# ============================================================
# CONTROL 2: intensidad igualada por submuestreo
# Igualamos nº de neuronas dorsal = ventral, con varias muestras
# aleatorias. Si DNp11 sigue diferenciando, es direccionalidad pura.
# ============================================================
print("\n" + "=" * 60)
print("CONTROL DE INTENSIDAD IGUALADA (submuestreo)")
print("=" * 60)

# Tamaño común = el menor de los dos grupos (dorsal vs ventral)
n_lplc2 = min(len(lplc2_dorsal), len(lplc2_ventral))
n_lc4   = min(len(lc4_dorsal),   len(lc4_ventral))
print(f"Submuestreando a {n_lplc2} LPLC2 y {n_lc4} LC4 por grupo")

path_res = './results/controls'
Path(path_res).mkdir(parents=True, exist_ok=True)

params = copy.deepcopy(default_params)
params['n_run'] = 10

N_SAMPLES = 3  # 3 submuestras aleatorias distintas

for s in range(N_SAMPLES):
    rng = np.random.default_rng(seed=s)
    d = (list(rng.choice(lplc2_dorsal,  n_lplc2, replace=False)) +
         list(rng.choice(lc4_dorsal,    n_lc4,   replace=False)))
    v = (list(rng.choice(lplc2_ventral, n_lplc2, replace=False)) +
         list(rng.choice(lc4_ventral,   n_lc4,   replace=False)))

    run_exp(exp_name=f'ctrl_dorsal_s{s}',  neu_exc=d, path_res=path_res,
            path_comp=path_comp, path_con=path_con, params=params,
            force_overwrite=True)
    run_exp(exp_name=f'ctrl_ventral_s{s}', neu_exc=v, path_res=path_res,
            path_comp=path_comp, path_con=path_con, params=params,
            force_overwrite=True)

# === Análisis del control de intensidad ===
print("\n" + "=" * 60)
print("RESULTADO: DNp11 con intensidad igualada")
print("=" * 60)
print(f"{'Muestra':<10} {'Dorsal':<12} {'Ventral':<12} {'Δ'}")
print("-" * 40)

deltas = []
for s in range(N_SAMPLES):
    d_df = pd.read_parquet(f'{path_res}/ctrl_dorsal_s{s}.parquet')
    v_df = pd.read_parquet(f'{path_res}/ctrl_ventral_s{s}.parquet')
    ids  = output_ids['DNp11']

    hz_d = len(d_df[d_df['flywire_id'].isin(ids)]) / (len(ids) * d_df['trial'].nunique())
    hz_v = len(v_df[v_df['flywire_id'].isin(ids)]) / (len(ids) * v_df['trial'].nunique())
    delta = hz_d - hz_v
    deltas.append(delta)
    print(f"s{s:<9} {hz_d:<12.1f} {hz_v:<12.1f} {delta:.1f}")

mean_delta = np.mean(deltas)
print("-" * 40)
print(f"Δ medio: {mean_delta:.1f} Hz")
print()
if mean_delta > 30:
    print("→ DIRECCIONALIDAD PURA: la diferencia persiste con intensidad igualada.")
elif mean_delta > 10:
    print("→ Direccionalidad parcial: hay señal pero parte era intensidad.")
else:
    print("→ EFECTO DE INTENSIDAD: la diferencia desaparece al igualar. No es direccional.")