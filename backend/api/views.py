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
from concurrent.futures import ThreadPoolExecutor
import boto3
timestream_query = boto3.client('timestream-query')
DATABASE_NAME = 'sampleDB'
TABLE_NAME = 'milli_data'

class ItemListView(ListAPIView):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer


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

def fetch_items_by_chunk(symbol, time_chunk):
    results = []

    for ts in time_chunk:
        iso_ts = ts.isoformat()
        query = f"""
            SELECT time, measure_name, measure_value::double 
            FROM "{DATABASE_NAME}"."{TABLE_NAME}" 
            WHERE Symbol = '{symbol}' 
              AND time = from_iso8601_timestamp('{iso_ts}')
        """

        try:
            response = timestream_query.query(QueryString=query)
            for row in response['Rows']:
                record = {col['Name']: val.get('ScalarValue') for col, val in zip(response['ColumnInfo'], row['Data'])}
                record['timestamp'] = iso_ts
                results.append(record)
        except Exception as e:
            print(f"Error querying Timestream for timestamp {iso_ts}: {e}")

    return results


def split_list(input_list, num_chunks):
    avg = len(input_list) // num_chunks
    return [input_list[i * avg:(i + 1) * avg] for i in range(num_chunks - 1)] + [input_list[(num_chunks - 1) * avg:]]
