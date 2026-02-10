import matplotlib.pyplot as plt
import pandas as pd
import os
import numpy as np
from scipy.signal import welch
from scipy.stats import linregress
from fooof import FOOOF
import argparse


BASE_PATH = '/LUSTRE/home/TIC117/cmg/alejandro'
PARAMETERS = ['J_EE', 'J_IE', 'J_EI', 'J_II', 'tau_syn_E', 'tau_syn_I', 'J_ext']

def load_cdm(trial_path, normalize=True, index=2):
    """
    Carga un trial y extrae la señal CDM.

    Args:
        trial_path: ruta al archivo pickle
        normalize: si True, aplica z-score

    Returns:
        np.ndarray con la señal CDM
    """
    sim = pd.read_pickle(trial_path)
    print(sim)
    cdm = sim[index]['EE'] + sim[index]['IE'] + sim[index]['EI'] + sim[index]['II']
    if normalize:
        cdm = (cdm - np.mean(cdm)) / np.std(cdm)
    return cdm


def compute_fooof(signal, fs, nperseg=None, aperiodic_mode='fixed',
                  freq_range=(1., 150.), peak_width_limits=(0.5, 12),
                  max_n_peaks=5, r_squared_th=None):
    """
    Aplica FOOOF a una señal individual.

    Args:
        signal: np.ndarray con la señal CDM
        fs: frecuencia de muestreo
        nperseg: muestras por segmento welch (default: fs * 0.5)
        aperiodic_mode: 'fixed' o 'knee'
        freq_range: rango de frecuencias para el fit
        peak_width_limits: límites de ancho de pico
        max_n_peaks: número máximo de picos
        r_squared_th: si se especifica, retorna None si r2 < threshold

    Returns:
        dict con resultados FOOOF o None si no pasa el umbral
    """
    if nperseg is None:
        nperseg = int(fs * 0.5)

    fm = FOOOF(
        peak_width_limits=peak_width_limits,
        max_n_peaks=max_n_peaks,
        peak_threshold=2.0,
        min_peak_height=0.0,
        aperiodic_mode=aperiodic_mode,
        verbose=False
    )

    freqs, psd = welch(signal, fs, nperseg=nperseg)
    fm.fit(freqs=freqs, power_spectrum=psd, freq_range=freq_range)

    if r_squared_th is not None and fm.r_squared_ < r_squared_th:
        return None

    result = {
        'exponent': fm.aperiodic_params_[1],
        'offset': fm.aperiodic_params_[0],
        'r_squared': fm.r_squared_,
        'error': fm.error_,
        'n_peaks': len(fm.peak_params_),
        'peak_params': fm.peak_params_,
        'aperiodic_params': fm.aperiodic_params_,
    }

    if len(fm.peak_params_) > 0:
        result['central_freq'] = np.mean(fm.peak_params_[:, 0])
        result['power'] = np.mean(fm.peak_params_[:, 1])
        result['bandwidth'] = np.mean(fm.peak_params_[:, 2])
    else:
        result['central_freq'] = np.nan
        result['power'] = np.nan
        result['bandwidth'] = np.nan

    return result


def create_dataframe(CONF_PATH):
    conf_split = CONF_PATH.split('/')
    conf = conf_split[-2]
    print(CONF_PATH)
    print(conf)
    model_type = conf_split[5]
    param = conf_split[6]
    param = param.split('-')[0]  # J_EE_J_IE-v2 -> J_EE_J_IE
    if param != 'J_ext':
        jext_dir = os.path.basename(os.path.dirname(CONF_PATH))
    # Limpiar el nombre del parámetro (quitar -v2, etc)
    FS = 1000. / (10. * 0.0625)  # Sampling frequency
    print(param)

    file_name = f"{model_type}-{param}-{conf}"
    fooof_dic = {
        'ID': [],
        'Trial': [],
        'Group': [],
        'Exponent': [],
        'CentralFreq': [],
        'Power': []
    }


    trials = []
    for trial in os.listdir(CONF_PATH):
        if trial.startswith('valid') and trial.endswith('.pkl'):
            trials.append(trial)
    trials = sorted(trials)

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

    # Procesar cada trial individualmente
    for i, trial in enumerate(trials):
        trial_path = os.path.join(CONF_PATH, trial)

        # Cargar y normalizar la señal CDM
        signal = load_cdm(trial_path, normalize=True, index=3)

        # Calcular FOOOF para esta señal
        fooof_result = compute_fooof(
            signal=signal,
            fs=FS,
            freq_range=(1., 100.),
            r_squared_th=0.9  # Filtrar por r_squared >= 0.9
        )

        # Si el resultado no pasa el umbral, saltar
        if fooof_result is None:
            continue

        # Agregar al diccionario
        fooof_dic['ID'].append(param)
        fooof_dic['Trial'].append(i)
        fooof_dic['Group'].append(configs)
        fooof_dic['Exponent'].append(fooof_result['exponent'])
        fooof_dic['CentralFreq'].append(fooof_result['central_freq'])
        fooof_dic['Power'].append(fooof_result['power'])

    fooof_df = pd.DataFrame(fooof_dic)

    return fooof_df, file_name


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('conf_path', type=str)
    parser.add_argument('--output_dir', type=str, default='results')

    args = parser.parse_args()

    df, file_name = create_dataframe(args.conf_path)

    df.to_pickle(os.path.join(args.output_dir, f"15-fooof-{file_name}.pkl"))


