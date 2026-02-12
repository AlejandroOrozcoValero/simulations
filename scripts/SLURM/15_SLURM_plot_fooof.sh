#!/bin/bash
#SBATCH --job-name=plot_fooof
#SBATCH --output=/SCRATCH/TIC117/cmg/alejandro/fooof_analysis/logs/plot_results/15_plot_fooof_%j.out
#SBATCH --error=/SCRATCH/TIC117/cmg/alejandro/fooof_analysis/logs/plot_results/15_plot_fooof_%j.err
#SBATCH --time=01:00:00
#SBATCH --mem=8GB
#SBATCH --cpus-per-task=1
#SBATCH --partition=NOParalela

# Script SLURM para generar figura con resultados de FOOOF analysis
# Genera una figura grid donde:
# - Cada columna = un parámetro (J_EE, J_IE, etc.)
# - Cada fila = una feature de specparam (Exponent, CentralFreq, Power)

echo "=========================================="
echo "Iniciando plot de resultados FOOOF"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "Fecha: $(date)"
echo "=========================================="

# Crear directorios necesarios
mkdir -p "$OUTPUT_DIR"

# Directorios
BASE_DIR="/home/TIC117/cmg/alejandro/Proyectos/plasticity_sims"
SCRATCH_DIR="/SCRATCH/TIC117/cmg/alejandro"
cd $BASE_DIR/scripts

# Activar entorno conda
echo "Activando entorno conda..."
source ~/.bashrc
conda activate ncpi-new

# Parámetros por defecto
RESULTS_DIR="${SCRATCH_DIR}/fooof_analysis/results"
OUTPUT_DIR="${SCRATCH_DIR}/fooof_analysis"
OUTPUT_NAME="15_FOOOF_grid.png"
JEXT=""  # Vacío = generar ambas figuras

# Permitir override desde línea de comandos
if [ ! -z "$1" ]; then
    RESULTS_DIR="$1"
fi

if [ ! -z "$2" ]; then
    OUTPUT_DIR="$2"
fi

if [ ! -z "$3" ]; then
    OUTPUT_NAME="$3"
fi

if [ ! -z "$4" ]; then
    JEXT="$4"  # Puede ser 29.89, 32, o "all"
fi

echo ""
echo "Configuración:"
echo "  Results dir: $RESULTS_DIR"
echo "  Output dir: $OUTPUT_DIR"
echo "  Output name: $OUTPUT_NAME"
echo "  J_ext filter: ${JEXT:-'all (ambas figuras)'}"
echo ""

# Construir comando Python
PYTHON_CMD="python 15_plot_fooof_results.py --results_dir \"$RESULTS_DIR\" --output_dir \"$OUTPUT_DIR\" --output_name \"$OUTPUT_NAME\""

if [ "$JEXT" == "all" ] || [ -z "$JEXT" ]; then
    PYTHON_CMD="$PYTHON_CMD --all"
elif [ ! -z "$JEXT" ]; then
    PYTHON_CMD="$PYTHON_CMD --jext $JEXT"
fi

# Ejecutar script de plotting
echo "Ejecutando: $PYTHON_CMD"
eval $PYTHON_CMD

EXIT_CODE=$?

echo ""
echo "=========================================="
echo "Job finalizado"
echo "Exit code: $EXIT_CODE"
echo "Fecha: $(date)"
echo "=========================================="

exit $EXIT_CODE
