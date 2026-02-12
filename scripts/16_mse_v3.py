import matplotlib.pyplot as plt
import pandas as pd
import os
import sys
import numpy as np
from scipy.signal import savgol_filter
from scipy.integrate import trapezoid
from kneed import KneeLocator
from ncpi import Features
import argparse


BASE_PATH = '/LUSTRE/home/TIC117/cmg/alejandro'
PARAMETERS = ['J_EE', 'J_IE', 'J_EI', 'J_II', 'tau_syn_E', 'tau_syn_I', 'J_ext']
FS = 1000. / (10. * 0.0625)

# MSE parameters
MSE_MAX_SCALE = 20
MSE_M = 2
MSE_R = 0.059
EPOCH_TIME = 5  # seconds
CTM_R = 0.043
LZC_W = [1, 3, 5, 7]


def create_features_extractor(feature, **kwargs):
    """
    Crea un objeto Features configurado para features no lineales.

    Args:
        feature: tipo de feature ('mse', 'ctm', 'lzc', 'se')
        **kwargs: parámetros específicos de la feature

    Returns:
        Features: objeto configurado para medusa
    """
    params = {
        'feature': feature,
        'normalize': False,
        **kwargs
    }
    return Features(method='medusa', params=params)


# ============ Data loading ============

def get_valid_trials(conf_path):
    """Obtiene lista de trials válidos ordenados."""
    trials = [t for t in os.listdir(conf_path) if t.startswith('valid') and t.endswith('.pkl')]
    return sorted(trials)


def load_cdm(trial_path, normalize=True, index=3):
    """
    Carga un trial y extrae la señal CDM.

    Args:
        trial_path: ruta al archivo pickle
        normalize: si True, aplica z-score
        index: índice del elemento a extraer del pickle

    Returns:
        np.ndarray con la señal CDM
    """
    sim = pd.read_pickle(trial_path)
    cdm = sim[index]['EE'] + sim[index]['IE'] + sim[index]['EI'] + sim[index]['II']
    if normalize:
        cdm = (cdm - np.mean(cdm)) / np.std(cdm)
    return cdm


def split_into_epochs(signal, time, fs):
    """Divide señal en epochs de `time` segundos."""
    if time == -1:
        return signal[np.newaxis, :]
    samples_per_epoch = int(fs * time)
    n_epochs = len(signal) // samples_per_epoch
    trimmed = signal[:n_epochs * samples_per_epoch]
    return trimmed.reshape(n_epochs, samples_per_epoch)


def get_cdm_array(conf_path, time=-1, normalize=True, index=3):
    """
    Carga todos los trials de una configuración y los devuelve como array.

    Args:
        conf_path: ruta al directorio de la configuración
        time: duración de cada epoch en segundos. -1 = sin dividir
        normalize: si True, aplica z-score a cada CDM
        index: índice del elemento a extraer del pickle

    Returns:
        np.ndarray de forma (n_epochs, n_samples, n_trials)
    """
    trials = get_valid_trials(conf_path)
    epoch_list = []
    
    for trial in trials:
        trial_path = os.path.join(conf_path, trial)
        cdm = load_cdm(trial_path, normalize=normalize, index=index)
        epochs = split_into_epochs(cdm, time, fs=FS)
        epoch_list.append(epochs)
    
    return np.stack(epoch_list, axis=2)


# ============ Feature computation ============

def compute_mse(cdm_array, max_scale=20, m=2, r=0.059):
    """Calcula Multiscale Entropy usando ncpi.Features."""
    fe = create_features_extractor('mse', max_scale=max_scale, m=m, r=r)
    return fe.multiscale_entropy(signal=cdm_array, max_scale=max_scale, m=m, r=r)


def compute_ctm(cdm_array, r):
    """Calcula Central Tendency Measure usando ncpi.Features."""
    fe = create_features_extractor('ctm', r=r)
    return fe.central_tendency_measure(signal=cdm_array, r=r)


def compute_lzc(cdm_array, W):
    """Calcula Multiscale Lempel-Ziv Complexity usando ncpi.Features."""
    fe = create_features_extractor('lzc', W=W)
    return fe.multiscale_lempelziv_complexity(signal=cdm_array, W=W)


def summarize_mse(mse_array):
    """
    Genera estadísticas agregadas de MSE.

    Args:
        mse_array: np.ndarray de forma (n_epochs, max_scale, n_trials)

    Returns:
        dict con mean, std, auc_mean, auc_std
    """
    mean_mse = np.mean(mse_array, axis=(0, 2))
    std_mse = np.std(mse_array, axis=(0, 2))
    mean_per_trial = np.mean(mse_array, axis=0)

    scales = np.arange(1, mse_array.shape[1] + 1)
    aucs = []
    for trial_idx in range(mse_array.shape[2]):
        trial_mse = np.mean(mse_array[:, :, trial_idx], axis=0)
        auc = trapezoid(trial_mse, scales)
        aucs.append(auc)

    return {
        'mean': mean_mse,
        'std': std_mse,
        'mean_per_trial': mean_per_trial,
        'auc': np.array(aucs),
        'auc_mean': np.mean(aucs),
        'auc_std': np.std(aucs)
    }


