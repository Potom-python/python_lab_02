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