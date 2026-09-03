import pandas as pd
import numpy as np
from collections import defaultdict, deque

# === CARGA ===
df_comp = pd.read_csv('Drosophila_brain_model/Completeness_783.csv', index_col=0)
df_con  = pd.read_parquet('Drosophila_brain_model/Connectivity_783.parquet')

# IDs de entrada y salida (los que ya tienes)
lplc2 = set(np.load('lplc2_all.npy', allow_pickle=True).tolist())
lc4   = set(np.load('lc4_all.npy',   allow_pickle=True).tolist())
output_ids = np.load('output_ids.npy', allow_pickle=True).item()

inputs  = lplc2 | lc4
outputs = set()
for dn in ['DNp01', 'DNp02', 'DNp04', 'DNp11', 'DNa01', 'DNa02']:
    outputs |= set(output_ids[dn])

# Mapeo flywire id <-> brian index
flyid2i = {j: i for i, j in enumerate(df_comp.index)}
i2flyid = {i: j for j, i in flyid2i.items()}

# Índices de entrada/salida
input_idx  = set(flyid2i[i] for i in inputs  if i in flyid2i)
output_idx = set(flyid2i[i] for i in outputs if i in flyid2i)

print(f"Inputs (LPLC2+LC4): {len(input_idx)} neuronas")
print(f"Outputs (DNs):      {len(output_idx)} neuronas")

# === Filtrar conexiones débiles antes de nada ===
# Solo conexiones con peso significativo (ajusta el umbral)
MIN_SYN = 5   # mínimo de sinapsis para contar como conexión real

if 'Connectivity' in df_con.columns:
    strong = df_con[df_con['Connectivity'] >= MIN_SYN]
else:
    # si la columna se llama distinto, míralo
    print("Columnas:", df_con.columns.tolist())
    strong = df_con

pre_col  = strong['Presynaptic_Index'].values
post_col = strong['Postsynaptic_Index'].values

upstream = defaultdict(set)
downstream = defaultdict(set)
for pre, post in zip(pre_col, post_col):
    upstream[post].add(pre)
    downstream[pre].add(post)

def bfs(seeds, adjacency, max_hops):
    reached = set(seeds)
    frontier = set(seeds)
    for _ in range(max_hops):
        nf = set()
        for n in frontier:
            nf |= adjacency[n] - reached
        reached |= nf
        frontier = nf
    return reached

# Guarda las dos versiones
for hops, fname in [(1, 'subcircuit_440.npy'), (2, 'subcircuit_14k.npy')]:
    back = bfs(output_idx, upstream, hops)
    fwd  = bfs(input_idx, downstream, hops)
    included = (back & fwd) | input_idx | output_idx
    sub_flyids = [i2flyid[i] for i in included]
    np.save(fname, sub_flyids)
    print(f"{fname}: {len(sub_flyids)} neuronas")