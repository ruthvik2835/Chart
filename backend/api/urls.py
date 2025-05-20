from rest_framework import routers
from .views import *
from django.urls import path, include


urlpatterns = [
    path('items/', ItemListView.as_view(), name='item-list'),
    path('items/add/', AddItemView.as_view(), name='add-item'),
    path('items/<int:id>/edit/', EditItemView.as_view(), name='edit-item'),
    path('items/<int:id>/', get_item, name='get-item'),
    # path('items/e/', get_equally_spaced_items_by_id, name='equally-spaced-items'),
    path('items/e/', get_items_equidistant, name='get_items_equidistant'),
    path('items/get/', get_item_by_symbol, name='nearest_item_by_symbol'),
    # path('items/ohlc/', get_minute_ohlc_data, name='ohlc_data'),
    # path('items/upload-csv/', CSVUploadView.as_view(), name='upload-items-csv'),
]
