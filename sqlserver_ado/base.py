"""Microsoft SQL Server database backend for Django."""
from django.db.backends import BaseDatabaseWrapper, BaseDatabaseFeatures, BaseDatabaseValidation, BaseDatabaseClient
from django.db.backends.signals import connection_created
from django.core.exceptions import ImproperlyConfigured

import dbapi as Database

from introspection import DatabaseIntrospection
from creation import DatabaseCreation
from operations import DatabaseOperations

DatabaseError = Database.DatabaseError
IntegrityError = Database.IntegrityError


class DatabaseFeatures(BaseDatabaseFeatures):
    uses_custom_query_class = True
    has_bulk_insert = False
    
    supports_timezones = False
    supports_sequence_reset = False
    
    query_needed_to_fetch_return_id = True

# IP Address recognizer taken from:
# http://mail.python.org/pipermail/python-list/2006-March/375505.html
def _looks_like_ipaddress(address):
    dots = address.split(".")
    if len(dots) != 4:
        return False
    for item in dots:
        if not 0 <= int(item) <= 255:
            return False
    return True

def connection_string_from_settings():
    from django.conf import settings
    return make_connection_string(settings)

def make_connection_string(settings):
    class wrap(object):
        def __init__(self, mapping):
            self._dict = mapping
            
        def __getattr__(self, name):
            d = self._dict
            result = None
            if hasattr(d, "get"):
                if d.has_key(name):
                    result = d.get(name)
                else:
                    result = d.get('DATABASE_' + name)    
            elif hasattr(d, 'DATABASE_' + name):
                result = getattr(d, 'DATABASE_' + name)
            else:
                result = getattr(d, name, None)
            return result    
            
    settings = wrap(settings) 
    
    db_name = settings.NAME.strip()
    db_host = settings.HOST or '127.0.0.1'
    if len(db_name) == 0:
        raise ImproperlyConfigured("You need to specify a DATABASE NAME in your Django settings file.")

    # Connection strings courtesy of:
    # http://www.connectionstrings.com/?carrier=sqlserver

    # If a port is given, force a TCP/IP connection. The host should be an IP address in this case.
    if settings.PORT:
        if not _looks_like_ipaddress(db_host):
            raise ImproperlyConfigured("When using DATABASE PORT, DATABASE HOST must be an IP address.")
        try:
            port = int(settings.PORT)
        except ValueError:
            raise ImproperlyConfigured("DATABASE PORT must be a number.")
        db_host = '{0},{1};Network Library=DBMSSOCN'.format(db_host, port)

    # If no user is specified, use integrated security.
    if settings.USER != '':
        auth_string = 'UID={0};PWD={1}'.format(settings.USER, settings.PASSWORD)
    else:
        auth_string = 'Integrated Security=SSPI'

    parts = [
        'DATA SOURCE={0};Initial Catalog={1}'.format(db_host, db_name),
        auth_string
    ]

    options = settings.OPTIONS

    if not options.get('provider', None):
        options['provider'] = 'sqlncli10'
    
    parts.append('PROVIDER={0}'.format(options['provider']))
        
    if options['provider'].lower().find('=sqlcli') != -1:
        # native client needs a compatibility mode that behaves like OLEDB
        parts.append('DataTypeCompatibility=80')

    if options.get('use_mars', True):
        parts.append('MARS Connection=True')
    
    if options.get('extra_params', None):
        parts.append(options['extra_params'])    
    
    return ";".join(parts)

class DatabaseWrapper(BaseDatabaseWrapper):
    vendor = 'microsoft'
    
    operators = {
        "exact": "= %s",
        "iexact": "LIKE %s ESCAPE '\\'",
        "contains": "LIKE %s ESCAPE '\\'",
        "icontains": "LIKE %s ESCAPE '\\'",
        "gt": "> %s",
        "gte": ">= %s",
        "lt": "< %s",
        "lte": "<= %s",
        "startswith": "LIKE %s ESCAPE '\\'",
        "endswith": "LIKE %s ESCAPE '\\'",
        "istartswith": "LIKE %s ESCAPE '\\'",
        "iendswith": "LIKE %S ESCAPE '\\'",
    }

    def __init__(self, *args, **kwargs):
        self.use_transactions = kwargs.pop('use_transactions', None)
        
        super(DatabaseWrapper, self).__init__(*args, **kwargs)
        
        try:
            # django < 1.3
            self.features = DatabaseFeatures()
        except TypeError:
            # django >= 1.3
            self.features = DatabaseFeatures(self)

        try:
            self.ops = DatabaseOperations()
        except TypeError:
            self.ops = DatabaseOperations(self)
        
        self.client = BaseDatabaseClient(self)
        self.creation = DatabaseCreation(self) 
        self.introspection = DatabaseIntrospection(self)
        self.validation = BaseDatabaseValidation(self)

        try:
            self.command_timeout = int(self.settings_dict.get('COMMAND_TIMEOUT', 30))
        except ValueError:   
            self.command_timeout = 30
        
        try:
            options = self.settings_dict.get('OPTIONS', {})
            self.cast_avg_to_float = not bool(options.get('disable_avg_cast', False))
        except ValueError:
            self.cast_avg_to_float = False
        
        self.ops.is_sql2005 = self.is_sql2005
        self.ops.is_sql2008 = self.is_sql2008

    def __connect(self):
        """Connect to the database"""
        self.connection = Database.connect(
            make_connection_string(self.settings_dict),
            self.command_timeout,
            use_transactions=self.use_transactions,
        )
        connection_created.send(sender=self.__class__, connection=self)
        return self.connection

    def is_sql2005(self):
        """
        Returns True if the current connection is SQL2005. Establishes a
        connection if needed.
        """
        if not self.connection:
            self.__connect()
        return self.connection.is_sql2005

    def is_sql2008(self):
        """
        Returns True if the current connection is SQL2008. Establishes a
        connection if needed.
        """
        if not self.connection:
            self.__connect()
        return self.connection.is_sql2008        

    def _cursor(self):
        if self.connection is None:
            self.__connect()
        return Database.Cursor(self.connection)

    def disable_constraint_checking(self):
        """
        Turn off constraint checking for every table
        """
        if self.connection:
            cursor = self.connection.cursor()
        else:
            cursor = self._cursor()
        cursor.execute('EXEC sp_msforeachtable "ALTER TABLE ? NOCHECK CONSTRAINT all"')

    def enable_constraint_checking(self):
        """
        Turn on constraint checking for every table
        """
        if self.connection:
            cursor = self.connection.cursor()
        else:
            cursor = self._cursor()
        cursor.execute('EXEC sp_msforeachtable "ALTER TABLE ? WITH CHECK CHECK CONSTRAINT all"')

    def check_constraints(self, table_names=None):
        """
        Check the table constraints.
        """
        if self.connection:
            cursor = self.connection.cursor()
        else:
            cursor = self._cursor()
        if not table_names:
            cursor.execute('DBCC CHECKCONSTRAINTS')
        else:
            qn = self.ops.quote_name
            for name in table_names:
                cursor.execute('DBCC CHECKCONSTRAINTS({0})'.format(
                    qn(name)
                ))
