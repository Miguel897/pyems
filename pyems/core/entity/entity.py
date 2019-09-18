from pyems.config import Constant
from pyems.core.utils.time import timestep_to_seconds, split_timestep


class Entity:
    """Base class of all entities in the EMS. Having a common ancestor allows to distinguish them from other non
    ems objects and provides some very basic common attributes."""

    __id = 1

    def __init__(self, name, entity_type):
        self.name = name
        self.entity_type = entity_type
        self.__id = Entity.__id
        self._timestep, self.timestep_value, self.timestep_unit, self.timestep_seconds = None, None, None, None
        Entity.__id += 1

    @property
    def id(self):
        return self.__id

    @id.setter
    def id(self, id):
        raise AttributeError('Modifying the id of on object is not allowed.')

    @property
    def timestep(self):
        return self._timestep

    @timestep.setter
    def timestep(self, timestep):
        if timestep is None:
            raise ValueError('A value should be assigned to timestep.')
        seconds = timestep_to_seconds(timestep)
        if 1 * Constant.MINUTE_SECONDS < seconds < 1 * Constant.HOUR_SECONDS:
            self._timestep = timestep
            self.timestep_seconds = timestep_to_seconds(timestep)
            self.timestep_value, self.timestep_unit = split_timestep(timestep, std_units=True)
        else:
            raise ValueError('The time step must be between 1 minute and 1 hour.')
