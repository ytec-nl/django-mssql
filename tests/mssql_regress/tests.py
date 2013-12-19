from __future__ import absolute_import

from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.test import TestCase

from .models import AutoPkPlusOne, PkPlusOne, TextPkPlusOne


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

