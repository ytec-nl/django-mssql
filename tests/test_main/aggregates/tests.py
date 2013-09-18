from __future__ import absolute_import

from operator import attrgetter

from django.db import connection
from django.test import TestCase, skipUnlessDBFeature

from .models import *

class BasicAggregateTest(TestCase):
    def setUp(self):
        AmountTable.objects.create(amount=100)
        AmountTable.objects.create(amount=101)
        AmountTable.objects.create(amount=102)

    def test_avg_disable_avg_cast(self):
        try:
            old_val = connection.cast_avg_to_float
            connection.cast_avg_to_float = False

            self.assertEqual(AmountTable.objects.aggregate(Avg('amount')), {'amount__avg': 101})
        finally:
            connection.cast_avg_to_float = old_val

    def test_avg_cast_avg_to_float(self):
        try:
            old_val = connection.cast_avg_to_float
            connection.cast_avg_to_float = True

            self.assertEqual(AmountTable.objects.aggregate(Avg('amount')), {'amount__avg': 101.0})
        finally:
            connection.cast_avg_to_float = old_val

    def test_max(self):
        self.assertEqual(AmountTable.objects.aggregate(Max('amount')), {'amount__max': 102})

    def test_min(self):
        self.assertEqual(AmountTable.objects.aggregate(Min('amount')), {'amount__min': 100})

    def test_sum(self):
        self.assertEqual(AmountTable.objects.aggregate(Sum('amount')), {'amount__sum': 303})

class CrossTableAggregateTest(TestCase):
    def setUp(self):
        p1 = Player.objects.create(name='player 1')
        p2 = Player.objects.create(name='player 2')

        GamerCard.objects.create(player=p1)
        GamerCard.objects.create(player=p2)

        Bet.objects.create(player=p1, amount="100.00")
        Bet.objects.create(player=p1, amount="200.00")
        Bet.objects.create(player=p1, amount="300.00")
        Bet.objects.create(player=p1, amount="400.00")
        Bet.objects.create(player=p1, amount="500.00")

        Bet.objects.create(player=p2, amount="1000.00")
        Bet.objects.create(player=p2, amount="2000.00")
        Bet.objects.create(player=p2, amount="3000.00")
        Bet.objects.create(player=p2, amount="4000.00")
        Bet.objects.create(player=p2, amount="5000.00")


    def test_cross_table_aggregates(self):
        p = Player.objects.annotate(Count('bet'), avg_bet=Avg('bet__amount')).order_by('name')

        self.assertEqual('player 1', p[0].name)
        self.assertEqual(5, p[0].bet__count)
        self.assertEqual(300, p[0].avg_bet)

        self.assertEqual('player 2', p[1].name)
        self.assertEqual(5, p[1].bet__count)
        self.assertEqual(3000, p[1].avg_bet)

    def test_cross_table_aggregates_values(self):
        p = Player.objects.annotate(bets=Count('bet'), avg_bet=Avg('bet__amount')).values()

        self.assertEqual(2, len(p))

        self.assertEqual(p[0], {'avg_bet': 300.0, 'bets': 5, u'id': 3, 'name': u'player 1'})
        self.assertEqual(p[1], {'avg_bet': 3000.0, 'bets': 5, u'id': 4, 'name': u'player 2'})
