"""
example_full_pipeline_v4.py

Simulacion + validacion + kernel + CDM para UNA configuracion de parametros.

Disenado para SLURM array jobs: cada job ejecuta una sola configuracion
con N trials. Los parametros se pasan por linea de comandos.

Estructura de guardado:
    save_path/
        <J_EE>_<J_IE>_<J_EI>_<J_II>_<tau_syn_E>_<tau_syn_I>_<J_ext>/
            valid_trial_0.pkl
            novalid_trial_1.pkl
            ...

Uso:
    python example_full_pipeline_v4.py \
        --J_EE 0.5 --J_IE 0.5 --J_EI -23.84 --J_II -8.441 \
        --tau_syn_E 0.5 --tau_syn_I 0.5 --J_ext 28.89 \
        --save-path /path/to/results
"""

import sys
import os
import pickle
import argparse
import shutil
import numpy as np
import time
import scipy.signal as ss
import ncpi
from ncpi import tools

# =============================================================================
# ARGPARSE (solo parametros del modelo y ruta de guardado)
# =============================================================================

parser = argparse.ArgumentParser(
    description='Simulacion LIF + CDM para una configuracion (SLURM array jobs)')

parser.add_argument('--J_EE',      type=float, required=True)
parser.add_argument('--J_IE',      type=float, required=True)
parser.add_argument('--J_EI',      type=float, required=True)
parser.add_argument('--J_II',      type=float, required=True)
parser.add_argument('--tau_syn_E', type=float, required=True)
parser.add_argument('--tau_syn_I', type=float, required=True)
parser.add_argument('--J_ext',     type=float, required=True)
parser.add_argument('--save-path', type=str,   required=True)

args = parser.parse_args()

# =============================================================================
# CONFIGURACION HARDCODEADA
# =============================================================================

sim_config_path = '/LUSTRE/home/TIC117/cmg/alejandro/ncpi/examples/simulation/Hagen_model/figures'
tem_output_base = '/SCRATCH/TIC117/cmg/alejandro/temp_sim' # This is for HPC use

zenodo_dw_mult = False
zenodo_URL_mult = "https://zenodo.org/api/records/15429373"
zenodo_dir = '/LUSTRE/home/TIC117/cmg/Marta/ncpi_13_11_25/examples/simulation/Hagen_model/simulation/multicompartment_neuron_network/'

simulation_type = 'normal' # tsodyks o normal
trials = 6

# =============================================================================
# SETUP
# =============================================================================

param_order = ['J_EE', 'J_IE', 'J_EI', 'J_II', 'tau_syn_E', 'tau_syn_I', 'J_ext']
config = {p: getattr(args, p) for p in param_order}

# Carpeta de resultados: save_path/<J_EE>_<J_IE>_<J_EI>_<J_II>_<tau_syn_E>_<tau_syn_I>_<J_ext>/
values_str = '_'.join([f'{config[p]:g}' for p in param_order])
result_dir = os.path.join(args.save_path, values_str)
os.makedirs(result_dir, exist_ok=True)

# Paths de simulacion
sys.path.append(os.path.join(sim_config_path, '../simulation/params'))

output_path = os.path.join(
    zenodo_dir, 'multicompartment_neuron_network', 'output',
    'adb947bfb931a5a8d09ad078a6d256b0')
multicompartment_neuron_network_path = os.path.join(
    zenodo_dir, 'multicompartment_neuron_network')


print(f'Configuracion: {config}')
print(f'Directorio de resultados: {result_dir}')

# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def get_ISI(gids, times):
    neurons_id = np.unique(gids)
    isi_list = []
    for neuron in neurons_id:
        mask = gids == neuron
        neuron_times = times[mask]
        if len(neuron_times) < 2:
            isi_list.append(0)
        else:
            isi = np.diff(neuron_times)
            isi_list.append(np.mean(isi))
    return isi_list


def get_CV(gids, times):
    neurons_id = np.unique(gids)
    all_isis = []
    for neuron in neurons_id:
        mask = gids == neuron
        neuron_times = times[mask]
        if len(neuron_times) >= 2:
            isi = np.diff(neuron_times)
            all_isis.extend(isi)

    if len(all_isis) == 0:
        print('No hay ISI validos, returning NaN')
        return np.nan

    all_isis = np.array(all_isis)
    mean_isi = np.mean(all_isis)

    if mean_isi == 0:
        print('Mean ISI = 0, returning NaN')
        return np.nan

    return np.std(all_isis) / mean_isi


def get_FiringRates(times, transient, tstop, dt, N_X):
    bins = np.arange(transient, tstop + dt, dt)
    hist, _ = np.histogram(times, bins=bins)
    hist = (1000.0 / dt) * hist / N_X
    return hist


