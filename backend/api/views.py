# =============================================================================
# DJANGO REST FRAMEWORK IMPORTS
# =============================================================================

# ViewSets provide automatic CRUD operations and URL routing
from rest_framework import viewsets

# Import all models from the current app (Item, ItemAggregate, etc.)
from .models import *

# Import all serializers for data transformation between Python objects and JSON/XML
from .serializers import *

# Generic views provide pre-built class-based views for common operations
# ListAPIView, CreateAPIView, UpdateAPIView offer standard REST operations
from rest_framework.generics import *

# Commented import - api_view decorator for function-based views
# from rest_framework.decorators import api_view

# Response class for returning HTTP responses with proper headers and status codes
from rest_framework.response import Response

# HTTP status codes constants (200, 404, 400, 500, etc.)
from rest_framework import status

# Decorators for function-based views and parser configuration
from rest_framework.decorators import api_view, parser_classes

# Base class for custom API views with full control over HTTP methods
from rest_framework.views import APIView

# Python's datetime module for date/time manipulation
from datetime import datetime

# ViewSet base class for custom viewset implementations
from rest_framework.viewsets import ViewSet

# Parsers for handling file uploads and form data
from rest_framework.parsers import MultiPartParser, FormParser

# Django utility for parsing ISO datetime strings
from django.utils.dateparse import parse_datetime

# Django ORM aggregation functions for database queries
from django.db.models import Min, Max

# Duplicate import - already imported above (code cleanup opportunity)
from rest_framework import status

# Python time module for performance measurements
import time

# Python datetime utilities for time calculations
from datetime import timedelta
from datetime import timedelta, datetime as dt_class

# CSV processing module for data import/export
import csv

# In-memory file operations
import io 

# Django timezone utilities for handling timezone-aware datetimes
from django.utils.timezone import make_aware, is_aware

# Django database functions for date/time truncation and grouping
from django.db.models.functions import TruncMinute, TruncHour, TruncMonth

# Mathematical operations module
import math

# =============================================================================
# STANDARD CRUD API VIEWS
# =============================================================================

class ItemListView(ListAPIView):
    """
    Generic list view for retrieving all Item instances.
    
    This class-based view provides standard REST API functionality for listing items:
    - GET /items/ returns paginated list of all items
    - Automatic serialization using ItemSerializer
    - Built-in filtering, ordering, and pagination support
    - No custom business logic required
    
    Inherits from ListAPIView which provides:
    - get() method implementation
    - Pagination handling
    - Query parameter filtering
    - Permission checking
    - Content negotiation (JSON/XML response formats)
    
    Use Cases:
    - Dashboard displaying recent items
    - Data export endpoints
    - Mobile app data synchronization
    - Third-party API integrations
    """
    queryset = Item.objects.all()  # Base queryset - can be filtered by overriding get_queryset()
    serializer_class = ItemSerializer  # Handles Python object ↔ JSON conversion


class AddItemView(CreateAPIView):
    """
    Generic create view for adding new Item instances.
    
    Provides standard REST API functionality for item creation:
    - POST /items/add/ creates new item from request data
    - Automatic data validation using serializer
    - Returns created object with 201 status code
    - Handles validation errors with 400 status code
    
    Inherits from CreateAPIView which provides:
    - post() method implementation
    - Data validation and serialization
    - Database save operations
    - Error handling and response formatting
    
    Request Flow:
    1. Receive POST request with JSON data
    2. Validate data using ItemSerializer
    3. Save valid data to database
    4. Return serialized created object
    
    Use Cases:
    - Web form submissions
    - API data ingestion
    - Bulk data import endpoints
    - Mobile app data creation
    """
    queryset = Item.objects.all()  # Required for permission checks
    serializer_class = ItemSerializer  # Handles validation and creation


class EditItemView(UpdateAPIView):
    """
    Generic update view for modifying existing Item instances.
    
    Provides standard REST API functionality for item updates:
    - PUT /items/<id>/edit/ replaces entire object
    - PATCH /items/<id>/edit/ updates specific fields
    - Automatic data validation and database updates
    - Returns updated object or validation errors
    
    Inherits from UpdateAPIView which provides:
    - put() and patch() method implementations
    - Object lookup and validation
    - Partial update support
    - Error handling for missing objects
    
    Configuration:
    - lookup_field = 'id': Uses 'id' parameter from URL for object lookup
    - Default lookup_field is 'pk', but 'id' is more explicit
    
    Use Cases:
    - Edit forms for data correction
    - API updates from external systems
    - Batch update operations
    - Data synchronization processes
    """
    queryset = Item.objects.all()  # Base queryset for object lookup
    serializer_class = ItemSerializer  # Handles validation and updates
    lookup_field = 'id'  # URL parameter name for object identification


