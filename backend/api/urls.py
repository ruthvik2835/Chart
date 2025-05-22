from rest_framework import routers
from .views import *
from django.urls import path, include


urlpatterns = [
    path('items/', ItemListView.as_view(), name='item-list'),
    path('items/add/', AddItemView.as_view(), name='add-item'),
    path('items/<int:id>/edit/', EditItemView.as_view(), name='edit-item'),
    path('items/<int:id>/', get_item, name='get-item'),
    path('items/e/', get_items_equidistant, name='get_items_equidistant'),
    path('items/symbols/', available_symbols, name='get_available_symbols'),
]
