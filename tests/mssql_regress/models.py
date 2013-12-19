from django.db import models

class AutoPkPlusOne(models.Model):
    id = models.AutoField(primary_key=True)
    a = models.IntegerField(null=True)

class PkPlusOne(models.Model):
    id = models.IntegerField(primary_key=True)
    a = models.IntegerField(null=True)

class TextPkPlusOne(models.Model):
    id = models.CharField(primary_key=True, max_length=10)
    a = models.IntegerField(null=True)
