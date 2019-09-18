"""
RESOURCE = 'https://data.sgil.jrc.nl'
rest_query = RESOURCE + '/query?u={}&p={}&db={}&q={}'.format(SGIL_DB_CREDENTIALS['username'], SGIL_DB_CREDENTIALS['password'], SGIL_DB_CREDENTIALS['dbname'], db_query)
response = get(rest_query)#.json()

Examples of queries:

    SELECT * FROM \"kW\" WHERE \"entity_id\"=\'311pv_total_active_power\'and time > now() - 1h and time < now()
    SELECT last(\"value\") FROM \"kW\" WHERE \"entity_id\"=\'311pv_total_active_power\'
    SELECT integral(\"value\") FROM \"kW\" WHERE \"entity_id\"=\'311pv_total_active_power\'and time > now() - 3d and time < now()'

"""

import datetime

import pandas
import numpy
from influxdb import InfluxDBClient

from pyems.config import Parameter
from pyems.core.utils.time import check_time_interval, timestep_conversion, series_upsampling


# INPUT


def get_hourly_stored_series(time_interval, timestep, upsample_values=False, **kwargs):

    time_interval = check_time_interval(time_interval, str_format=Parameter.UTC_DATETIME_FORMAT)

    old_timestep = '1h'

    if timestep != old_timestep:

        hourly_interval = time_interval.copy()

        if time_interval[0].time() > datetime.time(time_interval[0].hour):
            hourly_interval[0] = time_interval[0].replace(minute=0, second=0, microsecond=0)

        if time_interval[1].time() > datetime.time(time_interval[1].hour):
            hourly_interval[1] = time_interval[1].replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=1)

        series = get_df_from_influxdb(
            time_interval=hourly_interval, timestep=old_timestep, check_before_utc_now=False, **kwargs
        )

        timestep = timestep_conversion(timestep, pd_units=True)
        series = series_upsampling(
            series, new_time_interval=time_interval, new_timestep=timestep, old_timestep=old_timestep,
            upsample_values=upsample_values
        )

    else:
        series = get_df_from_influxdb(time_interval=time_interval, timestep=old_timestep, **kwargs)

    return series


def get_df_from_influxdb(
        entities, function='INTEGRAL', time_interval=None, timestep='1h', query_extra_conditions=None,
        db_credentials=None, db_network_route=None, ssl=False, utc_labeled=False,
        series_names=None, check_before_utc_now=True,
):
    """Query SGIL DB for an specific data series and function and return the result in df form. The database store data
    in utc time and then the interval must be also in utc time.
    """

    if function is not None and timestep is None:
        raise ValueError('The timestep is required when a function is provided.')

    if time_interval is not None:
        time_interval = list(time_interval)
        check_time_interval(
            time_interval, str_format=Parameter.UTC_DATETIME_FORMAT, check_before_utc_now=check_before_utc_now
        )

    pandas_timestep = timestep_conversion(timestep, pd_units=True)
    complete_index = pandas.date_range(
        start=time_interval[0], end=time_interval[1], freq=pandas_timestep, closed='left'
    )

    client = connect_to_influxdb(db_credentials=db_credentials, db_network_route=db_network_route, ssl=ssl)

    series_list = []
    for key in entities.keys():
        for entity in entities[key]:
            query_elements = ['SELECT']
            if function is not None:
                query_elements.append(f'{function}(\"{Parameter.INFLUX_VALUE_LABEL}\")')
            else:
                query_elements.append(f'\"{Parameter.INFLUX_VALUE_LABEL}\"')
            query_elements.append(f'FROM \"{key}\"')

            conditions = []
            if entity is not None:
                conditions.append(f'\"entity_id\"=\'{entity}\'')
            if time_interval is not None:
                conditions.append(f'(time >= \'{time_interval[0]}\' AND time < \'{time_interval[1]}\')')
            if query_extra_conditions is not None:
                try:
                    conditions += query_extra_conditions[entity]
                except KeyError:
                    pass
            if conditions:
                query_elements.append('WHERE')
                condition_statement = ' AND '.join(conditions)
                query_elements.append(condition_statement)

            if function is not None and timestep is not None:
                query_elements.append(f'GROUP BY time({timestep})')

            query = ' '.join(query_elements)

            response = client.query(query)
            if function is None:
                function = Parameter.INFLUX_VALUE_LABEL
            series = influxdb_response_to_series(response, function)

            series_name = entity
            if series_names is not None:
                try:
                    series_name = series_names[(key, entity)]
                except KeyError:
                    pass
            series = series.rename(series_name)

            series.index = pandas.to_datetime(series.index)
            if not utc_labeled:
                series.index = series.index.tz_convert(None)  # Delete the utc localize attribute
            if series.shape[0] < complete_index.shape[0]:
                series = series.reindex(complete_index)  # Fills the index gaps

            series.interpolate(inplace=True)
            series.fillna(method='bfill', inplace=True)  # In case the first sample is nan (not filled by interpolate)
            series_list.append(series)

    results = pandas.concat(series_list, axis=1)

    return results


