from rest_framework import serializers
from .models import *

class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = '__all__'

class Item_1msSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item_1ms
        fields = '__all__'

class Item_10msSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item_10ms
        fields = '__all__'

class Item_100msSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item_100ms
        fields = '__all__'

class Item_1sSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item_1s
        fields = '__all__'

class Item_10sSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item_10s
        fields = '__all__'

class Item_1minSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item_1min
        fields = '__all__'
