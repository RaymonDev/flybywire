import pandas as pd
import numpy as np

# === CARGA IDs ===
visual = pd.read_csv('visual_neuron_types.csv')
lplc2 = set(visual[visual['type'] == 'LPLC2']['root_id'].tolist())
lc4   = set(visual[visual['type'] == 'LC4']['root_id'].tolist())

print(f"LPLC2: {len(lplc2)} neuronas objetivo")
print(f"LC4:   {len(lc4)} neuronas objetivo")

# === CARGA SINAPSIS STREAMING ===
# synapse_coordinates.csv omite pre/post_root_id cuando no cambian respecto a la fila anterior (formato sparse)
# y los IDs son enteros de 18 dígitos que perderían precisión si se leen como float64.
print("\nCargando sinapsis mediante streaming (línea a línea con forward-fill)...")

lplc2_y = {}  # root_id -> lista de coordenadas Y
lc4_y   = {}

cur_pre  = None
cur_post = None
total_synapses = 0

with open('synapse_coordinates.csv', 'r') as f:
    header = f.readline()
    for line in f:
        total_synapses += 1
        parts = line.strip().split(',')
        if len(parts) < 5:
            continue
        pre, post, x, y, z = parts[0], parts[1], parts[2], parts[3], parts[4]
        if pre:
            cur_pre = int(pre)
        if post:
            cur_post = int(post)

        if cur_post in lplc2:
            lplc2_y.setdefault(cur_post, []).append(int(y))
        elif cur_post in lc4:
            lc4_y.setdefault(cur_post, []).append(int(y))

print(f"Procesadas {total_synapses:,} sinapsis.")

def split_by_input_synapses(syn_dict, neuron_ids, name):
    """Clasifica neuronas dorsal/ventral por el centroide Y de sus
    sinapsis de ENTRADA (donde la neurona es postsináptica)."""
    total_input_syn = sum(len(v) for v in syn_dict.values())
    print(f"\n{name}: {total_input_syn:,} sinapsis de entrada en {len(syn_dict)}/{len(neuron_ids)} neuronas")

    # Centroide Y de las sinapsis de entrada de cada neurona
    centroid_y = pd.Series({nid: np.mean(ys) for nid, ys in syn_dict.items()})

    median_y = centroid_y.median()
    print(f"{name}: mediana del centroide Y = {median_y:.0f} nm")

    dorsal  = centroid_y[centroid_y < median_y].index.tolist()
    ventral = centroid_y[centroid_y >= median_y].index.tolist()

    print(f"{name} dorsales:  {len(dorsal)}")
    print(f"{name} ventrales: {len(ventral)}")

    return dorsal, ventral

# === GUARDA LOS CENTROIDES ===
# structural_analysis.py los reutiliza para el analisis de sensibilidad al
# umbral sin tener que volver a leer los 824 MB de sinapsis.
centroids = {nid: float(np.mean(ys)) for d in (lplc2_y, lc4_y)
             for nid, ys in d.items()}
np.save('synapse_centroids.npy', centroids)
print(f"Centroides guardados: {len(centroids)} neuronas -> synapse_centroids.npy")

# === SPLIT POR SINAPSIS ===
lplc2_d, lplc2_v = split_by_input_synapses(lplc2_y, lplc2, 'LPLC2')
lc4_d,   lc4_v   = split_by_input_synapses(lc4_y,   lc4,   'LC4')

# === GUARDAR (con sufijo _syn para no pisar los del soma) ===
np.save('lplc2_dorsal_syn.npy',  lplc2_d)
np.save('lplc2_ventral_syn.npy', lplc2_v)
np.save('lc4_dorsal_syn.npy',    lc4_d)
np.save('lc4_ventral_syn.npy',   lc4_v)

print("\nSplit por sinapsis guardado.")

# === COMPARACIÓN CON EL SPLIT POR SOMA ===
print("\n" + "=" * 50)
print("¿Cuánto cambia respecto al split por soma?")

for name, new_d, old_file in [('LPLC2', lplc2_d, 'lplc2_dorsal.npy'), ('LC4', lc4_d, 'lc4_dorsal.npy')]:
    try:
        old_d = set(np.load(old_file, allow_pickle=True).tolist())
        new_d_set = set(new_d)
        overlap = len(old_d & new_d_set)
        pct = (overlap / len(old_d)) * 100 if len(old_d) > 0 else 0
        print(f"\n{name} dorsal: {overlap}/{len(old_d)} ({pct:.1f}%) coinciden entre soma y sinapsis")
        if overlap < len(old_d) * 0.8:
            print(f"-> Los metodos difieren para {name}. El split por sinapsis puede cambiar el resultado.")
        else:
            print(f"-> Los metodos coinciden mucho para {name}.")
    except FileNotFoundError:
        print(f"(No se encontró {old_file} para comparar)")