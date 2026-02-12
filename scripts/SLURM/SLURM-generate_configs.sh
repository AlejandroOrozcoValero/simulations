#!/bin/bash
#SBATCH --job-name=gen_configs
#SBATCH --output=/SCRATCH/TIC117/cmg/alejandro/logs/gen_configs_J_EI-%j.out
#SBATCH --error=/SCRATCH/TIC117/cmg/alejandro/logs/gen_configs_J_EI-%j.err
#SBATCH --time=00:05:00
#SBATCH --partition=albaicin
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1

# Ejemplo:
#   sbatch SLURM-generate_configs.sh configs.txt --J_ext 28.0 30.0 32.0

SCRATCH_BASE="/SCRATCH/TIC117/cmg/alejandro/configs"
OUTPUT_NAME="${1}"
OUTPUT_FILE="${SCRATCH_BASE}/${OUTPUT_NAME}"

if [ -z "$OUTPUT_FILE" ]; then
    echo "Error: se requiere el nombre del archivo de salida como primer argumento"
    echo "Uso: sbatch SLURM-generate_configs.sh <output.txt> [opciones de parametros]"
    exit 1
fi

shift  # quitar el primer argumento para pasar el resto a Python

source ~/.bashrc
conda activate lif

if [ $? -ne 0 ]; then
    echo "Error: No se pudo activar el entorno conda 'lif'"
    exit 1
fi

mkdir -p logs

python generate_param_values.py --output "$OUTPUT_FILE" "$@"
