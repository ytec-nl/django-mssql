# coding: utf-8
from django.db import models
from django.utils.encoding import python_2_unicode_compatible

from sqlserver_ado.fields import (LegacyDateTimeField, LegacyDateField,
    LegacyTimeField, DateField, DateTimeField, TimeField, DateTimeOffsetField)

@python_2_unicode_compatible
class LegacyDateTimeTable(models.Model):
    val = LegacyDateTimeField()

    def __str__(self):
        return self.val

    class Meta:
        db_table = 'LegacyDateTimeTable'

@python_2_unicode_compatible
class DateTimeLegacyDateTimeTable(models.Model):
    val = DateTimeField()

    def __str__(self):
        return self.val

    class Meta:
        managed = False
        db_table = 'LegacyDateTimeTable'

@python_2_unicode_compatible
class LegacyDateTable(models.Model):
    val = LegacyDateField()

    def __str__(self):
        return self.val

@python_2_unicode_compatible
class LegacyTimeTable(models.Model):
    val = LegacyTimeField()

    def __str__(self):
        return self.val

@python_2_unicode_compatible
class DateTable(models.Model):
    val = DateField()

    def __str__(self):
        return self.val

@python_2_unicode_compatible
class DateTimeTable(models.Model):
    val = DateTimeField()

    def __str__(self):
        return self.val

@python_2_unicode_compatible
class TimeTable(models.Model):
    val = TimeField()

    def __str__(self):
        return self.val

@python_2_unicode_compatible
class DateTimeOffsetTable(models.Model):
    val = DateTimeOffsetField()

    def __str__(self):
        return self.val
