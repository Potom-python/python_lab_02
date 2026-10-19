import argparse
import logging
import os
import sys

from .errors import CliConfigError, StreamStatsError
from .parsers import parse_jsonl_and_csv
from .report import out_report, write_report


def main() -> int:
    """Обработка CLI для дальнейшего использования значений в функциях

    Работает с помощью argparse.

    --help выводит справку об использовании анализатора.
    Делает проверку на корректность входных данных.
    После чего вызывает функцию parse_jsonl_and_csv(), чтобы
    получить словарь с обработанными данными.
    Далее в зависимости от того вводил ли пользователь --outputs
    выводит текст в stdout или создает json файл и заносит туда
    полученную статистику.
    Если во время обработки CLI были выявлены ошибки, то возвращается код возврата 2.
    В ином случае выводится код возврата 0, означающий верное выполнение.
    """

    logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
    epilog = ('Допустимые форматы файлов:\n'
              'csv и jsonl\n'
              'Использование:\n'
              'python -m streamstats analyze INPUT ...'
              ' --format csv | jsonl ... --output REPORT.json\n'
              'python -m streamstats analyze INPUT --format jsonl --skip-invalid\n'
              )
    parser = argparse.ArgumentParser(description='Анализатор файлов',
                                     epilog=epilog,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    subparser = parser.add_subparsers(dest='command', required=True)
    analyze_parser = subparser.add_parser('analyze')
    analyze_parser.add_argument('inputs', nargs='+')
    analyze_parser.add_argument('--format', choices=['csv', 'jsonl'], dest='format', nargs='+', required=True)
    analyze_parser.add_argument('--output', dest='output')
    analyze_parser.add_argument('--skip-invalid', action='store_true')
    args = parser.parse_args()

    try:
        if len(args.format) != len(args.inputs):
            raise CliConfigError('Количество файлов не совпадает с количеством форматов для них')
        if args.output is not None and os.path.abspath(args.output) in [os.path.abspath(p) for p in args.inputs]:
            raise CliConfigError('Файл отчёта совпадает с входным файлом')
        result = parse_jsonl_and_csv(args.inputs, args.format, args.skip_invalid)
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
