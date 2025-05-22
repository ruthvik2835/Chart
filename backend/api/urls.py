from rest_framework import routers
from .views import *
from django.urls import path, include


urlpatterns = [
    path('items/', ItemListView.as_view(), name='item-list'),
    path('items_1ms/', Item_1msListView.as_view(), name='item-1ms-list'),
    path('items_10ms/', Item_10msListView.as_view(), name='item-10ms-list'),
    path('items_100ms/', Item_100msListView.as_view(), name='item-100ms-list'),
    path('items_1s/', Item_1sListView.as_view(), name='item-1s-list'),
    path('items_10s/', Item_10sListView.as_view(), name='item-10s-list'),
    path('items_1min/', Item_1minListView.as_view(), name='item-1min-list'),
    path('items/add/', AddItemView.as_view(), name='add-item'),
    path('items/<int:id>/edit/', EditItemView.as_view(), name='edit-item'),
    path('items/<int:id>/', get_item, name='get-item'),
    path('items/e/', get_items_equidistant, name='get_items_equidistant'),
    path('items/symbols/', available_symbols, name='get_available_symbols'),
]
