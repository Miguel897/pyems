
import datetime

import pytz
import pandas
from requests import get

from pyems.config import Parameter, Constant
from pyems.core.utils.time import check_time_interval, timestep_conversion, series_upsampling


# REE


def get_spanish_electricity_prices(
        time_interval, timestep, tariff='tariff_2.0A', token=None, utc_interval=True, last_included=False
):

    time_interval = check_time_interval(time_interval, str_format=Parameter.UTC_DATETIME_FORMAT)
    hour_step = '1h'

    if timestep != hour_step:

        timestep = timestep_conversion(timestep, pd_units=True)
        hourly_interval = time_interval.copy()

        if time_interval[0].time() > datetime.time(time_interval[0].hour):
            hourly_interval[0] = time_interval[0].replace(minute=0, second=0, microsecond=0)

        if time_interval[1].time() > datetime.time(time_interval[1].hour):
            hourly_interval[1] = time_interval[1].replace(minute=0, second=0, microsecond=0) + datetime.timedelta(
                hours=1)

        prices = get_hourly_spanish_electricity_prices(
            time_interval=hourly_interval, utc_interval=utc_interval, token=token, tariff=tariff,
            last_included=last_included
        )
        prices = prices.to_frame('prices')  # Convert pandas.Series to pandas.DataFrame
        prices = series_upsampling(
            prices, new_time_interval=time_interval, new_timestep=timestep, old_timestep=hour_step,
            upsample_values=False
        )

    else:
        prices = get_hourly_spanish_electricity_prices(
            time_interval=time_interval, utc_interval=utc_interval, token=token, tariff=tariff,
            last_included=last_included
        )

    return prices


def get_hourly_spanish_electricity_prices(
        time_interval, tariff='tariff_2.0A', token=None, utc_interval=True, last_included=False
):
    """Get prices from REE (spanish TSO) for the household electricity prices.

    Some reading regading localize and pytz
        - https://stackoverflow.com/questions/1379740/pytz-localize-vs-datetime-replace
        - http://pytz.sourceforge.net/
    """

    time_zone = 'Europe/Madrid'
    tariff_indicators = {  # See https://www.esios.ree.es/en/pvpc
        'tariff_2.0A': '1013',
        'tariff_2.0DHA': '1014',
        'tariff_2.0DHS': '1015'
    }
    request_headers = {
        "Accept": "application/json; application/vnd.esios-api-v1+json",
        "Content-Type": "application/json",
        "Host": "api.esios.ree.es",
        "Authorization": f"Token token=\"{token}\"",
        "Cookie": ""
    }
    url = f'https://api.esios.ree.es/indicators/{tariff_indicators[tariff]}'

    try:
        time_interval[0]
    except TypeError:
        raise ValueError('The parameter time_interval must be a 2 element tuple-like object.')

    start_datetime, end_datetime = check_time_interval(
        time_interval, str_format=Parameter.O_CLOCK_FORMAT, last_step_included=last_included,
        delta_step='1h', check_oclock=True
    )

    # If the interval is not in utc time, convert the interval to utc time.
    if not utc_interval:

        utc_tz = pytz.utc
        spain_tz = pytz.timezone(time_zone)
        start_datetime_sp = spain_tz.localize(start_datetime)
        end_datetime_sp = spain_tz.localize(end_datetime)

        start_datetime_utc = start_datetime_sp.astimezone(utc_tz)
        end_datetime_utc = end_datetime_sp.astimezone(utc_tz)
    else:
        start_datetime_utc = start_datetime
        end_datetime_utc = end_datetime

    start_datetime_str = start_datetime_utc.strftime(Parameter.O_CLOCK_FORMAT)
    end_datetime_str = end_datetime_utc.strftime(Parameter.O_CLOCK_FORMAT)

    payload = {'start_date': start_datetime_str, 'end_date': end_datetime_str}
    response = get(url, headers=request_headers, params=payload)

    ok_code = 200
    if response.status_code == ok_code:
        pass
    else:
        raise ValueError(f'The query return unexpected status: {response.status_code}')

    response_json = response.json()
    hour_seconds = 3600
    vector_length = int((end_datetime_utc - start_datetime_utc).total_seconds() / hour_seconds) + 1

    price_vector = [response_json['indicator']['values'][h]['value'] / Constant.KILO for h in range(vector_length)]
    time_index = [start_datetime + datetime.timedelta(hours=h) for h in range(vector_length)]

    price_series = pandas.Series(data=price_vector, index=time_index)

    return price_series


# Solar website

def get_forecast_solar_website(time_interval, lat, long, declination, azimuth, pv_power):
    """Get data from the website forecast.solar.
    This website is still work in progress. The output have some errors.

    Example link:
        - https://api.forecast.solar/estimate/52.790066/4.677517/30/0/1

    Example of use:
        response = get_forecast_solar_website(
                    ['2019-08-14T07:00:00Z', '2019-08-14T22:00:00Z'], 52.790066, 4.677517, 30, 0, 1)
    """



    time_interval = check_time_interval(time_interval, last_step_included=True)

    query = f"https://api.forecast.solar/estimate/{lat}/{long}/{declination}/{azimuth}/{pv_power}"
    response = get(query).json()

    index = list(response['result']['watt_hours'].keys())
    values = list(response['result']['watt_hours'].values())
    forecast = pandas.DataFrame({'forecast_solar': values}, index=index)

    forecast.index = pandas.to_datetime(forecast.index)
    results = forecast[(forecast.index > time_interval[0]) & (forecast.index < time_interval[1])]

    return results
