#!/bin/bash
#SBATCH --job-name=features-15
#SBATCH --output=logs/%j-15.out
#SBATCH --error=logs/%j-15.err
#SBATCH --time=4:00:00
#SBATCH --partition=albaicin
#SBATCH --nodes=1
#SBATCH --cpus-per-task=14

# Cargar bashrc y activar conda
# Recibe como argumento el directorio de configuración
CONF_PATH="${1}"

if [ -z "$CONF_PATH" ]; then
    echo "Error: se requiere el directorio de configuración como argumento"
    echo "Uso: sbatch job_analysis.sh <config_dir>"
    exit 1
fi

source ~/.bashrc
conda activate ncpi-env


if [ $? -ne 0 ]; then
    echo "Error: No se pudo activar el entorno conda 'lif'"
    exit 1
fi

mkdir -p logs

# Ejecuta el script de análisis pasando la ruta de configuración
python 15_fooof_analysis_v4.py "$CONF_PATH"
