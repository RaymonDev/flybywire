import pandas as pd
import numpy as np
import ast

# === CARGA ===
visual  = pd.read_csv('visual_neuron_types.csv')
classif = pd.read_csv('classification.csv')
coords  = pd.read_csv('coordinates.csv')
types   = pd.read_csv('consolidated_cell_types.csv')

# Mira las columnas nada más cargar — dímelas si algo no encaja
print("Visual cols:  ", visual.columns.tolist())
print("Classif cols: ", classif.columns.tolist())
print("Coords cols:  ", coords.columns.tolist())
print("Types cols:   ", types.columns.tolist())

# === LPLC2 y LC4 — desde Visual Neuron Annotations ===
lplc2 = visual[visual['type'] == 'LPLC2']['root_id'].tolist()
lc4   = visual[visual['type'] == 'LC4']['root_id'].tolist()

print(f"\nLPLC2: {len(lplc2)} neuronas")
print(f"LC4:   {len(lc4)} neuronas")

# === DNs de output — desde Cell Types ===
# Primero mira qué columnas tiene ese archivo
print("\nPrimeras filas de Cell Types:")
print(types.head(10).to_string())

dn_targets = ['DNp01', 'DNp02', 'DNp04', 'DNp11', 'DNa01', 'DNa02']
output_ids = {}

for dn in dn_targets:
    # Busca en todas las columnas string del archivo
    found = set()
    for col in types.select_dtypes(include=['object', 'string']).columns:
        matches = types[types[col].str.contains(dn, na=False)]['root_id'].tolist()
        found.update(matches)
    # También busca en visual por si acaso
    found.update(visual[visual['type'] == dn]['root_id'].tolist())
    output_ids[dn] = list(found)
    print(f"{dn}: {len(output_ids[dn])} neuronas")

# === COORDENADAS — parsear la columna position ===
# La columna position es un string tipo "[x, y, z]", hay que parsearlo
def parse_pos(s):
    try:
        if isinstance(s, (list, tuple, np.ndarray)):
            return list(s)
        # Soporta tanto [1 2 3] (separado por espacios) como [1, 2, 3] (separado por comas)
        clean = str(s).replace('[', '').replace(']', '').replace(',', ' ')
        parts = [float(x) for x in clean.split() if x.strip()]
        if len(parts) == 3:
            return parts
        return [None, None, None]
    except:
        return [None, None, None]

coords[['x', 'y', 'z']] = pd.DataFrame(
    coords['position'].apply(parse_pos).tolist(),
    index=coords.index
)

# === SEPARAR LPLC2 DORSAL / VENTRAL por coordenada Y ===
lplc2_coords = coords[coords['root_id'].isin(lplc2)].copy()
lplc2_coords = lplc2_coords.dropna(subset=['y'])

# Agrupa por root_id y coge la Y media (puede haber varias entradas por neurona)
lplc2_mean_y = lplc2_coords.groupby('root_id')['y'].mean()

median_y = lplc2_mean_y.median()
print(f"\nMediana Y de LPLC2: {median_y:.0f} nm")

dorsal  = lplc2_mean_y[lplc2_mean_y < median_y].index.tolist()
ventral = lplc2_mean_y[lplc2_mean_y >= median_y].index.tolist()

print(f"LPLC2 dorsales:  {len(dorsal)}")
print(f"LPLC2 ventrales: {len(ventral)}")

# === SEPARAR LC4 DORSAL / VENTRAL por coordenada Y ===
lc4_coords = coords[coords['root_id'].isin(lc4)].copy()
lc4_coords = lc4_coords.dropna(subset=['y'])
lc4_mean_y = lc4_coords.groupby('root_id')['y'].mean()

median_y_lc4 = lc4_mean_y.median()
print(f"\nMediana Y de LC4: {median_y_lc4:.0f} nm")

lc4_dorsal  = lc4_mean_y[lc4_mean_y < median_y_lc4].index.tolist()
lc4_ventral = lc4_mean_y[lc4_mean_y >= median_y_lc4].index.tolist()

print(f"LC4 dorsales:  {len(lc4_dorsal)}")
print(f"LC4 ventrales: {len(lc4_ventral)}")

# === GUARDAR ===
np.save('lplc2_dorsal.npy',  dorsal)
np.save('lplc2_ventral.npy', ventral)
np.save('lplc2_all.npy',     lplc2)
np.save('lc4_all.npy',       lc4)
np.save('lc4_dorsal.npy',    lc4_dorsal)
np.save('lc4_ventral.npy',   lc4_ventral)
np.save('output_ids.npy',    output_ids)

print("\nArchivos guardados.")