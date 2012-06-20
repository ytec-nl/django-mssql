"""A DB API 2.0 interface to SQL Server for Django

Forked from: adodbapi v2.1
Copyright (C) 2002 Henrik Ekelund, version 2.1 by Vernon Cole
* http://adodbapi.sourceforge.net/
* http://sourceforge.net/projects/pywin32/

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

* Version 2.1D by Adam Vandenberg, forked for Django backend use.
  This module is a db-api 2 interface for ADO, but is Django & SQL Server.
  It won't work against other ADO sources (like Access.)

DB-API 2.0 specification: http://www.python.org/dev/peps/pep-0249/
"""

import sys
import time
import datetime

try:
    import decimal
except ImportError:  #perhaps running Cpython 2.3 
    from django.utils import _decimal as decimal

from django.conf import settings
from django.db.utils import IntegrityError as DjangoIntegrityError, \
    DatabaseError as DjangoDatabaseError

try:
    from django.utils import timezone
except ImportError:
    # timezone added in Django 1.4
    timezone = None

import pythoncom
import win32com.client

from ado_consts import *

# Used for COM to Python date conversions.
_milliseconds_per_day = 24*60*60*1000

class MultiMap(object):
    def __init__(self, mapping, default=None):
        """Defines a mapping with multiple keys per value.

        mapping is a dict of: tuple(key, key, key...) => value
        """
        self.storage = dict()
        self.default = default

        for keys, value in mapping.iteritems():
            for key in keys:
                self.storage[key] = value

    def __getitem__(self, key):
        return self.storage.get(key, self.default)


def standardErrorHandler(connection, cursor, errorclass, errorvalue):
    err = (errorclass, errorvalue)
    connection.messages.append(err)
    if cursor is not None:
        cursor.messages.append(err)
    raise errorclass(errorvalue)


class Error(StandardError):
    pass
class Warning(StandardError):
    pass
class InterfaceError(Error):
    pass
class DatabaseError(Error):
    pass
class InternalError(DatabaseError):
    pass
class OperationalError(DatabaseError):
    pass
class ProgrammingError(DatabaseError):
    pass
class IntegrityError(DatabaseError, DjangoIntegrityError):
    pass
class DataError(DatabaseError):
    pass
class NotSupportedError(DatabaseError):
    pass

class _DbType(object):
    def __init__(self,valuesTuple):
        self.values = valuesTuple

    def __eq__(self, other): return other in self.values
    def __ne__(self, other): return other not in self.values

# -----------------  The .connect method -----------------
def connect(connection_string, timeout=30, use_transactions=None):
    """Connect to a database.

    connection_string -- An ADODB formatted connection string, see:
        http://www.connectionstrings.com/?carrier=sqlserver2005
    timeout -- A command timeout value, in seconds (default 30 seconds)
    """
    try:
        pythoncom.CoInitialize()             #v2.1 Paj
        c = win32com.client.Dispatch('ADODB.Connection')
    except:
        raise InterfaceError #Probably COM Error
    try:
        c.CommandTimeout = timeout
        c.ConnectionString = connection_string
        c.Open()
        if use_transactions is None:
            useTransactions = _use_transactions(c)
        else:
            useTransactions = use_transactions
        return Connection(c, useTransactions)
    except (Exception), e:
        raise OperationalError(e, "Error opening connection: " + connection_string)

def _use_transactions(c):
    """Return True if the given ADODB.Connection supports transactions."""
    for prop in c.Properties:
        if prop.Name == 'Transaction DDL':
            return prop.Value > 0
    return False
# ------ DB API required module attributes ---------------------
apilevel='2.0' #String constant stating the supported DB API level.

threadsafety=1 
# Integer constant stating the level of thread safety the interface supports,
# 1 = Threads may share the module, but not connections. 
# TODO: Have not tried this, maybe it is better than 1?
## 
## Possible values are:
##0 = Threads may not share the module. 
##1 = Threads may share the module, but not connections. 
##2 = Threads may share the module and connections. 
##3 = Threads may share the module, connections and cursors. 

