#!/bin/bash
#SBATCH --job-name=plot_results
#SBATCH --output=logs/plot_results_%j.out
#SBATCH --error=logs/plot_results_%j.err
#SBATCH --time=00:02:00
#SBATCH --partition=albaicin
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G

# Ejemplo:
#   sbatch SLURM-plot_results.sh /SCRATCH/TIC117/cmg/alejandro/plasticity_sims/results

SAVE_PATH="${1}"
FIGNAME="${2}"

if [ -z "$SAVE_PATH" ]; then
    echo "Error: se requiere save_path como argumento"
    echo "Uso: sbatch SLURM-plot_results.sh <save_path>"
    exit 1
fi

source ~/.bashrc
conda activate ncpi-new

if [ $? -ne 0 ]; then
    echo "Error: No se pudo activar el entorno conda 'lif'"
    exit 1
fi

mkdir -p logs

python plot_results.py --save-path "$SAVE_PATH" --figname "$FIGNAME"
