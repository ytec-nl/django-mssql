"""
This file contains Microsoft SQL Server specific aggregates and overrides for
the default Django aggregates.
"""

from django.db.models.aggregates import Avg, StdDev, Variance

def avg_as_microsoft(self, compiler, connection):
    """
    Microsoft AVG doesn't cast type by default, but needs to CAST to FLOAT so
    that AVG([1, 2]) == 1.5, instead of 1.
    """
    if getattr(connection, 'cast_avg_to_float', True):
        return self.as_sql(compiler, connection, template='%(function)s(CAST(%(field)s AS FLOAT))')
    return self.as_sql(compiler, connection)
setattr(Avg, 'as_microsoft', avg_as_microsoft)


def stddev_as_microsoft(self, compiler, connection):
    """
    Fix function names to 'STDEV' or 'STDEVP' as used by mssql
    """
    function = 'STDEV'
    if self.function == 'STDDEV_POP':
        function = 'STDEVP'
    return self.as_sql(compiler, connection, function=function)
setattr(StdDev, 'as_microsoft', stddev_as_microsoft)


def variance_as_microsoft(self, compiler, connection):
    """
    Fix function names to 'VAR' or 'VARP' as used by mssql
    """
    function = 'VAR'
    if self.function == 'VAR_POP':
        function = 'VARP'
    return self.as_sql(compiler, connection, function=function)
setattr(Variance, 'as_microsoft', variance_as_microsoft)
