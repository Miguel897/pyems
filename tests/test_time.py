import unittest
import datetime
import pytz
import pandas
import numpy

from pyems.core.utils.time import (
    timestep_to_seconds, timestep_conversion,  get_following_midnight_utc_timestamp,
    find_next_step_start, check_timestep, series_upsampling, time_unit_conversion, split_timestep
)


class TimeStep(unittest.TestCase):
    """At the moment float timestep are not supported.
    """

    # @unittest.skip("skipping tested tests")
    def test_unit_conversion(self):

        case_std = [
            ('D', 'd'), ('H', 'h'), ('T', 'm'), ('min', 'm'), ('S', 's'), ('d', 'd'), ('h', 'h'), ('m', 'm'), ('s', 's'),
        ]
        case_pd = [
            ('d', 'D'), ('h', 'H'), ('m', 'T'), ('s', 'S'), ('D', 'D'), ('H', 'H'), ('T', 'T'), ('min', 'min'), ('S', 'S'),
        ]

        for case_input, case_output in case_std:
            self.assertEqual(time_unit_conversion(case_input, std_units=True), case_output)

        for case_input, case_output in case_pd:
            self.assertEqual(time_unit_conversion(case_input, pd_units=True), case_output)

    def test_timestep_to_seconds(self):
        with self.assertRaises(ValueError):
            timestep_conversion('1s', std_units=True, pd_units=False)
        with self.assertRaises(ValueError):
            timestep_conversion('10h', std_units=False, pd_units=True)

        case = [
            ('1H', 3600), ('1h', 3600), ('1T', 60), ('1m', 60), ('15min', 15 * 60),
            ('15T', 15 * 60), ('15m', 15 * 60), ('100s', 100), ('100S', 100),
        ]

        for case_input, case_output in case:
            self.assertEqual(timestep_to_seconds(case_input), case_output)

    def test_timestep_conversion(self):
        with self.assertRaises(ValueError):
            timestep_conversion('1h', std_units=True, pd_units=True)
        with self.assertRaises(ValueError):
            timestep_conversion('2h', std_units=True, pd_units=False)
        with self.assertRaises(ValueError):
            timestep_conversion('2h', std_units=False, pd_units=False)
        with self.assertRaises(ValueError):
            timestep_conversion('2s', std_units=True, pd_units=False)
        with self.assertRaises(ValueError):
            timestep_conversion('2s', std_units=False, pd_units=True)

        case_std = [
            ('1H', '1h'), ('1h', '1h'), ('1T', '1m'), ('1m', '1m'), ('15min', '15m'),
            ('15T', '15m'), ('15m', '15m'), ('100s', '100s'), ('100S', '100s'),
        ]

        case_pd = [
            ('1H', '1H'), ('1h', '1H'), ('1T', '1T'), ('1m', '1T'), ('15min', '15min'),
            ('15T', '15T'), ('15m', '15T'), ('100s', '100S'), ('100S', '100S'),
        ]

        for case_input, case_output in case_std:
            self.assertEqual(timestep_conversion(case_input, std_units=True), case_output)

        for case_input, case_output in case_pd:
            self.assertEqual(timestep_conversion(case_input, pd_units=True), case_output)

    def test_split_timestep(self):

        case_std = [
            ('1H', (1, 'h')), ('1h', (1, 'h')), ('1T', (1, 'm')), ('1m', (1, 'm')), ('15min', (15, 'm')),
            ('15T', (15, 'm')), ('15m', (15, 'm')), ('100s', (100, 's')), ('100S', (100, 's')),
        ]

        case_pd = [
            ('1H', (1, 'H')), ('1h', (1, 'H')), ('1T', (1, 'T')), ('1m', (1, 'T')), ('15min', (15, 'min')),
            ('15T', (15, 'T')), ('15m', (15, 'T')), ('100s', (100, 'S')), ('100S', (100, 'S')),
        ]

        for case_input, case_output in case_std:
            self.assertEqual(split_timestep(case_input, std_units=True), case_output)

        for case_input, case_output in case_pd:
            self.assertEqual(split_timestep(case_input, pd_units=True), case_output)

    def test_find_next_step_start(self):

        cases = [
            (
                datetime.datetime(2019, 12, 31, 23, 57),
                '5m',
                datetime.datetime(2020, 1, 1, 0, 0)
            ),
            (
                datetime.datetime(2019, 12, 31, 23, 15, 1),
                '15m',
                datetime.datetime(2019, 12, 31, 23, 30, 0)
            ),

        ]

        for current_time, timestep, next_step in cases:
            self.assertEqual(find_next_step_start(current_time=current_time, timestep=timestep), next_step)

    def test_get_following_midnight_utc_timestamp(self):

        cases = [
            (
                datetime.datetime(2019, 9, 18, 11, 57),
                'Europe/Amsterdam',
                0,
                datetime.datetime(2019, 9, 18, 22, 0)
            ),
            (
                datetime.datetime(2019, 9, 18, 22, 57),
                'Europe/Amsterdam',
                0,
                datetime.datetime(2019, 9, 19, 22, 0)
            ),
            (
                datetime.datetime(2019, 9, 18, 11, 57),
                'Europe/Amsterdam',
                2,
                datetime.datetime(2019, 9, 20, 22, 0)
            ),
            (
                datetime.datetime(2019, 12, 31, 23, 57),
                'Europe/Amsterdam',
                0,
                datetime.datetime(2020, 1, 1, 23, 0)
            )
        ]

        for current_utc_time, local_tz, nights_ahead, target in cases:
            local_tz = pytz.timezone(local_tz)
            self.assertEqual(
                get_following_midnight_utc_timestamp(
                    current_time=current_utc_time, local_tz=local_tz, midnight_ahead=nights_ahead
                ),
                target
            )

    def test_series_upsample(self):

        steps = 10
        index = pandas.date_range(start=datetime.datetime(2019, 12, 31, 23, 0), periods=steps, freq='1H')
        series = pandas.DataFrame({'test_data': list(range(steps))}, index=index)

        cases = [
            (
                '15m',
                [datetime.datetime(2019, 12, 31, 23, 30), datetime.datetime(2020, 1, 1, 1, 30)],
                '1h',
                True,
                [0, 0, 0.25, 0.25, 0.25, 0.25, 0.5, 0.5],
                pandas.date_range(start=datetime.datetime(2019, 12, 31, 23, 30), periods=8, freq='15T'),
            ),

            (
                '15m',
                [datetime.datetime(2019, 12, 31, 23, 30), datetime.datetime(2020, 1, 1, 1, 30)],
                '1h',
                False,
                [0, 0, 1, 1, 1, 1, 2, 2],
                pandas.date_range(start=datetime.datetime(2019, 12, 31, 23, 30), periods=8, freq='15T'),
            )

        ]

        for new_timestep, interval, old_timestep, upsample_values, tgt_values, tgt_index in cases:
            df = series_upsampling(
                series, new_timestep=new_timestep, old_timestep=old_timestep,
                new_time_interval=interval, upsample_values=upsample_values
            )
            self.assertTrue(numpy.array_equal(df['test_data'].values, tgt_values))
            self.assertTrue(numpy.array_equal(df['test_data'].index, tgt_index))


if __name__ == '__main__':
    unittest.main()
