"""
15_plot_fooof_results.py - Genera figura con resultados de FOOOF/specparam

Genera una figura donde:
- Cada columna es un parámetro
- Cada fila es una feature de specparam (Exponent, CentralFreq, Power)

Uso:
    python 15_plot_fooof_results.py --results_dir results --output_dir results/15
"""

import os
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from glob import glob
import seaborn as sns

# Configuración de estilo
sns.set_style("whitegrid")
plt.rcParams['font.size'] = 10
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['figure.titlesize'] = 14

# Parámetros posibles
PARAMETERS = ['J_EE', 'J_IE', 'J_EI', 'J_II', 'tau_syn_E', 'tau_syn_I', 'J_ext']
FEATURES = ['Exponent', 'CentralFreq', 'Power']

# Mapeo de nombres a LaTeX
PARAM_LABELS = {
    'J_EE': r'$J_{EE}$ (nA)',
    'J_IE': r'$J_{IE}$ (nA)',
    'J_EI': r'$J_{EI}$ (nA)',
    'J_II': r'$J_{II}$ (nA)',
    'tau_syn_E': r'$\tau_{syn}^{E}$ (ms)',
    'tau_syn_I': r'$\tau_{syn}^{I}$ (ms)',
    'J_ext': r'$J_{ext}$ (nA)'
}

FEATURE_LABELS = {
    'Exponent': 'Exponent (1/f)',
    'CentralFreq': 'Central Frequency (Hz)',
    'Power': 'Peak Power (dB)'
}


def load_all_fooof_results(results_dir, jext_filter=None):
    """
    Carga todos los archivos pickle con resultados de fooof.
    
    Args:
        results_dir: directorio con archivos .pkl
        jext_filter: valor de J_ext para filtrar (29.89 o 32), o None para no filtrar
        
    Returns:
        dict: diccionario con DataFrames por parámetro
    """
    pattern = os.path.join(results_dir, '15-fooof-*.pkl')
    pkl_files = glob(pattern)
    
    if not pkl_files:
        raise ValueError(f"No se encontraron archivos en {results_dir} con patrón 15-fooof-*.pkl")
    
    print(f"Encontrados {len(pkl_files)} archivos de resultados")
    if jext_filter is not None:
        print(f"Filtrando por J_ext = {jext_filter}")
    
    # Agrupar por parámetro
    data_by_param = {param: [] for param in PARAMETERS}
    
    for pkl_file in pkl_files:
        df = pd.read_pickle(pkl_file)
        
        # Identificar el parámetro del archivo
        param = df['ID'].iloc[0] if len(df) > 0 else None
        
        if param not in PARAMETERS:
            continue
        
        # Si estamos analizando J_ext, no filtrar
        # Si analizamos otro parámetro, filtrar por J_ext
        if param != 'J_ext' and jext_filter is not None:
            # Extraer J_ext del nombre del archivo
            # Formato: 15-fooof-no_plast-J_EE_J_IE-0.5_0.5_-23.84_-8.441_0.5_0.5_29.89.pkl
            basename = os.path.basename(pkl_file)
            jext_str = basename.split('_')[-1].replace('.pkl', '')
            try:
                jext_value = float(jext_str)
                if abs(jext_value - jext_filter) > 0.01:  # Tolerancia para comparación float
                    continue
            except ValueError:
                print(f"  Advertencia: no se pudo extraer J_ext de {basename}")
                continue
        
        data_by_param[param].append(df)
        print(f"  {os.path.basename(pkl_file)}: {param}, {len(df)} muestras")
    
    # Concatenar DataFrames por parámetro
    combined_data = {}
    for param, dfs in data_by_param.items():
        if dfs:
            combined_data[param] = pd.concat(dfs, ignore_index=True)
            print(f"Parámetro {param}: {len(combined_data[param])} muestras totales")
    
    return combined_data


def prepare_plot_data(data_by_param):
    """
    Prepara los datos para el plot, organizando por grupo de configuración.
    
    Args:
        data_by_param: dict con DataFrames por parámetro
        
    Returns:
        dict: datos organizados para plotting
    """
    plot_data = {}
    
    for param, df in data_by_param.items():
        if df is None or len(df) == 0:
            continue
        
        # Agrupar por configuración (Group)
        grouped = df.groupby('Group').agg({
            'Exponent': ['mean', 'std'],
            'CentralFreq': ['mean', 'std'],
            'Power': ['mean', 'std']
        }).reset_index()
        
        # Extraer valores de configuración
        if isinstance(grouped['Group'].iloc[0], tuple):
            # Para parámetros dobles (J_EE_J_IE, etc.)
            # Tomamos solo el primer valor del tuple como x-axis
            x_values = [g[0] for g in grouped['Group']]
        else:
            x_values = grouped['Group'].values
        
        plot_data[param] = {
            'x': np.array(x_values),
            'Exponent_mean': grouped[('Exponent', 'mean')].values,
            'Exponent_std': grouped[('Exponent', 'std')].values,
            'CentralFreq_mean': grouped[('CentralFreq', 'mean')].values,
            'CentralFreq_std': grouped[('CentralFreq', 'std')].values,
            'Power_mean': grouped[('Power', 'mean')].values,
            'Power_std': grouped[('Power', 'std')].values,
        }
    
    return plot_data


