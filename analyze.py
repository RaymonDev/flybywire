import pandas as pd
import numpy as np

output_ids = np.load('output_ids.npy', allow_pickle=True).item()

conditions = ['dorsal_only', 'ventral_only', 'dual']
duration_s = 1.0   # t_run por defecto = 1000ms; cámbialo si reduces t_run

# Neuronas de dirección que nos interesan especialmente
directional = ['DNp02', 'DNp04', 'DNp11']

print(f"{'Condición':<15} {'Neurona':<8} {'Hz medio':<12} {'n neuronas'}")
print("-" * 50)

results = {}

for cond in conditions:
    df = pd.read_parquet(f'results/experiment_lc4/{cond}.parquet')
    n_trials = df['trial'].nunique()
    results[cond] = {}

    for neuron_type, ids in output_ids.items():
        if not ids:
            continue
        spikes  = df[df['flywire_id'].isin(ids)]
        mean_hz = len(spikes) / (len(ids) * n_trials * duration_s)
        results[cond][neuron_type] = mean_hz
        print(f"{cond:<15} {neuron_type:<8} {mean_hz:<12.2f} {len(ids)}")
    print()

# === ANÁLISIS DIRECCIONAL ===
print("=" * 50)
print("ANÁLISIS DE DIFERENCIACIÓN DIRECCIONAL")
print("=" * 50)
print("\nHipótesis: amenaza dorsal y ventral deberían activar")
print("DNs de dirección distintos (DNp11 vs DNp02/04)\n")

print(f"{'Neurona':<8} {'Dorsal':<10} {'Ventral':<10} {'¿Diferencia?'}")
print("-" * 45)
for dn in directional:
    d = results['dorsal_only'].get(dn, 0)
    v = results['ventral_only'].get(dn, 0)
    diff = abs(d - v)
    marca = "SÍ" if diff > 20 else "no"
    print(f"{dn:<8} {d:<10.1f} {v:<10.1f} {marca} (Δ={diff:.1f})")

print("\n" + "=" * 50)
print("INTEGRACIÓN DUAL")
print("=" * 50)
print(f"\n{'Neurona':<8} {'Dorsal':<9} {'Ventral':<9} {'Dual':<9} {'Tipo'}")
print("-" * 50)
for dn in directional + ['DNp01']:
    d = results['dorsal_only'].get(dn, 0)
    v = results['ventral_only'].get(dn, 0)
    dual = results['dual'].get(dn, 0)
    maxi = max(d, v)
    if dual > maxi * 1.2:
        tipo = "superaditivo"
    elif dual < min(d, v) * 0.8:
        tipo = "supresión"
    else:
        tipo = "intermedio"
    print(f"{dn:<8} {d:<9.1f} {v:<9.1f} {dual:<9.1f} {tipo}")