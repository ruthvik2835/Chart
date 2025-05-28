from rest_framework import routers
from .views import *
from django.urls import path, include


urlpatterns = [
    path('items/e/', get_items_equidistant, name='get_items_equidistant'),
    # path('items/symbols/', available_symbols, name='get_available_symbols'),
]
