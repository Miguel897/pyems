
import logging
from functools import reduce

import numpy

from pyems.config import ElectricalType, ElectricalLoadSubType, ElectricalGeneratorSubType
from pyems.core.entity.entity import Entity
from pyems.core.components.base import BaseSystemComponent


class System(Entity):
    """This class is thought to contain other physical entities and represents a real physical system. It also provides
    the methods to evaluate global properties of the system, like the total load and demand or the final SOC.
    """

    def __init__(self, name):
        super().__init__(name, entity_type='system')

        self.entities = {}
        self.electrical_generators = {key: [] for key in ElectricalGeneratorSubType}
        self.electrical_loads = {key: [] for key in ElectricalLoadSubType}
        self.power_supply_id = None
        self.battery_id = None

        self.has_electrical_energy_source = False
        self.has_electrical_load = False
        self.has_fix_loads = False
        self.has_interruptable_loads = False
        self.has_schedulable_loads = False
        self.has_dispatchable_generators = False
        self.has_stochastic_generators = False
        self.has_external_grid = False
        self.has_battery = False

        self.stochastic_electrical_gen = None
        self.fix_electrical_load = None
        self.logger = logging.getLogger("pyems.System")
        self.logger.info('Creating System definition.')

    def __setattr__(self, name, value):
        self.__dict__[name] = value
        if isinstance(value, Entity):
            self.entities[value.id] = value
            if isinstance(value, BaseSystemComponent):
                self._add_component(value)

    def get_electrical_generators_list(self):
        return reduce((lambda x, y: x + y), self.electrical_generators.values())

    def get_electrical_loads_list(self):
        return reduce((lambda x, y: x + y), self.electrical_loads.values())

    def get_battery_object(self):
        return self.entities[self.battery_id]

    def get_external_grid_object(self):
        return self.entities[self.power_supply_id]

    def set_battery_attributes(self, **kwargs):
        battery = self.get_battery_object()
        for key, value in kwargs:
            setattr(battery, key, value)

    def set_grid_attributes(self, **kwargs):
        grid = self.get_external_grid_object()
        for key, value in kwargs:
            setattr(grid, key, value)

    def get_battery_attributes(self, *attributes):
        battery = self.get_battery_object()
        values = []
        for attribute in attributes:
            values.append(getattr(battery, attribute))
        if len(values) > 1:
            return values
        elif len(values) == 1:
            return values[0]
        else:
            pass

    def get_grid_attributes(self, *attributes):
        grid = self.get_external_grid_object()
        values = []
        for attribute in attributes:
            values.append(getattr(grid, attribute))
        if len(values) > 1:
            return values
        elif len(values) == 1:
            return values[0]
        else:
            pass

    def _add_component(self, entity):
        if entity.entity_type == ElectricalType.GENERATOR:
            self.has_electrical_energy_source = True
            self.electrical_generators[entity.entity_subtype].append(entity.id)
            if entity.entity_subtype == ElectricalGeneratorSubType.DISPATCHABLE:
                self.has_dispatchable_generators = True
            if entity.entity_subtype == ElectricalGeneratorSubType.STOCHASTIC:
                self.has_stochastic_generators = True

        elif entity.entity_type == ElectricalType.LOAD:
            self.has_electrical_load = True
            self.electrical_loads[entity.entity_subtype].append(entity.id)
            if entity.entity_subtype == ElectricalLoadSubType.FIX:
                self.has_fix_loads = True
            if entity.entity_subtype == ElectricalLoadSubType.INTERRUPTABLE:
                self.has_interruptable_loads = True
            if entity.entity_subtype == ElectricalLoadSubType.SCHEDULABLE:
                self.has_schedulable_loads = True

        elif entity.entity_type == ElectricalType.BATTERY:
            if not self.has_battery:
                self.has_battery = True
                self.battery_id = entity.id
            else:
                raise ValueError('There is already a Battery in this system.')

        elif entity.entity_type == ElectricalType.GRID:
            self.has_electrical_energy_source = True
            if not self.has_external_grid:
                self.has_external_grid = True
                self.power_supply_id = entity.id
            else:
                raise ValueError('There is already a Power Supply in this system.')

    def compute_total_fix_electrical_load(self, prediction_interval, simulation_periods):
        # todo: clean this code. Improve forecast process
        fix_electrical_load = numpy.zeros(simulation_periods)
        for load in self.electrical_loads[ElectricalLoadSubType.FIX]:
            load_forecast = numpy.squeeze(
                self.entities[load].forecast_load(prediction_interval=prediction_interval).values
            )
            fix_electrical_load = fix_electrical_load + load_forecast
        self.fix_electrical_load = fix_electrical_load
        # todo redo with df take into account the datahandler
        return fix_electrical_load

    def compute_total_stochastic_electrical_generation(self, prediction_interval, simulation_periods):
        stochastic_electrical_gen = numpy.zeros(simulation_periods)
        for gen in self.electrical_generators[ElectricalGeneratorSubType.STOCHASTIC]:
            generation_forecast = numpy.squeeze(
                self.entities[gen].forecast_generation(prediction_interval=prediction_interval).values
            )
            stochastic_electrical_gen = stochastic_electrical_gen + generation_forecast
        self.stochastic_electrical_gen = stochastic_electrical_gen
        return stochastic_electrical_gen

    def clear_total_fix_electrical_load(self):
        for load in self.electrical_loads[ElectricalLoadSubType.FIX]:
            self.entities[load].load_forecast_array = None

    def clear_total_stochastic_electrical_generation(self):
        for gen in self.electrical_generators[ElectricalGeneratorSubType.STOCHASTIC]:
            self.entities[gen].generation_forecast_array = None

    def check_system_composition(self):

        if not self.has_electrical_energy_source:
            raise ValueError('Either a external grid (power supply) or generator must be included in the system.')

        if not self.has_electrical_load:
            raise ValueError('At least one load must be included in the system to run a simulation.')

    def prepare_to_optimize(self, config):

        prediction_interval = config['prediction_interval']
        simulation_periods = config['periods']
        current_time = config['current_time']

        self.check_system_composition()
        self.compute_total_fix_electrical_load(prediction_interval, simulation_periods)
        self.compute_total_stochastic_electrical_generation(prediction_interval, simulation_periods)

        if self.has_battery:
            battery = self.get_battery_object()
            battery.get_initial_soc(prediction_interval=prediction_interval)
            battery.get_final_soc(prediction_interval=prediction_interval)

        if self.has_external_grid:
            self.get_external_grid_object().get_prices(prediction_interval)

    def clear(self):
        self.clear_total_fix_electrical_load()
        self.clear_total_stochastic_electrical_generation()
        if self.has_battery:
            self.get_battery_object().clear()
        if self.has_external_grid:
            self.get_external_grid_object().clear()


