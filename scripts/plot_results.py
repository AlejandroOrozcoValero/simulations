"""
plot_results.py - Genera plots a partir de simulaciones ya ejecutadas.

Lee las carpetas de resultados en save_path. Cada subcarpeta tiene como nombre
los 7 valores de parametros separados por guion bajo (generados por v4).

Genera la misma figura que example_full_pipeline.py:
  - A: Raster plots, firing rates y CDM para 3 configuraciones seleccionadas
  - B: Power spectrum (todas las configuraciones superpuestas)
  - C: Features (1/f slope, DFA, RS range, high fluct.) vs configuraciones

Uso:
    python plot_results.py --save-path /SCRATCH/.../results
"""

import sys
import os
import pickle
import numpy as np
import pandas as pd
import scipy.signal as ss
from matplotlib import pyplot as plt
import argparse
import ncpi

# Nombres de features catch22
try:
    import pycatch22
    catch22_names = pycatch22.catch22_all([0])['names']
except Exception:
    catch22_names = ['DN_HistogramMode_5',
                     'DN_HistogramMode_10',
                     'CO_f1ecac',
                     'CO_FirstMin_ac',
                     'CO_HistogramAMI_even_2_5',
                     'CO_trev_1_num',
                     'MD_hrv_classic_pnn40',
                     'SB_BinaryStats_mean_longstretch1',
                     'SB_TransitionMatrix_3ac_sumdiagcov',
                     'PD_PeriodicityWang_th0_01',
                     'CO_Embed2_Dist_tau_d_expfit_meandiff',
                     'IN_AutoMutualInfoStats_40_gaussian_fmmi',
                     'FC_LocalSimple_mean1_tauresrat',
                     'DN_OutlierInclude_p_001_mdrmd',
                     'DN_OutlierInclude_n_001_mdrmd',
                     'SP_Summaries_welch_rect_area_5_1',
                     'SB_BinaryStats_diff_longstretch0',
                     'SB_MotifThree_quantile_hh',
                     'SC_FluctAnal_2_rsrangefit_50_1_logi_prop_r1',
                     'SC_FluctAnal_2_dfa_50_1_2_logi_prop_r1',
                     'SP_Summaries_welch_rect_centroid',
                     'FC_LocalSimple_mean3_stderr']

# =============================================================================
# FUNCIONES AUXILIARES (definidas antes de main)
# =============================================================================

def parse_folder_values(folder_name):
    """Parsea los valores de parametros del nombre de carpeta '0.5_0.5_-23.84_...'"""
    return [float(v) for v in folder_name.split('_')]


def get_spike_rate(times, transient, dt, tstop):
    bins = np.arange(transient, tstop + dt, dt)
    hist, _ = np.histogram(times, bins=bins)
    return bins, hist.astype(float)


def format_param_title(param_name, param_value):
    """Formatea un parametro con nombre LaTeX para titulo de plot."""
    latex_map = {
        'J_ext': r'$J_{syn}^{ext}$',
        'J_EE': r'$J_{EE}$', 'J_IE': r'$J_{IE}$',
        'J_EI': r'$J_{EI}$', 'J_II': r'$J_{II}$',
        'tau_syn_E': r'$\tau_{syn}^{E}$',
        'tau_syn_I': r'$\tau_{syn}^{I}$',
    }
    units_map = {
        'J_ext': 'nA', 'J_EE': 'nA', 'J_IE': 'nA',
        'J_EI': 'nA', 'J_II': 'nA',
        'tau_syn_E': 'ms', 'tau_syn_I': 'ms',
    }
    label = latex_map.get(param_name, param_name)
    unit = units_map.get(param_name, '')
    return f'{label} = {param_value} {unit}'.strip()


def get_config_title(conf_meta, swept_names):
    """Genera titulo para una configuracion."""
    if len(swept_names) == 0:
        return 'Config'
    elif len(swept_names) == 1:
        pname = swept_names[0]
        return format_param_title(pname, conf_meta[pname])
    else:
        parts = [f'{pn}={conf_meta[pn]}' for pn in swept_names]
        return ', '.join(parts)


