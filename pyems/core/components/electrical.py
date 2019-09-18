import datetime
import weakref

import numpy

from pyems.core.components.base import BaseSystemComponent
from pyems.core.forecasting.prophet import ProphetOracle
from pyems.core.utils.time import check_time_interval
from pyems.config import ElectricalType, ElectricalLoadSubType, ElectricalGeneratorSubType


# ELECTRICAL_GENERATORS


class BaseElectricalGenerator(BaseSystemComponent):
    """Base class for electrical generators."""
    def __init__(self, name='generator', max_electrical_power=None, training_span=None, gap=0, **kwargs):
        super().__init__(name=name, entity_type=ElectricalType.GENERATOR, **kwargs)
        self.max_electrical_power = max_electrical_power
        self.min_electrical_power = 0
        self.training_span = training_span
        self.gap = gap  # Time step gap between the training and test data. In our case zero.
    
    def capacity_postprocessing(self, forecast):
        # todo: check implementation
        forecast[forecast < self.min_electrical_power] = self.min_electrical_power
        forecast[forecast > self.max_electrical_power] = self.max_electrical_power

        return forecast


class StochasticElectricalGenerator(BaseElectricalGenerator):
    """Generic class for implementing electrical generators of no specific type using some black box model forecast."""
    def __init__(
            self, name='stochatic_electrical_generator', historical_label=None, regressor_labels=None,
            forecast_model=None, data_handler=None,
            preprocessing_callback=None, postprocessing_callback=None, **kwargs
):
        super().__init__(name=name, entity_subtype=ElectricalGeneratorSubType.STOCHASTIC, **kwargs)

        self.generation_forecast_array = None
        self.historical_label = historical_label
        self.regressor_labels = regressor_labels

        self.forecast_model = ProphetOracle() if forecast_model is None else forecast_model
        self._data_handler = weakref.ref(data_handler)
        self._preprocessing_callback = preprocessing_callback
        self._postprocessing_callback = postprocessing_callback

    @property
    def data_handler(self):
        if not self._data_handler:
            return self._data_handler
        _data_handler = self._data_handler()
        if _data_handler:
            return _data_handler
        else:
            raise LookupError("Referenced data_handler was deleted.")

    @data_handler.setter
    def data_handler(self, data_handler):
        self.data_handler = weakref.ref(data_handler)

    def forecast_generation(self, prediction_interval):
        """This class connect to the InfluxDB to obtain historical data of the building consumption and uses the
        Facebook Prophet to produce a forecast."""
        prediction_interval = check_time_interval(prediction_interval)
        historical_interval = [
            prediction_interval[0] - datetime.timedelta(
                seconds=(self.gap + self.training_span) * self.timestep_seconds),
            prediction_interval[0] - datetime.timedelta(seconds=(self.gap + 1) * self.timestep_seconds)
        ]

        labels = [self.historical_label] + self.regressor_labels
        data = self.data_handler.get_data_series(
            labels=labels, prediction_interval=prediction_interval, historical_interval=historical_interval
        )

        # Preprocessing input data before forecasting
        if self._preprocessing_callback is not None:
            data = self._preprocessing_callback(data)

        forecast = self.forecast_model.forecast(
            prediction_interval, data, self.historical_label, timestep=self.timestep
        )

        # Postprocessing forecast
        # self.capacity_postprocessing(forecast)

        if self._postprocessing_callback is not None:
            forecast = self._postprocessing_callback(forecast)

        self.generation_forecast_array = forecast
        return forecast


class DispatchableElectricalGenerator(BaseElectricalGenerator):
    def __init__(self):
        raise NotImplementedError  # todo: implement


# ELECTRICAL_LOADS


class BaseElectricalLoad(BaseSystemComponent):
    """Base class for implementing electrical loads."""
    def __init__(self, name='load', training_span=None, gap=0, **kwargs):
        super().__init__(name=name, entity_type=ElectricalType.LOAD, **kwargs)
        self.training_span = training_span
        self.gap = gap


