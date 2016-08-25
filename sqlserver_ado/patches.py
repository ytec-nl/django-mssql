from __future__ import unicode_literals
import sys

if sys.version_info >= (2, 7):
    # Django Ticket #17671 - Allow using a cursor as a ContextManager
    # in Python 2.7
    from django.db.backends.utils import CursorWrapper
    if not hasattr(CursorWrapper, '__enter__'):
        def enter(self):
            return self

        def exit(self, type, value, traceback):
            return self.cursor.__exit__(type, value, traceback)

        CursorWrapper.__enter__ = enter
        CursorWrapper.__exit__ = exit


#25894 Evaluation of zero-length slices of queryset.values() fails
def set_limits(self, low=None, high=None):
    self._original_set_limits(low, high)
    if self.low_mark == self.high_mark:
        self.set_empty()

from django.db.models.sql.query import Query
Query._original_set_limits = Query.set_limits
Query.set_limits = set_limits