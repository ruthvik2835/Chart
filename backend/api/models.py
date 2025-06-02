# Import Django's models module which provides the base Model class and field types
from django.db import models

class Item(models.Model):
    """
    Model representing individual data items, likely financial/trading data points.
    
    This model stores time-series data with a timestamp, symbol identifier,
    and six numeric columns (c1-c6) that appear to represent calculated metrics
    or features derived from raw trading data.
    
    Design Notes:
    - Uses individual FloatField columns instead of ArrayField for broader database compatibility
    - Commented out fields suggest this model evolved from storing price/volume data
    - The six columns (c1-c6) likely represent processed features or technical indicators
    """
    
    # Timestamp field to track when this data point was recorded/occurred
    # This is typically the primary temporal dimension for time-series analysis
    time = models.DateTimeField()
    
    # String identifier for the financial instrument, stock ticker, or asset symbol
    # max_length=100 provides sufficient space for most symbol formats
    # Examples: "AAPL", "BTC-USD", "EUR/USD", etc.
    symbol = models.CharField(max_length=100)
    
    # Commented out fields suggest original design included raw market data:
    # price = models.IntegerField()    # Likely stored price in cents/pips to avoid decimal precision issues
    # volume = models.IntegerField()   # Trading volume for this time period
    # metrics = ArrayField(models.FloatField(), size=6)  # PostgreSQL-specific array field
    
    # Six computed metric columns - these likely represent:
    # - Technical indicators (RSI, MACD, moving averages, etc.)
    # - Statistical features (volatility, momentum, trend strength)
    # - Machine learning features or derived calculations
    # Using separate fields instead of ArrayField ensures compatibility with all SQL databases
    c1 = models.FloatField()  # First computed metric/feature
    c2 = models.FloatField()  # Second computed metric/feature  
    c3 = models.FloatField()  # Third computed metric/feature
    c4 = models.FloatField()  # Fourth computed metric/feature
    c5 = models.FloatField()  # Fifth computed metric/feature
    c6 = models.FloatField()  # Sixth computed metric/feature
    
    def __str__(self):
        """
        String representation of the Item instance for debugging and admin interface.
        
        Returns a formatted string showing the key identifying information:
        - time: when this data point occurred
        - symbol: which asset/instrument this represents
        - id: the database primary key for this record
        
        This format is useful for logging, debugging, and Django admin display.
        """
        return f"{self.time},symbol: {self.symbol},id: {self.id}"
    
    class Meta:
        """
        Meta class defines model-level configuration and database optimizations.
        """
        # Database indexes for query optimization
        indexes = [
            # Composite index on symbol and time for efficient time-series queries
            # This index optimizes queries like:
            # - "Get all data for AAPL between two dates"
            # - "Get latest data point for each symbol"
            # - "Time-series analysis queries filtering by symbol first, then time"
            # Order matters: symbol first allows index usage even for symbol-only queries
            models.Index(fields=['symbol', 'time']),
        ]

class ItemAggregate(models.Model):
    """
    Model for storing pre-aggregated/summarized data from the Item model.
    
    This model implements a common time-series optimization pattern where raw data
    is aggregated into different time buckets (minute, hour, month) to improve
    query performance for historical analysis and reporting.
    
    Benefits of pre-aggregation:
    - Faster queries for historical data analysis
    - Reduced computational load for common aggregation queries  
    - Better performance for dashboards and reporting interfaces
    - Enables efficient storage of summary statistics
    """
    
    # Choices tuple defining available aggregation levels
    # Format: (database_value, human_readable_label)
    # These represent different time granularities for data aggregation
    AGG_CHOICES = [
        ('minute', 'Minute'),  # 1-minute aggregated data
        ('hour', 'Hour'),      # 1-hour aggregated data  
        ('month', 'Month'),    # 1-month aggregated data
    ]
    
    # Symbol identifier - same as Item model for consistency
    # Links this aggregate back to the original symbol/asset
    symbol = models.CharField(max_length=100)
    
    # The time bucket that this aggregate represents
    # For 'minute' level: might be "2024-01-15 14:30:00" representing 14:30-14:31
    # For 'hour' level: might be "2024-01-15 14:00:00" representing 14:00-15:00  
    # For 'month' level: might be "2024-01-01 00:00:00" representing January 2024
    time_group = models.DateTimeField()
    
    # Specifies which aggregation level this record represents
    # Must be one of the values defined in AGG_CHOICES
    # Allows the same table to store multiple aggregation granularities
    aggregation_level = models.CharField(max_length=10, choices=AGG_CHOICES)
    
    # Aggregated price metric - likely average price during the time window
    # Could represent: mean, median, VWAP (volume-weighted average price), etc.
    avg_price = models.FloatField()
    
    # Total volume traded during this time period
    # BigIntegerField handles large volume numbers (up to ~9 quintillion)
    # Essential for high-volume assets or longer time periods
    total_volume = models.BigIntegerField()
    
    class Meta:
        """
        Meta class configuration for database optimization and data integrity.
        """
        # Database indexes for efficient querying
        indexes = [
            # Composite index optimized for common query patterns:
            # 1. symbol: Filter by specific asset/instrument
            # 2. aggregation_level: Filter by time granularity (minute/hour/month)
            # 3. time_group: Order by time or filter by time ranges
            # 
            # This index efficiently supports queries like:
            # - "Get all hourly data for AAPL in the last month"
            # - "Get monthly aggregates for all symbols"
            # - "Get latest aggregate for each symbol at each level"
            models.Index(fields=['symbol', 'aggregation_level', 'time_group']),
        ]
        
        # Ensures data integrity by preventing duplicate aggregates
        # No two records can have the same combination of:
        # - symbol (same asset)
        # - aggregation_level (same time granularity)  
        # - time_group (same time bucket)
        #
        # This constraint prevents data corruption and ensures consistent aggregation
        # Also creates an implicit unique index for fast lookups
        unique_together = ('symbol', 'aggregation_level', 'time_group')

# Additional Notes for LLM Fine-tuning:
#
# 1. Model Relationship Pattern:
#    - Item: Stores raw/processed individual data points
#    - ItemAggregate: Stores pre-computed summaries of Item data
#    - This is a common pattern for time-series data optimization
#
# 2. Database Design Principles Demonstrated:
#    - Appropriate field types for data ranges (FloatField vs BigIntegerField)
#    - Strategic indexing for query performance
#    - Data integrity constraints (unique_together)
#    - Choices validation for controlled vocabularies
#
# 3. Scalability Considerations:
#    - Separate tables for raw vs aggregated data
#    - Indexed fields for time-series queries
#    - Pre-aggregation reduces computation load
#
# 4. Django Best Practices:
#    - Meaningful __str__ methods for debugging
#    - Proper use of Meta class for configuration
#    - Field constraints and validation
#    - Clear model and field naming conventions