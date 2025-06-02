# Import Django REST Framework's router system for automatic URL pattern generation
# Routers automatically create URL patterns for ViewSets, providing standard CRUD operations
from rest_framework import routers

# Import all views from the current app's views module
# The asterisk (*) imports all public classes and functions from views.py
# This includes both class-based views (CBVs) and function-based views (FBVs)
from .views import *

# Import Django's URL pattern matching utilities
# path(): Creates URL patterns with named parameters and type conversion
# include(): Allows inclusion of other URL configuration modules
from django.urls import path, include

# Main URL configuration list - defines all URL patterns for this Django app
# Each pattern maps a URL path to a view function or class-based view
# Django processes these patterns in order, returning the first match
urlpatterns = [
    # ITEM LIST ENDPOINT
    # URL: /items/
    # Purpose: Display paginated list of all items, likely with filtering/search capabilities
    # View Type: Class-Based View (CBV) using ListView pattern
    # HTTP Methods: Typically GET for listing data
    # Use Cases: 
    #   - Dashboard displaying recent items
    #   - API endpoint for bulk data retrieval
    #   - Admin interface for data management
    path('items/', ItemListView.as_view(), name='item-list'),
    
    # ITEM CREATION ENDPOINT  
    # URL: /items/add/
    # Purpose: Handle creation of new Item instances
    # View Type: Class-Based View (CBV) using CreateView pattern
    # HTTP Methods: GET (show form), POST (process form submission)
    # Use Cases:
    #   - Web form for manual data entry
    #   - API endpoint for creating new records
    #   - Bulk import interface
    # Design Note: Separate endpoint for creation follows RESTful conventions
    path('items/add/', AddItemView.as_view(), name='add-item'),
    
    # ITEM EDIT ENDPOINT
    # URL: /items/<id>/edit/ (e.g., /items/123/edit/)
    # Purpose: Handle updating existing Item instances
    # View Type: Class-Based View (CBV) using UpdateView pattern  
    # URL Parameter: <int:id> captures integer ID and passes it to the view
    # HTTP Methods: GET (show pre-filled form), POST/PUT (process updates)
    # Use Cases:
    #   - Edit forms for correcting data errors
    #   - API endpoint for partial/full updates
    #   - Admin interface for data maintenance
    # Security Consideration: Should include permission checks to prevent unauthorized edits
    path('items/<int:id>/edit/', EditItemView.as_view(), name='edit-item'),
    
    # ITEM DETAIL ENDPOINT
    # URL: /items/<id>/ (e.g., /items/123/)
    # Purpose: Retrieve detailed information for a single Item instance
    # View Type: Function-Based View (FBV) - more lightweight for simple operations
    # URL Parameter: <int:id> captures the item's primary key
    # HTTP Methods: Typically GET for data retrieval
    # Use Cases:
    #   - Detail pages showing full item information
    #   - API endpoint for single record retrieval
    #   - Data validation and verification interfaces
    # Design Pattern: RESTful resource URL structure
    path('items/<int:id>/', get_item, name='get-item'),
    
    # SPECIALIZED EQUIDISTANT ITEMS ENDPOINT
    # URL: /items/e/
    # Purpose: Retrieve items with equidistant time spacing (specialized query)
    # View Type: Function-Based View (FBV) for custom business logic
    # HTTP Methods: Typically GET with query parameters
    # Use Cases:
    #   - Time-series analysis requiring evenly spaced data points
    #   - Chart/graph data where consistent intervals are needed
    #   - Statistical analysis requiring uniform temporal distribution
    #   - Downsampling dense time-series data for visualization
    # Design Note: Short URL 'e/' suggests this is a frequently used endpoint
    # Query Parameters (likely): 
    #   - symbol: filter by specific asset
    #   - start_time/end_time: time range bounds
    #   - interval: desired spacing between points
    #   - count: maximum number of points to return
    path('items/e/', get_items_equidistant, name='get_items_equidistant'),
]

# ADDITIONAL ARCHITECTURAL NOTES FOR LLM FINE-TUNING:
#
# 1. URL PATTERN DESIGN PRINCIPLES:
#    - RESTful resource naming: /items/ for collections, /items/<id>/ for individual resources
#    - Hierarchical structure: specific actions under resource paths (/items/add/, /items/<id>/edit/)
#    - Descriptive endpoints: specialized functionality gets dedicated paths (/items/e/)
#
# 2. VIEW TYPE SELECTION STRATEGY:
#    - Class-Based Views (CBV) for standard CRUD operations (list, add, edit)
#      * Benefit: Built-in functionality, less code, consistent behavior
#      * Use Case: Standard database operations with forms/templates
#    - Function-Based Views (FBV) for specialized logic (get_item, get_items_equidistant)
#      * Benefit: More control, easier custom logic, better for API endpoints
#      * Use Case: Custom business logic, specialized queries, API responses
#
# 3. URL PARAMETER PATTERNS:
#    - <int:id>: Type conversion ensures ID is integer, prevents invalid requests
#    - Named parameters: Enable reverse URL resolution and cleaner templates
#    - Consistent naming: 'id' parameter used consistently across edit/detail endpoints
#
# 4. NAMING CONVENTIONS:
#    - URL names follow kebab-case: 'item-list', 'add-item', 'edit-item'
#    - Names are descriptive and namespace-aware
#    - Enable reverse URL resolution: {% url 'item-list' %} in templates
#
# 5. MISSING PATTERNS TO CONSIDER:
#    - DELETE endpoint: /items/<id>/delete/ for item removal
#    - BULK operations: /items/bulk/ for batch processing
#    - API versioning: /api/v1/items/ for API evolution
#    - Filtering endpoints: /items/by-symbol/<symbol>/ for common filters
#
# 6. SECURITY CONSIDERATIONS:
#    - Authentication/authorization middleware should protect these endpoints
#    - CSRF protection for form-based views (add, edit)
#    - Rate limiting for API endpoints
#    - Input validation in corresponding views
#
# 7. PERFORMANCE CONSIDERATIONS:
#    - List view should implement pagination for large datasets
#    - Equidistant endpoint should have query optimization for time-series data
#    - Caching headers for frequently accessed detail views
#    - Database query optimization in corresponding views
#
# 8. REST API EVOLUTION:
#    - Current structure mixes web forms and API endpoints
#    - Could be enhanced with DRF ViewSets and routers for full REST API:
#      router = routers.DefaultRouter()
#      router.register(r'items', ItemViewSet)
#      urlpatterns += [path('api/', include(router.urls))]
#
# 9. ERROR HANDLING:
#    - Views should handle 404 errors for invalid IDs
#    - Proper HTTP status codes for different scenarios
#    - User-friendly error messages for web interface
#
# 10. TESTING CONSIDERATIONS:
#     - Each URL pattern should have corresponding test cases
#     - Test both valid and invalid parameter values
#     - Verify proper HTTP methods are accepted/rejected