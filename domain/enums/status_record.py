from enum import Enum, auto


class StatusRecord(Enum):
    STARTED = auto()
    PROCESSING = auto()
    FINISHED = auto()
