from __future__ import absolute_import

import unittest

# Base is used to get connection string using Django settings
from sqlserver_ado import base
# Internal dbapi module
from sqlserver_ado import dbapi

# Base unit test
from . import dbapi20

class DbApiTest(dbapi20.DatabaseAPI20Test):
    driver = dbapi
    connect_args = [ base.connection_string_from_settings() ]

    def _try_run(self, *args):
        con = self._connect()
        cur = None
        try:
            cur = con.cursor()
            for arg in args:
                cur.execute(arg)
        finally:
            try:
                if cur is not None:
                    cur.close()
            except: pass
            con.close()

    def _try_run2(self, cur, *args):
        for arg in args:
            cur.execute(arg)

    # This should create the "lower" sproc.
    def _callproc_setup(self, cur):
        self.lower_func = self.lowerfunc = 'to_lower'
        self._try_run2(cur,
            """IF OBJECT_ID(N'[dbo].[to_lower]', N'P') IS NOT NULL DROP PROCEDURE [dbo].[to_lower]""",
            """
CREATE PROCEDURE to_lower
    @input nvarchar(max)
AS
BEGIN
    select LOWER(@input)
END
""",
            )

    # This should create a sproc with a return value.
    def _retval_setup(self, cur):
        self._try_run2(cur,
            """IF OBJECT_ID(N'[dbo].[add_one]', N'P') IS NOT NULL DROP PROCEDURE [dbo].[add_one]""",
            """
CREATE PROCEDURE add_one (@input int)
AS
BEGIN
    return @input+1
END
""",
            )

    def test_retval(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self._retval_setup(cur)
            values = cur.callproc('add_one',(1,))
            self.assertEqual(values[0], 1, 'input parameter should be left unchanged: %s' % (values[0],))

            self.assertEqual(cur.description, None,"No resultset was expected.")
            self.assertEqual(cur.return_value, 2, "Invalid return value: %s" % (cur.return_value,))

        finally:
            con.close()

    # This should create a sproc with an output parameter.
    def _outparam_setup(self, cur):
        self._try_run2(cur,
            """IF OBJECT_ID(N'[dbo].[add_one_out]', N'P') IS NOT NULL DROP PROCEDURE [dbo].[add_one_out]""",
            """
CREATE PROCEDURE add_one_out (@input int, @output int OUTPUT)
AS
BEGIN
    SET @output = @input+1
END
""",
            )

    def test_outparam(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self._outparam_setup(cur)
            values = cur.callproc('add_one_out',(1,None))
            self.assertEqual(len(values), 2, 'expected 2 parameters')
            self.assertEqual(values[0], 1, 'input parameter should be unchanged')
            self.assertEqual(values[1], 2, 'output parameter should get new values')
        finally:
            con.close()

    # Don't need setoutputsize tests.
    def test_setoutputsize(self):
        pass

    def help_nextset_setUp(self,cur):
        self._try_run2(cur,
            """IF OBJECT_ID(N'[dbo].[more_than_one]', N'P') IS NOT NULL DROP PROCEDURE [dbo].[more_than_one]""",
            """
create procedure more_than_one
as
begin
    select 1,2,3
    select 4,5,6
end
""",
            )

    def help_nextset_tearDown(self,cur):
        pass

    def test_ExceptionsAsConnectionAttributes(self):
        pass

    def test_select_decimal_zero(self):
        from decimal import Decimal

        con = self._connect()
        try:
            expected = (
                Decimal('0.00'),
                Decimal('0.0'),
                Decimal('-0.00'))

            cur = con.cursor()
            cur.execute("SELECT %s as A, %s as B, %s as C", expected)

            result = cur.fetchall()
            self.assertEqual(result[0], expected)
        finally:
            con.close()

class MaskConnectionStringPasswordTest(unittest.TestCase):

    def test_mask(self):
        """
        Ensure the mask function does the proper substitution.
        """
        base_conn_string = 'SOURCE=127.0.0.1\\ss2008;Initial Catalog=MyDatabase;UID=testuser;%s=%s;PROVIDER=SQLNCLI10;DataTypeCompatibility=80;MARS Connection=True;DataTypeCompatibility=80;MARS Connection=True;'
        names = ['pwd', 'Pwd', 'PWD', 'password', 'PASSWORD', 'Password']
        passwords = ['', '12345', 'SLDFKJD**$#$', 'asd asdf']
        for n in names:
            for p in passwords:
                conn_str = dbapi.mask_connection_string_password(
                    base_conn_string % (n, p), mask='*')
                self.assertNotIn('%s=%s;' % (n,p), conn_str)
                self.assertIn('%s=*;' % n, conn_str)

    def test_connection_error(self):
        """
        Attempt an invalid connection and check the error for a password.
        """
        from django.conf import settings

        databases = {}
        databases.update(settings.DATABASES['default'])
        databases['USER'] = 'user'
        databases['PASSWORD'] = 'myPass'

        connection_string = base.make_connection_string(databases)

        with self.assertRaises(dbapi.OperationalError) as err:
            dbapi.connect(connection_string)
        self.assertNotIn('PWD=myPass;', str(err.exception))
        self.assertIn('PWD=******;', str(err.exception))
