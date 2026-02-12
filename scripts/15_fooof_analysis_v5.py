"""
Created 12/02/2026 by Alejandro Orozco Valero
It reads simulations of one parameter and compute specparam features
and a plot to check results.
"""
import matplotlib.pyplot as plt
import pandas as pd
import os
import numpy as np
import argparse
from ncpi import Features


PARAMETERS = ['J_EE', 'J_IE', 'J_EI', 'J_II', 'tau_syn_E', 'tau_syn_I', 'J_ext']
FREQ_RANGE = (5., 200.)
R2=0.9

def load_cdm(trial_path, normalize=True):
    """
    Load a trial and extract CDM.
    
    """

    sim = pd.read_pickle(trial_path)
    cdm = sim[3]['EE'] + sim[3]['IE'] + sim[3]['EI'] + sim[3]['II'] 

    if normalize:
        cdm = (cdm - np.mean(cdm)) / np.std(cdm)

    return cdm

def create_features_extractor(fs, freq_range, nperseg, r_squared_th=0.9):
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
    specparam_setup = {
        'peak_threshold': 1.,
        'min_peak_height': 0.0,
        'max_n_peaks': 5,
        'peak_width_limits': (10., 50.)
    }
    params = {
        'fs': fs,
        'freq_range': freq_range,
        'welch_kwargs': {'nperseg': nperseg},
        'normalize': False,  # Ya normalizamos en load_cdm
        'r_squared_th': r_squared_th,
        'specparam_model': dict(specparam_setup)
    }


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
    conf_split = CONF_PATH.rstrip('/').split('/')
    conf = conf_split[-1]
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
        signal = load_cdm(trial_path, normalize=True)

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

    return fooof_df

def create_parameter_df(PARAM_PATH, freq_range, r_squared_th):
    """
    Create a DataFrame for one parameter with all configurations.
    
    """

    configurations = os.listdir(PARAM_PATH)
    dfs = []
    for i, conf in enumerate(configurations):
        conf_path = os.path.join(PARAM_PATH, conf)

        conf_df = create_dataframe(conf_path,
                                   freq_range=freq_range,
                                   r_squared_th=r_squared_th,
                                   )
        dfs.append(conf_df)

    return pd.concat(dfs, ignore_index=True)

    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Análisis espectral de señales CDM usando ncpi.Features'
    )
    parser.add_argument('conf_path', type=str, help='Ruta al directorio de configuración')
    parser.add_argument('--output_dir', type=str, default='results', help='Directorio de salida')
    

    args = parser.parse_args()


    conf_path = args.conf_path
    conf_split = conf_path.rstrip('/').split('/')
    param = conf_split[6]
    print(param)
    if param != 'J_ext':
        file_name = f"{param}-{conf_split[-1]}"
    else:
        file_name = param

    df = create_parameter_df(
        args.conf_path,
        freq_range=FREQ_RANGE,
        r_squared_th=R2,
    )

    df.to_pickle(os.path.join(args.output_dir, f"15-fooof-{file_name}.pkl"))