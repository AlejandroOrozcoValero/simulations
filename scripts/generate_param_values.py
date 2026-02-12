"""
Genera un archivo configs.txt con combinaciones de parametros para SLURM array jobs.

Cada linea del archivo de salida contiene los 7 parametros del modelo:
    J_EE  J_IE  J_EI  J_II  tau_syn_E  tau_syn_I  J_ext

Para cada parametro se puede especificar:
  - Valores explicitos:  --J_EE 0.5 1.0 2.0
  - Rango linspace:      --J_EE_lin 0.5 4.0 10   (start, stop, N puntos)
  - Proporcional:        --J_IE_prod 3.5          (J_IE = fuente * 3.5)
  - Sin especificar:     usa el valor por defecto (best config)

La opcion _prod genera valores proporcionales al parametro "fuente" (el unico
parametro especificado con valores explicitos o _lin que tenga multiples valores).
Si hay mas de un parametro fuente candidato, se produce un error.

Ejemplos:
  # Barrer J_EE con 10 valores, resto fijo:
  python generate_param_values.py --J_EE_lin 0.5 4.0 10

  # Barrer J_EE y J_IE (producto cartesiano = 50 configs):
  python generate_param_values.py --J_EE_lin 0.5 4.0 10 --J_IE_lin 0.5 2.0 5

  # Barrer J_EE y J_IE emparejados (zip = 10 configs):
  python generate_param_values.py --J_EE_lin 0.5 4.0 10 --J_IE_lin 0.5 2.0 10 --combination zip

  # Valores explicitos para J_ext:
  python generate_param_values.py --J_ext 28.0 30.0 35.0 40.0

  # J_IE proporcional a J_EE (J_IE = J_EE * 3.5):
  python generate_param_values.py --J_EE_lin 0.5 4.0 10 --J_IE_prod 3.5 --combination zip

  # Multiples parametros proporcionales al mismo barrido:
  python generate_param_values.py --J_EE_lin 0.5 4.0 10 --J_IE_prod 3.5 --J_EI_prod -2.0 --combination zip
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

    # Para cada parametro: valores explicitos, linspace, o proporcional (mutuamente excluyentes)
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
        group.add_argument(
            f'--{p}_prod', type=float,
            metavar='FACTOR',
            help=f'Valores de {p} = fuente * FACTOR (proporcional al parametro barrido)'
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

    # --- Pasada 1: Resolver parametros explicitos y linspace ---
    param_values = {}
    prod_params = {}  # {param_name: factor}
    source_param = None

    for p in PARAM_ORDER:
        explicit = getattr(args, p)
        linspace = getattr(args, f'{p}_lin')
        prod_factor = getattr(args, f'{p}_prod')

        if explicit is not None:
            param_values[p] = explicit
        elif linspace is not None:
            start, stop, n = linspace
            param_values[p] = np.round(
                np.linspace(start, stop, int(n)), args.decimals
            ).tolist()
        elif prod_factor is not None:
            prod_params[p] = prod_factor
        else:
            param_values[p] = [DEFAULTS[p]]

    # --- Identificar parametro fuente para _prod ---
    if prod_params:
        source_candidates = [
            p for p in PARAM_ORDER
            if p in param_values and len(param_values[p]) > 1
        ]

        if len(source_candidates) == 0:
            parser.error(
                f'Se usaron opciones _prod ({", ".join(prod_params.keys())}), '
                f'pero ningun parametro tiene multiples valores para usar como fuente. '
                f'Especifica al menos un parametro con valores explicitos o _lin.'
            )
        elif len(source_candidates) > 1:
            parser.error(
                f'Se usaron opciones _prod ({", ".join(prod_params.keys())}), '
                f'pero hay multiples parametros con multiples valores: '
                f'{", ".join(source_candidates)}. '
                f'Ambiguo: no se puede determinar el parametro fuente. '
                f'Usa valores explicitos en lugar de _prod, o reduce a un solo barrido.'
            )

        source_param = source_candidates[0]
        source_values = param_values[source_param]

        # --- Pasada 2: Resolver parametros _prod ---
        for p, factor in prod_params.items():
            param_values[p] = np.round(
                np.array(source_values) * factor, args.decimals
            ).tolist()

        # Advertencia: _prod con product probablemente no es lo deseado
        if args.combination == 'product':
            print('AVISO: Usando _prod con --combination product genera producto cartesiano.')
            print('       Probablemente quieres usar --combination zip.')
            print()

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
        if p in prod_params:
            print(f'  {p}: {param_values[p]} ({len(param_values[p])} valores, '
                  f'= {source_param} * {prod_params[p]})')
        elif len(param_values[p]) > 1:
            print(f'  {p}: {param_values[p]} ({len(param_values[p])} valores)')
        else:
            print(f'  {p}: {param_values[p][0]} (fijo)')

    print(f'\nPara lanzar con SLURM:')
    print(f'  sbatch --array=1-{len(combinations)} SLURM-run_simulation.sh '
          f'{args.output} <SAVE_PATH> {args.combination}')


if __name__ == '__main__':
    main()
