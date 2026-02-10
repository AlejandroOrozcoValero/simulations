import matplotlib.pyplot as plt
import pandas as pd
import os
import numpy as np
import argparse
from ncpi import Features


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


def create_features_extractor(fs, freq_range, nperseg, r_squared_th=None):
    """
    Crea un objeto Features configurado para el análisis espectral.

    Args:
        fs: frecuencia de muestreo
        freq_range: tupla (fmin, fmax) para el rango de frecuencias
        nperseg: muestras por segmento Welch
        r_squared_th: umbral de r_squared para filtrar resultados

    Returns:
        Features: objeto configurado para specparam
    """
    params = {
        'fs': fs,
        'freq_range': freq_range,
        'welch_kwargs': {'nperseg': nperseg},
        'normalize': False,  # Ya normalizamos en load_cdm
        'select_peak': 'max_pw',
    }

    if r_squared_th is not None:
        params['metric_thresholds'] = {'gof_rsquared': r_squared_th}
        params['metric_policy'] = 'reject'

    return Features(method='specparam', params=params)


def create_dataframe(CONF_PATH, freq_range=(5., 45.), nperseg=None, r_squared_th=0.9):
    """
    Crea un DataFrame con los resultados del análisis spectral.

    Args:
        CONF_PATH: ruta al directorio de configuración
        freq_range: tupla (fmin, fmax) para el rango de frecuencias del fit
        nperseg: muestras por segmento Welch (default: fs * 0.5)
        r_squared_th: umbral de r_squared para filtrar resultados

    Returns:
        tuple: (DataFrame con resultados, nombre del archivo)
    """
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

    # Configurar nperseg por defecto
    if nperseg is None:
        nperseg = int(FS * 0.5)

    # Crear el extractor de features
    features_extractor = create_features_extractor(
        fs=FS,
        freq_range=freq_range,
        nperseg=nperseg,
        r_squared_th=r_squared_th
    )

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

        # Calcular features usando ncpi.Features
        result = features_extractor.specparam(sample=signal)

        # Si el resultado no es válido (no pasa el umbral), saltar
        if not result.get('valid', True):
            continue

        # Extraer el exponente (segundo elemento de aperiodic_params)
        aperiodic_params = result['aperiodic_params']
        exponent = aperiodic_params[1] if len(aperiodic_params) > 1 else np.nan

        # Agregar al diccionario
        fooof_dic['ID'].append(param)
        fooof_dic['Trial'].append(i)
        fooof_dic['Group'].append(configs)
        fooof_dic['Exponent'].append(exponent)
        fooof_dic['CentralFreq'].append(result['peak_cf'])
        fooof_dic['Power'].append(result['peak_pw'])

    fooof_df = pd.DataFrame(fooof_dic)

    return fooof_df, file_name


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Análisis espectral de señales CDM usando ncpi.Features'
    )
    parser.add_argument('conf_path', type=str, help='Ruta al directorio de configuración')
    parser.add_argument('--output_dir', type=str, default='results', help='Directorio de salida')
    parser.add_argument('--freq_min', type=float, default=5.0, help='Frecuencia mínima del rango (Hz)')
    parser.add_argument('--freq_max', type=float, default=45.0, help='Frecuencia máxima del rango (Hz)')
    parser.add_argument('--nperseg', type=int, default=None, help='Muestras por segmento Welch (default: fs * 0.5)')
    parser.add_argument('--r_squared_th', type=float, default=0.9, help='Umbral de r_squared para filtrar')

    args = parser.parse_args()

    freq_range = (args.freq_min, args.freq_max)

    df, file_name = create_dataframe(
        args.conf_path,
        freq_range=freq_range,
        nperseg=args.nperseg,
        r_squared_th=args.r_squared_th
    )

    df.to_pickle(os.path.join(args.output_dir, f"15-fooof-{file_name}.pkl"))


