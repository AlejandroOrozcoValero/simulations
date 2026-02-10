#!/bin/bash
#SBATCH --job-name=features-15
#SBATCH --output=logs/%j-15.out
#SBATCH --error=logs/%j-15.err
#SBATCH --time=4:00:00
#SBATCH --partition=albaicin
#SBATCH --nodes=1
#SBATCH --cpus-per-task=14

# Argumentos:
#   $1: CONF_PATH (requerido) - directorio de configuración
#   $2: OUTPUT_DIR (opcional) - directorio de salida (default: results)
#   $3: FREQ_MIN (opcional) - frecuencia mínima Hz (default: 5.0)
#   $4: FREQ_MAX (opcional) - frecuencia máxima Hz (default: 45.0)
#   $5: NPERSEG (opcional) - muestras por segmento Welch (default: fs * 0.5)
#   $6: R_SQUARED_TH (opcional) - umbral de r_squared (default: 0.9)

CONF_PATH="${1}"
OUTPUT_DIR="${2:-results}"
FREQ_MIN="${3:-5.0}"
FREQ_MAX="${4:-45.0}"
NPERSEG="${5:-}"
R_SQUARED_TH="${6:-0.9}"

if [ -z "$CONF_PATH" ]; then
    echo "Error: se requiere el directorio de configuración como argumento"
    echo "Uso: sbatch 15_SLURM_fooof_analysis_v4.sh <config_dir> [output_dir] [freq_min] [freq_max] [nperseg] [r_squared_th]"
    exit 1
fi

source ~/.bashrc
conda activate ncpi-env

if [ $? -ne 0 ]; then
    echo "Error: No se pudo activar el entorno conda 'ncpi-env'"
    exit 1
fi

mkdir -p logs
mkdir -p "$OUTPUT_DIR"

# Construir argumentos opcionales
OPTIONAL_ARGS="--output_dir $OUTPUT_DIR --freq_min $FREQ_MIN --freq_max $FREQ_MAX --r_squared_th $R_SQUARED_TH"

if [ -n "$NPERSEG" ]; then
    OPTIONAL_ARGS="$OPTIONAL_ARGS --nperseg $NPERSEG"
fi

# Ejecuta el script de análisis
python 15_fooof_analysis_v4.py "$CONF_PATH" $OPTIONAL_ARGS
