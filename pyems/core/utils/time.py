# -*- coding: utf-8 -*-
"""
Created on Wed May 15 14:31:22 2019

@author: Miguel
"""

import datetime
import re
from math import ceil

import pytz
import numpy

from pyems.config import (
    Parameter, Constant, PANDAS_TO_STD_CONVERSION_SHORT, STD_TO_PANDAS_CONVERSION_SHORT,
    SHORT_UNIT_CONVERSION,
)


def get_current_time(time_format='datetime'):
    if time_format == 'datetime':
        return datetime.datetime.utcnow()  # todo: check implications. Change results
    else:
        raise NotImplementedError()


def check_time_interval(
        time_interval, str_format=Parameter.UTC_DATETIME_FORMAT, check_before_utc_now=False,
        check_after_utc_now=False, zero_below=None, now=None, last_step_included=True, delta_step=None,
        check_oclock=False,
):

    time_units = ['hour', 'minute', 'second', 'microsecond']
    zero_units = {
        'h': 'hour',
        'm': 'minute',
        's': 'second',
        'hour': 'hour',
        'minute': 'minute',
        'second': 'second',
    }
    delta_units = {
        'h': 'hours',
        'm': 'minutes',
        's': 'seconds',
    }

    time_interval = list(time_interval)

    try:
        time_interval[0]
    except TypeError:
        raise ValueError('The parameter time_interval must be a 2 element tuple-like object.')

    if len(time_interval) != 2:
        raise ValueError('The parameter time_interval must be a 2 element tuple-like object.')

    if not (isinstance(time_interval[0], datetime.datetime) and isinstance(time_interval[1], datetime.datetime)):
        try:
            time_interval = [
                    datetime.datetime.strptime(time_interval[0], str_format),
                    datetime.datetime.strptime(time_interval[1], str_format)
            ]
        except TypeError:
            raise ValueError('The variable time_interval is neither a valid formatted string nor a datetime interval.')

    if time_interval[0] > time_interval[1]:
        raise ValueError('The left-hand side of the time interval must be previous or equal to the right-hand side.')

    if check_oclock:
        zero_units = ['minute', 'second', 'microsecond']
        for unit in zero_units:
            for dt_stamp in time_interval:
                if not eval(f'dt_stamp.{unit}') == 0:
                    raise InvalidTimeError('The datetime is not an o\'clock time.')

    if not last_step_included:
        delta_value, delta_unit = split_timestep(delta_step, std_units=True)
        delta_parameters = {delta_units[delta_unit]: delta_value}
        time_interval[1] = time_interval[1] - datetime.timedelta(**delta_parameters)

    if zero_below is not None:
        zero_units = time_units[time_units.index(zero_units[zero_below]):]
        replace_parameters = dict(zip(zero_units, [0 for _ in range(len(zero_units))]))

        time_interval[0] = time_interval[0].replace(**replace_parameters)
        time_interval[1] = time_interval[1].replace(**replace_parameters)

    if check_before_utc_now or check_after_utc_now:
        if now is None:
            now = datetime.datetime.utcnow()

        for t in time_interval:
            if check_before_utc_now:
                if t > now:
                    raise ValueError('At least one of the dates of the time interval is not a past date.')
            elif check_after_utc_now:
                if t < now:
                    raise ValueError('At least one of the datetime in the time interval is not a future date.')

    return time_interval


def split_timestep(timestep, std_units=False, pd_units=False):
    """Split a time step in the form 1h (value unit) in step=1 and time_unit=h.
    """

    if std_units and pd_units:
        raise ValueError('Select at most one unit conversion type.')

    check_timestep(timestep)

    # Equivalence in seconds

    match = timestep_match(timestep)

    if match:
        items = match.groups()
        if len(items) == 2:
            step = int(items[0])
            time_unit = items[1]
        else:
            raise ValueError('Invalid timestep.')

    else:
        raise ValueError('Invalid timestep.')

    if std_units or pd_units:
        time_unit = time_unit_conversion(time_unit, std_units=std_units, pd_units=pd_units)

    return step, time_unit


def timestep_match(timestep):
    # The re.I make the match case insensitive
    # return re.match(r"(^[\d.]+)([a-z]+)", timestep, flags=re.I)  # floats
    return re.match(r"(^[\d]+)([a-z]+)", timestep, flags=re.I)  # int


def timestep_to_seconds(timestep, check_length=True, check_hour_subdivision=True):

    second_conversion = check_timestep(
        timestep, check_length=check_length, check_hour_subdivision=check_hour_subdivision,
    )

    return second_conversion


def _timestep_to_seconds_no_check(timestep):

    match = timestep_match(timestep)
    if match:
        items = match.groups()
        if len(items) == 2:
            step = int(items[0])
            time_unit = items[1]
        else:
            raise ValueError('Invalid timestep.')

    else:
        raise ValueError('Invalid timestep.')

    second_conversion = step * SHORT_UNIT_CONVERSION[time_unit]

    return second_conversion


def time_unit_conversion(time_unit, std_units=False, pd_units=False):
    """

    Pandas Units as in:
        - https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#timeseries-offset-aliases

    :param time_unit:
    :param std_units:
    :param pd_units:
    :return:
    """

    unit_conversion = None

    if not(bool(std_units) != bool(pd_units)):
        raise ValueError('One and only one type of conversion should be selected.')

    if std_units:
        unit_conversion = PANDAS_TO_STD_CONVERSION_SHORT
    elif pd_units:
        unit_conversion = STD_TO_PANDAS_CONVERSION_SHORT

    return unit_conversion[time_unit]


