from __future__ import absolute_import

from django.db import connection
from django.db.models import Avg, Max, Min, Sum
from django.test import TestCase

from .models import AmountTable

class CastAvgToFloatTest(TestCase):
    def setUp(self):
        AmountTable.objects.create(amount=100)
        AmountTable.objects.create(amount=101)

    def test_avg_disable_avg_cast(self):
        old_val = connection.cast_avg_to_float
        connection.cast_avg_to_float = False
        try:
            self.assertEqual(AmountTable.objects.aggregate(Avg('amount')), {'amount__avg': 100})
        finally:
            connection.cast_avg_to_float = old_val

    def test_avg_cast_avg_to_float(self):
        old_val = connection.cast_avg_to_float
        connection.cast_avg_to_float = True

        try:
            self.assertEqual(AmountTable.objects.aggregate(Avg('amount')), {'amount__avg': 100.5})
        finally:
            connection.cast_avg_to_float = old_val