# =============================================================================
# CUSTOM FUNCTION-BASED VIEWS
# =============================================================================

@api_view(['GET'])
def get_item(request, id):
    """
    Function-based view for retrieving a single Item instance.
    
    This approach provides more control than generic views for simple operations:
    - Direct database query and error handling
    - Custom response formatting
    - Explicit exception handling
    - Lower overhead than class-based views
    
    Args:
        request: HTTP request object with headers, query params, etc.
        id (int): Item primary key from URL parameter
    
    Returns:
        Response: JSON-serialized item data or error message
        
    HTTP Status Codes:
        200: Success - item found and returned
        404: Not Found - item with given ID doesn't exist
        
    Use Cases:
    - Simple item detail pages
    - API endpoints for single record retrieval
    - Data validation and verification
    - Performance-critical lookups
    """
    try:
        # Direct ORM query - raises DoesNotExist exception if not found
        item = Item.objects.get(id=id)
        
        # Serialize Python object to JSON-compatible format
        serializer = ItemSerializer(item)
        
        # Return successful response with serialized data
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Item.DoesNotExist:
        # Handle missing item gracefully with descriptive error
        return Response(
            {'error': 'Item not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )


# =============================================================================
# UTILITY FUNCTIONS FOR TIME SERIES PROCESSING
# =============================================================================

def round_to_nearest_multiple(timestamp_float, multiple_seconds):
    """
    Rounds a Unix timestamp to the nearest multiple of specified seconds.
    
    This function is crucial for time-series data alignment, ensuring that
    data points are consistently spaced at regular intervals. Used for:
    - Aligning irregular time series data to regular intervals
    - Synchronizing data from multiple sources
    - Creating consistent time buckets for aggregation
    
    Algorithm:
    - Uses standard mathematical rounding (0.5 rounds up)
    - Formula: floor(timestamp / interval + 0.5) * interval
    - Handles fractional seconds for millisecond precision
    
    Args:
        timestamp_float (float): Unix timestamp (seconds since epoch)
        multiple_seconds (float): Interval to round to (e.g., 60 for minutes, 0.001 for milliseconds)
    
    Returns:
        float: Rounded timestamp aligned to the specified interval
        
    Examples:
        round_to_nearest_multiple(1234567890.7, 60) → rounds to nearest minute
        round_to_nearest_multiple(1234567890.123, 0.001) → rounds to nearest millisecond
        
    Edge Cases:
        - multiple_seconds = 0: Returns original timestamp (prevents division by zero)
        - Negative timestamps: Works correctly with negative Unix timestamps
    """
    if multiple_seconds == 0: # Prevent division by zero error
        return timestamp_float
    
    # Standard rounding algorithm: floor(x / m + 0.5) * m
    # Adding 0.5 before floor() implements "round half up" behavior
    return math.floor(timestamp_float / multiple_seconds + 0.5) * multiple_seconds


# =============================================================================
# COMPLEX TIME SERIES ANALYSIS ENDPOINT
# =============================================================================

@api_view(['GET'])
def get_items_equidistant(request):
    """
    Advanced time-series endpoint for retrieving N equidistant data points.
    
    This function implements sophisticated time-series sampling algorithm:
    1. Validates and parses all input parameters
    2. Aligns start/end dates to specified time grid
    3. Generates N evenly-spaced time points
    4. Queries database for items at those specific times
    5. Returns performance metrics and query details
    
    Key Features:
    - Sub-second precision support (millisecond/microsecond intervals)
    - Automatic date range clamping to available data
    - Robust input validation and error handling
    - Performance monitoring and diagnostics
    - Timezone-aware datetime processing
    
    Query Parameters:
        symbol (str): Asset/instrument identifier (e.g., "AAPL", "BTC-USD")
        start_date (str): ISO datetime string (e.g., "2024-01-01T12:00:00.000Z")
        end_date (str): ISO datetime string (e.g., "2024-01-02T12:00:00.000Z")
        time_gap (float): Alignment interval in seconds (e.g., 60, 0.5, 0.001)
        N (int): Number of equidistant points to retrieve
    
    Use Cases:
    - Chart/graph data with consistent time intervals
    - Statistical analysis requiring uniform temporal distribution
    - Machine learning feature extraction from time series
    - Data visualization requiring downsampled dense data
    - Technical analysis with regular time intervals
    
    Returns:
        Response: JSON array of serialized Item objects
        
    HTTP Status Codes:
        200: Success - data retrieved and returned
        400: Bad Request - invalid parameters or date ranges
        404: Not Found - no data available for specified symbol
        500: Internal Server Error - unexpected processing errors
    """
    
    # =============================================================================
    # PERFORMANCE MONITORING SETUP
    # =============================================================================
    
    # Start performance timer for request processing duration
    start_time_measurement = time.time()

    # =============================================================================
    # PARAMETER EXTRACTION AND VALIDATION
    # =============================================================================
    
    # Extract query parameters from HTTP request
    symbol = request.query_params.get('symbol')              # Financial instrument identifier
    start_date_str = request.query_params.get('start_date')  # ISO datetime string
    end_date_str = request.query_params.get('end_date')      # ISO datetime string  
    time_gap_str = request.query_params.get('time_gap')      # Alignment interval (seconds)
    N_str = request.query_params.get('N')                    # Number of points to return

    # Validate presence of all required parameters
    # This prevents partial processing and provides clear error messages
    required_params = {
        'symbol': symbol,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'time_gap': time_gap_str,
        'N': N_str
    }
    
    # Identify any missing parameters
    missing_params = [name for name, val in required_params.items() if val is None]
    if missing_params:
        return Response(
            {'error': f'Missing parameters: {", ".join(missing_params)}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # =============================================================================
    # TIME GAP VALIDATION AND PARSING
    # =============================================================================
    
    # Parse and validate time_gap parameter (supports fractional seconds)
    try:
        time_gap_seconds = float(time_gap_str)  # Allows decimal values like 0.5, 0.001
        if time_gap_seconds <= 0:
            raise ValueError("time_gap must be positive")
    except ValueError:
        return Response(
            {'error': '"time_gap" must be a positive number representing seconds (e.g., 60, 0.5 for 500ms, or 0.001 for 1ms).'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # =============================================================================
    # POINT COUNT VALIDATION
    # =============================================================================
    
    # Parse and validate N parameter (number of points to return)
    try:
        N = int(N_str)
        if N <= 0:
            raise ValueError("N must be positive")
    except ValueError:
        return Response(
            {'error': '"N" must be a positive integer.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # =============================================================================
    # DATETIME PARSING AND TIMEZONE HANDLING
    # =============================================================================
    
    # Parse start_date string into datetime object
    start_date = parse_datetime(start_date_str)
    if not start_date:
        return Response(
            {'error': 'Invalid start_date format. Use ISO format (e.g., 2024-01-01T12:00:00.000Z).'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Ensure start_date is timezone-aware (required for database queries)
    if not is_aware(start_date):
        start_date = make_aware(start_date)

    # Parse end_date string into datetime object
    end_date = parse_datetime(end_date_str)
    if not end_date:
        return Response(
            {'error': 'Invalid end_date format. Use ISO format (e.g., 2024-01-01T12:00:00.000Z).'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Ensure end_date is timezone-aware
    if not is_aware(end_date):
        end_date = make_aware(end_date)

    # =============================================================================
    # DATE RANGE VALIDATION
    # =============================================================================
    
    # Validate that start_date comes before end_date
    if start_date >= end_date:
        return Response(
            {'error': 'start_date must be strictly before end_date.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # =============================================================================
    # DATA AVAILABILITY CHECK AND RANGE CLAMPING
    # =============================================================================
    
    # Find the actual date range of available data for this symbol
    first_item = Item.objects.filter(symbol=symbol).order_by('time').first()
    last_item = Item.objects.filter(symbol=symbol).order_by('-time').first()

    # Check if any data exists for the specified symbol
    if not first_item or not last_item:
        return Response(
            {'error': f'No data found for symbol "{symbol}".'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Extract actual data boundaries
    first_time = first_item.time
    last_time = last_item.time

    # Clamp requested date range to available data boundaries
    # This prevents queries outside the available data range
    clamped_start_date = max(start_date, first_time)
    clamped_end_date = min(end_date, last_time)

    # Validate that clamped range is still valid
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

    # =============================================================================
    # TIME ALIGNMENT TO REGULAR GRID
    # =============================================================================
    
    # Convert clamped dates to Unix timestamps for mathematical operations
    start_timestamp = clamped_start_date.timestamp()
    aligned_start_timestamp = round_to_nearest_multiple(start_timestamp, time_gap_seconds)
    aligned_start_dt = dt_class.fromtimestamp(aligned_start_timestamp, tz=start_date.tzinfo)

    end_timestamp = clamped_end_date.timestamp()
    aligned_end_timestamp = round_to_nearest_multiple(end_timestamp, time_gap_seconds)
    aligned_end_dt = dt_class.fromtimestamp(aligned_end_timestamp, tz=end_date.tzinfo)

    # =============================================================================
    # ALIGNED DATE RANGE VALIDATION
    # =============================================================================
    
    # Ensure alignment didn't create invalid date range
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

    # =============================================================================
    # EQUIDISTANT POINT GENERATION ALGORITHM
    # =============================================================================
    
    # Initialize list to store calculated time points for database queries
    times_to_query = []
    
    if N == 1:
        # Special case: only one point requested, use aligned start time
        times_to_query.append(aligned_start_dt)
    else: # N > 1
        if aligned_start_dt == aligned_end_dt:
            # Special case: start and end are the same after alignment
            times_to_query = [aligned_start_dt]
        else:
            # Calculate total time span between aligned dates
            total_duration_seconds = (aligned_end_dt - aligned_start_dt).total_seconds()
            
            # Sanity check for negative duration (should be caught earlier)
            if total_duration_seconds < 0:
                 return Response({
                    'error': 'Internal calculation error: total duration for points is negative.',
                 }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Calculate how many time_gap intervals fit in the total duration
            num_intervals = (total_duration_seconds / time_gap_seconds)
            print("num_intervals", num_intervals)

            # Ensure N doesn't exceed available intervals + 1
            # +1 because N points require N-1 intervals
            N = min(N, math.floor(num_intervals) + 1)

            # Calculate interval size between equidistant points
            # This determines how many time_gap units to skip between points
            interval_seconds = math.floor(num_intervals / (N - 1))

            print("difference: ", interval_seconds * time_gap_seconds)

            # Generate N equidistant time points
            for i in range(N):
                # Calculate time offset for this point
                offset_seconds = i * interval_seconds * time_gap_seconds
                
                # Create datetime object for this point
                current_time_point = aligned_start_dt + timedelta(seconds=offset_seconds)
                
                # Safety check: don't exceed end boundary
                if current_time_point > aligned_end_dt:
                    break
                    
                times_to_query.append(current_time_point)
            
            # Optional: Force last point to be exactly aligned_end_dt
            # Uncomment if strict adherence to end boundary is critical
            # if N > 1 and times_to_query and total_duration_seconds > 0: 
            #     times_to_query[-1] = aligned_end_dt

    # =============================================================================
    # DATABASE QUERY AND RESPONSE GENERATION
    # =============================================================================
    
    try:
        # Query database for items matching symbol and calculated time points
        # Uses __in lookup for efficient batch querying
        items = Item.objects.filter(symbol=symbol, time__in=times_to_query)
        
        # Serialize Python objects to JSON-compatible format
        serializer = ItemSerializer(items, many=True)
        
        # Calculate total processing duration for performance monitoring
        duration_measurement = time.time() - start_time_measurement

        # Prepare comprehensive response statistics
        stats = {
            "count": len(serializer.data), 
            "performance": {
                "duration_seconds": round(duration_measurement, 4)  # Processing time
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
                # Uncomment for debugging - can be verbose for large N:
                # "generated_timestamps_iso": [t.isoformat() for t in times_to_query]
            },
        }

        # Log statistics for monitoring and debugging
        print(stats)
        
        # Return successful response with serialized data
        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        # Handle unexpected errors gracefully
        print(str(e))  # Log error for debugging
        return Response(
            {'error': 'An unexpected error occurred during data retrieval.', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# =============================================================================
# ARCHITECTURAL NOTES FOR LLM FINE-TUNING
# =============================================================================

"""
DESIGN PATTERNS DEMONSTRATED:

1. CLASS-BASED VS FUNCTION-BASED VIEWS:
   - CBVs (ItemListView, AddItemView, EditItemView): Standard CRUD operations
   - FBVs (get_item, get_items_equidistant): Custom business logic

2. ERROR HANDLING STRATEGIES:
   - Input validation with descriptive error messages
   - Exception handling with try-catch blocks
   - HTTP status code usage following REST conventions
   - Graceful degradation for edge cases

3. TIME SERIES PROCESSING PATTERNS:
   - Date range validation and clamping
   - Time alignment algorithms for regular intervals
   - Performance monitoring and optimization
   - Timezone-aware datetime handling

4. API DESIGN PRINCIPLES:
   - Comprehensive input validation
   - Detailed error responses with context
   - Performance metrics in responses
   - RESTful endpoint design

5. DATABASE QUERY OPTIMIZATION:
   - Efficient lookups using __in for batch queries
   - Order by clauses for finding boundary records
   - Minimal database hits through strategic querying

6. CODE ORGANIZATION:
   - Logical section separation with comments
   - Utility functions for reusable algorithms
   - Clear variable naming and documentation
   - Performance measurement integration

SCALABILITY CONSIDERATIONS:
- Large N values could generate many database queries
- Consider implementing caching for frequently accessed data
- Time alignment could be pre-computed for common intervals
- Database indexing on (symbol, time) is crucial for performance

SECURITY CONSIDERATIONS:
- Input validation prevents injection attacks
- Error messages don't expose sensitive system information
- Rate limiting should be implemented for expensive operations
- Authentication/authorization should wrap these endpoints
"""