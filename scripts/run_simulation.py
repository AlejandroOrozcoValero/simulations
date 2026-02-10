"""
run_simulation.py - Ejecuta simulaciones LIF y guarda resultados.

Modos de operacion:
  - 'best_config': una sola configuracion usando best_config del JSON
  - 'sweep': multiples configuraciones usando sweep_params del JSON

Los resultados se guardan en save_path junto con un simulation_info.json
que contiene toda la metadata necesaria para el script de plots.
"""

import sys
import os
import pickle
import numpy as np
import time
import json
import itertools
import scipy.signal as ss
import ncpi
from ncpi import tools

# =============================================================================
# CONFIGURACION DEL USUARIO
# =============================================================================

# Ruta con los archivos de simulación
sim_config_path = '/LUSTRE/home/TIC117/cmg/alejandro/ncpi_old/examples/simulation/Hagen_model/figures'

# Ruta donde se guardaran los resultados
save_path = '/SCRATCH/TIC117/cmg/alejandro/plasticity_sims/Jext28.89'

# Modo de simulacion: 'best_config' (1 configuracion) o 'sweep' (multiples)
simulation_mode = 'sweep'

# Archivo JSON con la configuracion de parametros
config_file = 'param_sweep_config_v2.json'

# Numero de repeticiones por configuracion
trials = 6

# Tipo de combinacion para sweep: 'product' (producto cartesiano) o 'zip' (pareado)
combination_type = 'zip'

# Zenodo
zenodo_dw_mult = False
zenodo_URL_mult = "https://zenodo.org/api/records/15429373"
zenodo_dir = '/LUSTRE/home/TIC117/cmg/Marta/ncpi_13_11_25/examples/simulation/Hagen_model/simulation/multicompartment_neuron_network/'

# =============================================================================
# SETUP DE PATHS
# =============================================================================
sys.path.append(os.path.join(sim_config_path, '../simulation/params'))

output_path = os.path.join(zenodo_dir, 'multicompartment_neuron_network',
                           'output', 'adb947bfb931a5a8d09ad078a6d256b0')
multicompartment_neuron_network_path = os.path.join(zenodo_dir,
                                                     'multicompartment_neuron_network')

# =============================================================================
# CARGAR CONFIGURACION DESDE JSON
# =============================================================================

with open(config_file, 'r') as f:
    sweep_config = json.load(f)

best_config = sweep_config['best_config']
sweep_params = sweep_config['sweep_params']

param_order = ['J_EE', 'J_IE', 'J_EI', 'J_II', 'tau_syn_E', 'tau_syn_I', 'J_ext']

# =============================================================================
# GENERAR CONFIGURACIONES SEGUN EL MODO
# =============================================================================

if simulation_mode == 'best_config':
    confs = [[best_config[p] for p in param_order]]
    conf_metadata = [best_config.copy()]
    swept_param_names = []
    print(f"Modo: best_config -> 1 configuracion")
    print(f"Parametros: {best_config}")

elif simulation_mode == 'sweep':
    swept_param_names = list(sweep_params.keys())
    swept_param_values = [sweep_params[name] for name in swept_param_names]

    if combination_type == 'product':
        combinations = list(itertools.product(*swept_param_values))
    elif combination_type == 'zip':
        combinations = list(zip(*swept_param_values))
    else:
        raise ValueError(f"combination_type invalido: {combination_type}")

    confs = []
    conf_metadata = []
    for combo in combinations:
        conf = [best_config[p] for p in param_order]
        for i, param_name in enumerate(swept_param_names):
            param_idx = param_order.index(param_name)
            conf[param_idx] = combo[i]
        confs.append(conf)
        conf_metadata.append({name: combo[i] for i, name in enumerate(swept_param_names)})

    print(f"Modo: sweep -> {len(confs)} configuraciones")
    print(f"Parametros barridos: {swept_param_names}")
else:
    raise ValueError(f"simulation_mode invalido: {simulation_mode}. Usar 'best_config' o 'sweep'")

