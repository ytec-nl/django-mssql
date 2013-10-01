import datetime
import decimal
from operator import attrgetter
import time
from django.core.exceptions import ImproperlyConfigured
from django.db import models, connection
from django.test import TestCase
from django.utils.safestring import mark_safe

from regressiontests.models import *

class Bug38Table(models.Model):
    d = models.DecimalField(max_digits=5, decimal_places=2)


class Bug38TestCase(TestCase):
    def testInsertVariousFormats(self):
        """
        Test adding decimals as strings with various formats.
        """
        Bug38Table(d=decimal.Decimal('0')).save()
        Bug38Table(d=decimal.Decimal('0e0')).save()
        Bug38Table(d=decimal.Decimal('0E0')).save()
        Bug38Table(d=decimal.Decimal('450')).save()
        Bug38Table(d=decimal.Decimal('450.0')).save()
        Bug38Table(d=decimal.Decimal('450.00')).save()
        Bug38Table(d=decimal.Decimal('450.000')).save()
        Bug38Table(d=decimal.Decimal('0450')).save()
        Bug38Table(d=decimal.Decimal('0450.0')).save()
        Bug38Table(d=decimal.Decimal('0450.00')).save()
        Bug38Table(d=decimal.Decimal('0450.000')).save()
        Bug38Table(d=decimal.Decimal('4.5e+2')).save()
        Bug38Table(d=decimal.Decimal('4.5E+2')).save()
        self.assertEquals(len(list(Bug38Table.objects.all())),13)

    def testReturnsDecimal(self):
        """
        Test if return value is a python Decimal object 
        when saving the model with a Decimal object as value 
        """
        Bug38Table(d=decimal.Decimal('0')).save()
        d1 = Bug38Table.objects.all()[0]
        self.assertEquals(decimal.Decimal, d1.d.__class__)

    def testReturnsDecimalFromString(self):
        """
        Test if return value is a python Decimal object 
        when saving the model with a unicode object as value.
        """
        Bug38Table(d=u'123').save()
        d1 = Bug38Table.objects.all()[0]
        self.assertEquals(decimal.Decimal, d1.d.__class__)        

    def testSavesAfterDecimal(self):
        """
        Test if value is saved correctly when there are numbers 
        to the right side of the decimal point 
        """
        Bug38Table(d=decimal.Decimal('450.1')).save()
        d1 = Bug38Table.objects.all()[0]
        self.assertEquals(decimal.Decimal('450.1'), d1.d)
    
    def testInsertWithMoreDecimals(self):
        """
        Test if numbers to the right side of the decimal point 
        are saved correctly rounding to a decimal with the correct 
        decimal places.
        """
        Bug38Table(d=decimal.Decimal('450.111')).save()
        d1 = Bug38Table.objects.all()[0]
        self.assertEquals(decimal.Decimal('450.11'), d1.d)    
        
    def testInsertWithLeadingZero(self):
        """
        Test if value is saved correctly with Decimals with a leading zero.
        """
        Bug38Table(d=decimal.Decimal('0450.0')).save()
        d1 = Bug38Table.objects.all()[0]
        self.assertEquals(decimal.Decimal('450.0'), d1.d)


class Bug69TestCase(TestCase):
    def setUp(self):
        for x in xrange(0,5):
            Bug69Table2.objects.create(
                id=x,
                related_obj=Bug69Table1.objects.create(id=x),
            )
        
    def testConflictingFieldNames(self):
        objs = list(Bug69Table2.objects.select_related('related_obj')[2:4])
        self.assertEqual(len(objs), 2)



class Bug70TestCase(TestCase):
    def testInsert(self):
        Bug70Table.objects.create(a=100);
        Bug70Table.objects.create(a=101);
        Bug70Table.objects.create(a=102);
        
        results = Bug70Table.objects.all()
        
        self.assertEquals(results.count(), 3)
        
        self.assertTrue(hasattr(results[0], 'id'))
        self.assertTrue(results[0].id == 1)

class Bug85TestCase(TestCase):
    def testEuropeanDecimalConversion(self):
        from sqlserver_ado.dbapi import _cvtDecimal
        
        val1 = _cvtDecimal('0,05')
        self.assertEqual(decimal.Decimal('0.05'), val1)
        
    def testEuropeanFloatConversion(self):
        from sqlserver_ado.dbapi import _cvtFloat
        
        val1 = _cvtFloat('0,05')
        self.assertEqual(float('0.05'), val1)
        

