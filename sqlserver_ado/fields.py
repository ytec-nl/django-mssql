"""This module provides SQL Server specific fields for Django models."""
from django.db import models
from django.forms import ValidationError
from django.utils.translation import ugettext_lazy as _

__all__ = (
    'BigAutoField',
    'BigForeignKey',
    'BigIntegerField',
    'DateField',
    'DateTimeField',
    'LegacyTimeField',
    'LegacyDateField',
    'LegacyDateTimeField',
    'TimeField',
)

class BigAutoField(models.AutoField):
    """A bigint IDENTITY field"""
    def get_internal_type(self):
        return "BigAutoField"

    def to_python(self, value):
        if value is None:
            return value
        try:
            return long(value)
        except (TypeError, ValueError):
            raise ValidationError(
                _("This value must be a long."))

    def get_db_prep_value(self, value, connection=None, prepared=False):
        if value is None:
            return None
        return long(value)

class BigForeignKey(models.ForeignKey):
    """A ForeignKey field that points to a BigAutoField or BigIntegerField"""
    def db_type(self, connection=None):
        try:
            return models.BigIntegerField().db_type(connection=connection)
        except AttributeError:
            return models.BigIntegerField().db_type()

BigIntegerField = models.BigIntegerField

class DateField(models.DateField):
    """
    A DateField backed by a 'date' database field.
    """
    def get_internal_type(self):
        return 'NewDateField'

class DateTimeField(models.DateTimeField):
    """
    A DateTimeField backed by a 'datetime2' database field.
    """
    def get_internal_type(self):
        return 'NewDateTimeField'

class TimeField(models.TimeField):
    """
    A TimeField backed by a 'time' database field.
    """
    def get_internal_type(self):
        return 'NewTimeField'

class LegacyDateField(models.DateField):
    """
    A DateField that is backed by a 'datetime' database field.
    """
    def get_internal_type(self):
        return 'LegacyDateTimeField'

class LegacyDateTimeField(models.DateTimeField):
    """
    A DateTimeField that is backed by a 'datetime' database field.
    """
    def get_internal_type(self):
        return 'LegacyDateTimeField'

class LegacyTimeField(models.TimeField):
    """
    A TimeField that is backed by a 'datetime' database field.
    """
    def get_internal_type(self):
        return 'LegacyDateTimeField'
