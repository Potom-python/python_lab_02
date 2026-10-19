import json


def out_report(result: dict) -> str:
    """Превращает dict в JSON"""
    return json.dumps(result, ensure_ascii=False, indent=2)


def write_report(result: dict, file: str) -> None:
    """Записывает результат в файл"""
    with open(file, 'w', encoding='utf-8') as f:
        f.write(out_report(result))