paramstyle='format' # the default parameter style
# the API defines this as a constant:
#String constant stating the type of parameter marker formatting expected by the interface. 
# -- but as an extension, adodbapi will allow the programmer to change paramstyles
# by making the paramstyle also an attribute of the connection,
# and allowing the programmer to one of the permitted values:
# 'qmark' = Question mark style, e.g. '...WHERE name=?'
# 'named' = Named style, e.g. '...WHERE name=:name'
# 'format' = ANSI C printf format codes, e.g. '...WHERE name=%s'
_accepted_paramstyles = ('qmark','named','format')
# so you could use something like:
#   myConnection.paramstyle = 'named'
# The programmer may also change the default.
#   For example, if I were using django, I would say:
#     import adodbapi as Database
#     Database.adodbapi.paramstyle = 'format'

# ------- other module level defaults --------
defaultIsolationLevel = adXactReadCommitted
#  Set defaultIsolationLevel on module level before creating the connection.
#   For example:
#   import adodbapi, ado_consts
#   adodbapi.adodbapi.defaultIsolationLevel=ado_consts.adXactBrowse"
#
#  Set defaultCursorLocation on module level before creating the connection.
# It may be one of the "adUse..." consts.
defaultCursorLocation = adUseServer

# ----- handy constansts --------
# Used for COM to Python date conversions.
_ordinal_1899_12_31 = datetime.date(1899,12,31).toordinal()-1

def format_parameters(parameters, show_value=False):
    """Format a collection of ADO Command Parameters.

    Used by error reporting in _execute_command.
    """
    if show_value:
        desc = [
            "Name: %s, Dir.: %s, Type: %s, Size: %s, Value: \"%s\", Precision: %s, NumericScale: %s" %\
            (p.Name, directions[p.Direction], adTypeNames.get(p.Type, str(p.Type)+' (unknown type)'), p.Size, p.Value, p.Precision, p.NumericScale)
            for p in parameters ]
    else:
        desc = [
            "Name: %s, Dir.: %s, Type: %s, Size: %s, Precision: %s, NumericScale: %s" %\
            (p.Name, directions[p.Direction], adTypeNames.get(p.Type, str(p.Type)+' (unknown type)'), p.Size, p.Precision, p.NumericScale)
            for p in parameters ]

    return '[' + '\n'.join(desc) + ']'

def _configure_parameter(p, value):
    """Configure the given ADO Parameter 'p' with the Python 'value'."""
    if p.Direction not in [adParamInput, adParamInputOutput, adParamUnknown]:
        return

    if isinstance(value, basestring):
        p.Value = value
        p.Size = len(value)

    elif isinstance(value, buffer):
        p.Size = len(value)
        p.AppendChunk(value)

    elif isinstance(value, decimal.Decimal):
        p.Value = value
        exponent = value.as_tuple()[2]
        digit_count = len(value.as_tuple()[1])
        
        if exponent == 0:
            p.NumericScale = 0
            p.Precision =  digit_count
        elif exponent < 0:
            p.NumericScale = -exponent
            p.Precision = digit_count
            if p.Precision < p.NumericScale:
                p.Precision = p.NumericScale            
        elif exponent > 0:
            p.NumericScale = 0
            p.Precision = digit_count + exponent

    elif isinstance(value, datetime.time):
            p.Value = datetime.datetime(1,1,1, value.hour, value.minute, value.second)
    else:
        # For any other type, set the value and let pythoncom do the right thing.
        p.Value = value

    # Use -1 instead of 0 for empty strings and buffers
    if p.Size == 0:
        p.Size = -1

VERSION_SQL2005 = 9
VERSION_SQL2008 = 10

