"""
Created 16/02/2026 by Alejandro Orozco Valero
Computes DFA and fEI features from CDM signals for a single parameter.
Uses band-pass filtering (alpha band 8-13 Hz) + Hilbert envelope.
"""
import pandas as pd
import os
import numpy as np
from ncpi import Features
import argparse


# ============ Constants ============

PARAMETERS = ['J_EE', 'J_IE', 'J_EI', 'J_II', 'tau_syn_E', 'tau_syn_I', 'J_ext']
FS = 1000. / (10. * 0.0625)  # Sampling frequency
FREQUENCY_RANGE = [30., 45.]  # Alpha band (Hz)
WINDOW_SIZE_SEC = 5.0  # fEI window size (seconds)
DFA_THRESHOLD = 0.4  # DFA threshold for fEI
TRANSIENT_TIME = 0  # Seconds to discard from start of signal


def load_cdm(trial_path, normalize=True):
    """
    Load a trial, discard first TRANSIENT_TIME seconds, and extract CDM.

    Args:
        trial_path: path to the pickle file
        normalize: if True, apply z-score normalization

    Returns:
        np.ndarray with the CDM signal
    """
    sim = pd.read_pickle(trial_path)
    cdm = sim[3]['EE'] + sim[3]['IE'] + sim[3]['EI'] + sim[3]['II']

    # Discard transient time
    transient_samples = int(FS * TRANSIENT_TIME)
    cdm = cdm[transient_samples:]

    if normalize:
        cdm = (cdm - np.mean(cdm)) / np.std(cdm)

    return cdm


def create_features_extractor(fs, frequency_range, window_size_sec, dfa_threshold):
    """
    Create a Features object configured for fEI/DFA analysis.

    Args:
        fs: sampling frequency
        frequency_range: [fmin, fmax] for band-pass filtering
        window_size_sec: fEI window size in seconds
        dfa_threshold: DFA threshold below which fEI is set to NaN

    Returns:
        Features: configured object for fEI computation
    """
    params = {
        'sampling_frequency': fs,
        'frequency_range': frequency_range,
        'window_size_sec': window_size_sec,
        'dfa_threshold': dfa_threshold,
        'normalize': False,
    }
    return Features(method='fEI', params=params)


def create_dataframe(CONF_PATH):
    """
    Process a single configuration directory and compute DFA/fEI features.

    Args:
        CONF_PATH: full path to the configuration directory

    Returns:
        pd.DataFrame with results, or empty DataFrame if no valid trials
    """
    conf_split = CONF_PATH.rstrip('/').split('/')
    conf = conf_split[-1]
    model_type = conf_split[5]
    param = conf_split[6].split('-')[0]

    print(CONF_PATH)
    print(conf)
    print(param)

    # Create features extractor
    features_extractor = create_features_extractor(
        fs=FS,
        frequency_range=FREQUENCY_RANGE,
        window_size_sec=WINDOW_SIZE_SEC,
        dfa_threshold=DFA_THRESHOLD,
    )

    # Parse configuration values
    confs = conf.split('_')
    if param == 'J_EE_J_II':
        configs = (float(confs[0]), float(confs[3]))
    elif param == 'J_IE_J_EI':
        configs = (float(confs[1]), float(confs[2]))
    elif param == 'J_EE_J_IE':
        configs = (float(confs[0]), float(confs[1]))
    elif param == 'J_EI_J_II':
        configs = (float(confs[2]), float(confs[3]))
    else:
        configs = float(confs[PARAMETERS.index(param)])

    # Get valid trials
    trials = [t for t in os.listdir(CONF_PATH)
              if t.startswith('valid') and t.endswith('.pkl')]
    trials = sorted(trials)

    result_dic = {
        'ID': [],
        'Trial': [],
        'Group': [],
        'DFA': [],
        'fEI': [],
        'fEI_raw': [],
        'num_outliers': [],
    }

    for i, trial in enumerate(trials):
        trial_path = os.path.join(CONF_PATH, trial)
        signal = load_cdm(trial_path, normalize=True)

        try:
            result = features_extractor.fEI(sample=signal)
        except Exception as e:
            print(f"Error processing trial {trial}: {e}")
            continue

        # Extract DFA value (1-channel -> squeeze)
        dfa_val = np.squeeze(result['DFA'])
        fei_outliers = np.squeeze(result['fEI'])
        fei_raw = np.squeeze(result['fEI_val'])
        n_outliers = np.squeeze(result['num_outliers'])

        result_dic['ID'].append(param)
        result_dic['Trial'].append(i)
        result_dic['Group'].append(configs)
        result_dic['DFA'].append(float(dfa_val))
        result_dic['fEI'].append(float(fei_outliers))
        result_dic['fEI_raw'].append(float(fei_raw))
        result_dic['num_outliers'].append(float(n_outliers))

    return pd.DataFrame(result_dic)


def create_parameter_df(PARAM_PATH):
    """
    Create a DataFrame for one parameter with all configurations.
    """
    configurations = os.listdir(PARAM_PATH)
    dfs = []
    for conf in configurations:
        conf_path = os.path.join(PARAM_PATH, conf)
        if not os.path.isdir(conf_path):
            continue
        conf_df = create_dataframe(conf_path)
        if conf_df.empty:
            print(f"{conf_path} has no valid trials. Skipping configuration.")
            continue
        dfs.append(conf_df)

    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='DFA and fEI analysis of CDM signals using ncpi.Features'
    )
    parser.add_argument('conf_path', type=str, help='Path to the parameter directory')
    parser.add_argument('--output_dir', type=str, default='results', help='Output directory')

    args = parser.parse_args()

    conf_path = args.conf_path
    conf_split = conf_path.rstrip('/').split('/')
    param = conf_split[6]
    print(param)
    if param != 'J_ext':
        file_name = f"{param}-{conf_split[-1]}-{FREQUENCY_RANGE[0]}_{FREQUENCY_RANGE[1]}"
    else:
        file_name = f"{param}-{FREQUENCY_RANGE[0]}_{FREQUENCY_RANGE[1]}"

    df = create_parameter_df(args.conf_path)

    os.makedirs(args.output_dir, exist_ok=True)
    df.to_pickle(os.path.join(args.output_dir, f"18-fei_dfa-{file_name}.pkl"))
