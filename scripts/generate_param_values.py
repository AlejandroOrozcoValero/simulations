"""
Genera un archivo configs.txt con combinaciones de parametros para SLURM array jobs.

Cada linea del archivo de salida contiene los 7 parametros del modelo:
    J_EE  J_IE  J_EI  J_II  tau_syn_E  tau_syn_I  J_ext

Para cada parametro se puede especificar:
  - Valores explicitos:  --J_EE 0.5 1.0 2.0
  - Rango linspace:      --J_EE_lin 0.5 4.0 10   (start, stop, N puntos)
  - Sin especificar:     usa el valor por defecto (best config)

Ejemplos:
  # Barrer J_EE con 10 valores, resto fijo:
  python generate_param_values.py --J_EE_lin 0.5 4.0 10

  # Barrer J_EE y J_IE (producto cartesiano = 50 configs):
  python generate_param_values.py --J_EE_lin 0.5 4.0 10 --J_IE_lin 0.5 2.0 5

  # Barrer J_EE y J_IE emparejados (zip = 10 configs):
  python generate_param_values.py --J_EE_lin 0.5 4.0 10 --J_IE_lin 0.5 2.0 10 --combination zip

  # Valores explicitos para J_ext:
  python generate_param_values.py --J_ext 28.0 30.0 35.0 40.0
"""

import argparse
import numpy as np
import itertools

PARAM_ORDER = ['J_EE', 'J_IE', 'J_EI', 'J_II', 'tau_syn_E', 'tau_syn_I', 'J_ext']

DEFAULTS = {
    'J_EE': 1.589,
    'J_IE': 2.020,
    'J_EI': -23.84,
    'J_II': -8.441,
    'tau_syn_E': 0.5,
    'tau_syn_I': 0.5,
    'J_ext': 29.89,
}


def main():
    parser = argparse.ArgumentParser(
        description='Genera configs.txt con combinaciones de parametros para SLURM array jobs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # Para cada parametro: valores explicitos O linspace (mutuamente excluyentes)
    for p in PARAM_ORDER:
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            f'--{p}', type=float, nargs='+',
            help=f'Valores explicitos para {p} (default: {DEFAULTS[p]})'
        )
        group.add_argument(
            f'--{p}_lin', type=float, nargs=3,
            metavar=('START', 'STOP', 'N'),
            help=f'Generar N valores equiespaciados de {p} entre START y STOP'
        )

    parser.add_argument(
        '--combination', choices=['product', 'zip'], default='product',
        help='product: todas las combinaciones (default). zip: emparejar 1 a 1'
    )
    parser.add_argument(
        '--output', type=str, default='configs.txt',
        help='Archivo de salida (default: configs.txt)'
    )
    parser.add_argument(
        '--decimals', type=int, default=4,
        help='Decimales para redondeo en linspace (default: 4)'
    )

    args = parser.parse_args()

    # Construir lista de valores para cada parametro
    param_values = {}
    for p in PARAM_ORDER:
        explicit = getattr(args, p)
        linspace = getattr(args, f'{p}_lin')

        if explicit is not None:
            param_values[p] = explicit
        elif linspace is not None:
            start, stop, n = linspace
            param_values[p] = np.round(
                np.linspace(start, stop, int(n)), args.decimals
            ).tolist()
        else:
            param_values[p] = [DEFAULTS[p]]

    # Generar combinaciones
    value_lists = [param_values[p] for p in PARAM_ORDER]

    if args.combination == 'product':
        combinations = list(itertools.product(*value_lists))
    else:  # zip
        # Verificar que los parametros con multiples valores tienen la misma longitud
        multi_lengths = [len(v) for v in value_lists if len(v) > 1]
        if multi_lengths and len(set(multi_lengths)) > 1:
            raise ValueError(
                f"Con --combination zip, todos los parametros con multiples valores "
                f"deben tener la misma longitud. Longitudes encontradas: {multi_lengths}"
            )
        max_len = max(len(v) for v in value_lists)
        expanded = [v if len(v) > 1 else v * max_len for v in value_lists]
        combinations = list(zip(*expanded))

    # Escribir archivo de salida
    with open(args.output, 'w') as f:
        f.write(f'# {" ".join(PARAM_ORDER)}\n')
        for combo in combinations:
            f.write(' '.join([f'{v:g}' for v in combo]) + '\n')

    # Resumen
    print(f'Generadas {len(combinations)} configuraciones en {args.output}')
    print(f'Orden de parametros: {PARAM_ORDER}')
    print()
    for p in PARAM_ORDER:
        if len(param_values[p]) > 1:
            print(f'  {p}: {param_values[p]} ({len(param_values[p])} valores)')
        else:
            print(f'  {p}: {param_values[p][0]} (fijo)')

    print(f'\nPara lanzar con SLURM:')
    print(f'  sbatch --array=1-{len(combinations)} SLURM-run_simulation.sh '
          f'{args.output} <SAVE_PATH> {args.combination}')


if __name__ == '__main__':
    main()
