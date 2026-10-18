# Лабораторная работа 2. Потоковый анализатор файлов  
Консольная утилита на Python: анализирует JSONL или CSV файл с логами  
Выводит статистику по этому файлу.  

## Установка и запуск
Чтобы репозиторий появился у вас на компьютере нужно ввести в командной строке (в той папке, в которой хотите, чтобы лежал репозиторий):  
```bash
git clone https://github.com/Potom-python/python_lab_02
```
Сначала в консоли нужно ввести команду (перед этим установить Python):
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

После этого команда доступна как модуль:
```bash
python -m streamstats analyze data/events.csv --format csv --output report.json
python -m streamstats analyze data/events.jsonl --format jsonl --skip-invalid
python -m streamstats analyze data/events.csv data/events.jsonl --format csv jsonl --output report.json
python -m streamstats --help
```

|Аргумент | Что делает?|
|---------|------------|
|`INPUTS`   | 1 или несколько файлов, нуждающихся в обработке|
|`--format`| формат каждого файла по порядку|
|`--output`| указывает куда записать файл, если не ввести, то выведет в консоль|
|`--skip-invalid`| пропускает поврежденные строки и выводит их в лог|

***Форматов должно быть ровно столько, сколько файлов. Флаг `--format` пишите
после списка файлов, иначе argparse примет имя файла за значение формата.***

## Формат файла с событиями

У каждого события 4 обязательных поля:

| Поле    | Требования                                 |
|---------|--------------------------------------------|
| timestamp | строка в формате ISO 8601 с часовым поясом |
| level   | DEBUG, INFO, WARNING, ERROR, CRITICAL      |
| source  | непустая строка                            |
| message | строка                                     |

**CSV**: первая строка содержит заголовки с именами полей
через разделитель. Разделитель можно выбирать из стандартных
"\t;,". В следующих строках информация соответствующая этим полям.  
**JSONL**: JSON объект с нужными полями.  
**Все метки времени переводятся в UTC**

# Отчет
```json
{
  "total": 0,
  "by_level": {
    "DEBUG": 0,
    "INFO": 0,
    "WARNING": 0,
    "ERROR": 0,
    "CRITICAL": 0
  },
  "by_source": {},
  "top_error_sources": [],
  "first_timestamp": null,
  "last_timestamp": null,
  "skipped_invalid": 0
}
```
- total - количество событий.
- by_level - подсчет сколько событий разных уровней встретилось.
- by_source - подсчет событий и errors для каждого source.
- errors - количество событий уровней ERROR и CRITICAL.
- top_error_sources - топ 5 источников по количеству ошибок.
- first_timestamp и last_timestamp - время первого и последнего события соответственно
- skipped_invalid - считает сколько строк было пропущено при введенном аргументе `--skip-invalid`
- Время в отчёте указано в UTC.

Как это устроено внутри: `parse_json_and_csv()` в `parsers.py` обходит файлы
по очереди и вызывает `read_csv()` или `read_json()`. Каждая строка
проверяется в `validate_file()` и `check_parse_timestamp()`, после чего
`update_stat()` из `analysis.py` обновляет счётчики. Когда файлы закончились,
считается топ источников и время приводится к текстовому виду.

# Потоковость и сложность алгоритма

- JSONL и CSV обрабатываются построчно.
- За счет этого достигается сложность алгоритма обработки строе O(n)

# Ошибки и коды возврата

Успешная команда завершается кодом `0`. Любая ошибка выводится в `stderr` и даёт код `2`.  

Исключения (`errors.py`) образуют иерархию с общим предком `StreamStatsError`,
которую ловит `__main__.py`:
```python
class StreamStatsError(Exception):
    pass
class InputFormatError(StreamStatsError):
    pass
class EventParseError(StreamStatsError):
    pass
class InvalidEventError(StreamStatsError):
    pass
class InvalidTimestampError(InvalidEventError):
    pass
class CliConfigError(StreamStatsError):
    pass
```

# Тесты и help
```bash
python -m pytest
python -m streamstats --help
```
Тесты используют готовые файлы из `tests/data`
прогоняют их через функцию `parse_json_and_csv()`
или запускает программу через subprocess, получившийся
отчет хранится в временной директории tmp_path от pytest
и сверяется с верным отчетом, который хранится в `tests/verified`.

# Структура

```
data/
src/streamstats/
    __init__.py
    __main__.py
    analysis.py
    errors.py
    models.py
    parsers.py
    report.py
tests/
    data/
    verified/
    test_parsers.py
```
