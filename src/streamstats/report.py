import json


def out_report(result: dict) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2)


def write_report(result: dict, file: str) -> None:
    with open(file, 'w', encoding='utf-8') as f:
        f.write(out_report(result))
