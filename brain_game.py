import pandas as pd
import numpy as np
import sys
sys.path.insert(0, 'Drosophila_brain_model')

from brian2 import (NeuronGroup, Synapses, SpikeMonitor, Network,
                    mV, ms, Hz, prefs, PoissonGroup)
prefs.codegen.target = 'cython'
from model import default_params


class BrainEngine:
    """
    Wrapper del subcircuito de escape que corre de forma continua.
    Permite ajustar la estimulación dorsal/ventral en vivo y leer
    las tasas de disparo recientes de las DNs.
    """

    def __init__(self,
                 comp_path='subcircuit_model/Completeness_sub.csv',
                 con_path='subcircuit_model/Connectivity_sub.parquet',
                 sub_ids_path='subcircuit_440.npy'):
        p = default_params
        self.p = p

        df_comp = pd.read_csv(comp_path, index_col=0)
        df_con  = pd.read_parquet(con_path)
        self.N = len(df_comp)
        self.flyid2i = {fid: i for i, fid in enumerate(df_comp.index)}

        # --- Neuronas ---
        neu = NeuronGroup(
            N=self.N, model=p['eqs'], method='linear',
            threshold=p['eq_th'], reset=p['eq_rst'],
            refractory='rfc', namespace=p,
        )
        neu.v = p['v_0']; neu.g = 0; neu.rfc = p['t_rfc']

        # --- Sinapsis ---
        syn = Synapses(neu, neu, 'w : volt', on_pre='g += w', delay=p['t_dly'])
        syn.connect(i=df_con['Presynaptic_Index'].values,
                    j=df_con['Postsynaptic_Index'].values)
        syn.w = df_con['Excitatory x Connectivity'].values * p['w_syn']

        # --- Grupos de estimulación (dorsal y ventral por separado) ---
        # Usamos PoissonGroup con rate ajustable en vivo
        sub_ids = set(np.load(sub_ids_path, allow_pickle=True).tolist())
        def idxs(fname):
            return [self.flyid2i[i]
                    for i in np.load(fname, allow_pickle=True).tolist()
                    if i in sub_ids]

        self.dorsal_idx  = idxs('lplc2_dorsal_syn.npy') + idxs('lc4_dorsal_syn.npy')
        self.ventral_idx = idxs('lplc2_ventral_syn.npy') + idxs('lc4_ventral_syn.npy')

        # PoissonGroups cuyo rate podemos cambiar en tiempo real
        self.pg_dorsal  = PoissonGroup(len(self.dorsal_idx),  rates=0*Hz)
        self.pg_ventral = PoissonGroup(len(self.ventral_idx), rates=0*Hz)

        syn_d = Synapses(self.pg_dorsal, neu, on_pre='v_post += {}*mV'.format(
            float(p['w_syn']*p['f_poi']/mV)))
        syn_d.connect(i=range(len(self.dorsal_idx)), j=self.dorsal_idx)

        syn_v = Synapses(self.pg_ventral, neu, on_pre='v_post += {}*mV'.format(
            float(p['w_syn']*p['f_poi']/mV)))
        syn_v.connect(i=range(len(self.ventral_idx)), j=self.ventral_idx)

        # Quita refractariedad de las neuronas estimuladas
        for i in self.dorsal_idx + self.ventral_idx:
            neu.rfc[i] = 0 * ms

        # --- Monitor de spikes de las DNs ---
        output_ids = np.load('output_ids.npy', allow_pickle=True).item()
        self.dn_idx = {}
        for dn in ['DNp01', 'DNp02', 'DNp04', 'DNp11']:
            self.dn_idx[dn] = [self.flyid2i[i] for i in output_ids[dn]
                               if i in sub_ids]

        self.spk_mon = SpikeMonitor(neu)
        self.net = Network(neu, syn, self.pg_dorsal, self.pg_ventral,
                           syn_d, syn_v, self.spk_mon)
        self.neu = neu

        # warmup / compilación
        self.net.run(1 * ms)
        self._last_count = {dn: 0 for dn in self.dn_idx}
        self._last_t = float(self.net.t / ms)

    def set_stimulation(self, freq_dorsal, freq_ventral):
        """Ajusta las frecuencias de estimulación (Hz)."""
        self.pg_dorsal.rates  = freq_dorsal * Hz
        self.pg_ventral.rates = freq_ventral * Hz

    def step(self, dt_ms):
        """Avanza la simulación dt_ms y devuelve tasas de las DNs (Hz)."""
        self.net.run(dt_ms * ms)
        now = float(self.net.t / ms)
        window_s = (now - self._last_t) / 1000.0
        rates = {}
        # cuenta spikes de cada DN en la ventana recién simulada
        all_i = np.array(self.spk_mon.i)
        all_t = np.array(self.spk_mon.t / ms)
        recent = all_t > self._last_t
        for dn, idxs in self.dn_idx.items():
            n_spk = np.isin(all_i[recent], idxs).sum()
            rates[dn] = n_spk / (len(idxs) * window_s) if window_s > 0 else 0.0
        self._last_t = now
        return rates


if __name__ == '__main__':
    # test rápido
    import time
    print("Construyendo BrainEngine...")
    brain = BrainEngine()
    print("Listo. Probando estimulación dorsal...")

    brain.set_stimulation(freq_dorsal=150, freq_ventral=0)
    t0 = time.time()
    for _ in range(5):
        rates = brain.step(50)
        print(f"  DNp11={rates['DNp11']:.0f}  DNp04={rates['DNp04']:.0f}  "
              f"DNp02={rates['DNp02']:.0f}  DNp01={rates['DNp01']:.0f}")
    print(f"5 pasos de 50ms en {time.time()-t0:.2f}s")