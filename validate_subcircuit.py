import pandas as pd
import numpy as np
import copy
import sys
from pathlib import Path



# Add repo folder to sys.path and import model
sys.path.insert(0, './Drosophila_brain_model')
from Drosophila_brain_model.model import run_exp, default_params

# === Elige qué subcircuito validar ===
SUBCIRCUIT = sys.argv[1] if len(sys.argv) > 1 else 'subcircuit_440.npy'
print(f"Validando: {SUBCIRCUIT}")

sub_ids = set(np.load(SUBCIRCUIT, allow_pickle=True).tolist())

# === Carga connectome completo ===
df_comp = pd.read_csv('Drosophila_brain_model/Completeness_783.csv', index_col=0)
df_con  = pd.read_parquet('Drosophila_brain_model/Connectivity_783.parquet')

# === Filtra completeness al subcircuito ===
df_comp_sub = df_comp[df_comp.index.isin(sub_ids)].copy()
print(f"Neuronas en subcircuito: {len(df_comp_sub)}")

# El modelo indexa por posición en df_comp. Al recortar, los índices
# Presynaptic_Index / Postsynaptic_Index del df_con viejo ya no valen:
# apuntan a posiciones del connectome completo. Hay que remapear.

# Mapeo: flywire_id -> nuevo índice (0..N-1) en el subcircuito
old_flyids = df_comp.index.tolist()
new_flyid_list = df_comp_sub.index.tolist()
new_pos = {fid: i for i, fid in enumerate(new_flyid_list)}

# El df_con usa índices del completo; conviértelos a flywire_id primero
old_i2flyid = {i: fid for i, fid in enumerate(old_flyids)}

# Filtra conexiones: solo las que van entre neuronas del subcircuito
pre_fly  = df_con['Presynaptic_Index'].map(old_i2flyid)
post_fly = df_con['Postsynaptic_Index'].map(old_i2flyid)
mask = pre_fly.isin(sub_ids) & post_fly.isin(sub_ids)
df_con_sub = df_con[mask].copy()

# Remapea a los nuevos índices
df_con_sub['Presynaptic_Index']  = pre_fly[mask].map(new_pos).values
df_con_sub['Postsynaptic_Index'] = post_fly[mask].map(new_pos).values

print(f"Conexiones en subcircuito: {len(df_con_sub)} "
      f"(de {len(df_con)} totales)")

# === Guarda los archivos recortados ===
Path('subcircuit_model').mkdir(exist_ok=True)
comp_path = 'subcircuit_model/Completeness_sub.csv'
con_path  = 'subcircuit_model/Connectivity_sub.parquet'
df_comp_sub.to_csv(comp_path)
df_con_sub.to_parquet(con_path)

# === Carga IDs de input/output (split por sinapsis) ===
lplc2_d = np.load('lplc2_dorsal_syn.npy', allow_pickle=True).tolist()
lplc2_v = np.load('lplc2_ventral_syn.npy', allow_pickle=True).tolist()
lc4_d   = np.load('lc4_dorsal_syn.npy', allow_pickle=True).tolist()
lc4_v   = np.load('lc4_ventral_syn.npy', allow_pickle=True).tolist()

# Solo los que sobrevivieron al subcircuito
lplc2_d = [i for i in lplc2_d if i in sub_ids]
lplc2_v = [i for i in lplc2_v if i in sub_ids]
lc4_d   = [i for i in lc4_d if i in sub_ids]
lc4_v   = [i for i in lc4_v if i in sub_ids]
print(f"Inputs sobrevivientes: dorsal {len(lplc2_d)+len(lc4_d)}, "
      f"ventral {len(lplc2_v)+len(lc4_v)}")

# === Corre las 3 condiciones en el subcircuito ===
params = copy.deepcopy(default_params)
params['n_run'] = 10

path_res = './results/subcircuit_val'
Path(path_res).mkdir(parents=True, exist_ok=True)

conditions = {
    'dorsal_only'  : lplc2_d + lc4_d,
    'ventral_only' : lplc2_v + lc4_v,
    'dual'         : lplc2_d + lplc2_v + lc4_d + lc4_v,
}

for name, neurons in conditions.items():
    run_exp(
        exp_name=name, neu_exc=neurons,
        path_res=path_res, path_comp=comp_path, path_con=con_path,
        params=params, n_proc=8, force_overwrite=True,
    )

# === Compara con el cerebro completo ===
# Se comparan TODAS las DNs monitorizadas, no solo las que coinciden.
# La version anterior de este script solo mostraba DNp11/DNp04/DNp02 y
# describia el resultado como "reproduce el cerebro completo casi exactamente".
# Eso era cherry-picking: DNa01 y DNa02 no se reproducen en absoluto.
output_ids = np.load('output_ids.npy', allow_pickle=True).item()
DN_ALL = ['DNp01', 'DNp02', 'DNp04', 'DNp11', 'DNa01', 'DNa02']


def hz(path, ids):
    """Tasa media (Hz) por neurona y trial, con t_run = 1000 ms."""
    df = pd.read_parquet(path)
    return len(df[df['flywire_id'].isin(ids)]) / (len(ids) * df['trial'].nunique())


print("
" + "=" * 74)
print("SUBCIRCUITO vs CEREBRO COMPLETO - todas las DNs monitorizadas")
print("=" * 74)
print(f"{'neurona':<9}{'condicion':<15}{'completo':>11}{'sub':>11}{'error':>11}")
print("-" * 74)

broken = []
for cond in ['dorsal_only', 'ventral_only', 'dual']:
    full_f = f'./results/experiment_syn/{cond}.parquet'
    sub_f = f'{path_res}/{cond}.parquet'
    if not (Path(full_f).exists() and Path(sub_f).exists()):
        print(f"  ({cond}: falta un fichero, se omite)")
        continue
    for dn in DN_ALL:
        ids = output_ids[dn]
        f, s = hz(full_f, ids), hz(sub_f, ids)
        err = s - f
        rel = abs(err) / f * 100 if f > 0.5 else float('inf')
        flag = '   <-- NO se reproduce' if rel > 25 else ''
        if rel > 25:
            broken.append((dn, cond))
        print(f"{dn:<9}{cond:<15}{f:>11.1f}{s:>11.1f}{err:>+11.1f}{flag}")

print()
if broken:
    print("El subcircuito NO reproduce el cerebro completo para:")
    for dn, cond in broken:
        print(f"  - {dn} en {cond}")
    print()
    print("Las DNp (escape) se conservan; las DNa (giro) no. El subcircuito de")
    print("440 neuronas descarta la inhibicion de todo el cerebro, que es")
    print("precisamente lo que suprime las DNa bajo amenaza dual. Por tanto la")
    print("reduccion es valida para el eje de escape y NO para el de giro.")
else:
    print("Todas las DNs monitorizadas se reproducen dentro del 25%.")
