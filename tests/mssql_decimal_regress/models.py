from django.db import models
from django.utils.encoding import python_2_unicode_compatible

@python_2_unicode_compatible
class DecimalTable(models.Model):
    d = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return d

@python_2_unicode_compatible
class PreciseDecimalTable(models.Model):
    d = models.DecimalField(max_digits=20, decimal_places=10)

    def __str__(self):
        return d
