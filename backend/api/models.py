from django.db import models


class Item(models.Model):
    time = models.DateTimeField()
    symbol = models.CharField(max_length=100)
    price = models.FloatField()


    def __str__(self):
        return f"{self.time},symbol: {self.symbol},id: {self.id}"

    class Meta:
        indexes = [
            models.Index(fields=['symbol', 'time']),
        ]
class Item_1ms(models.Model):
    time = models.DateTimeField()
    symbol = models.CharField(max_length=100)
    min = models.FloatField()
    max = models.FloatField()
    min_time = models.DateTimeField()
    max_time = models.DateTimeField()


    def __str__(self):
        return f"{self.time},symbol: {self.symbol},min&max: {self.min} & {self.max}"

    class Meta:
        indexes = [
            models.Index(fields=['symbol', 'time']),
        ]
class Item_10ms(models.Model):
    time = models.DateTimeField()
    symbol = models.CharField(max_length=100)
    min = models.FloatField()
    max = models.FloatField()
    min_time = models.DateTimeField()
    max_time = models.DateTimeField()

    def __str__(self):
        return f"{self.time},symbol: {self.symbol},min&max: {self.min} & {self.max}"

    class Meta:
        indexes = [
            models.Index(fields=['symbol', 'time']),
        ]
class Item_100ms(models.Model):
    time = models.DateTimeField()
    symbol = models.CharField(max_length=100)
    min = models.FloatField()
    max = models.FloatField()
    min_time = models.DateTimeField()
    max_time = models.DateTimeField()

    def __str__(self):
        return f"{self.time},symbol: {self.symbol},min&max: {self.min} & {self.max}"

    class Meta:
        indexes = [
            models.Index(fields=['symbol', 'time']),
        ]
class Item_1s(models.Model):
    time = models.DateTimeField()
    symbol = models.CharField(max_length=100)
    min = models.FloatField()
    max = models.FloatField()
    min_time = models.DateTimeField()
    max_time = models.DateTimeField()

    def __str__(self):
        return f"{self.time},symbol: {self.symbol},min&max: {self.min} & {self.max}"

    class Meta:
        indexes = [
            models.Index(fields=['symbol', 'time']),
        ]
class Item_10s(models.Model):
    time = models.DateTimeField()
    symbol = models.CharField(max_length=100)
    min = models.FloatField()
    max = models.FloatField()
    min_time = models.DateTimeField()
    max_time = models.DateTimeField()

    def __str__(self):
        return f"{self.time},symbol: {self.symbol},min&max: {self.min} & {self.max}"

    class Meta:
        indexes = [
            models.Index(fields=['symbol', 'time']),
        ]
class Item_1min(models.Model):
    time = models.DateTimeField()
    symbol = models.CharField(max_length=100)
    min = models.FloatField()
    max = models.FloatField()
    min_time = models.DateTimeField()
    max_time = models.DateTimeField()

    def __str__(self):
        return f"{self.time},symbol: {self.symbol},min&max: {self.min} & {self.max}"

    class Meta:
        indexes = [
            models.Index(fields=['symbol', 'time']),
        ]



    