class Bug93TestCase(TestCase):
    def setUp(self):
        dates = (
            (2009, 1),
            (2009, 2),
            (2009, 3),
            (2010, 1),
            (2010, 2)
        )
            
        for year, month in dates:
            dt = datetime.datetime(year, month, 1)

            Bug93Table.objects.create(
                dt=dt,
                d=dt.date()
            )   
    
    def testDateYear(self):
        dates = Bug93Table.objects.filter(d__year=2009)
        self.assertTrue(dates.count() == 3)

        dates = Bug93Table.objects.filter(d__year='2010')
        self.assertTrue(dates.count() == 2)
        
        
    def testDateTimeYear(self):
        dates = Bug93Table.objects.filter(dt__year=2009)
        self.assertTrue(dates.count() == 3)

        dates = Bug93Table.objects.filter(dt__year='2010')
        self.assertTrue(dates.count() == 2)

class BasicFunctionalityTestCase(TestCase):
    def testRandomOrder(self):
        """
        Check that multiple results with order_by('?') return
        different orders.
        """
        for x in xrange(1,20):
            IntegerIdTable.objects.create(id=x)

        a = list(IntegerIdTable.objects.all().order_by('?'))
        b = list(IntegerIdTable.objects.all().order_by('?'))
        
        self.assertNotEquals(a, b)

    def testRawUsingRowNumber(self):
        """Issue 120: raw requests failing due to missing slicing logic"""
        for x in xrange(1,5):
            IntegerIdTable.objects.create(id=x)
        
        objs = IntegerIdTable.objects.raw("SELECT [id] FROM [regressiontests_IntegerIdTable]")
        self.assertEquals(len(list(objs)), 4)

class ConnectionStringTestCase(TestCase):
    def assertInString(self, conn_string, pattern):
        """
        Asserts that the pattern is found in the string.
        """
        found = conn_string.find(pattern) != -1
        self.assertTrue(found,
            "pattern \"%s\" was not found in connection string \"%s\"" % (pattern, conn_string))

    def assertNotInString(self, conn_string, pattern):
        """
        Asserts that the pattern is found in the string.
        """
        found = conn_string.find(pattern) != -1
        self.assertFalse(found,
            "pattern \"%s\" was found in connection string \"%s\"" % (pattern, conn_string))

    def get_conn_string(self, data={}):
        db_settings = {
           'NAME': 'db_name',
           'ENGINE': 'sqlserver_ado',
           'HOST': 'myhost',
           'PORT': '',
           'USER': '',
           'PASSWORD': '',
           'OPTIONS' : {
               'provider': 'SQLOLEDB',
               'use_mars': True,
           },
        }
        db_settings.update(data)
        from sqlserver_ado.base import make_connection_string
        return make_connection_string(db_settings)

    def test_default(self):
        conn_string = self.get_conn_string()
        self.assertInString(conn_string, 'Initial Catalog=db_name')
        self.assertInString(conn_string, '=myhost;')
        self.assertInString(conn_string, 'Integrated Security=SSPI')
        self.assertInString(conn_string, 'PROVIDER=SQLOLEDB')
        self.assertNotInString(conn_string, 'UID=')
        self.assertNotInString(conn_string, 'PWD=')
        self.assertInString(conn_string, 'MARS Connection=True')

    def test_require_database_name(self):
        """Database NAME setting is required"""
        self.assertRaises(ImproperlyConfigured, self.get_conn_string, {'NAME': ''})

    def test_user_pass(self):
        """Validate username and password in connection string"""
        conn_string = self.get_conn_string({'USER': 'myuser', 'PASSWORD': 'mypass'})
        self.assertInString(conn_string, 'UID=myuser;')
        self.assertInString(conn_string, 'PWD=mypass;')
        self.assertNotInString(conn_string, 'Integrated Security=SSPI')

    def test_port_with_host(self):
        """Test the PORT setting to make sure it properly updates the connection string"""
        self.assertRaises(ImproperlyConfigured, self.get_conn_string,
            {'HOST': 'myhost', 'PORT': 1433})
        self.assertRaises(ImproperlyConfigured, self.get_conn_string, {'HOST': 'myhost', 'PORT': 'a'})

        conn_string = self.get_conn_string({'HOST': '127.0.0.1', 'PORT': 1433})
        self.assertInString(conn_string, '=127.0.0.1,1433;')

    def test_extra_params(self):
        """Test extra_params OPTIONS"""
        extras = 'Some=Extra;Stuff Goes=here'
        conn_string = self.get_conn_string({'OPTIONS': {'extra_params': extras}})
        self.assertInString(conn_string, extras)

    def test_host_fqdn_with_port(self):
        """
        Issue 21 - FQDN crashed on IP address detection.
        """
        with self.assertRaisesRegexp(ImproperlyConfigured, 'DATABASE HOST must be an IP address'):
            self.get_conn_string(data={
                'HOST': 'my.fqdn.com',
                'PORT': '1433',
            })


class PkPlusOne(models.Model):
    id = models.IntegerField(primary_key=True)
    a = models.IntegerField(null=True)

