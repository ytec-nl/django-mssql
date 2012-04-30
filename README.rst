Django MSSQL Database Backend
=============================

`Django-mssql`_ provies a Django database backend for Microsoft SQL Server.

Documentation is available at `django-mssql.readthedocs.org`_.

Requirements
------------

    * Python 2.6, 2.7
    * PyWin32_

SQL Server Versions
-------------------

Supported Versions:
    * 2005
    * 2008
    * 2008r2

The SQL Server version will be detected upon initial connection.

Django Version
--------------

The current version of django-mssql supports Django 1.2 thru 1.4. Django versions
1.0 and 1.1 are no longer actively supported, but working versions may be
found with the tags ``legacy-1.0`` and ``legacy-1.1``.

References
----------

    * Django-mssql on PyPi: http://pypi.python.org/pypi/django-mssql
    * DB-API 2.0 specification: http://www.python.org/dev/peps/pep-0249/


.. _`Django-mssql`: https://bitbucket.org/Manfre/django-mssql
.. _django-mssql.readthedocs.org: http://django-mssql.readthedocs.org/
.. _PyWin32: http://sourceforge.net/projects/pywin32/
