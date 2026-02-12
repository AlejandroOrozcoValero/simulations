#!/bin/bash
# launch_array_job.sh
# Script principal para lanzar el análisis de todas las configuraciones

echo "=========================================="
echo "FOOOF Analysis Array Job Launcher"
echo "=========================================="

# Crear estructura de directorios en SCRATCH
SCRATCH_BASE="/SCRATCH/TIC117/cmg/alejandro/fooof_analysis"
echo "Creando estructura de directorios en SCRATCH..."
mkdir -p "${SCRATCH_BASE}/logs"
mkdir -p "${SCRATCH_BASE}/results"
echo "  ✓ ${SCRATCH_BASE}/logs"
echo "  ✓ ${SCRATCH_BASE}/results"
echo ""

# Generar lista de configuraciones
echo "Generando lista de configuraciones..."
bash generate_config_list.sh

CONFIG_LIST="config_list.txt"

# Verificar que se generó correctamente
if [ ! -f config_list.txt ]; then
    echo "❌ Error: no se pudo generar config_list.txt"
    exit 1
fi

# Contar configuraciones
N_CONFIGS=$(wc -l < config_list.txt)

if [ $N_CONFIGS -eq 0 ]; then
    echo "❌ Error: no se encontraron configuraciones"
    exit 1
fi

echo ""
echo "=========================================="
echo "Configuraciones encontradas: $N_CONFIGS"
echo "Resultados se guardarán en: ${SCRATCH_BASE}/results"
echo "Logs se guardarán en: ${SCRATCH_BASE}/logs"
echo "=========================================="
echo ""

# Preguntar confirmación (opcional, comenta estas líneas si quieres auto-launch)
read -p "¿Lanzar array job? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelado por el usuario"
    exit 0
fi

# Lanzar array job con límite de concurrencia
# %20 = máximo 20 jobs ejecutándose simultáneamente
echo "Lanzando array job..."
sbatch --array=1-${N_CONFIGS}%20 process_single_config.sh

if [ $? -eq 0 ]; then
    echo "✓ Array job enviado exitosamente"
    echo ""
    echo "Monitorea el progreso con:"
    echo "  squeue -u \$USER"
    echo ""
    echo "Ver logs en tiempo real:"
    echo "  tail -f ${SCRATCH_BASE}/logs/fooof_*.out"
    echo ""
    echo "Cuando termine, recuerda respaldar los resultados:"
    echo "  rsync -av ${SCRATCH_BASE}/results/ /LUSTRE/home/TIC117/cmg/alejandro/fooof_backup/"
else
    echo "❌ Error al enviar el array job"
    exit 1
fi
