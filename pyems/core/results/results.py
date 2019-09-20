import os
import logging
import pytz

from pyems.config import Setting, Parameter
from pyems.core.entity.entity import Entity
from pyems.core.graphs.graphs import plot_results
from pyems.core.iodata.ioinflux import write_point_to_influxdb


class Results(Entity):
    """This class represents the results of the optimization model in a more user friendly. This class handles the
    output process to files and database and also is though to take care of plotting the solution."""
    def __init__(self, output_data, target_soc, initial_soc=None, timestamp=None):
        super().__init__(name='Results', entity_type='results')

        self.raw_results = output_data
        self.target_soc = target_soc
        self.initial_soc = initial_soc
        self.local_tz = pytz.timezone(Setting.time_zone)
        self.logger = logging.getLogger(f'{Parameter.PACKAGE_NAME}.Results')
        self.timestamp = timestamp.strftime(Parameter.FILE_DATETIME_FORMAT)

    def write_results_to_csv(self, file_name='results.csv', file_path=''):
        file_name = self.timestamp + '_' + file_name
        self.logger.info(f'Writing results to {file_name} file.')
        display_results = self.raw_results.copy()
        display_results.index = display_results.index.tz_localize(pytz.utc).tz_convert(self.local_tz)
        display_results.to_csv(os.path.join(file_path, file_name), sep=',')

    def write_target_soc_to_influxdb(self, soc_entity_id=None, db_connection_parameters=None, measurement='%'):

        self.logger.info('Writing target SOC to InfluxDB.')

        if soc_entity_id is None:
            raise ValueError('An entity id must be specified for the SOC.')

        write_point_to_influxdb(
            measurement=measurement, entity_id=soc_entity_id, value=self.target_soc * 100,
            db_connection_parameters=db_connection_parameters
        )

    def write_target_soc_toc_csv(self):
        raise NotImplementedError
        pass

    def write_target_soc_to_txt_file(
            self, file_name: str = 'soc_target.txt', file_path: str = None, mode: str = 'w'):

        with open(self.timestamp + os.path.join(file_path, file_name), mode=mode) as file:
            file.write(str(round(self.target_soc * 100, 2)))

    def plot(self):
        self.logger.info('Plotting results.')
        plot_results(self.raw_results)