class FixElectricalLoad(BaseElectricalLoad):
    """Generic class for implementing electrical loads of no specific type using some black box model forecast."""
    def __init__(
            self, historical_label, regressor_labels, forecast_model=None, data_handler=None,
            preprocessing_callback=None, postprocessing_callback=None, **kwargs
    ):
        super().__init__(entity_subtype=ElectricalLoadSubType.FIX, **kwargs)

        self.load_forecast_array = None
        self.historical_label = historical_label
        self.regressor_labels = regressor_labels

        self.forecast_model = ProphetOracle() if forecast_model is None else forecast_model
        self._data_handler = weakref.ref(data_handler)
        self._preprocessing_callback = preprocessing_callback
        self._postprocessing_callback = postprocessing_callback

    @property
    def data_handler(self):
        if not self._data_handler:
            return self._data_handler
        _data_handler = self._data_handler()
        if _data_handler:
            return _data_handler
        else:
            raise LookupError("Referenced data_handler was deleted.")

    @data_handler.setter
    def data_handler(self, data_handler):
        self.data_handler = weakref.ref(data_handler)

    def forecast_load(self, prediction_interval):
        """This class connect to the InfluxDB to obtain historical data of the building consumption and uses the
        Facebook Prophet to produce a forecast."""
        prediction_interval = check_time_interval(prediction_interval)
        historical_interval = [
            prediction_interval[0] - datetime.timedelta(
                seconds=(self.gap + self.training_span) * self.timestep_seconds),
            prediction_interval[0] - datetime.timedelta(seconds=(self.gap + 1) * self.timestep_seconds)
        ]

        labels = [self.historical_label] + self.regressor_labels
        data = self.data_handler.get_data_series(
            labels=labels, prediction_interval=prediction_interval, historical_interval=historical_interval
        )

        # Preprocessing input data before forecasting
        if self._preprocessing_callback is not None:
            data = self._preprocessing_callback(data)

        forecast = self.forecast_model.forecast(
            prediction_interval, data, self.historical_label, timestep=self.timestep
        )

        # Postprocessing forecast
        if self._postprocessing_callback is not None:
            forecast = self._postprocessing_callback(forecast)

        self.load_forecast_array = forecast
        return forecast


class SchedulableElectricalLoad(BaseElectricalLoad):
    def __init__(self):
        super().__init__()
        raise NotImplementedError  # todo: implement


# EXTERNAL GRIDS

class ElectricalExternalGrid(BaseSystemComponent):
    """Base class to implement grids."""
    def __init__(
            self, name='grid', max_power=None, max_selling=None, purchase_label=None,
            sell_label=None, data_handler=None, publication_time=None, forecast_model=None, **kwargs
    ):
        super().__init__(name=name, entity_type=ElectricalType.GRID, **kwargs)
        self.max_power = max_power
        self.max_selling = max_selling
        self.electricity_purchase_prices = None
        self.electricity_selling_prices = None
        self.publication_time = datetime.time.fromisoformat(publication_time)
        self.prices_known_in_advance = True
        self.selling_allowed = True

        self.purchase_label = purchase_label
        self.sell_label = sell_label
        self.purchase_regressor_labels = None
        self.sell_regressor_labels = None

        if forecast_model is not None:
            self.forecast_model = forecast_model
        if forecast_model is None and not self.prices_known_in_advance:
            self.forecast_model = ProphetOracle()
        else:
            self.forecast_model = None

        self._data_handler = weakref.ref(data_handler)
        # self._preprocessing_callback = preprocessing_callback
        # self._postprocessing_callback = postprocessing_callback

    @property
    def data_handler(self):
        if not self._data_handler:
            return self._data_handler
        _data_handler = self._data_handler()
        if _data_handler:
            return _data_handler
        else:
            raise LookupError("Referenced data_handler was deleted.")

    @data_handler.setter
    def data_handler(self, data_handler):
        self.data_handler = weakref.ref(data_handler)

    def get_prices(self, prediction_interval):
        if self.prices_known_in_advance:
            purchase_princes = self.get_purchase_prices(prediction_interval)
            sell_princes = self.get_sell_prices(prediction_interval)
        else:
            raise NotImplementedError('Not known prices not implemented yet.')
            # purchase_princes = self.forecast_purchase_prices(prediction_interval)
            # sell_princes = self.forecast_sell_prices(prediction_interval)

        return purchase_princes, sell_princes

    def get_purchase_prices(self, prediction_interval):
        purchase_prices = self.data_handler.get_data_series(
            labels=self.purchase_label, prediction_interval=prediction_interval
        )
        self.electricity_purchase_prices = numpy.squeeze(purchase_prices.values)
        return self.electricity_purchase_prices

    def get_sell_prices(self, prediction_interval):
        sell_prices = self.data_handler.get_data_series(
            labels=self.sell_label, prediction_interval=prediction_interval
        )
        self.electricity_selling_prices = numpy.squeeze(sell_prices.values)
        return self.electricity_selling_prices

    def forecast_purchase_prices(self, prediction_interval):
        pass

    def forecast_sell_prices(self, prediction_interval):
        pass

    def clear(self):
        self.electricity_purchase_prices = None
        self.electricity_selling_prices = None


