#!/bin/bash
# generate_config_list.sh
# Genera una lista con todas las configuraciones a procesar

OUTPUT_FILE="config_list.txt"

PARAM_DIRS=(
    "/SCRATCH/TIC117/cmg/alejandro/no_plast/J_EE_J_IE-v2/Jext2989"
    "/SCRATCH/TIC117/cmg/alejandro/no_plast/J_EI_J_II-v2/Jext2989"
    "/SCRATCH/TIC117/cmg/alejandro/no_plast/J_EE_J_IE-v2/Jext32"
    "/SCRATCH/TIC117/cmg/alejandro/no_plast/J_EI_J_II-v2/Jext32"
    "/SCRATCH/TIC117/cmg/alejandro/no_plast/tau_syn_E/Jext32"
    "/SCRATCH/TIC117/cmg/alejandro/no_plast/tau_syn_E/Jext2989"
    "/SCRATCH/TIC117/cmg/alejandro/no_plast/tau_syn_I/Jext32"
    "/SCRATCH/TIC117/cmg/alejandro/no_plast/tau_syn_I/Jext2989"
)

# Limpiar archivo previo
> "$OUTPUT_FILE"

echo "Buscando configuraciones..."

# Iterar sobre cada directorio de parámetro
for param_dir in "${PARAM_DIRS[@]}"; do
    echo "Procesando: $param_dir"
    
    if [ ! -d "$param_dir" ]; then
        echo "  ⚠ No existe, saltando..."
        continue
    fi
    
    # Contar subdirectorios
    count=0
    
    # Buscar subdirectorios y añadirlos al archivo
    while IFS= read -r -d '' config_dir; do
        echo "$config_dir" >> "$OUTPUT_FILE"
        ((count++))
    done < <(find "$param_dir" -mindepth 1 -maxdepth 1 -type d -print0)
    
    echo "  ✓ Encontrados: $count subdirectorios"
done

# Mostrar resumen
N_CONFIGS=$(wc -l < "$OUTPUT_FILE" 2>/dev/null || echo 0)
echo ""
echo "=========================================="
echo "Total de configuraciones: $N_CONFIGS"
echo "Archivo generado: $OUTPUT_FILE"
echo "=========================================="

if [ $N_CONFIGS -eq 0 ]; then
    echo "⚠ ADVERTENCIA: No se encontraron configuraciones"
    exit 1
fi
