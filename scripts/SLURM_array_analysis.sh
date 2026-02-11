#!/bin/bash
#SBATCH --job-name=array_analysis
#SBATCH --output=/SCRATCH/TIC117/cmg/alejandro/logs/%x_%A_%a.out
#SBATCH --error=/SCRATCH/TIC117/cmg/alejandro/logs/%x_%A_%a.err
#SBATCH --time=02:00:00
#SBATCH --partition=albaicin
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G

# =============================================================================
# SLURM_array_analysis.sh
# Script genérico para lanzar análisis en array sobre múltiples configuraciones
#
# Uso:
#   sbatch --array=1-N SLURM_array_analysis.sh <config_list> <script.py> <output_dir>
#
# Ejemplos:
#   # Generar lista de configuraciones
#   find /SCRATCH/.../no_plast -mindepth 2 -maxdepth 2 -type d > configs.txt
#
#   # Contar y lanzar
#   N=$(wc -l < configs.txt)
#   sbatch --array=1-${N}%20 SLURM_array_analysis.sh configs.txt 15_fooof_analysis_v4.py /SCRATCH/.../results
#
#   # Reusar para otro análisis
#   sbatch --array=1-${N}%20 SLURM_array_analysis.sh configs.txt 16_mse_v3.py /SCRATCH/.../mse_results
# =============================================================================

CONFIG_LIST="${1}"
SCRIPT="${2}"
OUTPUT_DIR="${3}"

# Validación de argumentos
if [ -z "$CONFIG_LIST" ] || [ -z "$SCRIPT" ] || [ -z "$OUTPUT_DIR" ]; then
    echo "Error: faltan argumentos"
    echo "Uso: sbatch --array=1-N $0 <config_list> <script.py> <output_dir>"
    exit 1
fi

if [ ! -f "$CONFIG_LIST" ]; then
    echo "Error: archivo de configuraciones no existe: $CONFIG_LIST"
    exit 1
fi

# Leer la configuración correspondiente a este task
CONFIG_DIR=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "$CONFIG_LIST")

if [ -z "$CONFIG_DIR" ]; then
    echo "Error: no se encontró configuración para task $SLURM_ARRAY_TASK_ID"
    exit 1
fi

if [ ! -d "$CONFIG_DIR" ]; then
    echo "Error: directorio no existe: $CONFIG_DIR"
    exit 1
fi

# Info del job
echo "=========================================="
echo "Array Task ID: $SLURM_ARRAY_TASK_ID"
echo "Job ID: $SLURM_JOB_ID"
echo "Script: $SCRIPT"
echo "Config: $CONFIG_DIR"
echo "Output: $OUTPUT_DIR"
echo "Inicio: $(date)"
echo "=========================================="

# Activar entorno
source ~/.bashrc
conda activate ncpi-env

if [ $? -ne 0 ]; then
    echo "Error: No se pudo activar el entorno conda 'ncpi-env'"
    exit 1
fi

# Crear directorio de salida
mkdir -p "$OUTPUT_DIR"
mkdir -p /SCRATCH/TIC117/cmg/alejandro/logs

# Ejecutar análisis
python "$SCRIPT" "$CONFIG_DIR" --output_dir "$OUTPUT_DIR"
exit_code=$?

echo "=========================================="
echo "Fin: $(date)"
echo "Exit code: $exit_code"
echo "=========================================="

exit $exit_code