def get_time_bounds_from_timestream(symbol):
    query = f"""
        SELECT MIN(time) as first_time, MAX(time) as last_time
        FROM "{DATABASE_NAME}"."{TABLE_NAME}"
        WHERE Symbol = '{symbol}'
    """
    try:
        response = timestream_query.query(QueryString=query)
        row = response['Rows'][0]['Data']
        first_time_str = row[0].get('ScalarValue')
        last_time_str = row[1].get('ScalarValue')

        if not first_time_str or not last_time_str:
            return None, None

        # Parse ISO8601 timestamps to Python datetime
        from datetime import datetime
        first_time = datetime.fromisoformat(first_time_str.replace('Z', '+00:00'))
        last_time = datetime.fromisoformat(last_time_str.replace('Z', '+00:00'))
        return first_time, last_time

    except Exception as e:
        print(f"Error querying Timestream time bounds: {e}")
        return None, None


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
    time_gap_str = request.query_params.get('time_gap')  # For aligning start/end dates
    N_str = request.query_params.get('N')               # Number of equidistant points

    # print("here 1")
    # --- 1. Validate presence of all required parameters ---
    required_params = {
        'symbol': symbol,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'time_gap': time_gap_str,
        'N': N_str
    }
    missing_params = [name for name, val in required_params.items() if val is None]
    if missing_params:
        return Response(
            {'error': f'Missing parameters: {", ".join(missing_params)}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # --- 2. Parse and validate time_gap_seconds (now allows float) ---
    try:
        time_gap_seconds = float(time_gap_str) # Changed to float
        if time_gap_seconds <= 0:
            raise ValueError("time_gap must be positive")
    except ValueError:
        return Response(
            {'error': '"time_gap" must be a positive number representing seconds (e.g., 60, 0.5 for 500ms, or 0.001 for 1ms).'}, # Updated error message
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
    first_time, last_time = get_time_bounds_from_timestream(symbol)

    if not first_time or not last_time:
        return Response(
            {'error': f'No data found for symbol "{symbol}".'},
            status=status.HTTP_404_NOT_FOUND
        )

    clamped_start_date = max(start_date, first_time)
    clamped_end_date = min(end_date, last_time)

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

    # --- 7. Align start_date and end_date to the NEAREST multiple of time_gap_seconds ---
    start_timestamp = clamped_start_date.timestamp()
    aligned_start_timestamp = round_to_nearest_multiple(start_timestamp, time_gap_seconds)
    aligned_start_dt = dt_class.fromtimestamp(aligned_start_timestamp, tz=start_date.tzinfo)

    end_timestamp = clamped_end_date.timestamp()
    aligned_end_timestamp = round_to_nearest_multiple(end_timestamp, time_gap_seconds)
    aligned_end_dt = dt_class.fromtimestamp(aligned_end_timestamp, tz=end_date.tzinfo)

    
    # --- 8. Validate aligned dates ---
    if aligned_start_dt > aligned_end_dt:
        return Response({
            'error': 'Adjusted start date is after adjusted end date due to rounding. Cannot generate points from this range.',
            'details': {
                'original_start_date': start_date.isoformat(),
                'original_end_date': end_date.isoformat(),
                'aligned_start_date': aligned_start_dt.isoformat(),
                'aligned_end_date': aligned_end_dt.isoformat(),
                'time_gap_seconds': time_gap_seconds
            }
        }, status=status.HTTP_400_BAD_REQUEST)
    # print("here 3")
    # --- 9. Generate N equidistant time points between aligned_start_dt and aligned_end_dt ---
    times_to_query = []
    if N == 1:
        times_to_query.append(aligned_start_dt)
    else: # N > 1
        if aligned_start_dt == aligned_end_dt:
            times_to_query = [aligned_start_dt]
        else:
            total_duration_seconds = (aligned_end_dt - aligned_start_dt).total_seconds() # Can be float
            if total_duration_seconds < 0: # Should be caught by earlier aligned_start_dt > aligned_end_dt check
                 return Response({
                    'error': 'Internal calculation error: total duration for points is negative.',
                 }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            num_intervals=(total_duration_seconds/time_gap_seconds)
            print("num_intervals",num_intervals)

            N=min(N,math.floor(num_intervals)+1) # Ensure N does not exceed the number of intervals

            interval_seconds = math.floor(num_intervals / (N - 1)) # Can be float

            print("difference: ",interval_seconds * time_gap_seconds)



            for i in range(N):
                offset_seconds = i * interval_seconds * time_gap_seconds
                current_time_point = aligned_start_dt + timedelta(seconds=offset_seconds) # timedelta handles float seconds
                if current_time_point > aligned_end_dt:
                    break
                times_to_query.append(current_time_point)
            
            # Optional: Ensure the last point is exactly aligned_end_dt if critical due to float arithmetic over many points.
            # For most cases, the above calculation is sufficient. If strict adherence to aligned_end_dt is needed:
            # if N > 1 and times_to_query and total_duration_seconds > 0 : 
            # times_to_query[-1] = aligned_end_dt
# def perf():                            
#     a = time.time()
#     items = Item.objects.filter()      
#     serializer = ItemSerializer(items, many=True).data
#     b = round(time.time() - a, 4)     
#     print(a, b)     
    # print("here 4")
    # --- 10. Query the database using the actual Item model ---

    try:
        NUM_THREADS = 4
        chunks = split_list(times_to_query, NUM_THREADS)

        with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
            futures = [executor.submit(fetch_items_by_chunk, symbol, chunk) for chunk in chunks]
            all_items = []
            for future in futures:
                all_items.extend(future.result())

        measure_1 = time.time() - start_time_measurement
        print(round(measure_1, 4))
        # serializer = ItemSerializer(all_items, many=True)
        # # print("here 6")
        # data1=serializer.data
        duration_measurement = time.time() - start_time_measurement

        stats = {
            "count": len(all_items), 
            "performance": {
                "duration_seconds": round(duration_measurement, 4)
            },
            "query_details": {
                "symbol": symbol,
                "requested_start_date": start_date_str,
                "requested_end_date": end_date_str,
                "time_gap_alignment_seconds": time_gap_seconds,
                "N_points_requested": N,
                "aligned_start_datetime": aligned_start_dt.isoformat(),
                "aligned_end_datetime": aligned_end_dt.isoformat(),
                "num_timestamps_generated": len(times_to_query),
                # "generated_timestamps_iso": [t.isoformat() for t in times_to_query] # Uncomment for debugging; can be verbose
            },
              
        }

        print(stats)
        return Response(all_items, status=status.HTTP_200_OK)
        

    except Exception as e:
        print(str(e))
        return Response(
            {'error': 'An unexpected error occurred during data retrieval.', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
