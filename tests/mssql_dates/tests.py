from __future__ import absolute_import

import datetime
from operator import attrgetter

from django.test import TestCase
from django.utils.unittest import expectedFailure

from .models import (LegacyDateTimeTable, LegacyDateTable, LegacyTimeTable,
	DateTable, DateTimeTable, TimeTable, DateTimeOffsetTable,
    DateTimeLegacyDateTimeTable)

class Bug93LookupTest(TestCase):
    # Google code bug #93

    def setUp(self):
        self.jan_2012 = datetime.datetime(2012, 1, 1)
        self.feb_2012 = datetime.datetime(2012, 2, 1)
        self.dec_2013 = datetime.datetime(2013, 12, 1)

    def _test_model_year(self, model, year, expected_count=2):
        model.objects.create(val=self.jan_2012)
        model.objects.create(val=self.feb_2012)
        model.objects.create(val=self.dec_2013)
        self.assertEqual(expected_count, model.objects.filter(val__year=year).count())

    def test_date_lookup_string(self):
        self._test_model_year(DateTable, '2012')

    def test_date_lookup_int(self):
        self._test_model_year(DateTable, 2012)

    def test_datetime_lookup_string(self):
        self._test_model_year(DateTimeTable, '2012')

    def test_datetime_lookup_int(self):
        self._test_model_year(DateTimeTable, 2012)


class DatesTest(TestCase):
    def _test(self, cls, val):
        cls.objects.create(val=val)
        self.assertQuerysetEqual(
            cls.objects.all(),
            [val],
            attrgetter('val')
        )

    def test_legacy_date(self):
        self._test(LegacyDateTable, datetime.date(1901, 1, 1))

    def test_legacy_datetime(self):
        self._test(LegacyDateTimeTable, datetime.datetime(1901, 1, 1, 1, 1, 1, 123000))

    # There is no good way to make this scenario pass
    @expectedFailure
    def test_wrapped_legacy_datetime(self):
        """
        Test a legacy 'datetime' column referenced with a newer 'DateTimeField'
        that expects a 'datetime2' column.
        """
        self._test(DateTimeLegacyDateTimeTable, datetime.datetime(1901, 1, 1, 1, 1, 1, 123000))

    def test_legacy_time(self):
        self._test(LegacyTimeTable, datetime.time(13, 13, 59, 123000))

    def test_new_date(self):
        self._test(DateTable, datetime.date(2013, 9, 18))

    def test_new_datetime(self):
        self._test(DateTimeTable, datetime.datetime(2013, 9, 18, 13, 1, 59, 123456))

    def test_new_time(self):
        self._test(TimeTable, datetime.time(13, 13, 59, 123456))

    def test_datetimeoffset(self):
        from django.utils import timezone
        val = timezone.make_aware(datetime.datetime.now(), timezone.LocalTimezone())
        self._test(DateTimeOffsetTable, val)
