from django.db import models


class Item(models.Model):
    time = models.DateTimeField()
    symbol = models.CharField(max_length=100)
    # price = models.IntegerField()
    # volume = models.IntegerField()
    # metrics = ArrayField(models.FloatField(), size=6) #->postgresql
    c1 = models.FloatField()
    c2 = models.FloatField()
    c3 = models.FloatField()
    c4 = models.FloatField()
    c5 = models.FloatField()
    c6 = models.FloatField()

    def __str__(self):
        return f"{self.time},symbol: {self.symbol},id: {self.id}"

    class Meta:
        indexes = [
            models.Index(fields=['symbol', 'time']),
        ]

class ItemAggregate(models.Model):
    AGG_CHOICES = [
        ('minute', 'Minute'),
        ('hour', 'Hour'),
        ('month', 'Month'),
    ]

    symbol = models.CharField(max_length=100)
    time_group = models.DateTimeField()
    aggregation_level = models.CharField(max_length=10, choices=AGG_CHOICES)
    avg_price = models.FloatField()
    total_volume = models.BigIntegerField()

    class Meta:
        indexes = [
            models.Index(fields=['symbol', 'aggregation_level', 'time_group']),
        ]
        unique_together = ('symbol', 'aggregation_level', 'time_group')

    


