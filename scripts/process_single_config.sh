#!/bin/bash
#SBATCH --job-name=fooof_analysis
#SBATCH --time=01:00:00
#SBATCH --mem=8G
#SBATCH --cpus-per-task=1
#SBATCH --output=/SCRATCH/TIC117/cmg/alejandro/fooof_analysis/logs/fooof_%A_%a.out
#SBATCH --error=/SCRATCH/TIC117/cmg/alejandro/fooof_analysis/logs/fooof_%A_%a.err

# Activar entorno si es necesario
# module load python/3.9
# source /path/to/venv/bin/activate

# Leer la configuración correspondiente a este array task
CONFIG_LIST="config_list.txt"

CONFIG_DIR=$(sed -n "${SLURM_ARRAY_TASK_ID}p" CONFIG_LIST)

source ~/.bashrc

conda activate ncpi-env

# Verificar que existe
if [ ! -d "$CONFIG_DIR" ]; then
    echo "Error: directorio no existe: $CONFIG_DIR"
    exit 1
fi

echo "=========================================="
echo "Array Task ID: $SLURM_ARRAY_TASK_ID"
echo "Job ID: $SLURM_JOB_ID"
echo "Procesando: $CONFIG_DIR"
echo "Inicio: $(date)"
echo "=========================================="

# Directorio de salida en SCRATCH
SCRATCH_BASE="/SCRATCH/TIC117/cmg/alejandro/fooof_analysis"
OUTPUT_DIR="${SCRATCH_BASE}/results"

# Asegurar que existe el directorio de salida
mkdir -p "$OUTPUT_DIR"

# Ejecutar el script de Python
python 15_fooof_analysis_v4.py "$CONFIG_DIR" \
    --output_dir "$OUTPUT_DIR" \
    --freq_min 5.0 \
    --freq_max 45.0 \
    --r_squared_th 0.9

exit_code=$?

echo "=========================================="
echo "Fin: $(date)"
echo "Exit code: $exit_code"
echo "=========================================="

exit $exit_code
