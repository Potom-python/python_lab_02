import sys, os
from argparse import ArgumentParser

from .errors import StreamStatsError, CliConfigError
from .parsers import parse_json_and_csv
from .report import out_report, write_report

def main() -> int:
    parser = ArgumentParser(description='Анализатор')

    subparser = parser.add_subparsers(dest='command', required=True)
    analyze_parser = subparser.add_parser('analyze')
    analyze_parser.add_argument('inputs', nargs='+')
    analyze_parser.add_argument('--format', choices=['csv', 'jsonl'], dest='format',  nargs='+', required=True)
    analyze_parser.add_argument('--output', dest='output')
    analyze_parser.add_argument('--skip-invalid', action='store_true')
    args = parser.parse_args()

    try:
        if len(args.format) != len(args.inputs):
            raise CliConfigError('Количество файлов не совпадает с количеством форматов для них')
        if args.output is not None and os.path.abspath(args.output) in [os.path.abspath(p) for p in args.inputs]:
            raise CliConfigError('Файл отчёта совпадает с входным файлом')
        result = parse_json_and_csv(args.inputs, args.format, args.skip_invalid)
        if args.output is None:
            print(out_report(result))
        else:
            write_report(result, args.output)
    except (OSError, StreamStatsError) as e:
        print(f'Ошибка: {e}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