class AutoPkPlusOne(models.Model):
    id = models.AutoField(primary_key=True)
    a = models.IntegerField(null=True)

class TextPkPlusOne(models.Model):
    id = models.CharField(primary_key=True, max_length=10)
    a = models.IntegerField(null=True)

class ReturnIdOnInsertWithTriggersTestCase(TestCase):
    def create_trigger(self, model):
        """Create a trigger for the provided model"""
        qn = connection.ops.quote_name
        table_name = qn(model._meta.db_table)
        trigger_name = qn('test_trigger_%s' % model._meta.db_table)
        
        with connection.cursor() as cur:
            # drop trigger if it exists
            drop_sql = """
IF OBJECT_ID(N'[dbo].{trigger}') IS NOT NULL
    DROP TRIGGER [dbo].{trigger}
""".format(trigger=trigger_name)
            
            create_sql = """
CREATE TRIGGER [dbo].{trigger} ON {tbl} FOR INSERT
AS UPDATE {tbl} set [a] = 100""".format(
                trigger=trigger_name,
                tbl=table_name,
            )
            
            cur.execute(drop_sql)
            cur.execute(create_sql)

    def test_pk(self):
        self.create_trigger(PkPlusOne)
        id = 1
        obj = PkPlusOne.objects.create(id=id)
        self.assertEqual(obj.pk, id)
        self.assertEqual(PkPlusOne.objects.get(pk=id).a, 100)

    def test_auto_pk(self):
        self.create_trigger(AutoPkPlusOne)
        id = 1
        obj = AutoPkPlusOne.objects.create()
        self.assertEqual(obj.pk, id)
        self.assertEqual(AutoPkPlusOne.objects.get(pk=id).a, 100)

    def test_text_pk(self):
        self.create_trigger(TextPkPlusOne)
        id = 'asdf'
        obj = TextPkPlusOne.objects.create(id=id)
        self.assertEqual(obj.pk, id)
        self.assertEqual(TextPkPlusOne.objects.get(pk=id).a, 100)

class CompilerRegexTestCase(TestCase):
    def test_data_type_terminator(self):
        """
        Make sure the regex to split a data type string works as expected.
        """
        pairs = [
            # data type string, left of split
            ('int', 'int'),
            ('int identity', 'int'),
            ('int IDENTITY (1, 1)', 'int'),
            ('int identity (1, 1)', 'int'),
            ('int default 0', 'int'),
            ('nvarchar(23)', 'nvarchar(23)'),
            ('nvarchar (max)', 'nvarchar (max)'),
            ('smallint CHECK ([name] >= 0)', 'smallint'),
            ('int null', 'int'),
            ('int not null', 'int'),
            ('decimal (2, 3)', 'decimal (2, 3)'),
        ]

        from sqlserver_ado.compiler import _re_data_type_terminator

        for val, expected in pairs:
            self.assertEqual(expected, _re_data_type_terminator.split(val)[0])

class SafeStringTestCase(TestCase):
    def test_ascii(self):
        obj = StringTable(name=mark_safe('string'))
        obj.save()
        self.assertEqual(str(obj.name), str(StringTable.objects.get(pk=obj.id).name))

    def test_unicode(self):
        obj = StringTable(name=mark_safe(u'string'))
        obj.save()
        self.assertEqual(unicode(obj.name), unicode(StringTable.objects.get(pk=obj.id).name))

class DateTestCase(TestCase):
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

class Ticket21203Tests(TestCase):
    def test_ticket_21203(self):
        now = datetime.datetime.now()
        p = Ticket21203Parent.objects.create(
            parent_bool=True,
            parent_created=now,
            parent_time=now.time(),
            parent_date=now.date(),
        )
        c = Ticket21203Child.objects.create(parent=p)
        qs = Ticket21203Child.objects.select_related('parent').defer('parent__parent_created')
        self.assertQuerysetEqual(qs, [c], lambda x: x)
        self.assertIs(qs[0].parent.parent_bool, True)

    def test_ticket_21203_mssql(self):
        """
        Ensure SQLCompiler.resolve_columns() 'fields' are properly aligned when
        using defer() and select_related(). Tests are specific to the value
        conversions that need to happen with the date values that are returned
        from the database as strings.
        """
        now = datetime.datetime.now()
        p = Ticket21203Parent.objects.create(
            parent_created=now,
            parent_time=now.time(),
            parent_date=now.date(),
        )
        c = Ticket21203Child.objects.create(parent=p)
        qs = Ticket21203Child.objects.select_related('parent').defer('parent__parent_bool')
        self.assertQuerysetEqual(qs, [c], lambda x: x)
        self.assertEqual(qs[0].parent.parent_created, now)
        self.assertEqual(qs[0].parent.parent_time, now.time())
        self.assertEqual(qs[0].parent.parent_date, now.date())
