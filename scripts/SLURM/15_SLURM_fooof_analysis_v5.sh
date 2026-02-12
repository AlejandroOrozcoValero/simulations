#!/bin/bash
#SBATCH --job-name=features-15
#SBATCH --output=/SCRATCH/TIC117/cmg/alejandro/logs/%x-%A_%a.out
#SBATCH --error=/SCRATCH/TIC117/cmg/alejandro/logs/%x-%A_%a.err
#SBATCH --time=4:00:00
#SBATCH --partition=albaicin
#SBATCH --nodes=1
#SBATCH --cpus-per-task=14
#SBATCH --array=0-8

PARAM_DIRS=(
    "/SCRATCH/TIC117/cmg/alejandro/no_plast/J_EE_J_IE/Jext32"
    "/SCRATCH/TIC117/cmg/alejandro/no_plast/J_EE_J_IE/Jext2989"
    "/SCRATCH/TIC117/cmg/alejandro/no_plast/J_EI_J_II/Jext32"
    "/SCRATCH/TIC117/cmg/alejandro/no_plast/J_EI_J_II/Jext2989"
    "/SCRATCH/TIC117/cmg/alejandro/no_plast/tau_syn_E/Jext32"
    "/SCRATCH/TIC117/cmg/alejandro/no_plast/tau_syn_E/Jext2989"
    "/SCRATCH/TIC117/cmg/alejandro/no_plast/tau_syn_I/Jext32"
    "/SCRATCH/TIC117/cmg/alejandro/no_plast/tau_syn_I/Jext2989"
    "/SCRATCH/TIC117/cmg/alejandro/no_plast/J_ext"
)

PARAM_PATH=${PARAM_DIRS[$SLURM_ARRAY_TASK_ID]}

source ~/.bashrc
conda activate ncpi-env

OUTPUT_DIR="/SCRATCH/TIC117/cmg/alejandro/fooof_analysis/results"
mkdir -p "$OUTPUT_DIR"

echo "Job array index: $SLURM_ARRAY_TASK_ID"
echo "Processing: $PARAM_PATH"

python ../15_fooof_analysis_v5.py "$PARAM_PATH" --output_dir "$OUTPUT_DIR"