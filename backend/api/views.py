from rest_framework import viewsets
from .models import *
from .serializers import *
from rest_framework.generics import *
# from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.views import APIView
from datetime import datetime
from rest_framework.viewsets import ViewSet
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils.dateparse import parse_datetime
from django.db.models import Min, Max
from rest_framework import status
import time
from datetime import timedelta
from datetime import timedelta, datetime as dt_class
import csv
import io 
from django.utils.timezone import make_aware, is_aware
from django.db.models.functions import TruncMinute, TruncHour, TruncMonth
import math

MODEL_MAP = {
    1: Item_1ms,
    10: Item_10ms,
    100: Item_100ms,
    1000: Item_1s,
    10000: Item_10s,
    60000: Item_1min,
}

SERIALIZER_MAP = {
    1: Item_1msSerializer,
    10: Item_10msSerializer,
    100: Item_100msSerializer,
    1000: Item_1sSerializer,
    10000: Item_10sSerializer,
    60000: Item_1minSerializer,
}

def compute_frame_and_timestamps_ms_aligned(start_dt, end_dt, N):
    """
    Returns:
      frame_ms: int          # chosen interval in milliseconds
      timestamps: List[str]  # ISO timestamps aligned to multiples of frame_ms
    """
    # 1) Compute total span in ms
    total_ms = int((end_dt - start_dt).total_seconds() * 1000)
    if total_ms <= 0 or N <= 0:
        return None, []

    # 2) Raw ideal step in ms, rounding up
    raw_step_ms = (total_ms) // N

    # 3) Allowed frames (all in ms)
    allowed_ms = [
        1,    # 1 ms
        # 5,    # 5 ms
        10,   # 10 ms
        # 50,   # 50 ms
        100,  # 100 ms
        # 500,  # 500 ms
        1000,    # 1 s
        # 5000,    # 5 s
        10000,   # 10 s
        60000,   # 1 min
        # 300000,  # 5 min
        # 600000,  # 10 min
    ]


    # 4) Pick the smallest allowed >= raw_step_ms, else the largest
    frame_ms = next((f for f in allowed_ms if f >= raw_step_ms), allowed_ms[-1])

    print(frame_ms)

    # 5) Align the first timestamp:
    #    find start_ms since epoch, then round *up* to nearest multiple of frame_ms
    start_ms = int(start_dt.timestamp() * 1000)
    mod = start_ms % frame_ms
    if mod == 0:
        aligned_start_ms = start_ms
    else:
        aligned_start_ms = start_ms + (frame_ms - mod)

    # 6) Build the timestamp list
    timestamps = []
    step = timedelta(milliseconds=frame_ms)
    cur_dt = start_dt + timedelta(milliseconds=(aligned_start_ms - start_ms))
    # note: cur_dt is the aligned first timestamp

    while cur_dt <= end_dt:
        timestamps.append(cur_dt.isoformat())
        cur_dt += step

    return frame_ms, timestamps


class ItemListView(ListAPIView):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer

class Item_1msListView(ListAPIView):
    queryset = Item_1ms.objects.all()
    serializer_class = Item_1msSerializer

class Item_10msListView(ListAPIView):
    queryset = Item_10ms.objects.all()
    serializer_class = Item_10msSerializer

class Item_100msListView(ListAPIView):
    queryset = Item_100ms.objects.all()
    serializer_class = Item_100msSerializer

class Item_1sListView(ListAPIView):
    queryset = Item_1s.objects.all()
    serializer_class = Item_1sSerializer

class Item_10sListView(ListAPIView):
    queryset = Item_10s.objects.all()
    serializer_class = Item_10sSerializer

class Item_1minListView(ListAPIView):
    queryset = Item_1min.objects.all()
    serializer_class = Item_1minSerializer


class AddItemView(CreateAPIView):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer

class EditItemView(UpdateAPIView):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    lookup_field = 'id'  


@api_view(['GET'])
def get_item(request, id):
    try:
        item = Item.objects.get(id=id)
        serializer = ItemSerializer(item)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Item.DoesNotExist:
        return Response({'error': 'Item not found'}, status=status.HTTP_404_NOT_FOUND)
    


def round_to_nearest_multiple(timestamp_float, multiple_seconds):
    """
    Rounds a Unix timestamp (float) to the nearest multiple of 'multiple_seconds'.
    'multiple_seconds' can be a float (e.g., for millisecond precision).
    Uses standard rounding (0.5 rounds up).
    """
    if multiple_seconds == 0: # Avoid division by zero
        return timestamp_float
    # Standard rounding: floor(x / m + 0.5) * m
    return math.floor(timestamp_float / multiple_seconds + 0.5) * multiple_seconds


