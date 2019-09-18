from math import sin, cos, radians, degrees, pi
import datetime

import pandas
import numpy
import pysolar
import pytz

from pyems.core.utils.time import check_time_interval, timestep_conversion


def polar2cart(r, polar_angle, azimuthal_angle, unit='degree'):
    """The polar_angle is to the z-axis. Azimuthal_angle to the x-axis.
    :return: (x, y, z) vector
    """
    if unit == 'degree':
        azimuthal_angle = radians(azimuthal_angle)
        polar_angle = radians(polar_angle)
    elif unit == 'radian':
        pass
    else:
        raise ValueError(f'Invalid unit: {unit}')

    cartesian_vector = (
         r * sin(polar_angle) * cos(azimuthal_angle),
         r * sin(polar_angle) * sin(azimuthal_angle),
         r * cos(polar_angle)
    )

    return cartesian_vector


def unit_vector(vector):
    """ Returns a unit vector parallel to the input one."""
    return vector / numpy.linalg.norm(vector)


def limit_angle(angle, unit='radian'):
    """Shed an angle in the interval (-90, 90) degrees
    """
    if unit not in ['radian', 'r', 'degree', 'd']:
        raise ValueError('Invalid unit.')

    limit = 90 if unit == 'degree' else pi/2

    if angle > limit:
        angle = limit
    elif angle < -1 * limit:
        angle = -1 * limit

    return angle


def angle_between(v1, v2, unit='radian', limit=True):
    """ Returns the angle in radians between vectors 'v1' and 'v2'::
    """
    v1_u = unit_vector(v1)
    v2_u = unit_vector(v2)

    angle = numpy.arccos(numpy.clip(numpy.dot(v1_u, v2_u), -1.0, 1.0))

    if unit == 'degree' or unit == 'd':
        angle = degrees(angle)
    if limit:
        angle = limit_angle(angle, unit=unit)

    return angle


def synthetic_solar_irradiance(
        time_interval, panel_tilt, panel_orientation, latitude, longitude, timestep='1h', unit='kW', utc_localize=False
):
    """Creates synthetic solar radiation data for a location and panel geometry.
    """
    ground_vector = (0.0, 0.0, 1.0)  # (x, y, z) length = 1
    panel_vector = polar2cart(1.0, polar_angle=90.0 - panel_tilt, azimuthal_angle=panel_orientation)

    time_interval = check_time_interval(time_interval, last_step_included=False, delta_step=timestep)

    if unit == 'kW' or unit == 'kw':
        scaler = 1000  # Converts to kW
    else:
        scaler = 1

    # The pysolar module requires localized data
    start_datetime = pytz.utc.localize(time_interval[0])
    end_datetime = pytz.utc.localize(time_interval[1])

    date_range = pandas.date_range(
        start=start_datetime, end=end_datetime, freq=timestep_conversion(timestep, pd_units=True)
    )

    dates, radiations = list(), list()

    for time in date_range:
        azimuth, altitude_deg = pysolar.solar.get_position(latitude, longitude, time)
        sun_vector = polar2cart(1, polar_angle=90.0 - altitude_deg, azimuthal_angle=azimuth)

        if altitude_deg <= 0:
            horizontal_radiation = 0.
        else:
            horizontal_radiation = pysolar.radiation.get_radiation_direct(time, altitude_deg) / scaler

        perpendicular_radiation = horizontal_radiation / cos(angle_between(sun_vector, ground_vector))
        tilted_radiatiation = perpendicular_radiation * cos(angle_between(sun_vector, panel_vector))

        radiations.append(tilted_radiatiation)

    radiation_results = pandas.DataFrame({'pysolar_radiation': radiations}, index=date_range)

    if not utc_localize:
        radiation_results.index = radiation_results.index.tz_convert(None)

    return radiation_results