# ============ MSE analysis ============

def smooth_MSE(mse_values, window_length=11, polyorder=3):
    """Suaviza la curva MSE usando filtro Savitzky-Golay."""
    window_length = min(window_length, len(mse_values) - 1)
    if window_length % 2 == 0:
        window_length += 1
    return savgol_filter(mse_values, window_length, polyorder)


def MSE_fractals(mse):
    """
    Calcula las pendientes antes y después del codo de la curva MSE.

    Returns:
        m1: pendiente de la primera mitad
        m2: pendiente de la segunda mitad
        elbow_index: índice del codo
    """
    x = np.arange(len(mse))
    kneedle = KneeLocator(x, mse, S=1.0, curve='concave', direction='increasing')
    elbow_index = kneedle.knee

    if elbow_index is None or elbow_index <= 1 or elbow_index >= len(mse) - 1:
        elbow_index = len(mse) // 2

    arr1 = mse[:elbow_index]
    arr2 = mse[elbow_index:]

    m1 = np.polyfit(np.arange(1, len(arr1) + 1), arr1, 1)[0]
    m2 = np.polyfit(np.arange(1, len(arr2) + 1), arr2, 1)[0]

    return m1, m2, elbow_index


# ============ Main processing ============

def create_dataframe(CONF_PATH):
    """
    Procesa una configuración específica y calcula todas las features MSE.
    
    Args:
        CONF_PATH: ruta completa al directorio de la configuración
    
    Returns:
        tuple: (dict con resultados, nombre de archivo)
    """
    # Parsear el path
    conf_split = CONF_PATH.rstrip('/').split('/')
    conf = conf_split[-1]  # Nombre de configuración
    
    # Extraer modelo y parámetro
    model_type = conf_split[5]  # tsodyks o no_plast
    param = conf_split[6].split('-')[0]  # J_EE_J_IE-v2 -> J_EE_J_IE
    
    if param != 'J_ext':
        jext_dir = conf_split[7]  # Jext32 o Jext2989
    else:
        jext_dir = 'all'
    
    print(CONF_PATH)
    print(conf)
    print(param)
    
    file_name = f"{model_type}-{param}-{jext_dir}-{conf}"
    
    # Parsear configuracion
    confs = conf.split('_')
    if param == 'J_EE_J_II':
        conf1 = float(confs[0])
        conf2 = float(confs[3])
        configs = (conf1, conf2)
    elif param == 'J_IE_J_EI':
        conf1 = float(confs[1])
        conf2 = float(confs[2])
        configs = (conf1, conf2)
    elif param == 'J_EE_J_IE':
        conf1 = float(confs[0])
        conf2 = float(confs[1])
        configs = (conf1, conf2)
    elif param == 'J_EI_J_II':
        conf1 = float(confs[2])
        conf2 = float(confs[3])
        configs = (conf1, conf2)
    else:
        configs = float(confs[PARAMETERS.index(param)])
    
    # Get CDM array: (n_epochs, n_samples, n_trials)
    cdm_array = get_cdm_array(CONF_PATH, time=EPOCH_TIME, normalize=True, index=3)
    
    # Compute features
    mse = compute_mse(cdm_array, max_scale=MSE_MAX_SCALE, m=MSE_M, r=MSE_R)
    ctm = compute_ctm(cdm_array, r=CTM_R)
    lzc = compute_lzc(cdm_array, W=LZC_W)
    
    # Summary statistics
    mse_summary = summarize_mse(mse)
    mse_mean = mse_summary['mean']
    mse_smooth = smooth_MSE(mse_mean)
    
    # Fractals
    m1, m2, elbow_index = MSE_fractals(mse_smooth)
    
    # Store results
    results = {
        'Parameter': param,
        'Configuration': configs,
        'MSE_curve': mse_mean,
        'MSE_smooth': mse_smooth,
        'AUC_mean': mse_summary['auc_mean'],
        'AUC_std': mse_summary['auc_std'],
        'AUC_all': mse_summary['auc'],
        'm1': m1,
        'm2': m2,
        'elbow_index': elbow_index,
        'lzc': lzc,
        'ctm': ctm,
    }
    
    return results, file_name


def create_parameter_df(PARAM_PATH):
    """
    Create a DataFrame for one parameter with all configurations.
    """
    configurations = os.listdir(PARAM_PATH)
    results_list = []
    for conf in configurations:
        conf_path = os.path.join(PARAM_PATH, conf)
        if not os.path.isdir(conf_path):
            continue
        results, _ = create_dataframe(conf_path)
        results_list.append(results)
    return pd.DataFrame(results_list)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('conf_path', type=str)
    parser.add_argument('--output_dir', type=str, default='results')

    args = parser.parse_args()

    conf_path = args.conf_path
    conf_split = conf_path.rstrip('/').split('/')
    param = conf_split[6]
    print(param)
    if param != 'J_ext':
        file_name = f"{param}-{conf_split[-1]}"
    else:
        file_name = param

    df = create_parameter_df(args.conf_path)
    df.to_pickle(os.path.join(args.output_dir, f"16-mse-{file_name}.pkl"))