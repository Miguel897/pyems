import pandas
from pyems.core.entity.entity import Entity


class BaseDataHandler(Entity):
    def __init__(self, name='data_handler', timestep=None):
        super().__init__(name=name, entity_type='data_handler')
        if timestep is not None:
            self.timestep = timestep
        else:
            raise ValueError('A value must be assigned to the DataHandler timestep')

        self._series_dispatcher = None
        self._point_dispatcher = None

    def get_data_series(self, labels, prediction_interval=None, historical_interval=None, timestep=None, **kwargs):
        """Obtain data series from DataHandler.

        :param labels:
        :param prediction_interval:
        :param historical_interval:
        :param timestep:
        :param kwargs:
        :return:
        """

        if prediction_interval is None and historical_interval is None:
            raise ValueError('Either the historical or the prediction interval must be specified.')

        if timestep is None:
            timestep = self.timestep

        if isinstance(labels, str):  # In case of a unique label
            label = labels
            if label not in self._series_dispatcher.keys():
                raise KeyError(f'Unable to find the handler of the label: {label}.')

            series = self._series_dispatcher[label](
                prediction_interval=prediction_interval, historical_interval=historical_interval, **kwargs
            )

            if isinstance(series, pandas.DataFrame):
                return series
            elif isinstance(series, pandas.Series):
                return pandas.DataFrame(series)
            else:
                # todo: handle none pandas returns types
                raise NotImplementedError('The return type of a get_data function should be Series or DataFrame.')

        else:  # In case of a list of labels
            labels[:0]  # Duck test for list-like
            container = []
            for label in labels:
                if label not in self._series_dispatcher.keys():
                    raise KeyError(f'Unable to find the handler of the label: {label}.')

                series = self._series_dispatcher[label](
                    prediction_interval=prediction_interval, historical_interval=historical_interval, **kwargs
                )

                container.append(series)

            return pandas.concat(container, axis=1)

    def get_data_point(self, labels, prediction_interval=None, **kwargs):

        if isinstance(labels, str):  # In case of a unique label
            label = labels
            if label not in self._point_dispatcher.keys():
                raise KeyError(f'Unable to find the handler of the label: {label}.')

            point = self._point_dispatcher[label](
                prediction_interval=prediction_interval, **kwargs
            )

            return point

        else:  # In case of a list of labels
            labels[:0]  # Duck test for list-like
            container = []
            for label in labels:
                if label not in self._point_dispatcher.keys():
                    raise KeyError(f'Unable to find the handler of the label: {label}.')

                point = self._point_dispatcher[label](
                    prediction_interval=prediction_interval, **kwargs
                )

                container.append(point)

            return container

    def add_series_dispatcher(self, dispatcher):
        self._series_dispatcher = dispatcher

    def add_point_dispatcher(self, dispatcher):
        self._point_dispatcher = dispatcher