def get_config_label(conf_meta, swept_names):
    """Genera label de leyenda para una configuracion."""
    if len(swept_names) == 0:
        return 'Config'
    elif len(swept_names) == 1:
        pname = swept_names[0]
        return format_param_title(pname, conf_meta[pname])
    else:
        parts = [f'{pn}={conf_meta[pn]}' for pn in swept_names]
        return ', '.join(parts)


def get_xlabel(swept_names):
    """Genera etiqueta para eje X de plots de features."""
    if len(swept_names) == 0:
        return 'Config'
    elif len(swept_names) == 1:
        pname = swept_names[0]
        latex_map = {
            'J_ext': r'$J_{syn}^{ext}$ (nA)',
            'J_EE': r'$J_{EE}$ (nA)', 'J_IE': r'$J_{IE}$ (nA)',
            'J_EI': r'$J_{EI}$ (nA)', 'J_II': r'$J_{II}$ (nA)',
            'tau_syn_E': r'$\tau_{syn}^{E}$ (ms)',
            'tau_syn_I': r'$\tau_{syn}^{I}$ (ms)',
        }
        return latex_map.get(pname, pname)
    else:
        return '_'.join(swept_names)


# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def main():
    # =============================================================================
    # ARGPARSE (solo save_path)
    # =============================================================================

    parser = argparse.ArgumentParser(description='Genera plots de simulaciones')
    parser.add_argument('--save-path', type=str, required=True,
                        help='Ruta donde estan las carpetas de resultados')
    parser.add_argument('--figname', type=str, required=True)
    args = parser.parse_args()

    # =============================================================================
    # CONFIGURACION (modificar aqui segun necesidad)
    # =============================================================================

    # Indices de las configuraciones a mostrar en raster/FR/CDM (0-indexed, acepta negativos)
    conf_to_plot = [0, 5, -1]

    # Numero de trials por configuracion
    trials = 6

    # Directorio y nombre de la figura de salida
    figure_dir = 'results'
    figure_name = args.figname

    # =============================================================================
    # DESCUBRIR CONFIGURACIONES desde las carpetas en save_path
    # =============================================================================

    param_order = ['J_EE', 'J_IE', 'J_EI', 'J_II', 'tau_syn_E', 'tau_syn_I', 'J_ext']

    # Listar subdirectorios y ordenarlos numericamente
    config_dirs = []
    for d in os.listdir(args.save_path):
        full_path = os.path.join(args.save_path, d)
        if os.path.isdir(full_path):
            try:
                parse_folder_values(d)
                config_dirs.append(d)
            except ValueError:
                pass  # ignorar carpetas que no siguen el formato

    config_dirs.sort(key=parse_folder_values)
    num_configs = len(config_dirs)

    if num_configs == 0:
        print(f"ERROR: No se encontraron carpetas de configuracion en {args.save_path}")
        sys.exit(1)

    # Extraer valores y detectar parametros barridos automaticamente
    all_values = [parse_folder_values(d) for d in config_dirs]

    swept_param_names = []
    for i, p in enumerate(param_order):
        unique_vals = set(v[i] for v in all_values)
        if len(unique_vals) > 1:
            swept_param_names.append(p)

    # Metadata por configuracion (todos los parametros)
    conf_metadata = [
        {p: all_values[k][i] for i, p in enumerate(param_order)}
        for k in range(num_configs)
    ]

    print(f"Configuraciones encontradas: {num_configs}")
    print(f"Parametros barridos: {swept_param_names if swept_param_names else '(ninguno)'}")
    print(f"Trials: {trials}")
    print(f"Configuraciones a plotear (raster/FR/CDM): {conf_to_plot}")

    # =============================================================================
    # CARGAR TODOS LOS PICKLES
    # =============================================================================

    spikes = [[] for _ in range(trials)]
    CDMs = [[] for _ in range(trials)]

    dt = None
    tstop = None
    transient = None
    P_X = None

    for trial in range(trials):
        for k in range(num_configs):
            result_dir = os.path.join(args.save_path, config_dirs[k])

            valid_file = os.path.join(result_dir, f'valid_trial_{trial}.pkl')
            novalid_file = os.path.join(result_dir, f'novalid_trial_{trial}.pkl')

            filepath = None
            if os.path.exists(valid_file):
                filepath = valid_file
            elif os.path.exists(novalid_file):
                filepath = novalid_file

            if filepath is None:
                print(f"AVISO: No se encontro archivo para config {k} ({config_dirs[k]}), trial {trial}")
                spikes[trial].append(None)
                CDMs[trial].append(None)
                continue

            with open(filepath, 'rb') as f:
                loaded_data = pickle.load(f)

            if isinstance(loaded_data[0], dict) and 'J_EE' in loaded_data[0]:
                _config, times, gids, CDM_data, dt, tstop, transient, P_X, N_X, metrics = loaded_data
            else:
                times, gids, CDM_data, dt, tstop, transient, P_X, N_X, metrics = loaded_data

            spikes[trial].append([times, gids])
            CDMs[trial].append(CDM_data)

            if trial == 0 and k == 0:
                print(f"  dt={dt}, tstop={tstop}, transient={transient}, P_X={P_X}")

    if dt is None:
        print("ERROR: No se pudo cargar ningun archivo de simulacion.")
        sys.exit(1)

    print(f"\nDatos cargados correctamente.")

    # =============================================================================
    # CREAR FIGURA (misma disposicion que example_full_pipeline_v3.py)
    # =============================================================================

    fig = plt.figure(figsize=(7.5, 6.), dpi=300)
    plt.rcParams.update({'font.size': 10, 'font.family': 'Arial'})
    plt.rc('xtick', labelsize=6)
    plt.rc('ytick', labelsize=6)

    T = [4000, 4100]

    # =============================================================================
    # A: RASTER PLOTS
    # =============================================================================

    for j, col in enumerate(conf_to_plot):
        if spikes[0][col] is None:
            continue
        ax = fig.add_axes([0.1 + j * 0.3, 0.72, 0.25, 0.2])
        title = get_config_title(conf_metadata[col], swept_param_names)
        ax.set_title(title, fontsize=8)

        # Raster
        X_X = P_X
        for i, X in enumerate(X_X):
            sp = spikes[0][col]
            xp = sp[0][X]
            yp = sp[1][X]
            ii = (xp >= T[0]) & (xp <= T[1])
            xp = xp[ii]
            yp = yp[ii]
            ax.plot(xp, yp, '.', color='C{}'.format(i), markersize=2)

        if j == 0:
            ax.set_ylabel('gid')
            ax.yaxis.set_label_coords(-0.22, 0.5)
        ax.set_yticks([])
        ax.axis('tight')
        ax.set_xticklabels([])
        ax.set_xticks([])

    # =============================================================================
    # FIRING RATES
    # =============================================================================

    for j, col in enumerate(conf_to_plot):
        if spikes[0][col] is None:
            continue
        ax = fig.add_axes([0.1 + j * 0.3, 0.60, 0.25, 0.12])

        for i, X in enumerate(P_X):
            bins, spike_rate = get_spike_rate(spikes[0][col][0][X], transient, dt, tstop)
            bins = bins[:-1]
            ii = (bins >= T[0]) & (bins <= T[1])
            ax.plot(bins[ii], spike_rate[ii], color='C{}'.format(i),
                    label=r'$\nu_\mathrm{%s}$' % X)

        if j == 0:
            ax.legend(loc=1)
            ax.set_ylabel(r'$\nu_X$ (spik./$\Delta t$)')
            ax.yaxis.set_label_coords(-0.22, 0.5)
        ax.axis('tight')
        ax.set_xticklabels([])
        ax.set_xticks([])

    # =============================================================================
    # CDMs
    # =============================================================================

    for j, col in enumerate(conf_to_plot):
        if CDMs[0][col] is None:
            continue
        ax = fig.add_axes([0.1 + j * 0.3, 0.47, 0.25, 0.12])
        CDM = CDMs[0][col]['EE'] + CDMs[0][col]['EI'] + CDMs[0][col]['IE'] + CDMs[0][col]['II']
        bins_cdm = np.arange(transient, tstop, dt)
        bins_cdm = bins_cdm[::10]  # decimate ratio
        ii = (bins_cdm >= T[0]) & (bins_cdm <= T[1])
        ax.plot(bins_cdm[ii], CDM[ii], color='k')

        if j == 0:
            ax.set_ylabel(r'CDM ($P_z$)')
            ax.yaxis.set_label_coords(-0.22, 0.5)
        ax.set_yticks([])
        ax.set_xlabel('t (ms)')
        ax.axis('tight')

        # Escala
        y_max = np.max(CDM[ii])
        y_min = np.min(CDM[ii])
        scale = (y_max - y_min) / 5
        x_pos = T[0] if j < 2 else T[0] + 50
        ax.plot([x_pos, x_pos], [y_min + scale, y_min], 'k')
        ax.text(x_pos + 1, y_min + scale / 4.,
                r'$2^{%s}nAcm$' % np.round(np.log2(scale * 10**(-4))), fontsize=8)

    # =============================================================================
    # B: POWER SPECTRA (todas las configuraciones)
    # =============================================================================

    ax_psd = fig.add_axes([0.1, 0.07, 0.35, 0.3])

    if num_configs <= 10:
        cmap = plt.get_cmap('tab10')
    else:
        cmap = plt.get_cmap('tab20')

    for col in range(num_configs):
        trial_cdms = []
        for trial in range(trials):
            if CDMs[trial][col] is not None:
                trial_cdms.append(
                    CDMs[trial][col]['EE'] + CDMs[trial][col]['EI'] +
                    CDMs[trial][col]['IE'] + CDMs[trial][col]['II']
                )

        if len(trial_cdms) == 0:
            continue

        f, Pxx = ss.welch(np.array(trial_cdms), fs=1000. / (10. * dt))
        Pxx = np.mean(Pxx, axis=0)
        Pxx = Pxx / np.sum(Pxx)

        f_mask = (f >= 0) & (f <= 200)
        label = get_config_label(conf_metadata[col], swept_param_names)
        color = cmap(col / max(num_configs - 1, 1)) if num_configs > 1 else 'C0'

        ax_psd.semilogy(f[f_mask], Pxx[f_mask], label=label, color=color)

    ax_psd.legend(loc='upper right', fontsize=5.5, labelspacing=0.2)
    ax_psd.set_xlabel('Frequency (Hz)')
    ax_psd.set_ylabel('Normalized power')

    # =============================================================================
    # C: FEATURES (catch22 + specparam, como en example_full_pipeline.py)
    # =============================================================================

    # Recopilar CDMs para features
    all_CDMs_list = []
    IDs = []
    epochs = []
    for trial in range(trials):
        for k in range(num_configs):
            if CDMs[trial][k] is not None:
                all_CDMs_list.append(
                    CDMs[trial][k]['EE'] + CDMs[trial][k]['EI'] +
                    CDMs[trial][k]['IE'] + CDMs[trial][k]['II']
                )
                IDs.append(k)
                epochs.append(trial)

    IDs = np.array(IDs)
    fs = 1000. / (10. * dt)

    print('\n--- Calculando features ---')

    all_features = {}
    all_methods = ['catch22', 'power_spectrum_parameterization']

    for method in all_methods:
        print(f'  Metodo: {method}')

        df = pd.DataFrame({
            'ID': IDs.tolist(),
            'Group': IDs.tolist(),
            'Epoch': epochs,
            'Sensor': np.zeros(len(IDs)),
            'Data': all_CDMs_list
        })
        df.Recording = 'LFP'
        df.fs = fs

        if method == "catch22":
            feat_obj = ncpi.Features(method="catch22", params={"normalize": True})
            feats = feat_obj.compute_features(df["Data"].to_list())
            df = df.copy()
            df["Features"] = feats

        elif method == "power_spectrum_parameterization":
            fooof_setup_sim = {
                "peak_threshold": 1.0,
                "min_peak_height": 0.0,
                "max_n_peaks": 5,
                "peak_width_limits": (10.0, 50.0),
            }

            feat_obj = ncpi.Features(
                method="specparam",
                params={
                    "fs": fs,
                    "freq_range": (5.0, 200.0),
                    "specparam_model": dict(fooof_setup_sim),
                    "r_squared_th": 0.9,
                },
            )

            feats = feat_obj.compute_features(df["Data"].to_list())
            df = df.copy()
            df["Features"] = [float(np.asarray(d["aperiodic_params"])[1]) for d in feats]

        all_features[method] = df

    # --- Plots de features (2x2 grid como en example_full_pipeline.py) ---

    plot_colors = ['lightcoral', 'lightblue', 'lightgreen', 'lightgrey']

    for row in range(2):
        for col_idx in range(2):
            ax = fig.add_axes([0.5 + col_idx * 0.27, 0.24 - row * 0.16, 0.18, 0.13])

            if row == 0 and col_idx == 0:
                feats = np.array(all_features['power_spectrum_parameterization']['Features'].tolist())
                ax.set_ylabel(r'$1/f$' + ' ' + r'$slope$')
            elif row == 0 and col_idx == 1:
                feats = np.array(all_features['catch22']['Features'].tolist())
                idx = catch22_names.index('SC_FluctAnal_2_dfa_50_1_2_logi_prop_r1')
                feats = feats[:, idx]
                ax.set_ylabel(r'$dfa$')
            elif row == 1 and col_idx == 0:
                feats = np.array(all_features['catch22']['Features'].tolist())
                idx = catch22_names.index('SC_FluctAnal_2_rsrangefit_50_1_logi_prop_r1')
                feats = feats[:, idx]
                ax.set_ylabel(r'$rs\ range$')
            elif row == 1 and col_idx == 1:
                feats = np.array(all_features['catch22']['Features'].tolist())
                idx = catch22_names.index('MD_hrv_classic_pnn40')
                feats = feats[:, idx]
                ax.set_ylabel(r'$high\ fluct.$')

            # Reorganizar features por configuracion
            feats_plot = np.full((trials, num_configs), np.nan)
            for conf in range(num_configs):
                conf_feats = feats[IDs == conf]
                if len(conf_feats) <= trials:
                    feats_plot[:len(conf_feats), conf] = conf_feats

            # Linea + fill_between
            means = np.nanmean(feats_plot, axis=0)
            stds = np.nanstd(feats_plot, axis=0)
            x = np.arange(num_configs)
            color = plot_colors[row * 2 + col_idx]

            ax.plot(x, means, color=color)
            ax.fill_between(x, means - stds, means + stds, color=color, alpha=0.3)

            # Etiquetas del eje X
            if row == 1:
                ax.set_xlabel(get_xlabel(swept_param_names), fontsize=6)
                ax.set_xticks(x)
                if len(swept_param_names) == 1:
                    pname = swept_param_names[0]
                    ax.set_xticklabels(
                        [f'{conf_metadata[i][pname]}' for i in range(num_configs)],
                        fontsize=5)
                elif len(swept_param_names) > 1:
                    labels = []
                    for i in range(num_configs):
                        values = [str(conf_metadata[i][pn]) for pn in swept_param_names]
                        labels.append(f"({', '.join(values)})")
                    ax.set_xticklabels(labels, fontsize=4)
                ax.tick_params(axis='x', rotation=45)
            else:
                ax.set_xticks([])
                ax.set_xticklabels([])

    # =============================================================================
    # LETRAS DE PANELES
    # =============================================================================

    ax_letters = fig.add_axes([0., 0., 1., 1.])
    ax_letters.axis('off')
    ax_letters.text(0.01, 0.97, 'A', fontsize=12, fontweight='bold')
    ax_letters.text(0.01, 0.37, 'B', fontsize=12, fontweight='bold')
    ax_letters.text(0.47, 0.37, 'C', fontsize=12, fontweight='bold')

    # =============================================================================
    # GUARDAR FIGURA
    # =============================================================================

    os.makedirs(figure_dir, exist_ok=True)
    figure_path = os.path.join(figure_dir, figure_name)
    plt.savefig(figure_path, bbox_inches='tight')
    print(f'\nFigura guardada en: {figure_path}')


# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================

if __name__ == '__main__':
    main()
