from django.db import models

class DecimalTable(models.Model):
    d = models.DecimalField(max_digits=5, decimal_places=2)