# # # # # ----- the Class that defines a connection ----- # # # # # 
class Connection(object):
    def __init__(self, adoConn, useTransactions=False):
        self.adoConn = adoConn
        self.paramstyle = paramstyle
        self.supportsTransactions = useTransactions
        self.adoConn.CursorLocation = defaultCursorLocation #v2.1 Rose
        if self.supportsTransactions:
            self.adoConn.IsolationLevel = defaultIsolationLevel
            self.adoConn.BeginTrans() # Disables autocommit per DBPAI
        self.errorhandler = None
        self.messages = []
        self.adoConnProperties = dict([(x.Name, x.Value) for x in self.adoConn.Properties])


    @property
    def is_sql2005(self):
        v = self.adoConnProperties.get('DBMS Version', '')
        return v.startswith(unicode(VERSION_SQL2005))
    
    @property
    def is_sql2008(self):
        v = self.adoConnProperties.get('DBMS Version', '')
        return v.startswith(unicode(VERSION_SQL2008))

    def _raiseConnectionError(self, errorclass, errorvalue):
        eh = self.errorhandler
        if eh is None:
            eh = standardErrorHandler
        eh(self, None, errorclass, errorvalue)

    def _close_connection(self):
        """Close the underlying ADO Connection object, rolling back an active transaction if supported."""
        if self.supportsTransactions:
            self.adoConn.RollbackTrans()
        self.adoConn.Close()

    def close(self):
        """Close the connection now (rather than whenever __del__ is called).

        The connection will be unusable from this point forward;
        an Error (or subclass) exception will be raised if any operation is attempted with the connection.
        The same applies to all cursor objects trying to use the connection. 
        """
        self.messages = []

        try:
            self._close_connection()
        except (Exception), e:
            self._raiseConnectionError(InternalError, e)
        pythoncom.CoUninitialize()                             #v2.1 Paj

    def commit(self):
        """Commit any pending transaction to the database.

        Note that if the database supports an auto-commit feature,
        this must be initially off. An interface method may be provided to turn it back on. 
        Database modules that do not support transactions should implement this method with void functionality. 
        """
        self.messages = []
        if not self.supportsTransactions:
            return

        try:
            self.adoConn.CommitTrans()
            if not(self.adoConn.Attributes & adXactCommitRetaining):
                #If attributes has adXactCommitRetaining it performs retaining commits that is,
                #calling CommitTrans automatically starts a new transaction. Not all providers support this.
                #If not, we will have to start a new transaction by this command:
                self.adoConn.BeginTrans()
        except (Exception), e:
            self._raiseConnectionError(Error, e)

    def rollback(self):
        """In case a database does provide transactions this method causes the the database to roll back to
        the start of any pending transaction. Closing a connection without committing the changes first will
        cause an implicit rollback to be performed.

        If the database does not support the functionality required by the method, the interface should
        throw an exception in case the method is used. 
        The preferred approach is to not implement the method and thus have Python generate
        an AttributeError in case the method is requested. This allows the programmer to check for database
        capabilities using the standard hasattr() function. 

        For some dynamically configured interfaces it may not be appropriate to require dynamically making
        the method available. These interfaces should then raise a NotSupportedError to indicate the
        non-ability to perform the roll back when the method is invoked. 
        """
        self.messages = []
        if not self.supportsTransactions:
            self._raiseConnectionError(NotSupportedError, None)
        self.adoConn.RollbackTrans()
        if not(self.adoConn.Attributes & adXactAbortRetaining):
            #If attributes has adXactAbortRetaining it performs retaining aborts that is,
            #calling RollbackTrans automatically starts a new transaction. Not all providers support this.
            #If not, we will have to start a new transaction by this command:
            self.adoConn.BeginTrans()

        #TODO: Could implement the prefered method by havins two classes,
        # one with trans and one without, and make the connect function choose which one.
        # the one without transactions should not implement rollback

    def cursor(self):
        "Return a new Cursor Object using the connection."
        self.messages = []
        return Cursor(self)

    def printADOerrors(self):
        j=self.adoConn.Errors.Count
        if j:
            print 'ADO Errors:(%i)' % j
        for e in self.adoConn.Errors:
            print 'Description: %s' % e.Description
            print 'Error: %s %s ' % (e.Number, adoErrors.get(e.Number, "unknown"))
            if e.Number == ado_error_TIMEOUT:
                print 'Timeout Error: Try using adodbpi.connect(constr,timeout=Nseconds)'
            print 'Source: %s' % e.Source
            print 'NativeError: %s' % e.NativeError
            print 'SQL State: %s' % e.SQLState
            
    def _suggest_error_class(self):
        """Introspect the current ADO Errors and determine an appropriate error class.
        
        Error.SQLState is a SQL-defined error condition, per the SQL specification:
        http://www.contrib.andrew.cmu.edu/~shadow/sql/sql1992.txt
        
        The 23000 class of errors are integrity errors.
        Error 40002 is a transactional integrity error.
        """
        if self.adoConn is not None:
            for e in self.adoConn.Errors:
                state = str(e.SQLState)
                if state.startswith('23') or state=='40002':
                    return IntegrityError
        return DatabaseError

    def __del__(self):
        try:
            self._close_connection()
        except:
            pass
        self.adoConn = None


