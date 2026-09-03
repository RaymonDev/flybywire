import pandas as pd
import numpy as np
import time
import sys
sys.path.insert(0, 'Drosophila_brain_model')

from brian2 import prefs
prefs.codegen.target = 'cython'
prefs.codegen.cpp.extra_compile_args = ['-w', '-O3']

from brian2 import (NeuronGroup, Synapses, PoissonInput, SpikeMonitor,
                    Network, mV, ms, Hz, prefs)
# Add repo folder to sys.path and import model
sys.path.insert(0, './Drosophila_brain_model')
from Drosophila_brain_model.model import run_exp, default_params

params = default_params

# === Carga subcircuito recortado ===
comp_path = 'subcircuit_model/Completeness_sub.csv'
con_path  = 'subcircuit_model/Connectivity_sub.parquet'

df_comp = pd.read_csv(comp_path, index_col=0)
df_con  = pd.read_parquet(con_path)
N = len(df_comp)
print(f"Subcircuito: {N} neuronas, {len(df_con)} conexiones")

# === Construye la red UNA vez (esto es el overhead único) ===
print("Construyendo red (una sola vez)...")
t0 = time.time()

neu = NeuronGroup(
    N=N, model=params['eqs'], method='linear',
    threshold=params['eq_th'], reset=params['eq_rst'],
    refractory='rfc', namespace=params,
)
neu.v = params['v_0']
neu.g = 0
neu.rfc = params['t_rfc']

syn = Synapses(neu, neu, 'w : volt', on_pre='g += w', delay=params['t_dly'])
syn.connect(i=df_con['Presynaptic_Index'].values,
            j=df_con['Postsynaptic_Index'].values)
syn.w = df_con['Excitatory x Connectivity'].values * params['w_syn']

# Inputs dorsales para el test
sub_ids = set(np.load('subcircuit_440.npy', allow_pickle=True).tolist())
flyid2i = {fid: i for i, fid in enumerate(df_comp.index)}
lplc2_d = [i for i in np.load('lplc2_dorsal_syn.npy', allow_pickle=True).tolist() if i in sub_ids]
lc4_d   = [i for i in np.load('lc4_dorsal_syn.npy', allow_pickle=True).tolist() if i in sub_ids]
stim_idx = [flyid2i[i] for i in (lplc2_d + lc4_d)]

pois = []
for i in stim_idx:
    p = PoissonInput(target=neu[i], target_var='v', N=1,
                     rate=params['r_poi'], weight=params['w_syn']*params['f_poi'])
    neu[i].rfc = 0 * ms
    pois.append(p)

spk_mon = SpikeMonitor(neu)
net = Network(neu, syn, spk_mon, *pois)

# Fuerza la construcción/compilación corriendo 1ms
net.run(1 * ms)
build_time = time.time() - t0
print(f"Construcción + primera compilación: {build_time:.2f}s (ocurre 1 sola vez)\n")

# === Ahora mide avances cortos sobre la red YA construida ===
print("Midiendo avances por 'frame':")
for step_ms in [10, 20, 50]:
    # descarta el primer paso (aún puede tener overhead)
    net.run(step_ms * ms)
    # mide varios pasos y promedia
    times = []
    for _ in range(10):
        t = time.time()
        net.run(step_ms * ms)
        times.append(time.time() - t)
    avg = np.mean(times)
    ratio = (step_ms/1000) / avg
    fps = 1/avg
    print(f"  Avanzar {step_ms}ms → {avg*1000:.1f}ms de reloj "
          f"| ratio {ratio:.2f}x | ~{fps:.0f} pasos/seg")