print(f"Trials por configuracion: {trials}")
print(f"Total simulaciones: {len(confs) * trials}")


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


def get_result_dir(save_path, simulation_mode, swept_param_names, conf_metadata, k):
    """Calcula la ruta del directorio para la configuracion k."""
    if simulation_mode == 'best_config':
        return os.path.join(save_path, 'best_config')
    elif len(swept_param_names) == 1:
        return os.path.join(save_path, swept_param_names[0],
                            str(conf_metadata[k][swept_param_names[0]]))
    else:
        param_dir = '_'.join(swept_param_names)
        value_str = '_'.join([str(conf_metadata[k][name]) for name in swept_param_names])
        return os.path.join(save_path, param_dir, value_str)


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
# LOOP DE SIMULACION
# =============================================================================

np.random.seed(0)

print(f"\n{'='*60}")
print(f"Iniciando simulaciones")
print(f"{'='*60}")
print(f"Configuraciones: {confs}")

for trial in range(trials):
    for k, params in enumerate(confs):
        valid_simulation = True
        print(f'\nTrial {trial+1}/{trials}, Configuracion {k+1}/{len(confs)}')

        # Extraer parametros
        J_EE = params[0]
        J_IE = params[1]
        J_EI = params[2]
        J_II = params[3]
        tau_syn_E = params[4]
        tau_syn_I = params[5]
        J_ext = params[6]

        # Cargar LIF_params
        from network_params import LIF_params

        # Modificar parametros
        LIF_params['J_YX'] = [[J_EE, J_IE], [J_EI, J_II]]
        LIF_params['tau_syn_YX'] = [[tau_syn_E, tau_syn_I],
                                    [tau_syn_E, tau_syn_I]]
        LIF_params['J_ext'] = J_ext

        # Diccionario de configuracion
        config = {
            'J_EE': J_EE, 'J_IE': J_IE, 'J_EI': J_EI, 'J_II': J_II,
            'tau_syn_E': tau_syn_E, 'tau_syn_I': tau_syn_I, 'J_ext': J_ext
        }

        # Crear objeto Simulation
        sim = ncpi.Simulation(param_folder=os.path.join(sim_config_path, '../simulation/params'),
                              python_folder=os.path.join(sim_config_path, '../simulation/python'),
                              output_folder=os.path.join(sim_config_path, '../simulation/output'))

        # Guardar parametros de red
        with open(os.path.join(sim_config_path, '../simulation/output', 'network.pkl'), 'wb') as f:
            pickle.dump(LIF_params, f)

        # Ejecutar simulacion
        sim.simulate('simulation_tsodyks.py', 'simulation_params.py')

        # Cargar resultados de la simulacion
        with open(os.path.join(sim_config_path, '../simulation/output', 'times.pkl'), 'rb') as f:
            times = pickle.load(f)
        with open(os.path.join(sim_config_path, '../simulation/output', 'gids.pkl'), 'rb') as f:
            gids = pickle.load(f)
        with open(os.path.join(sim_config_path, '../simulation/output', 'tstop.pkl'), 'rb') as f:
            tstop = pickle.load(f)
        with open(os.path.join(sim_config_path, '../simulation/output', 'dt.pkl'), 'rb') as f:
            dt = pickle.load(f)
        with open(os.path.join(sim_config_path, '../simulation/output', 'network.pkl'), 'rb') as f:
            LIF_params = pickle.load(f)
            P_X = LIF_params['X']
            N_X = LIF_params['N_X']

        from analysis_params import KernelParams
        transient = KernelParams.transient

        # --- Validacion de la simulacion ---
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
            mean_corr, std_corr = get_pair_correlation(gids[X], times[X], transient, tstop, 10)

            metrics[X]['mean_firing_rate'] = mean_firing_rate
            metrics[X]['mean_correlation'] = mean_corr
            metrics[X]['CV'] = cv

            print(f"Poblacion {X}:")
            print(f"  ISI medio: {mean_isi:.2f} ms")
            print(f"  Firing Rate: {mean_firing_rate:.2f} Hz")
            print(f"  CV: {cv:.2f}")
            print(f"  Correlacion pares: {mean_corr:.3f} +/- {std_corr:.3f}")

            # Validacion para poblacion E
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
                        print("  Correlacion(E) muy alta (sincronizacion excesiva)")
                        valid_simulation = False
                    elif mean_corr > 0.3:
                        valid_simulation = False
                        print("  Correlacion(E) alta (posible hiperactividad)")
                    elif mean_corr < -0.1:
                        valid_simulation = False
                        print("  Correlacion(E) negativa (inusual)")
                    elif 0.0 <= mean_corr <= 0.2:
                        print("  Correlacion(E) en rango asincronico esperado")

            # Validacion para poblacion I
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
                        print("  Correlacion(I) muy alta (sincronizacion excesiva)")
                        valid_simulation = False
                    elif mean_corr > 0.3:
                        valid_simulation = False
                        print("  Correlacion(I) alta")
                    elif mean_corr < -0.1:
                        valid_simulation = False
                        print("  Correlacion(I) negativa (inusual)")
                    elif 0.0 <= mean_corr <= 0.01:
                        print("  Correlacion(I) en rango asincronico esperado")

        status = 'VALIDA' if valid_simulation else 'NO VALIDA'
        print(f"\nSimulacion {status}")

        # --- Calcular kernel CDM ---
        print('Calculando el kernel...')
        potential = ncpi.FieldPotential()
        biophys = ['set_Ih_linearized_hay2011', 'make_cell_uniform']

        H_YX = potential.create_kernel(multicompartment_neuron_network_path,
                                       output_path,
                                       KernelParams,
                                       biophys,
                                       dt,
                                       tstop,
                                       electrodeParameters=None,
                                       CDM=True)

        # Calcular CDM
        probe = 'KernelApproxCurrentDipoleMoment'
        CDM_data = dict(EE=[], EI=[], IE=[], II=[])

        for X in P_X:
            for Y in P_X:
                bins, spike_rate = get_spike_rate(times[X], transient, dt, tstop)
                kernel = H_YX[f'{X}:{Y}'][probe][2, :]
                sig = np.convolve(spike_rate, kernel, 'same')
                CDM_data[f'{X}{Y}'] = ss.decimate(sig, q=10, zero_phase=True)

        # --- Guardar resultados ---
        result_dir = get_result_dir(save_path, simulation_mode,
                                    swept_param_names, conf_metadata, k)
        os.makedirs(result_dir, exist_ok=True)

        if valid_simulation:
            filename = f'valid_trial_{trial}.pkl'
        else:
            filename = f'novalid_trial_{trial}.pkl'

        with open(os.path.join(result_dir, filename), 'wb') as f:
            pickle.dump([config, times, gids, CDM_data, dt, tstop,
                         transient, P_X, N_X, metrics], f)

        print(f"Guardado como: {os.path.join(result_dir, filename)}")
        print(f"Configuracion: {config}")

# =============================================================================
# GUARDAR METADATA (simulation_info.json)
# =============================================================================

directory_structure = {}
for k in range(len(confs)):
    result_dir = get_result_dir(save_path, simulation_mode,
                                swept_param_names, conf_metadata, k)
    directory_structure[str(k)] = os.path.relpath(result_dir, save_path)

simulation_info = {
    'simulation_mode': simulation_mode,
    'config_file': config_file,
    'best_config': best_config,
    'param_order': param_order,
    'swept_param_names': swept_param_names,
    'combination_type': combination_type,
    'trials': trials,
    'num_configurations': len(confs),
    'conf_metadata': conf_metadata,
    'confs': confs,
    'directory_structure': directory_structure,
}

info_path = os.path.join(save_path, 'simulation_info.json')
with open(info_path, 'w') as f:
    json.dump(simulation_info, f, indent=2)

print(f"\n{'='*60}")
print(f"Simulaciones completadas")
print(f"Metadata guardada en: {info_path}")
print(f"{'='*60}")
