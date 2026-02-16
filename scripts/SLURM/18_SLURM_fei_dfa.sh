#!/bin/bash
#SBATCH --job-name=fei_dfa_analysis
#SBATCH --output=/SCRATCH/TIC117/cmg/alejandro/fei_dfa_analysis/logs/fei_dfa_analysis-%j.out
#SBATCH --error=/SCRATCH/TIC117/cmg/alejandro/fei_dfa_analysis/logs/fei_dfa_analysis-%j.err
#SBATCH --time=02:00:00
#SBATCH --partition=albaicin
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=alexoroval@ugr.es

# Argumentos:
#   $1: CONF_PATH (requerido) - directorio de configuración
#   $2: OUTPUT_DIR (opcional) - directorio de salida (default: results)

CONF_PATH="${1}"
OUTPUT_DIR="${2:-results}"

if [ -z "$CONF_PATH" ]; then
    echo "Error: se requiere el directorio de configuración como argumento"
    echo "Uso: sbatch 18_SLURM_fei_dfa.sh <config_dir> [output_dir]"
    exit 1
fi

# Cargar bashrc y activar conda
source ~/.bashrc
conda activate ncpi-env

if [ $? -ne 0 ]; then
    echo "Error: No se pudo activar el entorno conda 'ncpi-env'"
    exit 1
fi

mkdir -p /SCRATCH/TIC117/cmg/alejandro/fei_dfa_analysis/logs
mkdir -p "$OUTPUT_DIR"

# Ejecuta el script de análisis DFA/fEI
python 18_fei_dfa.py "$CONF_PATH" --output_dir "$OUTPUT_DIR"
