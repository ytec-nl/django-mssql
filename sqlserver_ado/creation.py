from __future__ import absolute_import

from django.conf import settings
from django.db.backends.creation import BaseDatabaseCreation, TEST_DATABASE_PREFIX
from django.utils import six

class DatabaseCreation(BaseDatabaseCreation):
    # This dictionary maps Field objects to their associated Server Server column
    # types, as strings. Column-type strings can contain format strings; they'll
    # be interpolated against the values of Field.__dict__.
    data_types = {
        'AutoField':                    'int IDENTITY (1, 1)',
        'BigAutoField':                 'bigint IDENTITY (1, 1)',
        'BigIntegerField':              'bigint',
        'BinaryField':                  'varbinary(max)',
        'BooleanField':                 'bit',
        'CharField':                    'nvarchar(%(max_length)s)',
        'CommaSeparatedIntegerField':   'nvarchar(%(max_length)s)',
        'DateField':                    'date',
        'DateTimeField':                'datetime2',
        'DateTimeOffsetField':          'datetimeoffset',
        'DecimalField':                 'decimal(%(max_digits)s, %(decimal_places)s)',
        'FileField':                    'nvarchar(%(max_length)s)',
        'FilePathField':                'nvarchar(%(max_length)s)',
        'FloatField':                   'double precision',
        'GenericIPAddressField':        'nvarchar(39)',
        'IntegerField':                 'int',
        'IPAddressField':               'nvarchar(15)',
        'LegacyDateField':              'datetime',
        'LegacyDateTimeField':          'datetime',
        'LegacyTimeField':              'time',
        'NewDateField':                 'date',
        'NewDateTimeField':             'datetime2',
        'NewTimeField':                 'time',
        'NullBooleanField':             'bit',
        'OneToOneField':                'int',
        'PositiveIntegerField':         'int CHECK ([%(column)s] >= 0)',
        'PositiveSmallIntegerField':    'smallint CHECK ([%(column)s] >= 0)',
        'SlugField':                    'nvarchar(%(max_length)s)',
        'SmallIntegerField':            'smallint',
        'TextField':                    'nvarchar(max)',
        'TimeField':                    'time',
    }

    def __init__(self, *args, **kwargs):
        super(DatabaseCreation, self).__init__(*args, **kwargs)

        if self.connection.use_legacy_date_fields:
            self.data_types.update({
                'DateField': 'datetime',
                'DateTimeField': 'datetime',
                'TimeField': 'datetime',
            })

    def _create_master_connection(self):
        """
        Create a transactionless connection to 'master' database.
        """
        from .base import DatabaseWrapper
        
        master_settings = self.connection.settings_dict
        if not master_settings['TEST_NAME']:
            master_settings['TEST_NAME'] = 'test_' + master_settings['NAME']
        master_settings['NAME'] = 'master'
        return DatabaseWrapper(master_settings, use_transactions=False)

    def _create_test_db(self, verbosity=1, autoclobber=False):
        """
        Create the test databases using a connection to database 'master'.
        """
        test_database_name = self._test_database_name(settings)

        if not self._test_database_create(settings):
            if verbosity >= 1:
                six.print_("Skipping Test DB creation")
            return test_database_name

        # clear any existing connections to the database
        old_wrapper = self.connection
        old_wrapper.close()

        # connect to master database
        self.connection = self._create_master_connection()

        try:
            super(DatabaseCreation, self)._create_test_db(verbosity, autoclobber)

            self.install_regex_clr(test_database_name)
        except Exception as e:
            if 'Choose a different database name.' in str(e):
                print 'Database "%s" could not be created because it already exists.' % test_database_name
            else:
                raise
        finally:
            # set thing back
            self.connection = old_wrapper

        return test_database_name


    def _destroy_test_db(self, test_database_name, verbosity=1):
        """
        Drop the test databases using a connection to database 'master'.
        """
        if not self._test_database_create(settings):
            if verbosity >= 1:
                six.print_("Skipping Test DB destruction")
            return

        old_wrapper = self.connection
        old_wrapper.close()
        self.connection = self._create_master_connection()

        try:
            super(DatabaseCreation, self)._destroy_test_db(test_database_name, verbosity)
        except Exception as e:
            if 'it is currently in use' in str(e):
                print 'Cannot drop database %s because it is in use' % test_database_name
            else:
                raise
        finally:
            self.connection = old_wrapper

    def _test_database_create(self, settings):
        """
        Check the settings to see if the test database should be created.
        """
        if 'TEST_CREATE' in self.connection.settings_dict:
            return self.connection.settings_dict.get('TEST_CREATE', True)
        if hasattr(settings, 'TEST_DATABASE_CREATE'):
            return settings.TEST_DATABASE_CREATE
        else:
            return True

    def _test_database_name(self, settings):
        """
        Get the test database name.
        """
        try:
            name = TEST_DATABASE_PREFIX + self.connection.settings_dict['NAME']
            if self.connection.settings_dict['TEST_NAME']:
                name = self.connection.settings_dict['TEST_NAME']
        except AttributeError:
            if hasattr(settings, 'TEST_DATABASE_NAME') and settings.TEST_DATABASE_NAME:
                name = settings.TEST_DATABASE_NAME
            else:
                name = TEST_DATABASE_PREFIX + settings.DATABASE_NAME
        return name



    def install_regex_clr(self, database_name):
        sql = '''
USE {database_name};

-- Enable CLR in this database
sp_configure 'show advanced options', 1;
RECONFIGURE;
sp_configure 'clr enabled', 1;
RECONFIGURE;

-- Drop and recreate the function if it already exists
IF OBJECT_ID('REGEXP_LIKE') IS NOT NULL
    DROP FUNCTION [dbo].[REGEXP_LIKE]

IF EXISTS(select * from sys.assemblies where name like 'regex_clr')
    DROP ASSEMBLY regex_clr
;

CREATE ASSEMBLY regex_clr
FROM 0x{assembly_hex}
WITH PERMISSION_SET = SAFE;

create function [dbo].[REGEXP_LIKE]
(
    @input nvarchar(max),
    @pattern nvarchar(max),
    @caseSensitive int
)
RETURNS INT  AS
EXTERNAL NAME regex_clr.UserDefinedFunctions.REGEXP_LIKE
        '''.format(
            database_name=self.connection.ops.quote_name(database_name),
            assembly_hex=self.get_regex_clr_assembly_hex(),
        ).split(';')

        with self.connection.cursor() as cursor:
            for s in sql:
                cursor.execute(s)

    def get_regex_clr_assembly_hex(self):
        import os
        import binascii
        with open(os.path.join(os.path.dirname(__file__), 'regex_clr.dll'), 'rb') as f:
            assembly = binascii.hexlify(f.read()).decode('ascii')
        return assembly
