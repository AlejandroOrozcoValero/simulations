#!/bin/bash
#SBATCH --job-name=nonlinear_analysis
#SBATCH --output=logs/nonlinear_analysis-%j.out
#SBATCH --error=logs/nonlinear_analysis-%j.err
#SBATCH --time=01:00:00
#SBATCH --partition=albaicin
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=alexoroval@ugr.es

# Recibe como argumento el directorio de configuración
CONF_PATH="${1}"

if [ -z "$CONF_PATH" ]; then
    echo "Error: se requiere el directorio de configuración como argumento"
    echo "Uso: sbatch job_nonlinear_analysis.sh <config_dir>"
    exit 1
fi

# Cargar bashrc y activar conda
source ~/.bashrc
conda activate ncpi-env

if [ $? -ne 0 ]; then
    echo "Error: No se pudo activar el entorno conda 'ncpi-sim'"
    exit 1
fi

mkdir -p logs

# Ejecuta el script de análisis de features no lineales
python 17_nonlinear_features.py "$CONF_PATH"