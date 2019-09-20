import logging
import pytz
import weakref
import pandas
import datetime

# Local application imports
from pyems.config import Constant, Parameter
from pyems.core.optimization.optimizer import Optimizer
from pyems.core.system.system import System
from pyems.core.entity.entity import Entity
from pyems.core.utils.time import (
    timestep_conversion, split_timestep, local_to_utc, utc_to_local, get_current_time, find_next_step_start,
    get_following_midnight_utc_timestamp, get_fix_simulation_length_end_timestamp, timestep_to_seconds
)
from pyems.core.utils.singleton import Singleton


class Simulation(Entity, metaclass=Singleton):

    def __init__(self, timestep, current_time=None):
        super().__init__(name='Simulation', entity_type='simulation')

        self._system, self._optimizer = None, None
        self.start, self.end, self.periods, self.interval = None, None, None, None
        self.results = None
        self.simulation_mode = None

        self.timestep = timestep
        self.max_timestep_seconds = 1 * Constant.HOUR_SECONDS  # 1 hour is the max step
        self.min_timestep_seconds = 1 * Constant.MINUTE_SECONDS  # 1 min is the minimum step

        if not self.min_timestep_seconds <= self.timestep_seconds <= self.max_timestep_seconds:
            raise ValueError('Time step is lower than 1 min or higher than 1 hour.')
        if not self.max_timestep_seconds % self.timestep_seconds == 0:
            raise ValueError('The time step must be the result of dividing one hour in equal parts.')

        self.current_time = current_time  # UTC time
        self.local_tz = pytz.timezone('Europe/Amsterdam')
        self.logger = logging.getLogger(f"{Parameter.PACKAGE_NAME}.Simulation")

    @property
    def optimizer(self):
        if not self._optimizer:
            return self._optimizer
        _optimizer = self._optimizer()
        if _optimizer:
            return _optimizer
        else:
            raise LookupError("Referenced optimizer was deleted.")

    @optimizer.setter
    def optimizer(self, optimizer):
        if isinstance(optimizer, Optimizer):
            self._optimizer = weakref.ref(optimizer)
        else:
            ValueError('Error assigning optimizer to the simulation.')
    
    @property
    def system(self):
        if not self._system:
            return self._system
        _system = self._system()
        if _system:
            return _system
        else:
            raise LookupError("Referenced system was deleted.")

    @system.setter
    def system(self, system):
        if isinstance(system, System):
            self._system = weakref.ref(system)
        else:
            ValueError('Error assigning system to the simulation.')

    @property
    def prediction_interval(self):
        return [self.start, self.end]

    def get_time_configuration(self):
        attributes = [
            'start',
            'end',
            'periods',
            'timestep',
            'current_time',
            'prediction_interval',
        ]

        config = {attribute: getattr(self, attribute) for attribute in attributes}
        return config

    def run_rolling_window(self, rolling_interval, rolling_step, system=None, optimizer=None,):
        self.logger.info('Running simulation.')

        if system is not None and self.system is None:
            self.system = system
        else:
            ValueError('Error assigning system to the simulation.')

        if optimizer is not None and self.optimizer is None:
            self.optimizer = optimizer
        else:
            ValueError('Error assigning optimizer to the simulation.')

        if self.system is None:
            raise ValueError('A system is required.')

        if self.optimizer is None:
            raise ValueError('An optimizer is required.')

        rolling_step = timestep_conversion(rolling_step, pd_units=True)
        time_range = pandas.date_range(start=rolling_interval[0], end=rolling_interval[1], freq=rolling_step)

        for step in time_range:
            self.run_single_step(current_time=step)
            self.system.clear()
            self.optimizer.clear()
            self.clear()

    def run_single_step(
            self, system=None, optimizer=None, current_time=None, simulation_end='prices_availability',
            midnight_ahead=None, simulation_length=None
    ):
        self.logger.info('Running simulation.')

        if system is not None and self.system is None:
            self.system = system
        else:
            ValueError('Error assigning system to the simulation.')

        if optimizer is not None and self.optimizer is None:
            self.optimizer = optimizer
        else:
            ValueError('Error assigning optimizer to the simulation.')

        if current_time is not None:
            self.current_time = current_time
        else:
            self.current_time = get_current_time()  # Utc time

        self.start = find_next_step_start(current_time=self.current_time, timestep=self.timestep)
        # i.e. assume current_time=13:23, and timestep=5m, next start would be 13:25

        if simulation_end == 'fix':
            self.end = get_fix_simulation_length_end_timestamp(self.start, simulation_length=simulation_length)
        elif simulation_end == 'prices_availability':
            if self.system.has_external_grid:

                """Assume we are at day D and we want to run the simulation, at least, for the remaining of day D."
                The next day is D+1. We want the prices of the remaining of the D plus, if available, the prices of day D+1. 
                Therefore, we'll need the utc time corresponding to 
                the midnight between day D and D+1 or between D+1 and D+2 (depending on prices availability).
                """
                publication_time = self.system.get_external_grid_object().publication_time
                local_current_datetime = utc_to_local(self.current_time, local_tz=self.local_tz)
                midnight_ahead = 1 if local_current_datetime.time() >= publication_time else 0  # 0 is D-D+1 midnight
                self.end = get_following_midnight_utc_timestamp(
                    self.current_time, local_tz=self.local_tz, midnight_ahead=midnight_ahead
                )
            else:
                message = (
                    f'The Simulation object cannot determine the end of the simulation based '
                    f'on prices availability because there is no grid in the system.'
                )
                raise ValueError(message)
        elif simulation_end == 'midnight_ahead':
            self.end = get_following_midnight_utc_timestamp(
                self.current_time, local_tz=self.local_tz, midnight_ahead=midnight_ahead
            )
        else:
            raise ValueError('Invalid method to compute the simulation end.')

        pandas_timestep = timestep_conversion(self.timestep, pd_units=True)
        self.periods = len(pandas.date_range(start=self.start, end=self.end, closed='left', freq=pandas_timestep))
        self.interval = [self.start, self.end]

        time_config = self.get_time_configuration()
        self.system.prepare_to_optimize(config=time_config)
        self.results = self.optimizer.solve(system=self.system, config=time_config)

        return self.results

    def clear(self):
        self.start, self.end, self.periods, self.interval = None, None, None, None
        self.results = None

