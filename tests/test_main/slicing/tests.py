from django.core.paginator import Paginator
from django.test import TestCase

from slicing.models import *

class PagingTestCase(TestCase):
    """The Paginator uses slicing internally."""
    fixtures = ['paging.json']
    
    def get_q(self, a1_pk):
        return SecondTable.objects.filter(a=a1_pk).order_by('b').select_related(depth=1)

    def try_page(self, page_number, q):
        # Use a single item per page, to get multiple pages.
        pager = Paginator(q, 1)
        self.assertEquals(pager.count, 3)

        on_this_page = list(pager.page(page_number).object_list)
        self.assertEquals(len(on_this_page), 1)
        self.assertEquals(on_this_page[0].b, 'B'+str(page_number))
    
    def testWithDuplicateColumnNames(self):
        a1_pk = FirstTable.objects.get(b='A1').pk
        q = self.get_q(a1_pk)
        
        for i in (1,2,3):
            self.try_page(i, q)
            
    def testPerRowSelect(self):
        a1_pk = FirstTable.objects.get(b='A1').pk
        q = SecondTable.objects.filter(a=a1_pk).order_by('b').select_related(depth=1).extra(select=
        {
        'extra_column': 
            "select slicing_FirstTable.id from slicing_FirstTable where slicing_FirstTable.id=%s" % (a1_pk,)
        })
        
        for i in (1,2,3):
            self.try_page(i, q)

    def testBasicPaging(self):
        names = ['D', 'F', 'B', 'A', 'C', 'E', 'G']
        for n in names: product = Products.objects.create(name=n)
        p = Products.objects
        
        self.assertEquals(len(list(p.all())), 7)
        self.assertEquals(len(list(p.all()[:3])), 3)
        self.assertEquals(len(list(p.all()[2:5])), 3)
        self.assertEquals(len(list(p.all()[5:])), 2)
        self.assertEquals(len(p.all()[0:0]), 0)
        self.assertEquals(len(p.all()[0:0][:10]), 0)
        
        pn = p.order_by('name').values_list('name', flat=True)
        self.assertEquals(list(pn), ['A', 'B', 'C', 'D', 'E', 'F', 'G'])
        self.assertEquals(list(pn[:3]), ['A', 'B', 'C'])
        self.assertEquals(list(pn[2:5]), ['C', 'D', 'E'])
        self.assertEquals(list(pn[5:]), ['F', 'G'])

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
        self.assertEquals(stuff, [u'abc', u'def'])

        stuff = list(baseQ[3:])
        self.assertEquals(stuff, [u'ijk', u'xyz'])

        stuff = list(baseQ[2:4])
        self.assertEquals(stuff, [u'fgh', u'ijk'])

    def testUnusedDistinct(self):
        
        baseQ = DistinctTable.objects.distinct()
        
        stuff = list(baseQ)
        self.assertEquals(len(stuff), 12)
        
        stuff = list(baseQ[:2])
        self.assertEquals(
            [o.s for o in stuff],
            [u'abc', u'abc'])

        stuff = list(baseQ[3:])
        self.assertEquals(
            [o.s for o in stuff], 
            [u'def', u'def', u'fgh', u'fgh', u'fgh', u'fgh', u'ijk', u'ijk', u'xyz'])

        stuff = list(baseQ[2:4])
        self.assertEquals(
            [o.s for o in stuff], 
            [u'abc', u'def'])
