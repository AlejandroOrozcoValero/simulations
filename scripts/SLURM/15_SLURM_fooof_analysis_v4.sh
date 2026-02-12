#!/bin/bash
#SBATCH --job-name=features-15
#SBATCH --output=/SCRATCH/TIC117/cmg/alejandro/logs/%x-%j.out
#SBATCH --error=/SCRATCH/TIC117/cmg/alejandro/logs/%x-%j.err
#SBATCH --time=4:00:00
#SBATCH --partition=albaicin
#SBATCH --nodes=1
#SBATCH --cpus-per-task=14

# Argumentos
CONF_PATH="${1}"
OUTPUT_DIR="${2:-results}"
FREQ_MIN="${3:-5.0}"
FREQ_MAX="${4:-45.0}"
NPERSEG="${5:-}"
R_SQUARED_TH="${6:-0.9}"

# Validación
if [ -z "$CONF_PATH" ]; then
    echo "ERROR: Se requiere el directorio de configuración"
    echo "Uso: sbatch $0 <config_dir> [output_dir] [freq_min] [freq_max] [nperseg] [r_squared_th]"
    exit 1
fi

if [ ! -d "$CONF_PATH" ]; then
    echo "ERROR: Directorio no existe: $CONF_PATH"
    exit 1
fi

# Info del job
echo "=========================================="
echo "JOB INFO"
echo "=========================================="
echo "Job ID: $SLURM_JOB_ID"
echo "Job Name: $SLURM_JOB_NAME"
echo "Node: $SLURMD_NODENAME"
echo "Fecha inicio: $(date)"
echo "Config path: $CONF_PATH"
echo "Output dir: $OUTPUT_DIR"
echo "=========================================="

# Crear directorios necesarios
mkdir -p /SCRATCH/TIC117/cmg/alejandro/logs
mkdir -p "$OUTPUT_DIR"

# Activar conda
echo "Activando entorno conda..."
source ~/.bashrc

conda activate ncpi-new
if [ $? -ne 0 ]; then
    echo "ERROR: No se pudo activar el entorno conda 'ncpi-new'"
    echo "Entornos disponibles:"
    conda env list
    exit 1
fi

echo "Entorno activado: $CONDA_DEFAULT_ENV"
echo "Python: $(which python)"
echo "Python version: $(python --version)"

# Construir argumentos opcionales
OPTIONAL_ARGS="--output_dir $OUTPUT_DIR --freq_min $FREQ_MIN --freq_max $FREQ_MAX --r_squared_th $R_SQUARED_TH"
if [ -n "$NPERSEG" ]; then
    OPTIONAL_ARGS="$OPTIONAL_ARGS --nperseg $NPERSEG"
fi

# Ejecutar análisis
echo ""
echo "=========================================="
echo "EJECUTANDO ANÁLISIS"
echo "=========================================="
echo "Comando: python 15_fooof_analysis_v4.py $CONF_PATH $OPTIONAL_ARGS"
echo ""

python 15_fooof_analysis_v4.py "$CONF_PATH" $OPTIONAL_ARGS
EXIT_CODE=$?

echo ""
echo "=========================================="
echo "JOB FINALIZADO"
echo "=========================================="
echo "Exit code: $EXIT_CODE"
echo "Fecha fin: $(date)"
echo "=========================================="

exit $EXIT_CODE