import csv
import json
import logging
from datetime import UTC, datetime
from typing import TextIO

from .analysis import update_stat
from .errors import (
    EventParseError,
    InputFormatError,
    InvalidEventError,
    InvalidTimestampError,
)
from .models import DELIMITERS, KEYS, LEVELS

logger = logging.getLogger(__name__)


def check_parse_timestamp(timestamp: str, line_number: int, file: str) -> datetime:
    """Проверка на корректность timestamp и возвращает обработанный timestamp.

    Сначала проверяет является ли timestamp строкой.
    Далее избавляется от лишних символов в начале и в конце для дальнейшей обработки.
    Смотрит не превратился ли timestamp в пустую строку после .strip().
    Переводит в объект datetime и проверяет корректный ли формат.
    Если часового пояса нет, то считает время UTC.
    Возвращает объект datetime с часовым поясом UTC.
    """
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
        parsed_timestamp = parsed_timestamp.replace(tzinfo=UTC)

    return parsed_timestamp.astimezone(UTC)


def parse_jsonl_and_csv(files: list, format: list, skip: bool, top_n: int=5) -> dict:
    """Парсер jsonl и csv файлов.

    Создает изначальную статистику.
    Проходит по каждому файлу и перезаписывает stats исходя из файла.
    если был введен неверный формат, то вызывается исключение.
    После обработки всех файлов сортирует ресурсы по ошибкам и именам.
    Исходя из сортировки записывает первые top_n ресурсов в top_error_sources.
    Переводит last и first timestamp из datetime в отформатированную строку.
    Возвращает конечную статистику по всем файлам.
    """
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
                stats = read_jsonl(f, stats, skip, file)
            else:
                raise InputFormatError(
                    f'Неподдерживаемый формат: {format}'
                )
    sorted_sources = sorted(stats['by_source'].items(), key=lambda x: (-x[1]['errors'], x[0]))

    stats['top_error_sources'] = []
    for s in sorted_sources[:top_n]:
        if s[1]['errors'] != 0:
            stats['top_error_sources'].append({'source': f'{s[0]}', 'errors': s[1]['errors']})
    if stats['last_timestamp']:
        stats['last_timestamp'] = stats['last_timestamp'].strftime('%Y-%m-%d %H:%M:%S')
    if stats['first_timestamp']:
        stats['first_timestamp'] = stats['first_timestamp'].strftime('%Y-%m-%d %H:%M:%S')

    return stats


def validate_file(event: dict, file: str, line_number: int, stats: dict) -> None:
    """Проверка файлов на корректность

    Происходит несколько этапов проверки:
    1. Проверка на содержание всех обязательных ключей в файле
    2. Проверка на то является ли поле level строкой
    3. Проверка на пустоту поля level
    4. Проверка является ли поле level разрешенным
    5. Проверка является ли поле message строкой
    6. Проверка является ли поле source строкой
    7. Проверка на пустоту source
    """
    if not all(key in event for key in KEYS):
        raise InvalidEventError(f'Файл {file}. Строка {line_number}: отсутствуют обязательные поля')

    if not isinstance(event['level'], str):
        raise InvalidEventError(f'Файл {file}. Строка {line_number}: level должен быть строкой')

    if not event['level'].strip():
        raise InvalidEventError(f'Файл {file}. Строка {line_number}: level не должен быть пустым')

    if event['level'].strip() not in stats['by_level']:
        raise InvalidEventError(f'Файл {file}. Строка {line_number}: неизвестный уровень {event['level']}')

    if not isinstance(event['message'], str):
        raise InvalidEventError(f'Файл {file}. Строка {line_number}: message должен быть строкой')

    if not isinstance(event['source'], str):
        raise InvalidEventError(f'Файл {file}. Строка {line_number}: source должен быть строкой')

    if not event['source'].strip():
        raise InvalidEventError(f'Файл {file}. Строка {line_number}: source не должен быть пустым')


def read_csv(f: TextIO, stats: dict, skip: bool, file: str) -> dict:
    """Функция для чтения csv файлов.

    Для начала определяет делитель csv файла с помощью csv.Sniffer(),
    если его не удалось найти вызывает исключение.
    Далее создает итератор через csv.DictReader() и с помощью него
    построчно проходит по файлу. Каждая строка проверяется на валидность.
    Дальше происходит проверка timestamp с помощью функции
    check_parse_timestamp() и обновление статистики с помощью функции
    update_stat().
    Если во время этого вызывается исключение, то оно перехватывается,
    после чего происходит проверка на тип вызванного исключения.
    Если не InvalidEventError, то она в нее превращается.
    Если в CLI был передан аргумент --skip-invalid, то ошибка не вызывается,
    а записывается в логи с номером строки и названием файла, также
    обновляется количество пропущенных строк.
    """
    headline = f.readline()
    if not headline.strip():
        return stats
    try:
        delimiter = csv.Sniffer().sniff(headline, delimiters=DELIMITERS).delimiter
    except csv.Error as exc:
        raise InvalidEventError(f'Файл {file}. Не удалось определить разделитель') from exc
    f.seek(0)
    reader = csv.DictReader(f, delimiter=delimiter)
    for line_number, event in enumerate(reader, start=2):
        try:
            validate_file(event, file, line_number, stats)

            event['level'] = event['level'].strip()
            event['timestamp'] = check_parse_timestamp(event['timestamp'], line_number, file)
            stats = update_stat(event, stats)
        except (InvalidEventError, KeyError, TypeError, ValueError) as exc:
            if not skip:
                if isinstance(exc, InvalidEventError):
                    raise
                raise InvalidEventError(f'Файл {file}. Строка {line_number}. Ошибка: {exc}') from exc
            stats['skipped_invalid'] += 1
            logger.warning(exc)

    return stats


def read_jsonl(f: TextIO, stats: dict, skip: bool, file: str) -> dict:
    """Функция для чтения jsonl файлов.
    
    Проходится по всем строкам файла. Если они пустые пропускает их.
    Далее преобразует строку файла в dict, если это не удается, то
    вызывается исключение. Далее происходит проверка, точно ли в
    JSON файле был словарь.
    Дальше происходит проверка timestamp с помощью функции
    check_parse_timestamp() и обновление статистики с помощью функции
    update_stat().
    Если во время этого вызывается исключение, то оно перехватывается,
    после чего происходит проверка на тип вызванного исключения.
    Если не InvalidEventError, то она в нее превращается.
    Если в CLI был передан аргумент --skip-invalid, то ошибка не вызывается,
    а записывается в логи с номером строки и названием файла, также
    обновляется количество пропущенных строк.
    """
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

            validate_file(event, file, line_number, stats)

            event['level'] = event['level'].strip()
            event['timestamp'] = check_parse_timestamp(event['timestamp'], line_number, file)
            stats = update_stat(event, stats)
        except (EventParseError, InvalidEventError, KeyError, TypeError, ValueError) as exc:
            if not skip:
                if isinstance(exc, (EventParseError, InvalidEventError)):
                    raise
                raise InvalidEventError(f'Файл {file}. Строка {line_number}. Ошибка: {exc}') from exc
            stats['skipped_invalid'] += 1
            logger.warning(exc)

    return stats
