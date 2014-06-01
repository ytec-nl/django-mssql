from __future__ import absolute_import

from django.core.paginator import Paginator
from django.db.models import Q
from django.test import TestCase

from .models import DistinctTable, ItemGroup, Item

class DistinctTestCase(TestCase):
    def setUp(self):
        DistinctTable(s='abc').save()
        DistinctTable(s='abc').save()
        DistinctTable(s='abc').save()
        DistinctTable(s='def').save()
        DistinctTable(s='def').save()
        DistinctTable(s='fgh').save()
        DistinctTable(s='fgh').save()
        DistinctTable(s='fgh').save()
        DistinctTable(s='fgh').save()
        DistinctTable(s='ijk').save()
        DistinctTable(s='ijk').save()
        DistinctTable(s='xyz').save()

    def testLimitDistinct(self):

        baseQ = DistinctTable.objects.values_list('s', flat=True).distinct()

        stuff = list(baseQ)
        self.assertEquals(len(stuff), 5)

        stuff = list(baseQ[:2])
        self.assertEquals(stuff, ['abc', 'def'])

        stuff = list(baseQ[3:])
        self.assertEquals(stuff, ['ijk', 'xyz'])

        stuff = list(baseQ[2:4])
        self.assertEquals(stuff, ['fgh', 'ijk'])

    def testUnusedDistinct(self):

        baseQ = DistinctTable.objects.distinct()

        stuff = list(baseQ)
        self.assertEquals(len(stuff), 12)

        stuff = list(baseQ[:2])
        self.assertEquals(
            [o.s for o in stuff],
            ['abc', 'abc'])

        stuff = list(baseQ[3:])
        self.assertEquals(
            [o.s for o in stuff],
            ['def', 'def', 'fgh', 'fgh', 'fgh', 'fgh', 'ijk', 'ijk', 'xyz'])

        stuff = list(baseQ[2:4])
        self.assertEquals(
            [o.s for o in stuff],
            ['abc', 'def'])


class SlicingRegressionTests(TestCase):
    def test_order_from_foreign_key(self):
        """
        Page a query that is ordered by a column from the foreign key.
        """
        group1 = ItemGroup.objects.create(name='group1')
        group1.items.create(name='g1 item1')
        group1.items.create(name='g1 item2')
        group1.items.create(name='g1 item3')
        group2 = ItemGroup.objects.create(name='group2')
        group2.items.create(name='g2 item1')
        group2.items.create(name='g2 item2')
        group3 = ItemGroup.objects.create(name='group3')
        group3.items.create(name='g3 item1')
        group3.items.create(name='g3 item1')

        qs = Item.objects.filter(
            Q(name__icontains='item')
        )[5:7]


        self.assertEqual(2, len(qs))
        for item in qs:
            self.assertTrue(item.name.startswith('g3'))

