from django.db import models

class DistinctTable(models.Model):
    s = models.CharField(max_length=10)

class ItemGroup(models.Model):
    name = models.CharField(max_length=10)
    group_type = models.CharField(max_length=10, default='test')

class Item(models.Model):
    group = models.ForeignKey(ItemGroup,
        related_name='items',
        limit_choices_to={
            'group_type__in': ('test'),
        },
    )
    name = models.CharField(max_length=10)

    class Meta:
        ordering = ('group__group_type', 'name')
