
import logging

from pyems.core.entity.entity import Entity
from pyems.core.utils.time import split_timestep, timestep_to_seconds


class BaseSystemComponent(Entity):
    """Base class for implementing electrical loads."""
    def __init__(self, name, entity_type='base_component', entity_subtype=None, timestep=None):
        super().__init__(name=name, entity_type=entity_type)
        self.entity_subtype = entity_subtype
        if timestep is not None:
            self.timestep = timestep

        self._logger_name = self.name.capitalize()
        self.logger = logging.getLogger(f"ems.system_entities.{self._logger_name}")
