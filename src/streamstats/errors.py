# Класс от которого наследуются все остальные ошибки
class StreamStatsError(Exception):
    pass


# Неправильный формат ввода
class InputFormatError(StreamStatsError):
    pass


# Некорректно созданный файл
class EventParseError(StreamStatsError):
    pass


# Некорректные данные внутри файла
class InvalidEventError(StreamStatsError):
    pass


# Некорректный timestamp в файле
class InvalidTimestampError(InvalidEventError):
    pass


# Некорректный ввод в CLI
class CliConfigError(StreamStatsError):
    pass
