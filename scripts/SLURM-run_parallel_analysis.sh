#!/bin/bash
# Redirigir toda la salida a un log
exec > launcher.log 2>&1

echo "Iniciando launcher a las $(date)"
# Define las rutas de los parámetros que quieres analizar
PARAM_DIRS=(
    "/SCRATCH/TIC117/cmg/alejandro/no_plast/J_EE_J_IE-v2/Jext2989"
    "/SCRATCH/TIC117/cmg/alejandro/no_plast/J_EI_J_II-v2/Jext2989"
    "/SCRATCH/TIC117/cmg/alejandro/no_plast/J_EE_J_IE-v2/Jext32"
    "/SCRATCH/TIC117/cmg/alejandro/no_plast/J_EI_J_II-v2/Jext32"

    # "/SCRATCH/TIC117/cmg/alejandro/no_plast/J_EE_J_IE-v2/Jext2989"
    # "/SCRATCH/TIC117/cmg/alejandro/no_plast/J_EI_J_II-v2/Jext2989"
    # "/SCRATCH/TIC117/cmg/alejandro/no_plast/J_EE_J_IE-v2/Jext32"
    # "/SCRATCH/TIC117/cmg/alejandro/no_plast/J_EI_J_II-v2/Jext32"

    "/SCRATCH/TIC117/cmg/alejandro/no_plast/tau_syn_E/Jext32"
    "/SCRATCH/TIC117/cmg/alejandro/no_plast/tau_syn_E/Jext2989"
    # "/SCRATCH/TIC117/cmg/alejandro/no_plast/tau_syn_E/Jext32"
    # "/SCRATCH/TIC117/cmg/alejandro/no_plast/tau_syn_E/Jext2989"

    "/SCRATCH/TIC117/cmg/alejandro/no_plast/tau_syn_I/Jext32"
    "/SCRATCH/TIC117/cmg/alejandro/no_plast/tau_syn_I/Jext2989"
    # "/SCRATCH/TIC117/cmg/alejandro/no_plast/tau_syn_I/Jext32"
    # "/SCRATCH/TIC117/cmg/alejandro/no_plast/tau_syn_I/Jext2989"

    "/SCRATCH/TIC117/cmg/alejandro/no_plast/J_ext"
    # "/SCRATCH/TIC117/cmg/alejandro/no_plast/J_ext"
)

# Crea el directorio de logs si no existe
mkdir -p logs

# Contador de jobs enviados
job_count=0

# Itera sobre cada directorio de parámetro
for param_dir in "${PARAM_DIRS[@]}"; do
    # Verifica que el directorio existe
    if [ ! -d "$param_dir" ]; then
        echo "Advertencia: El directorio $param_dir no existe, saltando..."
        continue
    fi
    
    # Extrae el nombre del parámetro del path
    param_name=$(basename "$param_dir")
    
    echo "Procesando parámetro: $param_name"
    
    # Busca todas las carpetas de configuración dentro del parámetro
    for config_dir in "$param_dir"/*/ ; do
        # Verifica que no sea solo el wildcard expandido
        if [ ! -d "$config_dir" ]; then
            continue
        fi
        
        # Extrae el nombre de la configuración
        config_name=$(basename "$config_dir")
        
        # Crea el nombre del job
        job_name="${param_name}_${config_name}"
        
        # Lanza el job con sbatch
        sbatch --job-name="$job_name" \
               --output="logs/${job_name}-%j.out" \
               --error="logs/${job_name}-%j.err" \
               17_SLURM_nonlinear_features.sh "$config_dir"
        
        if [ $? -eq 0 ]; then
            echo "  ✓ Submitted job: $job_name"
            ((job_count++))
        else
            echo "  ✗ Error submitting job: $job_name"
        fi
    done
    
    echo ""
done

echo "=========================================="
echo "Total de jobs enviados: $job_count"
echo "=========================================="
