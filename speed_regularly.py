import pandas as pd
import numpy as np
import time
import sys
sys.path.insert(0, 'Drosophila_brain_model')

from brian2 import (NeuronGroup, Synapses, PoissonInput, SpikeMonitor,
                    Network, mV, ms, Hz, prefs)
prefs.codegen.target = 'cython'

# Add repo folder to sys.path and import model
sys.path.insert(0, './Drosophila_brain_model')
from Drosophila_brain_model.model import run_exp, default_params

params = default_params

df_comp = pd.read_csv('subcircuit_model/Completeness_sub.csv', index_col=0)
df_con  = pd.read_parquet('subcircuit_model/Connectivity_sub.parquet')
N = len(df_comp)
print(f"Subcircuito: {N} neuronas, {len(df_con)} conexiones")

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

# === Corre 1 segundo de un tirón y mide ===
print("Corriendo 1000ms de un tirón (sin parar/rearrancar)...")
net.run(10 * ms)  # warmup + compilación
t0 = time.time()
net.run(1000 * ms)
wall = time.time() - t0
ratio = 1.0 / wall
print(f"\n1000ms biológicos de un tirón → {wall:.3f}s de reloj")
print(f"Ratio tiempo-real: {ratio:.2f}x")
print(f"Spikes totales registrados: {len(spk_mon.t)}")

if ratio >= 1:
    print("\n✓ TIEMPO REAL posible si se corre de forma continua.")
    print("  El overhead estaba en parar/rearrancar, no en el cómputo.")
else:
    print(f"\n✗ Ni de un tirón llega a tiempo real ({ratio:.2f}x).")
    print("  El cómputo puro es el límite. → 3 FPS o tabla.")