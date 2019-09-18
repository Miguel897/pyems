

import pandas as pd
import logging
import os

from fbprophet import Prophet
from pyems.core.utils.time import check_time_interval, timestep_conversion
from pyems.config import Parameter


class suppress_stdout_stderr(object):
    """A context manager for doing a "deep suppression" of stdout and stderr in
    Python, i.e. will suppress all print, even if the print originates in a
    compiled C/Fortran sub-function.
       This will not suppress raised exceptions, since exceptions are printed
    to stderr just before a script exits, and after the context manager has
    exited (at least, I think that is why it lets exceptions through)."""

    def __init__(self):
        # Open a pair of null files
        self.null_fds = [os.open(os.devnull, os.O_RDWR) for x in range(2)]
        # Save the actual stdout (1) and stderr (2) file descriptors.
        self.save_fds = (os.dup(1), os.dup(2))

    def __enter__(self):
        # Assign the null pointers to stdout and stderr.
        os.dup2(self.null_fds[0], 1)
        os.dup2(self.null_fds[1], 2)

    def __exit__(self, *_):
        # Re-assign the real stdout/stderr back to (1) and (2)
        os.dup2(self.save_fds[0], 1)
        os.dup2(self.save_fds[1], 2)
        # Close the null files
        os.close(self.null_fds[0])
        os.close(self.null_fds[1])


class ProphetOracle:

    def __init__(self):
        self.y_hat = 'yhat'
        self.ph_index = 'ds'
        self.raw_index_label = 'index'
        self.raw_target_label = 'y'
        self.datetime_format = '%Y-%m-%d %H:%M:%S'
        self.logger = logging.getLogger(f'{Parameter.PACKAGE_NAME}.ProphetOracle')

    def forecast(self, forecast_interval, input_data, target_label, timestep):

        forecast_interval = check_time_interval(forecast_interval)

        try:
            input_data.index = input_data.index.tz_convert(None)
        except TypeError:
            pass

        columns = list(input_data.columns)
        columns.remove(target_label)

        if len(columns) > 0:
            self.logger.info(f'Using regressors: {columns}, in FB Prophet model.')

        input_data.interpolate(inplace=True)

        training_data = input_data[input_data.index < forecast_interval[0]].copy()
        test_data = input_data[input_data.index >= forecast_interval[0]].copy()

        training_data[self.raw_index_label] = training_data.index.strftime(self.datetime_format)
        training_data.reset_index(inplace=True, drop=True)
        rename_columns = {self.raw_index_label: self.ph_index, target_label: self.raw_target_label}
        training_data.rename(index=str, columns=rename_columns, inplace=True)

        model = Prophet()
        for column in columns:
            model.add_regressor(column)

        self.logger.info('Training FB Prophet model.')

        with suppress_stdout_stderr():
            model.fit(training_data)

        if test_data.empty:
            timestep = timestep_conversion(timestep, pd_units=True)
            future = pd.date_range(start=forecast_interval[0], end=forecast_interval[1], freq=timestep).values
            test_data = pd.DataFrame({self.ph_index: future})
        else:
            test_data[self.raw_index_label] = test_data.index.strftime(self.datetime_format)
            test_data.reset_index(inplace=True, drop=True)
            rename_columns = {self.raw_index_label: self.ph_index, target_label: self.raw_target_label}
            test_data.rename(index=str, columns=rename_columns, inplace=True)
            test_data.drop(columns=[self.raw_target_label], inplace=True)

        self.logger.info('Producing FB Prophet forecast.')

        forecast_table = model.predict(test_data)
        forecast_table.set_index(self.ph_index, drop=True, inplace=True)
        forecast_table.index = pd.to_datetime(forecast_table.index, format=self.datetime_format, utc=True)

        forecast = forecast_table.loc[:, [self.y_hat]]
        forecast.rename(columns={self.y_hat: target_label}, inplace=True)
        forecast.index.rename(self.raw_index_label, inplace=True)

        return forecast


