from enum import Enum, auto


class FlightStatus(Enum):
    scheduled = auto()
    active = auto()
    landed = auto()
    cancelled = auto()
    diverted = auto()
