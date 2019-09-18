from dataclasses import dataclass
from enum import Enum, auto
# from typing_extensions import Final, final


@dataclass
class Setting:
    time_zone: str = None
    timestep: str = None


@dataclass
class Parameter:
    PACKAGE_NAME: str = 'pyems'
    UTC_DATETIME_FORMAT: str = '%Y-%m-%dT%H:%M:%SZ'
    LOCAL_DATETIME_FORMAT: str = '%Y-%m-%d %H:%M:%S'
    FILE_DATETIME_FORMAT: str = '%Y%m%d_%H%M%S'
    O_CLOCK_FORMAT: str = '%Y-%m-%dT%H:00:00Z'
    INFLUX_VALUE_LABEL = 'value'


@dataclass
class Constant:
    SECOND_SECONDS: int = 1
    MINUTE_SECONDS: int = 60
    HOUR_SECONDS: int = 60 * 60
    DAY_SECONDS: int = 24 * 60 * 60
    DAY_HOURS: int = 24
    MONTH_DAYS: int = 30
    MONTH_HOURS: int = 30 * 24
    KILO: int = 1e3
    MEGA: int = 1e6


@dataclass
class FigureParameter:
    SHOW: bool = True
    SAVE: bool = True
    TIMESTAMP: bool = True
    RATIO: float = 4 / 3
    WIDTH: float = 7.5
    SPACE_RATIO: float = 0.33
    NAME: str = 'figure'
    PATH: str = r''
    FORMAT: str = 'png'


class NoValue(Enum):
    def __repr__(self):
        return '<%s.%s>' % (self.__class__.__name__, self.name)


class ElectricalType(NoValue):
    GENERATOR = auto()
    LOAD = auto()
    BATTERY = auto()
    GRID = auto()


class ElectricalGeneratorSubType(NoValue):
    DISPATCHABLE = auto()
    STOCHASTIC = auto()


class ElectricalLoadSubType(NoValue):
    INTERRUPTABLE = auto()
    FIX = auto()
    SCHEDULABLE = auto()


PANDAS_TO_STD_CONVERSION_SHORT = {
    'D': 'd',
    'H': 'h',
    'T': 'm',
    'min': 'm',
    'S': 's',
    'd': 'd',
    'h': 'h',
    'm': 'm',
    's': 's',
}

STD_TO_PANDAS_CONVERSION_SHORT = {
    'd': 'D',
    'h': 'H',
    'm': 'T',
    's': 'S',
    'D': 'D',
    'H': 'H',
    'T': 'T',
    'min': 'min',
    'S': 'S',
}

SHORT_UNIT_CONVERSION = {
        'D': Constant.DAY_SECONDS,
        'H': Constant.HOUR_SECONDS,
        'T': Constant.MINUTE_SECONDS,
        'min': Constant.MINUTE_SECONDS,
        'S': Constant.SECOND_SECONDS,
        'd': Constant.DAY_SECONDS,
        'h': Constant.HOUR_SECONDS,
        'm': Constant.MINUTE_SECONDS,
        's': Constant.SECOND_SECONDS,
    }



