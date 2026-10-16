import json
import sys
from argparse import ArgumentParser

from .errors import StreamStatsError
from .parsers import parse_json_and_csv

def main():
    parser = ArgumentParser(description='Анализатор')

    subparser = parser.add_subparsers(dest='command', required=True)
    analyze_parser = subparser.add_parser('analyze')
    analyze_parser.add_argument('inputs', nargs='+')
    analyze_parser.add_argument('--format', choices=['csv', 'jsonl'], dest='format', required=True)
    analyze_parser.add_argument('--output', dest='output', required=True)
    analyze_parser.add_argument('--skip-invalid', action='store_true')
    args = parser.parse_args()

    try:
        result = parse_json_and_csv(args.inputs, args.format, args.skip_invalid)
        with open(args.output, 'w', encoding='utf-8') as f_report:
            json.dump(result, f_report, ensure_ascii=False, indent=2)
    except (OSError, StreamStatsError) as e:
        print(f'Ошибка: {e}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