# # # # # ----- the Class that defines a cursor ----- # # # # #
class Cursor(object):
## ** api required attributes:
## description...
##    This read-only attribute is a sequence of 7-item sequences.
##    Each of these sequences contains information describing one result column:
##        (name, type_code, display_size, internal_size, precision, scale, null_ok).
##    This attribute will be None for operations that do not return rows or if the
##    cursor has not had an operation invoked via the executeXXX() method yet.
##    The type_code can be interpreted by comparing it to the Type Objects specified in the section below.
## rowcount...
##    This read-only attribute specifies the number of rows that the last executeXXX() produced
##    (for DQL statements like select) or affected (for DML statements like update or insert). 
##    The attribute is -1 in case no executeXXX() has been performed on the cursor or
##    the rowcount of the last operation is not determinable by the interface.[7]
##    NOTE: -- adodbapi returns "-1" by default for all select statements
## arraysize...
##    This read/write attribute specifies the number of rows to fetch at a time with fetchmany().
##    It defaults to 1 meaning to fetch a single row at a time. 
##    Implementations must observe this value with respect to the fetchmany() method,
##    but are free to interact with the database a single row at a time.
##    It may also be used in the implementation of executemany(). 
## ** extension attributes:
## paramstyle...
##   allows the programmer to override the connection's default paramstyle
## errorhandler...
##   allows the programmer to override the connection's default error handler

    def __init__(self, connection):
        self.messages = []
        self.connection = connection
        self.rs = None  # the ADO recordset for this cursor
        self.description = None
        self.errorhandler = connection.errorhandler
        self.arraysize = 1
        self.rowcount = -1
        self.description = None

    def __iter__(self):                   # [2.1 Zamarev]
        return iter(self.fetchone, None)  # [2.1 Zamarev]
        
    def next(self):
        r = self.fetchone()
        if r:
            return r
        raise StopIteration

    def __enter__(self):
        "Allow database cursors to be used with context managers."
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        "Allow database cursors to be used with context managers."
        self.close()

    def _raiseCursorError(self, errorclass, errorvalue):
        eh = self.errorhandler
        if eh is None:
            eh = standardErrorHandler
        eh(self.connection, self, errorclass, errorvalue)

    def _description_from_recordset(self, recordset):
    	# Abort if closed or no recordset.
        if (recordset is None) or (recordset.State == adStateClosed):
            self.rs = None
            self.description = None
            return

        # Since we use a forward-only cursor, rowcount will always return -1
        self.rowcount = -1
        self.rs = recordset
        desc = list()

        for f in self.rs.Fields:
            display_size = None
            if not(self.rs.EOF or self.rs.BOF):
                display_size = f.ActualSize
            null_ok= bool(f.Attributes & adFldMayBeNull)          #v2.1 Cole 
            desc.append( (f.Name, f.Type, display_size, f.DefinedSize, f.Precision, f.NumericScale, null_ok) )
        self.description = desc

    def close(self):
        """Close the cursor now (rather than whenever __del__ is called).
            The cursor will be unusable from this point forward; an Error (or subclass)
            exception will be raised if any operation is attempted with the cursor.
        """
        self.messages = []
        self.connection = None    #this will make all future method calls on me throw an exception
        if self.rs and self.rs.State != adStateClosed: # rs exists and is open      #v2.1 Rose
            self.rs.Close()
            self.rs = None  #let go of the recordset so ADO will let it be disposed #v2.1 Rose

    def _new_command(self, command_type=adCmdText):
        self.cmd = None
        self.messages = []

        if self.connection is None:
            self._raiseCursorError(Error, None)
            return

        try:
            self.cmd = win32com.client.Dispatch("ADODB.Command")
            self.cmd.ActiveConnection = self.connection.adoConn
            self.cmd.CommandTimeout = self.connection.adoConn.CommandTimeout  #v2.1 Simons
            self.cmd.CommandType = command_type
        except:
            self._raiseCursorError(DatabaseError, None)

    def _execute_command(self):
        # Sprocs may have an integer return value
        self.return_value = None
        recordset = None; count = -1 #default value
        try:
            # ----- the actual SQL is executed here ---
            recordset, count = self.cmd.Execute()
            # ----- ------------------------------- ---
        except (Exception), e:
            _message = ""
            if hasattr(e, 'args'): _message += str(e.args)+"\n"
            _message += "Command:\n%s\nParameters:\n%s" %  (self.cmd.CommandText, format_parameters(self.cmd.Parameters, True))
            klass = self.connection._suggest_error_class()
            self._raiseCursorError(klass, _message)

        self.rowcount = count
        self._description_from_recordset(recordset)


    def callproc(self, procname, parameters=None):
        """Call a stored database procedure with the given name.

        The sequence of parameters must contain one entry for each
        argument that the sproc expects. The result of the
        call is returned as modified copy of the input
        sequence. Input parameters are left untouched, output and
        input/output parameters replaced with possibly new values.

        The sproc may also provide a result set as output,
        which is available through the standard .fetch*() methods.

        Extension: A "return_value" property may be set on the
        cursor if the sproc defines an integer return value.
        """
        self._new_command(adCmdStoredProc)
        self.cmd.CommandText = procname
        self.cmd.Parameters.Refresh()

        try:
            # Return value is 0th ADO parameter. Skip it.
            for i, p in enumerate(tuple(self.cmd.Parameters)[1:]):
                _configure_parameter(p, parameters[i])
        except:
            _message = u'Converting Parameter %s: %s, %s\n' %\
                (p.Name, ado_type_name(p.Type), repr(parameters[i]))

            self._raiseCursorError(DataError, _message)

        self._execute_command()

        p_return_value = self.cmd.Parameters(0)
        self.return_value = _convert_to_python(p_return_value.Value, p_return_value.Type)

        return [_convert_to_python(p.Value, p.Type)
            for p in tuple(self.cmd.Parameters)[1:] ]


    def execute(self, operation, parameters=None):
        """Prepare and execute a database operation (query or command).

        Return value is not defined.
        """
        self._new_command()

        if parameters is None:
            parameters = list()

        parameter_replacements = list()
        for i, value in enumerate(parameters):
            if value is None:
                parameter_replacements.append('NULL')
                continue
                
            if isinstance(value, basestring) and value == "":
                parameter_replacements.append("''")
                continue

            # Otherwise, process the non-NULL, non-empty string parameter.
            parameter_replacements.append('?')
            try:
                p = self.cmd.CreateParameter('p%i' % i, _ado_type(value))
            except KeyError:
                _message = u'Failed to map python type "%s" to an ADO type' % (value.__class__.__name__,)
                self._raiseCursorError(DataError, _message)
            except:
                _message = u'Creating Parameter p%i, %s' % (i, _ado_type(value))
                self._raiseCursorError(DataError, _message)

            try:
                _configure_parameter(p, value)
                self.cmd.Parameters.Append(p)
            except Exception as e:
                _message = u'Converting Parameter %s: %s, %s\n' %\
                    (p.Name, ado_type_name(p.Type), repr(value))

                self._raiseCursorError(DataError, _message)

        # Replace params with ? or NULL
        if parameter_replacements:
            operation = operation % tuple(parameter_replacements)

        self.cmd.CommandText = operation
        self._execute_command()

    def executemany(self, operation, seq_of_parameters):
        """Execute the given command against all parameter sequences or mappings given in seq_of_parameters."""
        self.messages = list()
        total_recordcount = 0

        for params in seq_of_parameters:
            self.execute(operation, params)

            if self.rowcount == -1:
                total_recordcount = -1

            if total_recordcount != -1:
                total_recordcount += self.rowcount

        self.rowcount = total_recordcount

    def _fetch(self, rows=None):
        """Fetch rows from the current recordset.

        rows -- Number of rows to fetch, or None (default) to fetch all rows.
        """
        if self.connection is None or self.rs is None:
            self._raiseCursorError(Error, None)
            return

        if self.rs.State == adStateClosed or self.rs.BOF or self.rs.EOF:
            if rows == 1: # fetchone returns None
                return None
            else: # fetchall and fetchmany return empty lists
                return list()

        if rows:
            ado_results = self.rs.GetRows(rows)
        else:
            ado_results = self.rs.GetRows()

        py_columns = list()
        column_types = [column_desc[1] for column_desc in self.description]
        for ado_type, column in zip(column_types, ado_results):
            py_columns.append( [_convert_to_python(cell, ado_type) for cell in column] )

        return tuple(zip(*py_columns))

    def fetchone(self):
        """ Fetch the next row of a query result set, returning a single sequence,
            or None when no more data is available.

            An Error (or subclass) exception is raised if the previous call to executeXXX()
            did not produce any result set or no call was issued yet.
        """
        self.messages = []
        result = self._fetch(1)
        if result: # return record (not list of records)
            return result[0]
        return None


    def fetchmany(self, size=None):
        """Fetch the next set of rows of a query result, returning a list of tuples. An empty sequence is returned when no more rows are available."""
        self.messages = []
        if size is None:
            size = self.arraysize
        return self._fetch(size)

    def fetchall(self):
        """Fetch all (remaining) rows of a query result, returning them as a sequence of sequences (e.g. a list of tuples).

            Note that the cursor's arraysize attribute
            can affect the performance of this operation. 
            An Error (or subclass) exception is raised if the previous call to executeXXX()
            did not produce any result set or no call was issued yet. 
        """
        self.messages=[]
        return self._fetch()

    def nextset(self):
        """Skip to the next available recordset, discarding any remaining rows from the current recordset.

        If there are no more sets, the method returns None. Otherwise, it returns a true
        value and subsequent calls to the fetch methods will return rows from the next result set.
        """
        self.messages = []
        if self.connection is None or self.rs is None:
            self._raiseCursorError(Error, None)
            return None

        try:                                               #[begin 2.1 ekelund]
            rsTuple=self.rs.NextRecordset()                # 
        except pywintypes.com_error, exc:                  # return appropriate error
            self._raiseCursorError(NotSupportedError, exc.args)#[end 2.1 ekelund]
        recordset = rsTuple[0]
        if recordset is None:
            return None
            
        self._description_from_recordset(recordset)
        return True

    def setinputsizes(self, sizes):
        pass

    def setoutputsize(self, size, column=None):
        pass

