import pandas as pd
import numpy as np

output_ids = np.load('output_ids.npy', allow_pickle=True).item()
conditions = ['dorsal_only', 'ventral_only', 'dual']
duration_s = 1.0
directional = ['DNp02', 'DNp04', 'DNp11']

print(f"{'Condición':<15} {'Neurona':<8} {'Hz medio':<12} {'± STD':<10} {'n'}")
print("-" * 55)

results = {}
results_std = {}

for cond in conditions:
    df = pd.read_parquet(f'results/experiment_syn/{cond}.parquet')
    n_trials = df['trial'].nunique()
    results[cond] = {}
    results_std[cond] = {}

    for neuron_type, ids in output_ids.items():
        if not ids:
            continue
        # Hz por trial: cuenta spikes de cada trial por separado
        per_trial = []
        for t in df['trial'].unique():
            sub = df[(df['trial'] == t) & (df['flywire_id'].isin(ids))]
            per_trial.append(len(sub) / (len(ids) * duration_s))
        mean_hz = np.mean(per_trial)
        std_hz  = np.std(per_trial)
        results[cond][neuron_type] = mean_hz
        results_std[cond][neuron_type] = std_hz
        print(f"{cond:<15} {neuron_type:<8} {mean_hz:<12.2f} {std_hz:<10.2f} {len(ids)}")
    print()

# === DIFERENCIACIÓN DIRECCIONAL con STD ===
print("=" * 55)
print("DIFERENCIACIÓN DIRECCIONAL (media ± std)")
print("=" * 55)
print(f"\n{'Neurona':<8} {'Dorsal':<16} {'Ventral':<16} {'Δ'}")
print("-" * 50)
for dn in directional:
    d  = results['dorsal_only'].get(dn, 0)
    ds = results_std['dorsal_only'].get(dn, 0)
    v  = results['ventral_only'].get(dn, 0)
    vs = results_std['ventral_only'].get(dn, 0)
    diff = abs(d - v)
    print(f"{dn:<8} {d:>6.1f} ± {ds:<6.1f}  {v:>6.1f} ± {vs:<6.1f}  {diff:.1f}")