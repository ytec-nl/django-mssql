from django.db.backends.base.features import BaseDatabaseFeatures
from django.db.utils import InterfaceError as DjangoInterfaceError
from django.utils.functional import cached_property


try:
    import pytz
except ImportError:
    pytz = None


class DatabaseFeatures(BaseDatabaseFeatures):
    uses_custom_query_class = True
    has_bulk_insert = True

    # DateTimeField doesn't support timezones, only DateTimeOffsetField
    supports_timezones = False
    supports_sequence_reset = False

    can_return_id_from_insert = True

    supports_regex_backreferencing = False

    supports_tablespaces = True

    # Django < 1.7
    ignores_nulls_in_unique_constraints = False
    # Django >= 1.7
    supports_nullable_unique_constraints = False
    supports_partially_nullable_unique_constraints = False

    can_introspect_autofield = True
    can_introspect_small_integer_field = True

    supports_subqueries_in_group_by = False

    allow_sliced_subqueries = False

    uses_savepoints = True

    supports_paramstyle_pyformat = False

    closed_cursor_error_class = DjangoInterfaceError

    # connection_persists_old_columns = True

    requires_literal_defaults = True

    has_native_uuid_field = True

    @cached_property
    def has_zoneinfo_database(self):
        return pytz is not None

    # Dict of test import path and list of versions on which it fails
    failing_tests = {
        # Some tests are known to fail with django-mssql.
        'aggregation.tests.BaseAggregateTestCase.test_dates_with_aggregation': [(1, 6), (1, 7)],
        'aggregation.tests.ComplexAggregateTestCase.test_expression_on_aggregation': [(1, 8)],

        'aggregation_regress.tests.AggregationTests.test_more_more_more': [(1, 6), (1, 7)],

        # MSSQL throws an arithmetic overflow error.
        'expressions_regress.tests.ExpressionOperatorTests.test_righthand_power': [(1, 7)],

        # The migrations and schema tests also fail massively at this time.
        'migrations.test_operations.OperationTests.test_alter_field_pk': [(1, 7)],

    }
