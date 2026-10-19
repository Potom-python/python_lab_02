import json
import os
import subprocess
import sys

import pytest

from streamstats.errors import (
    EventParseError,
    InputFormatError,
    InvalidEventError,
    InvalidTimestampError,
)
from streamstats.parsers import parse_jsonl_and_csv

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(TESTS_DIR, 'data')
VERIFIED = os.path.join(TESTS_DIR, 'verified')


def read_json(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def run_cli(tmp_path, inputs: list, formats: list, skip_invalid: bool=False, out_file=None, to_stdout: bool=False):
    if out_file is None:
        out_file = os.path.join(tmp_path, 'report.json')

    commands = [
        sys.executable,
        '-m',
        'streamstats',
        'analyze', *[str(file) for file in inputs],
        '--format', *formats,
    ]

    if not to_stdout:
        commands += ['--output', str(out_file)]

    if skip_invalid:
        commands.append('--skip-invalid')

    result = subprocess.run(
        commands,
        check=False,
        capture_output=True,
        text=True,
        encoding='utf-8',
        env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
    )

    return result, out_file


def test_csv_parser():
    checked_file = parse_jsonl_and_csv([os.path.join(DATA, 'events.csv')],
                                       ['csv'], False)
    verified_res = read_json(os.path.join(VERIFIED, 'check_csv.json'))
    assert checked_file == verified_res


def test_jsonl_parser():
    checked_file = parse_jsonl_and_csv([os.path.join(DATA, 'events.jsonl')],
                                       ['jsonl'], False)
    verified_res = read_json(os.path.join(VERIFIED, 'check_jsonl.json'))
    assert checked_file == verified_res


def test_csv_and_jsonl_equal():
    checked_csv = parse_jsonl_and_csv([os.path.join(DATA, 'events.csv')],
                                      ['csv'], False)
    checked_jsonl = parse_jsonl_and_csv([os.path.join(DATA, 'events.jsonl')],
                                        ['jsonl'], False)
    assert checked_csv == checked_jsonl


def test_csv_semicolon():
    checked_file = parse_jsonl_and_csv([os.path.join(DATA, 'events_semicolon.csv')],
                                       ['csv'], False)
    verified_res = read_json(os.path.join(VERIFIED, 'check_csv.json'))
    assert checked_file == verified_res


def test_csv_tab():
    checked_file = parse_jsonl_and_csv([os.path.join(DATA, 'events_tab.csv')],
                                       ['csv'], False)
    verified_res = read_json(os.path.join(VERIFIED, 'check_csv.json'))
    assert checked_file == verified_res


def test_unknown_delimiter_stops():
    with pytest.raises(InvalidEventError, match='Не удалось определить разделитель'):
        parse_jsonl_and_csv([os.path.join(DATA, 'bad_header.csv')],
                            ['csv'], False)


def test_wrong_columns_stops():
    with pytest.raises(InvalidEventError, match='Строка 2: отсутствуют обязательные поля'):
        parse_jsonl_and_csv([os.path.join(DATA, 'wrong_columns.csv')],
                            ['csv'], False)


def test_empty_jsonl(tmp_path):
    result, out_file = run_cli(tmp_path, [os.path.join(DATA, 'empty.jsonl')], ['jsonl'])
    assert result.returncode == 0
    assert os.path.exists(out_file)
    assert read_json(out_file) == read_json(os.path.join(VERIFIED, 'empty_verif.json'))


def test_empty_csv():
    checked_file = parse_jsonl_and_csv([os.path.join(DATA, 'empty.csv')],
                                       ['csv'], False)
    verified_res = read_json(os.path.join(VERIFIED, 'empty_verif.json'))
    assert checked_file == verified_res


def test_csv_only_header():
    checked_file = parse_jsonl_and_csv([os.path.join(DATA, 'header_only.csv')],
                                       ['csv'], False)
    verified_res = read_json(os.path.join(VERIFIED, 'empty_verif.json'))
    assert checked_file == verified_res


def test_invalid_timestamp_stops():
    with pytest.raises(InvalidTimestampError, match='Строка 3: некорректный timestamp not-a-date'):
        parse_jsonl_and_csv([os.path.join(DATA, 'events_invalid.jsonl')],
                            ['jsonl'], False)


def test_invalid_timestamp_skips(caplog):
    file = os.path.join(DATA, 'events_invalid.jsonl')
    checked_file = parse_jsonl_and_csv([file], ['jsonl'], True)
    verified_res = read_json(os.path.join(VERIFIED, 'report_skip.json'))
    assert f'Файл {file}. Строка 3: некорректный timestamp not-a-date' in caplog.text
    assert checked_file == verified_res


def test_invalid_json_stops():
    with pytest.raises(EventParseError, match='Строка 3: некорректный JSON'):
        parse_jsonl_and_csv([os.path.join(DATA, 'events_bad_json.jsonl')],
                            ['jsonl'], False)


def test_invalid_json_skips(caplog):
    checked_file = parse_jsonl_and_csv([os.path.join(DATA, 'events_bad_json.jsonl')],
                                       ['jsonl'], True)
    verified_res = read_json(os.path.join(VERIFIED, 'report_bad_json_skip.json'))
    assert 'некорректный JSON' in caplog.text
    assert checked_file == verified_res


def test_invalid_csv_stops():
    with pytest.raises(InvalidTimestampError, match='Строка 4'):
        parse_jsonl_and_csv([os.path.join(DATA, 'events_invalid.csv')],
                            ['csv'], False)


def test_invalid_csv_skips(caplog):
    checked_file = parse_jsonl_and_csv([os.path.join(DATA, 'events_invalid.csv')],
                                       ['csv'], True)
    verified_res = read_json(os.path.join(VERIFIED, 'report_skip.json'))
    assert 'Строка 4: некорректный timestamp not-a-date' in caplog.text
    assert checked_file == verified_res


def test_bad_level_stops():
    with pytest.raises(InvalidEventError, match='Строка 2: level должен быть строкой'):
        parse_jsonl_and_csv([os.path.join(DATA, 'bad_level.jsonl')],
                            ['jsonl'], False)


def test_bad_level_skips(caplog):
    checked_file = parse_jsonl_and_csv([os.path.join(DATA, 'bad_level.jsonl')],
                                       ['jsonl'], True)
    verified_res = read_json(os.path.join(VERIFIED, 'bad_level_skip.json'))
    assert 'Строка 2: level должен быть строкой' in caplog.text
    assert checked_file == verified_res


def test_multiple_files():
    checked_file = parse_jsonl_and_csv([os.path.join(DATA, 'events.csv'), os.path.join(DATA, 'events.csv')],
                                       ['csv', 'csv'], False)
    verified_res = read_json(os.path.join(VERIFIED, 'report_combined.json'))
    assert checked_file == verified_res


def test_multiple_files_different_formats():
    checked_file = parse_jsonl_and_csv([os.path.join(DATA, 'events.csv'), os.path.join(DATA, 'second.jsonl')],
                                       ['csv', 'jsonl'], False)
    verified_res = read_json(os.path.join(VERIFIED, 'two_files.json'))
    assert checked_file == verified_res


def test_utc():
    checked_file = parse_jsonl_and_csv([os.path.join(DATA, 'tz_offsets.jsonl')],
                                       ['jsonl'], False)
    verified_res = read_json(os.path.join(VERIFIED, 'tz_offsets.json'))
    assert checked_file == verified_res


def test_unsupported_format():
    with pytest.raises(InputFormatError, match="xml"):
        parse_jsonl_and_csv([os.path.join(DATA, 'events.csv')],
                            ['xml'], False)


def test_unicode_jsonl(tmp_path):
    result, out_file = run_cli(tmp_path, [os.path.join(DATA, 'unicode.jsonl')], ['jsonl'])
    assert result.returncode == 0
    assert os.path.exists(out_file)
    with open(out_file, 'r', encoding='utf-8') as file:
        text = file.read()
    assert 'база' in text
    assert '\\u' not in text
    assert read_json(out_file) == read_json(os.path.join(VERIFIED, 'unicode.json'))


def test_unicode_csv(tmp_path):
    result, out_file = run_cli(tmp_path, [os.path.join(DATA, 'unicode.csv')], ['csv'])
    assert result.returncode == 0
    assert os.path.exists(out_file)
    with open(out_file, 'r', encoding='utf-8') as file:
        text = file.read()
    assert 'база' in text
    assert '\\u' not in text
    assert read_json(out_file) == read_json(os.path.join(VERIFIED, 'unicode.json'))


def test_cli(tmp_path):
    result, out_file = run_cli(tmp_path, [os.path.join(DATA, 'events.csv')], ['csv'])
    verified_res = read_json(os.path.join(VERIFIED, 'check_csv.json'))
    assert result.returncode == 0
    assert read_json(out_file) == verified_res


def test_cli_no_output(tmp_path):
    result, out_file = run_cli(tmp_path, [os.path.join(DATA, 'events.csv')], ['csv'],
                               to_stdout=True)
    verified_res = read_json(os.path.join(VERIFIED, 'check_csv.json'))
    assert result.returncode == 0
    assert not os.path.exists(out_file)
    assert json.loads(result.stdout) == verified_res


def test_cli_wrong_format_count(tmp_path):
    result, out_file = run_cli(tmp_path, [os.path.join(DATA, 'events.csv')], ['csv', 'jsonl'])
    assert result.returncode == 2
    assert 'Количество' in result.stderr
    assert not os.path.exists(out_file)


def test_cli_invalid_json(tmp_path):
    result, out_file = run_cli(tmp_path, [os.path.join(DATA, 'events_invalid.jsonl')], ['jsonl'])
    assert result.returncode == 2
    assert 'events_invalid.jsonl' in result.stderr
    assert 'Строка 3' in result.stderr
    assert not os.path.exists(out_file)


def test_cli_skip_invalid_json(tmp_path):
    result, out_file = run_cli(tmp_path, [os.path.join(DATA, 'events_invalid.jsonl')],
                               ['jsonl'], True)
    verified_res = read_json(os.path.join(VERIFIED, 'report_skip.json'))
    assert 'WARNING' in result.stderr
    assert 'Строка 3' in result.stderr
    assert result.returncode == 0
    assert read_json(out_file) == verified_res


def test_cli_equal_input_and_output(tmp_path):
    source = os.path.join(tmp_path, 'input.csv')
    result, _out_file = run_cli(tmp_path, [source], ['csv'], out_file=source)
    assert result.returncode == 2
    assert 'совпадает' in result.stderr


def test_cli_missing_file(tmp_path):
    result, out_file = run_cli(tmp_path, [os.path.join(tmp_path, 'bor.csv')], ['csv'])
    assert result.returncode == 2
    assert not os.path.exists(out_file)


def test_cli_help():
    result = subprocess.run(
        [sys.executable, '-m', 'streamstats', '--help'],
        check=False,
        capture_output=True,
        text=True,
        encoding='utf-8',
        env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
    )
    assert result.returncode == 0
    assert 'Анализатор' in result.stdout