def plot_fooof_grid(plot_data, output_path, jext_value=None):
    """
    Genera la figura con grid de parámetros x features.
    
    Args:
        plot_data: datos organizados para plotting
        output_path: ruta donde guardar la figura
        jext_value: valor de J_ext usado (para el título), o None
    """
    # Determinar parámetros disponibles
    available_params = [p for p in PARAMETERS if p in plot_data and plot_data[p]]
    n_params = len(available_params)
    n_features = len(FEATURES)
    
    if n_params == 0:
        raise ValueError("No hay datos disponibles para plotear")
    
    # Crear figura
    fig, axes = plt.subplots(n_features, n_params, figsize=(4*n_params, 3*n_features))
    
    # Asegurar que axes sea 2D
    if n_params == 1 and n_features == 1:
        axes = np.array([[axes]])
    elif n_params == 1:
        axes = axes.reshape(-1, 1)
    elif n_features == 1:
        axes = axes.reshape(1, -1)
    
    # Plotear cada combinación
    for col_idx, param in enumerate(available_params):
        data = plot_data[param]
        x = data['x']
        
        for row_idx, feature in enumerate(FEATURES):
            ax = axes[row_idx, col_idx]
            
            y_mean = data[f'{feature}_mean']
            y_std = data[f'{feature}_std']
            
            # Plot con error bars
            ax.errorbar(x, y_mean, yerr=y_std, 
                       marker='o', markersize=6, 
                       linewidth=2, capsize=4,
                       label=feature, color='C0')
            
            # Títulos solo en la primera fila
            if row_idx == 0:
                ax.set_title(PARAM_LABELS.get(param, param), fontsize=12, fontweight='bold')
            
            # Labels en los ejes externos
            if col_idx == 0:
                ax.set_ylabel(FEATURE_LABELS.get(feature, feature), fontsize=11)
            
            if row_idx == n_features - 1:
                ax.set_xlabel('Parameter Value', fontsize=11)
            
            # Grid y estética
            ax.grid(True, alpha=0.3)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
    
    # Título general si se especifica J_ext
    if jext_value is not None:
        fig.suptitle(f'FOOOF Analysis Results (J_ext = {jext_value} nA)', 
                    fontsize=16, fontweight='bold', y=0.995)
    
    plt.tight_layout()
    
    # Guardar figura
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Figura guardada en: {output_path}")
    
    plt.close()


def main():
    parser = argparse.ArgumentParser(
        description='Genera figura con resultados de análisis FOOOF/specparam'
    )
    parser.add_argument('--results_dir', type=str, default='results',
                       help='Directorio con archivos .pkl de resultados')
    parser.add_argument('--output_dir', type=str, default='results/15',
                       help='Directorio de salida para la figura')
    parser.add_argument('--output_name', type=str, default='15_FOOOF_grid.png',
                       help='Nombre del archivo de salida')
    parser.add_argument('--jext', type=float, default=None,
                       help='Valor de J_ext para filtrar (29.89 o 32). Si no se especifica, genera ambas figuras')
    parser.add_argument('--all', action='store_true',
                       help='Generar figuras para ambos valores de J_ext')
    
    args = parser.parse_args()
    
    # Crear directorio de salida si no existe
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Determinar qué valores de J_ext procesar
    jext_values = []
    if args.all:
        jext_values = [29.89, 32]
        print("Modo: Generar figuras para ambos J_ext")
    elif args.jext is not None:
        jext_values = [args.jext]
        print(f"Modo: Generar figura solo para J_ext = {args.jext}")
    else:
        # Por defecto, generar ambas
        jext_values = [29.89, 32]
        print("Modo: Generar figuras para ambos J_ext (default)")
    
    # Procesar cada valor de J_ext
    for jext_val in jext_values:
        print(f"\n{'='*50}")
        print(f"Procesando J_ext = {jext_val}")
        print('='*50)
        
        # Cargar datos
        print("\nCargando resultados de FOOOF...")
        data_by_param = load_all_fooof_results(args.results_dir, jext_filter=jext_val)
        
        if not data_by_param:
            print(f"No se encontraron datos para J_ext = {jext_val}")
            continue
        
        # Preparar datos para plot
        print("\nPreparando datos para plot...")
        plot_data = prepare_plot_data(data_by_param)
        
        # Generar figura
        print("\nGenerando figura...")
        # Modificar nombre del archivo para incluir J_ext
        base_name = args.output_name.replace('.png', '')
        output_name = f"{base_name}_Jext{jext_val:.2f}.png"
        output_path = os.path.join(args.output_dir, output_name)
        
        plot_fooof_grid(plot_data, output_path, jext_value=jext_val)
    
    print("\n¡Listo!")


if __name__ == "__main__":
    main()
