#!/bin/bash
#SBATCH --job-name=lif_array
#SBATCH --output=/SCRATCH/TIC117/cmg/alejandro/logs/simulations/sim_%A_%a.out
#SBATCH --error=/SCRATCH/TIC117/cmg/alejandro/logs/simulations/sim_%A_%a.err
#SBATCH --time=0:30:00
#SBATCH --partition=albaicin
#SBATCH --nodes=1
#SBATCH --cpus-per-task=14
# IMPORTANTE: anadir --array=1-N al lanzar con sbatch, donde N = numero de lineas en configs.txt
# Ejemplo: sbatch --array=1-10 SLURM-run_simulation.sh configs.txt /SCRATCH/TIC117/cmg/alejandro/plasticity_sims/results


# --- Argumentos del script ---
# $1: archivo de configuraciones (default: configs.txt)
# $2: ruta de guardado (save_path)
CONFIG_FILE="${1:-configs.txt}"
SAVE_PATH="${2}"


if [ -z "$SAVE_PATH" ]; then
    echo "Error: se requiere save_path como segundo argumento"
    echo "Uso: sbatch --array=1-N SLURM-run_simulation.sh <configs.txt> <save_path>"
    exit 1
fi

# Cargar bashrc y activar conda
source ~/.bashrc
conda activate lif

if [ $? -ne 0 ]; then
    echo "Error: No se pudo activar el entorno conda 'lif'"
    exit 1
fi


# Leer la linea correspondiente a este task (saltando lineas de comentario #)
PARAMS=$(grep -v '^#' "$CONFIG_FILE" | sed -n "${SLURM_ARRAY_TASK_ID}p")

if [ -z "$PARAMS" ]; then
    echo "Error: No se encontro configuracion para task $SLURM_ARRAY_TASK_ID en $CONFIG_FILE"
    exit 1
fi

# Parsear los 7 parametros (orden: J_EE J_IE J_EI J_II tau_syn_E tau_syn_I J_ext)
J_EE=$(echo $PARAMS | awk '{print $1}')
J_IE=$(echo $PARAMS | awk '{print $2}')
J_EI=$(echo $PARAMS | awk '{print $3}')
J_II=$(echo $PARAMS | awk '{print $4}')
TAU_SYN_E=$(echo $PARAMS | awk '{print $5}')
TAU_SYN_I=$(echo $PARAMS | awk '{print $6}')
J_EXT=$(echo $PARAMS | awk '{print $7}')

echo "Task $SLURM_ARRAY_TASK_ID: J_EE=$J_EE J_IE=$J_IE J_EI=$J_EI J_II=$J_II tau_syn_E=$TAU_SYN_E tau_syn_I=$TAU_SYN_I J_ext=$J_EXT"
echo "Save path: $SAVE_PATH"

python example_full_pipeline_v4.py \
    --J_EE $J_EE \
    --J_IE $J_IE \
    --J_EI $J_EI \
    --J_II $J_II \
    --tau_syn_E $TAU_SYN_E \
    --tau_syn_I $TAU_SYN_I \
    --J_ext $J_EXT \
    --save-path "$SAVE_PATH"

if [ $? -ne 0 ]; then
    echo "Error: example_full_pipeline_v4.py fallo para task $SLURM_ARRAY_TASK_ID"
    exit 1
fi

echo "Task $SLURM_ARRAY_TASK_ID completada"