def influxdb_response_to_series(response, function):
    """Converts influx response Points into pandas Series
    """

    function = Parameter.INFLUX_VALUE_LABEL if function is None else function.lower()

    index, values = [], []
    for point in response.get_points():
        index.append(point['time'])
        values.append(point[function])

    series = pandas.Series(values, index=index)

    return series


# OUTPUT


def write_point_to_influxdb(measurement, entity_id, value, db_connection_parameters, time=None):
    """Write a point to the SGIL DB. If the time is specified, the value is labeled with that stamp, otherwise,
    use current time.
    """

    if time is None:
        time = datetime.datetime.utcnow().strftime(Parameter.UTC_DATETIME_FORMAT)

    point = {
        'measurement': measurement,
        'tags': {'entity_id': entity_id},
        'time': time,
        'fields': {'value': value}
    }

    client = InfluxDBClient(**db_connection_parameters)
    client.write_points([point], time_precision='s', protocol='json')


def write_series_to_influxdb(
        series=None, timestamps=None, values=None, measurement=None, entity_id=None,
        db_credentials=None, db_network_route=None
):

    if measurement is None:
        raise ValueError('A measurement should be specified.')

    if timestamps is None and values is None and series is not None:
        if isinstance(series, pandas.DataFrame):
            is_series = False
            if series.shape[1] == 1:
                values = numpy.squeeze(series.values)
            else:
                raise ValueError('The DataFrame has more than one column.')

        elif isinstance(series, pandas.Series):
            is_series = True
            values = series.values
        else:
            raise NotImplementedError('This type of data object is not supported yet.')

        if entity_id is None:
            if is_series:
                entity_id = series.name
            else:
                entity_id = series.columns[0]

        timestamps = list(series.index.strftime(Parameter.UTC_DATETIME_FORMAT))

    if timestamps is not None and values is not None and series is None:
        pass
    else:
        ValueError('Only one of series or timestamps and values should be not None.')

    points = []

    for value, time in zip(values, timestamps):
        points.append(
            {
                'measurement': measurement,
                'tags': {'entity_id': entity_id},
                'time': time,
                'fields': {'value': value}
            }

        )

    client = connect_to_influxdb(db_credentials=db_credentials, db_network_route=db_network_route)
    client.write_points(points, time_precision='s', protocol='json')


# OTHER FUNCTIONS

def connect_to_influxdb(db_credentials, db_network_route, ssl=False):
    """Creates a client to connect to InfluxDB.

    Then the query can be created as: response = client.query(query)
    """

    connection_options = {'ssl': True, 'verify_ssl': True} if ssl else {}
    client = InfluxDBClient(**db_credentials, **db_network_route, **connection_options)

    return client


def get_measurement_list_from_influxdb(
        file_name='measurement_list', break_dot=True, db_credentials=None, db_network_route=None, ssl=False
):

    client = connect_to_influxdb(db_credentials=db_credentials, db_network_route=db_network_route, ssl=ssl)
    response = client.get_list_measurements()

    measurement_list = [table['name'] for table in response]
    with open(file_name + '.csv', 'a', encoding='utf-8') as f:
        for measurement in measurement_list:
            if break_dot:
                if measurement.find('.') >= 0:
                    line = measurement.replace('.', ',')

                else:
                    line = f'measurement_table,{measurement}'

                f.write(f"{line}\n")

            else:
                f.write(f"{measurement}\n")
