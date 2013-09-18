from django.db import models
from django.db.models import (
    Avg, Count, Max, Min, StdDev, Sum, Variance)

class AmountTable(models.Model):
    amount = models.IntegerField()

class Player(models.Model):
    name = models.CharField(max_length=40)
    
class GamerCard(models.Model):
    player = models.ForeignKey(Player)
    name = models.CharField(max_length=40, default="default_card")
    avatar = models.CharField(max_length=40)
    
class Bet(models.Model):
    player = models.ForeignKey(Player)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