def timestep_conversion(timestep, std_units=False, pd_units=False, check_length=True, check_hour_subdivision=True):

    if not(bool(std_units) != bool(pd_units)):
        raise ValueError('One and only one type of conversion should be selected.')

    check_timestep(
        timestep, check_length=check_length, check_hour_subdivision=check_hour_subdivision,
    )

    match = timestep_match(timestep)
    if match:
        items = match.groups()
        output = items[0] + time_unit_conversion(items[1], std_units=std_units, pd_units=pd_units)
    else:
        raise ValueError('Invalid timestep.')

    return output


def series_upsampling(series, new_timestep, new_time_interval=None, old_timestep='1h', upsample_values=False):
    old_timestep_seconds = timestep_to_seconds(old_timestep)
    new_timestep_seconds = timestep_to_seconds(new_timestep)

    if new_time_interval is None:
        index = series.index.to_pydatetime()
        time_interval = [index[0], index[-1]]
    else:
        time_interval = new_time_interval

    if new_timestep_seconds > old_timestep_seconds:
        raise ValueError('Downsampling not supported.')

    if new_timestep_seconds != old_timestep_seconds:
        series = series.copy()

        try:
            series.at[time_interval[1], series.columns[0]]
        except KeyError:
            series.at[time_interval[1], series.columns[0]] = numpy.NAN

        new_timestep_pandas = timestep_conversion(new_timestep, pd_units=True)
        series = series.resample(new_timestep_pandas).pad()
        if upsample_values:
            down_fraction = new_timestep_seconds / old_timestep_seconds  # Number of new periods in the old one
            series = series * down_fraction

    series = series[(series.index >= time_interval[0]) & (series.index < time_interval[1])]

    return series


def utc_to_local(utc_datetime, local_tz, output='dt'):

    if output not in ['dt', 'str']:
        raise ValueError(f'Invalid output format tag: {output}.')

    try:
        tz_offset = local_tz.utcoffset(utc_datetime)
    except AttributeError:
        utc_datetime = datetime.datetime.strptime(utc_datetime, format=Parameter.UTC_DATETIME_FORMAT)
        tz_offset = local_tz.utcoffset(utc_datetime)

    local_time = utc_datetime + tz_offset

    if output == 'str':
        local_time = local_time.strftime(Parameter.LOCAL_DATETIME_FORMAT)

    return local_time


def local_to_utc(local_datetime, local_tz, output='dt'):

    if output not in ['dt', 'str']:
        raise ValueError(f'Invalid output format tag: {output}.')

    try:
        local_datetime = local_tz.localize(local_datetime)
    except AttributeError:
        local_datetime = datetime.datetime.strptime(local_datetime, format=Parameter.UTC_DATETIME_FORMAT)
        local_datetime = local_tz.localize(local_datetime)

    utc_time = local_datetime.astimezone(pytz.utc)

    if output == 'str':
        utc_time = utc_time.strftime(format=Parameter.UTC_DATETIME_FORMAT)
    elif output == 'dt':
        utc_time = datetime.datetime(
            year=utc_time.year, month=utc_time.month, day=utc_time.day, hour=utc_time.hour,
            minute=utc_time.minute, second=utc_time.second, microsecond=utc_time.microsecond
        )

    return utc_time


def check_timestep(timestep, check_length=True, check_hour_subdivision=True):
    second_conversion = _timestep_to_seconds_no_check(timestep)

    if check_length and not (1 * Constant.MINUTE_SECONDS <= second_conversion <= 1 * Constant.HOUR_SECONDS):
        raise ValueError('The timestep must be between 1 minute and 1 hour.')
    if check_hour_subdivision and (Constant.HOUR_SECONDS % second_conversion != 0):
        raise ValueError('The timestep must be the result of dividing 1 hour in equal intervals.')

    return second_conversion


def find_next_step_start(current_time, timestep):
    """Compute the start of the next timestep.

    This function assume the timestep is between 1 minute and 1 hour.

    :param timestep:
    :param current_time:
    :return:
    """

    starting_hour = datetime.datetime.combine(current_time.date(), datetime.time(current_time.hour))
    delta_seconds = ceil((current_time - starting_hour).total_seconds())
    timestep_seconds = timestep_to_seconds(timestep)
    steps = ceil(delta_seconds / timestep_seconds)
    start = starting_hour + datetime.timedelta(seconds=steps * timestep_seconds)
    
    return start


def get_following_midnight_utc_timestamp(current_time, local_tz, midnight_ahead=0):

    local_current_datetime = utc_to_local(current_time, local_tz=local_tz)
    local_midnight_datetime = datetime.datetime.combine(
        local_current_datetime.date() + datetime.timedelta(days=midnight_ahead + 1), datetime.time(0)
    )
    utc_midnight_datetime = local_to_utc(local_midnight_datetime, local_tz=local_tz)

    return utc_midnight_datetime


def get_fix_simulation_length_end_timestamp(start, simulation_length):
    delta_seconds = timestep_to_seconds(simulation_length)
    end = start + datetime.timedelta(seconds=delta_seconds)
    return end


class InvalidTimeError(Exception):
    pass


class TimeInterval:
    pass  # todo: implement this class to replace the time interval list