@api_view(['GET'])
def get_items_equidistant(request):
    """
    Fetches N equidistant items for a given symbol between a start and end date.
    The start and end dates are first aligned to the nearest multiple of time_gap.
    Time_gap can be specified in seconds, including fractional seconds for millisecond precision.
    """
    start_time_measurement = time.time()

    symbol = request.query_params.get('symbol')
    start_date_str = request.query_params.get('start_date')
    end_date_str = request.query_params.get('end_date')
    # time_gap_str = request.query_params.get('time_gap')  # For aligning start/end dates
    N_str = request.query_params.get('N')               # Number of equidistant points

    # print("here 1")
    # --- 1. Validate presence of all required parameters ---
    required_params = {
        'symbol': symbol,
        'start_date': start_date_str,
        'end_date': end_date_str,
        # 'time_gap': time_gap_str,
        'N': N_str
    }
    missing_params = [name for name, val in required_params.items() if val is None]
    if missing_params:
        return Response(
            {'error': f'Missing parameters: {", ".join(missing_params)}'},
            status=status.HTTP_400_BAD_REQUEST
        )


    # --- 3. Parse and validate N (number of points) ---
    try:
        N = int(N_str)
        if N <= 0:
            raise ValueError("N must be positive")
    except ValueError:
        return Response(
            {'error': '"N" must be a positive integer.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # --- 4. Parse and make start_date timezone-aware ---
    start_date = parse_datetime(start_date_str)
    if not start_date:
        return Response(
            {'error': 'Invalid start_date format. Use ISO format (e.g., 2024-01-01T12:00:00.000Z).'},
            status=status.HTTP_400_BAD_REQUEST
        )
    if not is_aware(start_date):
        start_date = make_aware(start_date)

    # --- 5. Parse and make end_date timezone-aware ---
    end_date = parse_datetime(end_date_str)
    if not end_date:
        return Response(
            {'error': 'Invalid end_date format. Use ISO format (e.g., 2024-01-01T12:00:00.000Z).'},
            status=status.HTTP_400_BAD_REQUEST
        )
    if not is_aware(end_date):
        end_date = make_aware(end_date)

    # --- 6. Validate date order (original dates) ---
    if start_date >= end_date:
        return Response(
            {'error': 'start_date must be strictly before end_date.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # print("here 2")
    first_item = Item.objects.filter(symbol=symbol).order_by('time').first()
    last_item = Item.objects.filter(symbol=symbol).order_by('-time').first()

    if not first_item or not last_item:
        return Response(
            {'error': f'No data found for symbol "{symbol}".'},
            status=status.HTTP_404_NOT_FOUND
        )

    first_time = first_item.time
    last_time = last_item.time

    clamped_end_date = min(end_date, last_time)
    clamped_start_date = max(start_date, first_time)

    # --- Validate clamped range ---
    if clamped_start_date > clamped_end_date:
        return Response({
            'error': 'After clamping to available data range, start_date > end_date.',
            'details': {
                'requested_start_date': start_date.isoformat(),
                'requested_end_date': end_date.isoformat(),
                'clamped_start_date': clamped_start_date.isoformat(),
                'clamped_end_date': clamped_end_date.isoformat(),
                'available_start_date': first_time.isoformat(),
                'available_end_date': last_time.isoformat()
            }
        }, status=status.HTTP_400_BAD_REQUEST)

    frame_ms,times_to_query=compute_frame_and_timestamps_ms_aligned(clamped_start_date,clamped_end_date,N)


    # print("here 4")
    # --- 10. Query the database using the actual Item model ---
    try:
        model_class = MODEL_MAP.get(frame_ms)
        
        items = model_class.objects.filter(symbol=symbol, time__in=times_to_query)

        # print("here 5")

        serializer_class = SERIALIZER_MAP.get(frame_ms)       
        serializer = serializer_class(items, many=True)

        # print("here 6")
        duration_measurement = time.time() - start_time_measurement

        stats = {
            "count": len(serializer.data), 
            "performance": {
                "duration_seconds": round(duration_measurement, 4)
            },
            "query_details": {
                "symbol": symbol,
                "requested_start_date": start_date_str,
                "requested_end_date": end_date_str,
                "N_points_requested": N,
                "num_timestamps_generated": len(times_to_query),
                # "generated_timestamps_iso": [t.isoformat() for t in times_to_query] # Uncomment for debugging; can be verbose
            },
              
        }

        response = {
            'data': serializer.data,
            'framems': frame_ms
        }

        print(stats)
        
        return Response(response, status=status.HTTP_200_OK)

    except Exception as e:
        print(str(e))
        return Response(
            {'error': 'An unexpected error occurred during data retrieval.', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
@api_view(['GET'])
def available_symbols(request):
    symbols = Item.objects.values_list('symbol', flat=True).distinct()
    return Response({'symbols': list(symbols)})
