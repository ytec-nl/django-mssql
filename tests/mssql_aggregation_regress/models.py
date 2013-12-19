from django.db import models

class AmountTable(models.Model):
    amount = models.IntegerField()

class Bug40Table(models.Model):
	# Google Code Bug 40
    int1 = models.IntegerField()
