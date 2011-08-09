from django.db import models

class FirstTable(models.Model):
    b = models.CharField(max_length=100)
    # Add a reserved word column; this will get quoted correctly
    # in queries, but need to make sure paging doesn't break:
    # * Paging should re-quote alias names correctly
    # * The string splitting on 'FROM' shouldn't break either
    c = models.CharField(default=u'test', max_length=10, db_column=u'FROM')
    
    def __repr__(self):
        return '<FirstTable %s: %s, %s>' % (self.pk, self.b, self.c)

class SecondTable(models.Model):
    a = models.ForeignKey(FirstTable)
    b = models.CharField(max_length=100)
    
    def __repr__(self):
        return '<FirstTable %s: %s, %s>' % (self.pk, self.a_id, self.b)


class Products(models.Model):
    productid = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
        
    def __repr__(self):
        return self.name
        
    def __unicode__(self):
        return "<Product %u: %s>" % (self.productid, self.name)

class DistinctTable(models.Model):
    s = models.CharField(max_length=10)