def get_spike_rate(times, transient, dt, tstop):
    bins = np.arange(transient, tstop + dt, dt)
    hist, _ = np.histogram(times, bins=bins)
    return bins, hist.astype(float)


def get_pair_correlation(gids, times, transient, tstop, dt):
    neurons_id = np.unique(gids)
    max_neurons = 500
    if len(neurons_id) > max_neurons:
        neurons_id = np.random.choice(neurons_id, size=max_neurons, replace=False)

    firing_rates = []
    for nid in neurons_id:
        neuron_times = times[gids == nid]
        _, hist = get_spike_rate(neuron_times, transient, dt, tstop)
        firing_rates.append(hist)

    firing_rates = np.array(firing_rates)
    stds = np.std(firing_rates, axis=1)
    valid_neurons = stds > 0

    if np.sum(valid_neurons) < 2:
        return np.nan, np.nan

    firing_rates = firing_rates[valid_neurons]
    corr_matrix = np.corrcoef(firing_rates)
    triu_indices = np.triu_indices_from(corr_matrix, k=1)
    correlations = corr_matrix[triu_indices]
    correlations = correlations[~np.isnan(correlations)]

    if len(correlations) == 0:
        return np.nan, np.nan

    return np.mean(correlations), np.std(correlations)


# =============================================================================
# DESCARGA DE DATOS (si es necesario)
# =============================================================================

if zenodo_dw_mult:
    print('\n--- Descargando datos.')
    start_time = time.time()
    tools.download_zenodo_record(zenodo_URL_mult, download_dir=zenodo_dir)
    end_time = time.time()
    print(f"Datos descargados en {(end_time - start_time) / 60:.2f} minutos.")

# =============================================================================
# SIMULACION (una configuracion, N trials)
# =============================================================================

np.random.seed(0)

print(f"\n{'='*60}")
print(f"Iniciando: {trials} trials")
print(f"{'='*60}")

job_id = f"{os.environ.get('SLURM_ARRAY_JOB_ID', 'local')}_{os.environ.get('SLURM_ARRAY_TASK_ID', str(os.getpid()))}"

