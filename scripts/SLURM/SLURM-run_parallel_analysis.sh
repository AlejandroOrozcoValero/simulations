#!/bin/bash

# Configuración
SCRATCH_BASE="/SCRATCH/TIC117/cmg/alejandro"
LOG_DIR="${SCRATCH_BASE}/logs"
OUTPUT_DIR="${SCRATCH_BASE}/features"
SCRIPT_DIR="/home/TIC117/cmg/alejandro/Proyectos/plasticity_sims/scripts"
SLURM_SCRIPT="${SCRIPT_DIR}/15_SLURM_fooof_analysis_v4.sh"  # ← CORREGIDO

# Crear directorios
mkdir -p "$LOG_DIR"
mkdir -p "$OUTPUT_DIR"

# Log del launcher
LAUNCHER_LOG="${LOG_DIR}/launcher_$(date +%Y%m%d_%H%M%S).log"
exec > "$LAUNCHER_LOG" 2>&1

echo "=========================================="
echo "LAUNCHER DE JOBS"
echo "=========================================="
echo "Fecha: $(date)"
echo "Script SLURM: $SLURM_SCRIPT"
echo "Log: $LAUNCHER_LOG"
echo "=========================================="

# Verificar que el script SLURM existe
if [ ! -f "$SLURM_SCRIPT" ]; then
    echo "ERROR: No se encuentra el script $SLURM_SCRIPT"
    exit 1
fi

# Directorios de parámetros
PARAM_DIRS=(
    "${SCRATCH_BASE}/no_plast/J_EE_J_IE-v2/Jext2989"
    "${SCRATCH_BASE}/no_plast/J_EI_J_II-v2/Jext2989"
    "${SCRATCH_BASE}/no_plast/J_EE_J_IE-v2/Jext32"
    "${SCRATCH_BASE}/no_plast/J_EI_J_II-v2/Jext32"
    "${SCRATCH_BASE}/no_plast/tau_syn_E/Jext32"
    "${SCRATCH_BASE}/no_plast/tau_syn_E/Jext2989"
    "${SCRATCH_BASE}/no_plast/tau_syn_I/Jext32"
    "${SCRATCH_BASE}/no_plast/tau_syn_I/Jext2989"
    "${SCRATCH_BASE}/no_plast/J_ext"
)

# Contadores
job_count=0
failed_count=0
skipped_count=0

# Procesar cada directorio
for param_dir in "${PARAM_DIRS[@]}"; do
    if [ ! -d "$param_dir" ]; then
        echo "⚠ SKIP: No existe $param_dir"
        ((skipped_count++))
        continue
    fi
    
    # Extraer nombre descriptivo
    parent=$(basename "$(dirname "$param_dir")")
    current=$(basename "$param_dir")
    param_name="${parent}_${current}"
    
    echo ""
    echo "Procesando: $param_name"
    echo "  Ruta: $param_dir"
    
    config_count=0
    
    # Buscar configuraciones
    for config_dir in "$param_dir"/*/ ; do
        if [ ! -d "$config_dir" ]; then
            continue
        fi
        
        config_name=$(basename "$config_dir")
        job_name="${param_name}_${config_name}"
        
        # Lanzar job
        output=$(sbatch \
            --job-name="$job_name" \
            "$SLURM_SCRIPT" "$config_dir" "$OUTPUT_DIR" \
            2>&1)
        
        if echo "$output" | grep -q "Submitted batch job"; then
            job_id=$(echo "$output" | grep -oP '\d+')
            echo "  ✓ Job $job_id: $job_name"
            ((job_count++))
            ((config_count++))
        else
            echo "  ✗ ERROR: $job_name"
            echo "    Mensaje: $output"
            ((failed_count++))
        fi
        
        # Pequeña pausa para no saturar el scheduler
        sleep 0.1
    done
    
    echo "  → Configuraciones procesadas: $config_count"
done

echo ""
echo "=========================================="
echo "RESUMEN FINAL"
echo "=========================================="
echo "Jobs enviados:    $job_count"
echo "Jobs fallidos:    $failed_count"
echo "Dirs no encontrados: $skipped_count"
echo "Finalizado:       $(date)"
echo "=========================================="
echo ""
echo "Para ver el estado de los jobs:"
echo "  squeue -u \$USER"
echo ""
echo "Para ver logs de errores:"
echo "  tail -f ${LOG_DIR}/*.err"