# Type specific constructors as required by the DB-API 2 specification.
Date = datetime.date
Time = datetime.time
Timestamp = datetime.datetime
Binary = buffer

def DateFromTicks(ticks):
    """Construct an object holding a date value from the given # of ticks."""
    return Date(*time.localtime(ticks)[:3])

def TimeFromTicks(ticks):
    """Construct an object holding a time value from the given # of ticks."""
    return Time(*time.localtime(ticks)[3:6])

def TimestampFromTicks(ticks):
    """Construct an object holding a timestamp value from the given # of ticks."""
    return Timestamp(*time.localtime(ticks)[:6])

adoIntegerTypes = (adInteger,adSmallInt,adTinyInt,adUnsignedInt,adUnsignedSmallInt,adUnsignedTinyInt,adError)
adoRowIdTypes = (adChapter,)
adoLongTypes = (adBigInt, adUnsignedBigInt, adFileTime)
adoExactNumericTypes = (adDecimal, adNumeric, adVarNumeric, adCurrency)
adoApproximateNumericTypes = (adDouble, adSingle)
adoStringTypes = (adBSTR,adChar,adLongVarChar,adLongVarWChar,adVarChar,adVarWChar,adWChar,adGUID)
adoBinaryTypes = (adBinary, adLongVarBinary, adVarBinary)
adoDateTimeTypes = (adDBTime, adDBTimeStamp, adDate, adDBDate)