# ELECTRICAL_BATTERIES


class ElectricalBattery(BaseSystemComponent):
    """Base class to implement a battery."""
    def __init__(
            self, name='battery', timestep=None, batt_C=None, soc_0=None, soc_l=None, soc_lb=None, soc_ub=None,
            batt_chrg_speed=None, batt_dis_speed=None, batt_chrg_per=None, batt_dis_per=None, data_handler=None,
            initial_soc_label=None, final_soc_labels=None
    ):
        super().__init__(name=name, entity_type=ElectricalType.BATTERY, timestep=timestep)
        self.batt_C = batt_C  # (kWh) Capacity of the battery
        self.soc_0 = soc_0  # (%) Initial battery SOC
        self.soc_l = soc_l  # (%) Battery SOC at hour 24
        self.soc_lb = soc_lb   # (%) Minimum battery SOC at any hour
        self.soc_ub = soc_ub  # (%) Max battery SOC at any hour
        self.batt_chrg_speed = batt_chrg_speed  # (kWh) Max energy to charge the battery
        self.batt_dis_speed = batt_dis_speed  # (kWh) Max energy to discharge the battery
        self.batt_chrg_per = batt_chrg_per  # (%) Charging performance
        self.batt_dis_per = batt_dis_per  # (%) Disharging performance
        self.target_soc = None
        self.initial_soc_label = initial_soc_label
        self.final_soc_labels = final_soc_labels
        self._data_handler = weakref.ref(data_handler)

    @property
    def data_handler(self):
        if not self._data_handler:
            return self._data_handler
        _data_handler = self._data_handler()
        if _data_handler:
            return _data_handler
        else:
            raise LookupError("Referenced data_handler was deleted.")

    @data_handler.setter
    def data_handler(self, data_handler):
        self.data_handler = weakref.ref(data_handler)

    def get_initial_soc(self):
        self.soc_0 = self.data_handler.get_data_point(labels=self.initial_soc_label)

    def assess_final_soc(self, current_time, day_ahead=2):
        prediction_interval = [current_time, current_time + datetime.timedelta(days=day_ahead)]

        solar_energy = self.data_handler.get_data_series(
            labels=self.final_soc_labels, prediction_interval=prediction_interval
        )
        mean = numpy.mean(solar_energy.values)

        # Higher value of average sunpower for the next days means less battery SOC required. Tune this values with
        # a more detailed analysis.

        # todo: improve final soc assessment
        if mean >= 225:
            self.soc_l = 0.4
        elif mean >= 175:
            self.soc_l = 0.6
        else:
            self.soc_l = 0.8

    def soc_to_energy(self, soc_delta):

        # Positive soc_ delta, battery is charging
        if soc_delta <= 0:  # Discharging if the soc_delta is negative
            energy_delta = -1 * soc_delta * self.batt_C * self.batt_dis_per
        else:
            energy_delta = -1 * soc_delta * self.batt_C / self.batt_chrg_per

        return energy_delta

    def energy_to_soc(self, energy):
        # Positive energy: battery is discharging, giving energy to the system

        if energy >= 0:  # Discharging if the energy is positive
            soc_delta = -1 * energy / self.batt_dis_per / self.batt_C
        else:
            soc_delta = -1 * energy * self.batt_chrg_per / self.batt_C

        return soc_delta

    def determine_power(self, target_soc, time=3600):
        # time in seconds
        self.target_soc = target_soc

        soc_delta = self.target_soc - self.soc_0
        energy_delta = self.soc_to_energy(soc_delta)
        power = energy_delta * 3600 / time

        return power

    def clear(self):
        self.soc_0 = None
        self.soc_l = None




