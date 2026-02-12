#!/usr/bin/env python3
"""
17_nonlinear_features_v4.py

Computes nonlinear features (Sample Entropy, Central Tendency Measure)
from CDM signals for a single configuration.
"""

import pandas as pd
import os
import sys
import numpy as np
from ncpi import Features
import argparse


# ============ Constants ============

BASE_PATH = '/LUSTRE/home/TIC117/cmg/alejandro'
PARAMETERS = ['J_EE', 'J_IE', 'J_EI', 'J_II', 'tau_syn_E', 'tau_syn_I', 'J_ext']
FS = 1000. / (10. * 0.0625)
EPOCH_TIME = 5  # seconds

# Sample Entropy parameters
SE_M = 2
SE_R = 0.059

# CTM parameters
CTM_R = 0.043


def create_features_extractor(feature, **kwargs):
    """
    Crea un objeto Features configurado para features no lineales.

    Args:
        feature: tipo de feature ('se', 'ctm', 'mse', 'lzc')
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
    """Returns sorted list of valid trial filenames."""
    trials = [t for t in os.listdir(conf_path) 
              if t.startswith('valid') and t.endswith('.pkl')]
    return sorted(trials)


def load_cdm(trial_path, index=3):
    """Loads a trial pickle and returns the raw CDM signal."""
    sim = pd.read_pickle(trial_path)
    return sim[index]['EE'] + sim[index]['EI'] + sim[index]['IE'] + sim[index]['II']


def split_into_epochs(signal, fs, time):
    """Splits signal into non-overlapping epochs of `time` seconds."""
    samples_per_epoch = int(fs * time)
    n_epochs = len(signal) // samples_per_epoch
    trimmed = signal[:n_epochs * samples_per_epoch]
    return trimmed.reshape(n_epochs, samples_per_epoch)


def get_cdm_array(conf_path, time, normalize=False, index=3):
    """
    Loads all trials from a configuration and returns epoched CDM array.

    Args:
        conf_path: path to configuration directory
        time: epoch duration in seconds
        normalize: if True, z-score the whole signal before epoching
        index: index to extract from pickle

    Returns:
        np.ndarray of shape (n_epochs, n_samples, n_trials), or None
    """
    trials = get_valid_trials(conf_path)
    if not trials:
        return None

    epoch_list = []
    for trial in trials:
        trial_path = os.path.join(conf_path, trial)
        cdm = load_cdm(trial_path, index=index)
        if normalize:
            cdm = (cdm - np.mean(cdm)) / np.std(cdm)
        epochs = split_into_epochs(cdm, FS, time)
        epoch_list.append(epochs)

    return np.stack(epoch_list, axis=2)


# ============ Feature computation ============

def compute_se(cdm_array, m=SE_M, r=SE_R):
    """
    Computes Sample Entropy using ncpi.Features. Expects already-normalized input.

    Args:
        cdm_array: (n_epochs, n_samples, n_trials)

    Returns:
        np.ndarray of shape (n_epochs, n_trials)
    """
    fe = create_features_extractor('se', m=m, r=r)
    return fe.sample_entropy(signal=cdm_array, m=m, r=r)


def compute_ctm(cdm_array, r=CTM_R):
    """
    Computes Central Tendency Measure using ncpi.Features on raw CDM.

    Args:
        cdm_array: (n_epochs, n_samples, n_trials)

    Returns:
        np.ndarray of shape (n_epochs, n_trials)
    """
    fe = create_features_extractor('ctm', r=r)
    return fe.central_tendency_measure(signal=cdm_array, r=r)


# ============ Main processing ============

def create_dataframe(CONF_PATH):
    """
    Procesa una configuración específica y calcula features no lineales.
    
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
    
    # Load CDM arrays
    cdm_raw = get_cdm_array(CONF_PATH, time=EPOCH_TIME, normalize=False, index=3)
    cdm_norm = get_cdm_array(CONF_PATH, time=EPOCH_TIME, normalize=True, index=3)
    
    # Compute features
    se = compute_se(cdm_norm, m=SE_M, r=SE_R)
    ctm = compute_ctm(cdm_raw, r=CTM_R)
    
    # Store results
    results = {
        'Parameter': param,
        'Configuration': configs,
        'se_mean': np.mean(se),
        'se_std': np.std(se),
        'se_all': se,
        'ctm_mean': np.mean(ctm),
        'ctm_std': np.std(ctm),
        'ctm_all': ctm,
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
    df.to_pickle(os.path.join(args.output_dir, f"17-nonlinear-{file_name}.pkl"))