# Required DBAPI type specifiers
STRING   = _DbType(adoStringTypes)
BINARY   = _DbType(adoBinaryTypes)
NUMBER   = _DbType((adBoolean,) + adoIntegerTypes + adoLongTypes + adoExactNumericTypes + adoApproximateNumericTypes)
DATETIME = _DbType(adoDateTimeTypes)
# Not very useful for SQL Server, as normal row ids are usually just integers.
ROWID    = _DbType(adoRowIdTypes)


# Mapping ADO data types to Python objects.
def _convert_to_python(variant, adType):
    if variant is None:
        return None
    return _variantConversions[adType](variant)

def _cvtDecimal(variant):
    return _convertNumberWithCulture(variant, decimal.Decimal)

def _cvtFloat(variant):
    return _convertNumberWithCulture(variant, float)

def _convertNumberWithCulture(variant, f):
    try:
        return f(variant)
    except (ValueError,TypeError,decimal.InvalidOperation):
        try:
            europeVsUS = str(variant).replace(",",".")
            return f(europeVsUS)
        except (ValueError,TypeError,decimal.InvalidOperation): pass

def _cvtComDate(comDate):
    date_as_float = float(comDate)
    day_count = int(date_as_float)
    fraction_of_day = abs(date_as_float - day_count)

    dt = (datetime.datetime.fromordinal(day_count + _ordinal_1899_12_31) +
        datetime.timedelta(milliseconds=fraction_of_day * _milliseconds_per_day))
    
    if timezone and getattr(settings, 'USE_TZ', False):
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

_variantConversions = MultiMap(
    {
        adoDateTimeTypes : _cvtComDate,
        adoExactNumericTypes: _cvtDecimal,
        adoApproximateNumericTypes: _cvtFloat,
        (adBoolean,): bool,
        adoLongTypes+adoRowIdTypes : long,
        adoIntegerTypes: int,
        adoBinaryTypes: buffer, 
    }, 
    lambda x: x)

# Mapping Python data types to ADO type codes
def _ado_type(data):
    if isinstance(data, basestring):
        return adBSTR
    return _map_to_adotype[type(data)]

_map_to_adotype = {
    buffer: adBinary,
    float: adDouble,
    int: adInteger,
    long: adBigInt,
    bool: adBoolean,
    decimal.Decimal: adDecimal,
    datetime.date: adDate,
    datetime.datetime: adDate,
    datetime.time: adDate, 
}
