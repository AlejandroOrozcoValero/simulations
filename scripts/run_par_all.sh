#!/bin/bash
#SBATCH --job-name=simulations
#SBATCH --output=logs/%j-Jext32_J_EE.out
#SBATCH --error=logs/%j-Jext32_J_EE.err
#SBATCH --time=48:00:00
#SBATCH --partition=albaicin
#SBATCH --nodes=1
#SBATCH --cpus-per-task=14

# Cargar bashrc y activar conda
source ~/.bashrc
conda activate lif

# Verificar que el entorno se activó correctamente
if [ $? -ne 0 ]; then
    echo "Error: No se pudo activar el entorno conda 'lif'"
    exit 1
fi

# Ejecutar primer script
echo "Ejecutando generate_full_pipeline.py..."
python generate_param_values.py

# Verificar que el primer script terminó correctamente
if [ $? -ne 0 ]; then
    echo "Error: generate_full_pipeline.py falló"
    exit 1
fi

# Ejecutar segundo script
echo "Ejecutando example_full_pipeline_v2.py..."
python example_full_pipeline_v2.py

# Verificar que el segundo script terminó correctamente
if [ $? -ne 0 ]; then
    echo "Error: example_full_pipeline_v2.py falló"
    exit 1
fi

echo "Trabajo completado exitosamente"