for trial in range(trials):
    # Directorio temporal unico por job para evitar conflictos entre jobs paralelos
    sim_output_dir = os.path.join(tem_output_base, f'output_{job_id}_trial_{trial}')

    valid_simulation = True
    print(f'\nTrial {trial+1}/{trials}')

    os.makedirs(sim_output_dir, exist_ok=True)

    # Cargar y modificar LIF_params
    from network_params import LIF_params

    LIF_params['J_YX'] = [[config['J_EE'], config['J_IE']],
                           [config['J_EI'], config['J_II']]]
    LIF_params['tau_syn_YX'] = [[config['tau_syn_E'], config['tau_syn_I']],
                                 [config['tau_syn_E'], config['tau_syn_I']]]
    LIF_params['J_ext'] = config['J_ext']

    # Crear objeto Simulation con directorio temporal unico
    sim = ncpi.Simulation(
        param_folder=os.path.join(sim_config_path, '../simulation/params'),
        python_folder=os.path.join(sim_config_path, '../simulation/python'),
        output_folder=sim_output_dir)

    # Guardar parametros de red
    with open(os.path.join(sim_output_dir, 'network.pkl'), 'wb') as f:
        pickle.dump(LIF_params, f)

    # Ejecutar simulacion
    simulation_file = 'simulation_tsodyks.py' if simulation_type == 'tsodyks' else 'simulation.py'
    sim.simulate(simulation_file, 'simulation_params.py')

    # Cargar resultados
    with open(os.path.join(sim_output_dir, 'times.pkl'), 'rb') as f:
        times = pickle.load(f)
    with open(os.path.join(sim_output_dir, 'gids.pkl'), 'rb') as f:
        gids = pickle.load(f)
    with open(os.path.join(sim_output_dir, 'tstop.pkl'), 'rb') as f:
        tstop = pickle.load(f)
    with open(os.path.join(sim_output_dir, 'dt.pkl'), 'rb') as f:
        dt = pickle.load(f)
    with open(os.path.join(sim_output_dir, 'network.pkl'), 'rb') as f:
        LIF_params = pickle.load(f)
        P_X = LIF_params['X']
        N_X = LIF_params['N_X']

    from analysis_params import KernelParams
    transient = KernelParams.transient

    # --- Validacion ---
    print("\n--- Validando simulacion ---")
    metrics = {}
    for i, X in enumerate(P_X):
        metrics[X] = {}
        gids[X] = gids[X][times[X] >= transient]
        times[X] = times[X][times[X] >= transient]

        isi = get_ISI(gids[X], times[X])

        if len(isi) == 0:
            print(f"  Poblacion {X}: No hay spikes suficientes")
            valid_simulation = False
            continue

        mean_isi = np.mean(isi)
        cv = get_CV(gids[X], times[X])
        firing_rate_hist = get_FiringRates(times[X], transient, tstop, dt, N_X[i])
        mean_firing_rate = np.mean(firing_rate_hist)
        mean_corr, std_corr = get_pair_correlation(
            gids[X], times[X], transient, tstop, 10)

        metrics[X]['mean_firing_rate'] = mean_firing_rate
        metrics[X]['mean_correlation'] = mean_corr
        metrics[X]['CV'] = cv

        print(f"Poblacion {X}:")
        print(f"  ISI medio: {mean_isi:.2f} ms")
        print(f"  Firing Rate: {mean_firing_rate:.2f} Hz")
        print(f"  CV: {cv:.2f}")
        print(f"  Correlacion pares: {mean_corr:.3f} +/- {std_corr:.3f}")

        if X == 'E':
            if mean_firing_rate < 0.1:
                print("  FR(E) demasiado bajo (red silenciosa)")
                valid_simulation = False
            elif mean_firing_rate > 50:
                print("  FR(E) demasiado alto (hiperactividad)")
                valid_simulation = False
            elif not (0.2 <= mean_firing_rate <= 10):
                print("  FR(E) atipico pero aceptable")

            if cv < 0.1 or cv > 3.0:
                print("  CV(E) extremo (reloj o caotico)")
                valid_simulation = False
            elif not (0.5 <= cv <= 2.0):
                print("  CV(E) atipico pero aceptable")

            if not np.isnan(mean_corr):
                if mean_corr > 0.5:
                    print("  Correlacion(E) muy alta")
                    valid_simulation = False
                elif mean_corr > 0.3:
                    valid_simulation = False
                    print("  Correlacion(E) alta")
                elif mean_corr < -0.1:
                    valid_simulation = False
                    print("  Correlacion(E) negativa")
                elif 0.0 <= mean_corr <= 0.2:
                    print("  Correlacion(E) en rango asincronico esperado")

        elif X == 'I':
            if mean_firing_rate < 0.5:
                print("  FR(I) demasiado bajo")
                valid_simulation = False
            elif mean_firing_rate > 100:
                print("  FR(I) demasiado alto")
                valid_simulation = False
            elif not (2 <= mean_firing_rate <= 30):
                print("  FR(I) atipico pero aceptable")

            if cv < 0.1 or cv > 3.0:
                print("  CV(I) extremo")
                valid_simulation = False
            elif not (0.5 <= cv <= 2.0):
                print("  CV(I) atipico pero aceptable")

            if not np.isnan(mean_corr):
                if mean_corr > 0.5:
                    print("  Correlacion(I) muy alta")
                    valid_simulation = False
                elif mean_corr > 0.3:
                    valid_simulation = False
                    print("  Correlacion(I) alta")
                elif mean_corr < -0.1:
                    valid_simulation = False
                    print("  Correlacion(I) negativa")
                elif 0.0 <= mean_corr <= 0.01:
                    print("  Correlacion(I) en rango asincronico esperado")

    status = 'VALIDA' if valid_simulation else 'NO VALIDA'
    print(f"\nSimulacion {status}")

    # --- Kernel CDM ---
    print('Calculando el kernel...')
    potential = ncpi.FieldPotential()
    biophys = ['set_Ih_linearized_hay2011', 'make_cell_uniform']

    H_YX = potential.create_kernel(multicompartment_neuron_network_path,
                                   output_path,
                                   KernelParams,
                                   biophys,
                                   dt, tstop,
                                   electrodeParameters=None,
                                   CDM=True)

    probe = 'KernelApproxCurrentDipoleMoment'
    CDM_data = dict(EE=[], EI=[], IE=[], II=[])

    for X in P_X:
        for Y in P_X:
            bins, spike_rate = get_spike_rate(times[X], transient, dt, tstop)
            kernel = H_YX[f'{X}:{Y}'][probe][2, :]
            sig = np.convolve(spike_rate, kernel, 'same')
            CDM_data[f'{X}{Y}'] = ss.decimate(sig, q=10, zero_phase=True)

    # --- Guardar trial en save_path/<valores>/ ---
    filename = f'valid_trial_{trial}.pkl' if valid_simulation else f'novalid_trial_{trial}.pkl'
    filepath = os.path.join(result_dir, filename)
    with open(filepath, 'wb') as f:
        pickle.dump([config, times, gids, CDM_data, dt, tstop,
                     transient, P_X, N_X, metrics], f)

    print(f"Guardado: {filepath}")

    # Limpiar directorio temporal de este trial
    shutil.rmtree(sim_output_dir, ignore_errors=True)

print(f"\n{'='*60}")
print(f"Pipeline completado")
print(f"Resultados en: {result_dir}")
print(f"{'='*60}")
