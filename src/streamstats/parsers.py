import csv, json
from datetime import datetime, timezone
import logging
from typing import TextIO

from .models import LEVELS, KEYS
from .analysis import update_stat
from .errors import InvalidEventError, InputFormatError, EventParseError, InvalidTimestampError

logger = logging.getLogger(__name__)


def check_parse_timestamp(timestamp: str, line_number: int, file: str) -> datetime:
    if not isinstance(timestamp, str):
        raise InvalidTimestampError(f'Файл {file}. Строка {line_number}: timestamp должен быть строкой')

    timestamp = timestamp.strip()

    if not timestamp:
        raise InvalidTimestampError(f'Файл {file}. Строка {line_number}: timestamp не должен быть пустым')

    try:
        parsed_timestamp = datetime.fromisoformat(timestamp)
    except ValueError as exc:
        raise InvalidTimestampError(f'Файл {file}. Строка {line_number}: некорректный timestamp {timestamp}') from exc

    if parsed_timestamp.tzinfo is None:
        raise InvalidTimestampError(f'Файл {file}. Строка {line_number}: timestamp должен содержать часовой пояс')

    return parsed_timestamp.astimezone(timezone.utc)


def parse_json_and_csv(files: list, format: list, skip: bool, top_n=5) -> dict:
    stats = {
        'total': 0,
        'by_level': dict.fromkeys(LEVELS, 0),
        'by_source': {},
        'top_error_sources': [],
        'first_timestamp': None,
        'last_timestamp': None,
        'skipped_invalid': 0
    }

    for index, file in enumerate(files, start=0):
        with open(file, 'r', encoding='utf-8', newline='') as f:
            if format[index] == 'csv':
                stats = read_csv(f, stats, skip, file)
            elif format[index] == 'jsonl':
                stats = read_json(f, stats, skip, file)
            else:
                raise InputFormatError(
                    f'Неподдерживаемый формат: {format}'
                )
    sorted_sources = list(sorted(stats['by_source'].items(), key=lambda x: (-x[1]['errors'], x[0])))

    stats['top_error_sources'] = []
    for s in sorted_sources[:top_n]:
        if s[1]['errors'] != 0:
            stats['top_error_sources'].append({'source': f'{s[0]}', 'errors': s[1]['errors']})
    if stats['last_timestamp']:
        stats['last_timestamp'] = stats['last_timestamp'].strftime('%Y-%m-%d %H:%M:%S')
    if stats['first_timestamp']:
        stats['first_timestamp'] = stats['first_timestamp'].strftime('%Y-%m-%d %H:%M:%S')

    return stats


def read_csv(f: TextIO, stats: dict, skip: bool, file: str) -> dict:
    reader = csv.DictReader(f)
    for line_number, event in enumerate(reader, start=2):
        try:
            if not all(key in event for key in KEYS):
                raise InvalidEventError(f'Файл {file}. Строка {line_number}: отсутствуют обязательные поля')

            if not isinstance(event['level'], str):
                raise InvalidEventError(f'Файл {file}. Строка {line_number}: level должен быть строкой')
            if not event['level'].strip():
                raise InvalidEventError(f'Файл {file}. Строка {line_number}: level не должен быть пустым')

            event['level'] = event['level'].strip()

            if event['level'] not in stats['by_level']:
                raise InvalidEventError(f'Файл {file}. Строка {line_number}: неизвестный уровень {event['level']}')

            if not isinstance(event['message'], str):
                raise InvalidEventError(f'Файл {file}. Строка {line_number}: message должен быть строкой')

            if not isinstance(event['source'], str):
                raise InvalidEventError(f'Файл {file}. Строка {line_number}: source должен быть строкой')

            if not event['source'].strip():
                raise InvalidEventError(f'Файл {file}. Строка {line_number}: source не должен быть пустым')

            event['timestamp'] = check_parse_timestamp(event['timestamp'], line_number, file)
            stats = update_stat(event, stats)
        except (InvalidEventError, KeyError, TypeError, ValueError) as exc:
            if not skip:
                if isinstance(exc, InvalidEventError):
                    raise
                raise InvalidEventError(f'Файл {file}. Строка {line_number}. Ошибка: {exc}') from exc
            stats['skipped_invalid'] += 1
            logger.warning(f'Пропуск строки: {exc}')

    return stats


def read_json(f: TextIO, stats: dict, skip: bool, file: str) -> dict:
    for line_number, line in enumerate(f, start=1):
        if not line.strip():
            continue
        try:
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise EventParseError(f'Файл {file}. Строка {line_number}: некорректный JSON: {exc.msg}') from exc

            if not isinstance(event, dict):
                raise InvalidEventError(f'Файл {file}. Строка {line_number}: событие должно быть JSON-объектом')

            if not all(key in event for key in KEYS):
                raise InvalidEventError(f'Файл {file}. Строка {line_number}: отсутствуют обязательные поля')

            if not isinstance(event['level'], str):
                raise InvalidEventError(f'Файл {file}. Строка {line_number}: level должен быть строкой')
            if not event['level'].strip():
                raise InvalidEventError(f'Файл {file}. Строка {line_number}: level не должен быть пустым')

            event['level'] = event['level'].strip()

            if event['level'] not in stats['by_level']:
                raise InvalidEventError(f'Файл {file}. Строка {line_number}: неизвестный уровень {event['level']}')

            if not isinstance(event['message'], str):
                raise InvalidEventError(f'Файл {file}. Строка {line_number}: message должен быть строкой')

            if not isinstance(event['source'], str):
                raise InvalidEventError(f'Файл {file}. Строка {line_number}: source должен быть строкой')

            if not event['source'].strip():
                raise InvalidEventError(f'Файл {file}. Строка {line_number}: source не должен быть пустым')

            event['timestamp'] = check_parse_timestamp(event['timestamp'], line_number, file)
            stats = update_stat(event, stats)
        except (EventParseError, InvalidEventError, KeyError, TypeError, ValueError) as exc:
            if not skip:
                if isinstance(exc, (EventParseError, InvalidEventError)):
                    raise
                raise InvalidEventError(f'Файл {file}. Строка {line_number}. Ошибка: {exc}') from exc
            stats['skipped_invalid'] += 1
            logger.warning(f'Пропуск строки: {exc}')

    return stats
