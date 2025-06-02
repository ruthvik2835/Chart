
import React, { useEffect, useState, useRef, useCallback } from 'react';
import Highcharts from 'highcharts/highstock';
import HighchartsReact from 'highcharts-react-official';

// ===== CONFIGURATION CONSTANTS =====
// Array of stock symbols that users can select from in the dropdown
const SYMBOLS = ['AAPL', 'NFLX', 'GOOG', 'AMZN', 'TSLA'];

// Default visibility state for all 6 data columns (c1-c6)
// When component loads, all columns are visible by default
const DEFAULT_VISIBLE_COLUMNS = {
  c1: true, c2: true, c3: true, c4: true, c5: true, c6: true
};

// Default timeframe for data aggregation (1 minute intervals)
const DEFAULT_TIMEFRAME = '1min';

// Default Y-axis scale type (linear vs logarithmic)
const DEFAULT_YSCALE = 'linear';

// ===== TIME UTILITIES =====
// Constant representing milliseconds in one day (24 hours * 3600 seconds * 1000 ms)
// Used for day-based calculations and visual separators
const oneDay = 24 * 3600 * 1000;

/**
 * Parses a time string and converts it to seconds
 * Supports formats like: "1s", "5min", "1h", "2d", "500ms"
 * 
 * @param {string} timeStr - Time string to parse (e.g., "1min", "5s")
 * @returns {number} - Time in seconds, or NaN if invalid format
 * 
 * Examples:
 * - "1ms" → 0.001 seconds
 * - "30s" → 30 seconds  
 * - "5min" → 300 seconds
 * - "2h" → 7200 seconds
 * - "1d" → 86400 seconds
 */
function parseTimeGapToSeconds(timeStr) {
  // Regular expression to match number + optional unit
  // Captures: (number)(unit) where unit is optional
  const match = /^([\d.]+)\s*(ms|s|min|h|d)?$/.exec(timeStr.trim());
  
  if (!match) return NaN; // Return NaN if string doesn't match expected format
  
  const value = parseFloat(match[1]); // Extract numeric value
  const unit = match[2] || 's'; // Default to seconds if no unit specified
  
  // Convert to seconds based on unit
  switch (unit) {
    case 'ms': return value / 1000;    // Milliseconds to seconds
    case 's': return value;            // Already in seconds
    case 'min': return value * 60;     // Minutes to seconds
    case 'h': return value * 3600;     // Hours to seconds
    case 'd': return value * oneDay;   // Days to seconds (using oneDay constant)
    default: return value;             // Fallback: assume seconds
  }
}

/**
 * Generates alternating colored bands for day visualization
 * Creates background stripes to help distinguish different days on the chart
 * 
 * @param {number} min - Minimum timestamp (in milliseconds)
 * @param {number} max - Maximum timestamp (in milliseconds)
 * @returns {Array} - Array of band objects for Highcharts plotBands
 * 
 * Each band object contains:
 * - from: Start timestamp of the band
 * - to: End timestamp of the band  
 * - color: Background color (alternates between two shades of gray)
 */
const generateDayBands = (min, max) => {
  const bands = [];
  
  // Start from the beginning of the day containing 'min'
  // Math.floor(min / oneDay) * oneDay rounds down to start of day
  let start = Math.floor(min / oneDay) * oneDay;
  
  while (start < max) {
    const end = start + oneDay; // End of current day
    
    bands.push({
      from: start,
      to: end,
      // Alternate colors every other day for visual distinction
      // Uses modulo to determine if day number is even or odd
      color: start % (oneDay * 2) === 0 
        ? 'rgba(200, 200, 200, 0.1)'  // Lighter gray for even days
        : 'rgba(150, 150, 150, 0.05)' // Darker gray for odd days
    });
    
    start = end; // Move to start of next day
  }
  
  return bands;
};

/**
 * Generates vertical separator lines at day boundaries
 * Creates dashed lines to clearly mark the start of each new day
 * 
 * @param {number} min - Minimum timestamp (in milliseconds)
 * @param {number} max - Maximum timestamp (in milliseconds)  
 * @returns {Array} - Array of line objects for Highcharts plotLines
 * 
 * Each line object contains:
 * - value: Timestamp where line should be drawn
 * - color: Line color
 * - width: Line thickness
 * - dashStyle: Line style (solid, dashed, etc.)
 * - zIndex: Layer order (higher values appear on top)
 */
const generateDaySeparators = (min, max) => {
  const lines = [];
  
  // Start from beginning of day containing 'min'
  let time = Math.floor(min / oneDay) * oneDay;
  
  while (time <= max) {
    lines.push({
      value: time,
      color: '#888',           // Medium gray color
      width: 1,                // 1 pixel wide
      dashStyle: 'ShortDash',  // Dashed line style
      zIndex: 5                // Appear above data series but below UI elements
    });
    
    time += oneDay; // Move to next day boundary
  }
  
  return lines;
};

// ===== TIMEFRAME CONFIGURATION =====
// Maps timeframe strings to their equivalent in milliseconds
// Used for data aggregation intervals and chart navigation
const timeframeMinMs = { 
  '1ms': 1,        // 1 millisecond
  '10ms': 10,      // 10 milliseconds  
  '100ms': 100,    // 100 milliseconds
  '1s': 1000,      // 1 second
  '1min': 60000,   // 1 minute (60 * 1000)
  '5min': 300000,  // 5 minutes (5 * 60 * 1000) 
  '1h': 3600000,   // 1 hour (60 * 60 * 1000)
  '1d': oneDay     // 1 day (24 * 60 * 60 * 1000)
};

// ===== VISUAL STYLING =====
// Color palette for the 6 data series (c1-c6)
// Uses distinct colors for easy visual differentiation
const COLORS = [
  '#007bff', // Blue (c1)
  '#28a745', // Green (c2) 
  '#ffc107', // Yellow (c3)
  '#dc3545', // Red (c4)
  '#6f42c1', // Purple (c5)
  '#17a2b8'  // Teal (c6)
];

// Array of column keys corresponding to the 6 data series
// Used for iteration and mapping operations
const COLUMN_KEYS = ['c1', 'c2', 'c3', 'c4', 'c5', 'c6'];

// ===== MAIN COMPONENT =====
const TradingChart = () => {
  // ===== REFS =====
  // Reference to the Highcharts chart instance for direct manipulation
  const chartRef = useRef(null);
  
  // Reference to the main container div for fullscreen and event handling
  const chartContainerRef = useRef(null);

  // ===== STATE VARIABLES =====
  
  // Currently selected stock symbol from SYMBOLS array
  const [symbol, setSymbol] = useState('AMZN');
  
  // Array of formatted data series ready for Highcharts consumption
  // Each series contains: {name, data, type, color, visible}
  const [seriesData, setSeriesData] = useState([]);
  
  // Raw data series before visibility filtering
  // Stored separately to allow toggling visibility without re-fetching data
  const [rawSeries, setRawSeries] = useState([]);
  
  // Current timeframe for data aggregation (e.g., '1min', '5min')
  const [timeframe, setTimeframe] = useState('1min');
  
  // Y-axis scale type: 'linear' or 'logarithmic'
  const [yScale, setYScale] = useState('linear');
  
  // Currently visible time range on the chart
  // Used for day bands/separators and performance optimization
  const [visibleRange, setVisibleRange] = useState({ min: null, max: null });
  
  // Range of data that has been loaded from the server
  // Used to determine when new data fetching is needed
  const [loadedRange, setLoadedRange] = useState({ min: null, max: null });
  
  // Loading state indicator for UI feedback
  const [isLoading, setIsLoading] = useState(false);

  // Visibility state for each of the 6 data columns
  // Controls which series are displayed on the chart
  const [visibleColumns, setVisibleColumns] = useState({
    c1: true, c2: true, c3: true, c4: true, c5: true, c6: true
  });

  // ===== DATA FETCHING =====
  /**
   * Fetches financial data from the API for the specified time range
   * 
   * @param {number} min - Start timestamp (milliseconds)
   * @param {number} max - End timestamp (milliseconds)
   * 
   * This function:
   * 1. Makes HTTP request to backend API
   * 2. Transforms response data into Highcharts format
   * 3. Creates 6 separate data series (c1-c6)
   * 4. Updates component state with new data
   * 5. Expands the requested range to reduce future API calls
   */
  const fetchData = useCallback(async (min, max) => {
    setIsLoading(true); // Show loading indicator
    
    try {
      const starttime = performance.now(); // Performance measurement
      
      // Expand the requested range to reduce future API calls
      // d = duration of requested range
      const d = max - min;
      
      // Request data from (min-d) to (max+d) for buffering
      const startISO = new Date(min - d).toISOString();
      const endISO = new Date(max + d).toISOString();
      
      console.log(startISO, endISO); // Debug logging
      
      // Construct API request URL with parameters:
      // - symbol: Stock symbol (AAPL, AMZN, etc.)
      // - time_gap: Aggregation interval in seconds
      // - start_date/end_date: Time range in ISO format
      // - N: Maximum number of data points (500)
      const resp = await fetch(
        `/api/items/e/?symbol=${symbol}&time_gap=${parseTimeGapToSeconds(timeframe)}&start_date=${startISO}&end_date=${endISO}&N=500`
      );
      
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      
      const data = await resp.json();

      // Initialize arrays for each of the 6 data series
      const c1 = [], c2 = [], c3 = [], c4 = [], c5 = [], c6 = [];
      
      // Transform API response into Highcharts format
      // Each data point becomes [timestamp, value] array
      data.forEach(item => {
        const t = new Date(item.time).getTime(); // Convert to timestamp
        c1.push([t, Number(item.c1)]); // Ensure numeric values
        c2.push([t, Number(item.c2)]);
        c3.push([t, Number(item.c3)]);
        c4.push([t, Number(item.c4)]);
        c5.push([t, Number(item.c5)]);
        c6.push([t, Number(item.c6)]);
      });

      // Create series objects with Highcharts configuration
      const raw = [
        { name: 'c1', data: c1, type: 'line', color: COLORS[0] },
        { name: 'c2', data: c2, type: 'line', color: COLORS[1] },
        { name: 'c3', data: c3, type: 'line', color: COLORS[2] },
        { name: 'c4', data: c4, type: 'line', color: COLORS[3] },
        { name: 'c5', data: c5, type: 'line', color: COLORS[4] },
        { name: 'c6', data: c6, type: 'line', color: COLORS[5] }
      ];
      
      setRawSeries(raw); // Store raw data for visibility toggling
      
      // Create visible series with current visibility settings
      setSeriesData(
        raw.map((s, i) => ({ 
          ...s, 
          visible: visibleColumns[s.name], // Apply current visibility
          boostThreshold: 1 // Enable Highcharts boost for performance
        }))
      );
      
      // Update loaded range to include the expanded buffer
      setLoadedRange({ min: min - d, max: max + d });
      
      console.log("time of fetch: ", performance.now() - starttime); // Performance log
      
    } catch (err) {
      console.error('Fetch error:', err);
    } finally {
      setIsLoading(false); // Hide loading indicator
    }
  }, [timeframe, symbol, visibleColumns]); // Dependencies for useCallback

  // ===== VISIBILITY MANAGEMENT =====
  /**
   * Updates seriesData when visibility settings or raw data changes
   * This effect runs whenever:
   * - User toggles column visibility checkboxes
   * - New data is fetched and stored in rawSeries
   * - Symbol changes (resets visibility)
   */
  useEffect(() => {
    setSeriesData(
      rawSeries.map(s => ({ 
        ...s, 
        visible: visibleColumns[s.name], // Apply current visibility state
        boostThreshold: 1 // Maintain performance boost setting
      }))
    );
  }, [visibleColumns, symbol, rawSeries]);

  // ===== CHART INTERACTION HANDLERS =====
  /**
   * Handles chart zoom/pan events and manages data loading
   * This is the core function for dynamic data loading
   * 
   * @param {Object} e - Event object from Highcharts
   * @param {number} e.min - New minimum visible timestamp
   * @param {number} e.max - New maximum visible timestamp  
   * @param {string} e.trigger - What caused the event ('zoom', 'pan', etc.)
   * 
   * Logic flow:
   * 1. Ignore initialization and loading states
   * 2. Update visible range for UI updates
   * 3. Check if current view requires new data
   * 4. Fetch additional data if needed based on trigger type
   */
  const handleAfterSetExtremes = e => {
    const { min, max, trigger } = e;
    
    // Skip processing during loading or initial chart setup
    if (isLoading || trigger === 'init') return;
    
    // Update visible range for day bands and other UI elements
    setVisibleRange({ min: min, max: max });
    
    const span = max - min; // Current visible time span
    const nowspan = loadedRange.max - loadedRange.min; // Currently loaded span
    
    // ZOOM IN DETECTION
    // If user zoomed in significantly (visible span < 30% of loaded span)
    if (trigger !== 'zoomout' && span <= nowspan * 0.3) {
      console.log(trigger);
      
      // Align fetch range to timeframe boundaries for cleaner data
      const unit = timeframeMinMs[timeframe];
      const alignedMin = Math.floor(min / unit) * unit;
      const alignedMax = Math.ceil(max / unit) * unit;
      
      fetchData(alignedMin, alignedMax);
      return;
    }
    
    console.log("hello", trigger);
    
    // PAN DETECTION  
    // If user panned and is approaching the edge of loaded data
    if (trigger == "pan") {
      console.log("arrow cause pan trigger");
      
      // Define buffer zone (1/5 of loaded range)
      const diff = Math.floor((loadedRange.max - loadedRange.min) / 5);
      
      // Check if visible area is near the edges of loaded data
      if ((max >= loadedRange.max - diff) || (min <= loadedRange.min + diff)) {
        const unit = timeframeMinMs[timeframe];
        const alignedMin = Math.floor(min / unit) * unit;
        const alignedMax = Math.ceil(max / unit) * unit;
        fetchData(alignedMin, alignedMax);
      }
      return;
    }
    
    // ZOOM OUT DETECTION
    // If user zoomed out and might need more data
    if (trigger == 'zoomout') {
      console.log("wheel cause zoomout");
      
      const diff = Math.floor((loadedRange.max - loadedRange.min) / 5);
      console.log(min, max, diff, loadedRange.min, loadedRange.max);
      
      // Check if zoomed out view approaches loaded data boundaries
      if ((max >= loadedRange.max - diff) || (min <= loadedRange.min + diff)) {
        console.log("fetching");
        const unit = timeframeMinMs[timeframe];
        const alignedMin = Math.floor(min / unit) * unit;
        const alignedMax = Math.ceil(max / unit) * unit;
        fetchData(alignedMin, alignedMax);
        return;
      }
      
      console.log("not fetching");
      return;
    }
    
    // UNDEFINED TRIGGER HANDLING
    // Some chart interactions don't specify a trigger
    if (trigger == undefined) {
      console.log("handling undefined trigger");
      return;
    }
    
    console.log(trigger);
    
    // GENERAL RANGE CHECK
    // For other triggers, check if new view is outside loaded range
    if (loadedRange.min != null && loadedRange.max != null) {
      // If completely within loaded range, no fetch needed
      if (min >= loadedRange.min && max <= loadedRange.max) {
        console.log("Within range: skipping fetch");
        return;
      }
      
      // Expand loaded range to include new visible area
      const newMin = Math.min(min, loadedRange.min);
      const newMax = Math.max(max, loadedRange.max);
      const unit = timeframeMinMs[timeframe];
      fetchData(newMin, newMax);
    } else {
      // No data loaded yet, fetch for current view
      fetchData(min, max);
    }
  };

  /**
   * Programmatically zooms out the chart by a specified factor
   * 
   * @param {Object} chart - Highcharts chart instance
   * @param {number} factor - Zoom factor (1.2 = 20% wider view)
   * 
   * Process:
   * 1. Get current visible range
   * 2. Calculate center point
   * 3. Expand range around center
   * 4. Apply new range to chart
   */
  function instantZoomOut(chart, factor = 1.2) {
    if (!chart || !chart.xAxis || !chart.xAxis[0]) return;
    
    const min0 = chart.xAxis[0].min; // Current minimum
    const max0 = chart.xAxis[0].max; // Current maximum
    
    if (min0 == null || max0 == null) return;
    
    const center = Math.floor((min0 + max0) / 2); // Center point
    const range0 = max0 - min0; // Current range
    const range1 = range0 * factor; // New expanded range
    
    // Calculate new boundaries centered on current view
    const newMin = center - Math.ceil(range1 / 2);
    const newMax = center + Math.ceil(range1 / 2);
    
    // Apply new range with animation and custom trigger
    chart.xAxis[0].setExtremes(
      newMin,
      newMax,
      true,  // Redraw chart
      true,  // Animate transition
      { trigger: 'zoomout' } // Custom trigger for handleAfterSetExtremes
    );
  }

  /**
   * Handler for zoom out button click
   * Gets chart instance and calls instantZoomOut
   */
  const handleZoomOut = () => {
    const chart = chartRef.current?.chart;
    instantZoomOut(chart);
  };

  // ===== EVENT LISTENERS =====
  /**
   * Sets up mouse wheel event listener for zoom out functionality
   * Only triggers on wheel down (scroll down) without modifier keys
   */
  useEffect(() => {
    const container = chartContainerRef.current;
    if (!container) return;
    
    const onWheel = (e) => {
      // Skip if Ctrl/Cmd is pressed (browser zoom)
      if (e.ctrlKey || e.metaKey) return;
      
      // Only zoom out on scroll down (positive deltaY)
      if (e.deltaY > 0) {
        handleZoomOut();
        e.preventDefault(); // Prevent page scroll
      }
    };
    
    // Add listener with passive: false to allow preventDefault
    container.addEventListener('wheel', onWheel, { passive: false });
    
    // Cleanup listener on component unmount
    return () => container.removeEventListener('wheel', onWheel);
  }, [handleZoomOut]);

  /**
   * Toggles fullscreen mode for the chart container
   * Uses the Fullscreen API to maximize/minimize the chart
   */
  const toggleFullScreen = () => {
    const el = chartContainerRef.current;
    
    if (!document.fullscreenElement) {
      // Enter fullscreen mode
      el.requestFullscreen().catch(console.error);
    } else {
      // Exit fullscreen mode
      document.exitFullscreen();
    }
  };

  // ===== INITIALIZATION EFFECTS =====
  /**
   * Initial data load when component mounts
   * Sets up default time range and fetches initial data
   */
  useEffect(() => {
    console.log("Initial fetch!");
    
    const now = Date.now();
    // Load last 10,000 hours of data initially (very wide range)
    const initialMin = now - 60 * 60 * 1000 * 10000;
    const initialMax = now;
    
    setVisibleRange({ min: initialMin, max: initialMax });
    fetchData(initialMin, initialMax);
  }, []); // Empty dependency array = run once on mount

  /**
   * Handles symbol changes (stock symbol dropdown)
   * Resets all state and fetches new data for selected symbol
   */
  useEffect(() => {
    console.log("Symbol Change!");
    
    // Reset all state to defaults
    setLoadedRange({ min: null, max: null });
    setSeriesData([]);
    setRawSeries([]);
    setTimeframe(DEFAULT_TIMEFRAME);
    setYScale(DEFAULT_YSCALE);
    setVisibleColumns(DEFAULT_VISIBLE_COLUMNS);
    
    // Set up new time range and fetch data
    const now = Date.now();
    const initialMin = now - 60 * 60 * 1000 * 10000;
    const initialMax = now;
    
    console.log(initialMin, initialMax);
    setVisibleRange({ min: initialMin, max: initialMax });
    fetchData(initialMin, initialMax);
  }, [symbol]); // Run when symbol changes

  /**
   * Keyboard navigation handler
   * Allows left/right arrow keys to pan the chart
   */
  useEffect(() => {
    const handleKeyDown = (e) => {
      const chart = chartRef.current?.chart;
      if (!chart) return;
      
      console.log("loaded range", loadedRange);
      console.log("arrowpressed");
      
      // Calculate pan amount (5% of visible range)
      const visibleSpan = chart.xAxis[0].max - chart.xAxis[0].min;
      const panAmount = visibleSpan * 0.05;
      
      if (e.key === 'ArrowLeft') {
        // Pan left (show earlier data)
        const newMin = Math.max(
          chart.xAxis[0].min - panAmount, 
          -8640000000000000 // JavaScript Date minimum
        );
        const newMax = Math.max(
          chart.xAxis[0].max - panAmount, 
          newMin + 1000 // Ensure minimum range
        );
        
        chart.xAxis[0].setExtremes(
          newMin,
          newMax,
          true,  // Redraw
          false, // No animation for responsive feel
          { trigger: 'pan' } // Custom trigger
        );
        
      } else if (e.key === 'ArrowRight') {
        // Pan right (show later data)
        const newMax = Math.min(
          chart.xAxis[0].max + panAmount, 
          8640000000000000 // JavaScript Date maximum
        );
        const newMin = Math.min(
          chart.xAxis[0].min + panAmount, 
          newMax - 1000 // Ensure minimum range
        );
        
        chart.xAxis[0].setExtremes(
          newMin,
          newMax,  
          true,  // Redraw
          false, // No animation
          { trigger: 'pan' } // Custom trigger
        );
      }
    };
    
    // Global keyboard listener
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []); // No dependencies - always use latest chart state

  // ===== CHART CONFIGURATION =====
  /**
   * Highcharts configuration object
   * Defines all chart behavior, styling, and features
   */
  const chartOptions = {
    // Basic chart setup
    chart: { 
      zoomType: 'x',      // Allow horizontal zooming only
      panning: true,      // Enable mouse panning
      panKey: 'shift',    // Require Shift key for panning
      animation: false    // Disable animations for better performance
    },
    
    // Chart title (shows current timeframe)
    title: { 
      text: `Trading Chart (${timeframe})` 
    },
    
    // X-axis configuration (time axis)
    xAxis: {
      type: 'datetime',   // Treat as datetime axis
      ordinal: false,     // Don't skip gaps in data
      minRange: timeframeMinMs[timeframe], // Minimum zoom level
      events: { 
        afterSetExtremes: handleAfterSetExtremes // Data loading handler
      },
      // Visual enhancements
      plotBands: visibleRange.min != null 
        ? generateDayBands(visibleRange.min, visibleRange.max) 
        : [],
      plotLines: visibleRange.min != null 
        ? generateDaySeparators(visibleRange.min, visibleRange.max) 
        : []
    },
    
    // Y-axis configuration (price axis)
    yAxis: { 
      type: yScale,       // Linear or logarithmic scale
      title: { text: 'Price' }
    },
    
    // Tooltip configuration
    tooltip: { 
      shared: true,       // Show all series values in one tooltip
      xDateFormat: '%Y-%m-%d %H:%M:%S' // Format for timestamp display
    },
    
    // Disable data grouping for precise display
    dataGrouping: { enabled: false },
    
    // Data series array (populated by state)
    series: seriesData,
    
    // Performance optimization
    boost: {
      useGPUTranslations: true, // Use GPU for rendering
      seriesThreshold: 1        // Enable boost for any number of series
    },
    
    // Line series styling
    plotOptions: {
      line: { 
        marker: { enabled: false } // Hide individual data point markers
      }
    },
    
    // Navigation and scrolling
    navigator: { enabled: true },   // Show mini-chart navigator
    scrollbar: { enabled: true },   // Show horizontal scrollbar
    
    // Branding
    credits: { enabled: false },    // Hide Highcharts credit link
    
    // Stock tools configuration
    navigation: {
      stockTools: {
        gui: {
          enabled: true,
          buttons: [
            'fullScreen', 'indicators', 'separator',
            'crookedLines', 'measure', 'typeChange',
            'zoomChange', 'annotations', 'verticalLabels',
            'flags', 'fibonacci', 'toggleAnnotations'
          ]
        }
      }
    }
  };

// ===== RENDER =====
  return (
    <div ref={chartContainerRef} style={{ height: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: '#fff' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '12px', backgroundColor: '#f8f9fa' }}>
        {['1ms','10ms','100ms','1s', '1min', '5min', '1h', '1d'].map(tf => (
          <button key={tf} onClick={() => setTimeframe(tf)} style={{
            background: timeframe === tf ? '#007bff' : '#e2e6ea',
            color: timeframe === tf ? '#fff' : '#000',
            border: '1px solid #ced4da',
            padding: '6px 12px',
            borderRadius: '4px',
            cursor: 'pointer'
          }}>{tf}</button>
        ))}
        <select value={yScale} onChange={e => setYScale(e.target.value)} style={{ padding: '6px', borderRadius: '4px' }}>
          <option value="linear">Y-Scale: Linear</option>
          <option value="logarithmic">Y-Scale: Logarithmic</option>
        </select>
        {/* Column visibility checkboxes */}
        <div style={{ marginLeft: 16, display: 'flex', alignItems: 'center', gap: '8px' }}>
          {COLUMN_KEYS.map((col, idx) => (
            <label key={col} style={{ marginRight: 8, display: 'flex', alignItems: 'center', fontWeight: 500 }}>
              <input
                type="checkbox"
                checked={visibleColumns[col]}
                onChange={() =>
                  setVisibleColumns(v => ({ ...v, [col]: !v[col] }))
                }
                style={{ marginRight: 4 }}
              />
              <span style={{ color: COLORS[idx] }}>{col}</span>
            </label>
          ))}
        </div>
        <select value={symbol} onChange={e => setSymbol(e.target.value)}>
            {SYMBOLS.map(sym => (
              <option value={sym} key={sym}>{sym}</option>
            ))}
        </select>

        <div style={{ flexGrow: 1 }} />
        <button onClick={handleZoomOut} style={{
          padding: '6px 12px',
          borderRadius: '4px',
          border: '1px solid #ced4da',
          cursor: 'pointer',
          background: '#ffc107',
          color: '#000'
        }}>Zoom Out</button>
        <button onClick={toggleFullScreen} style={{
          padding: '6px 12px',
          borderRadius: '4px',
          border: '1px solid #ced4da',
          cursor: 'pointer',
          background: '#6c757d',
          color: '#fff'
        }}>Fullscreen</button>
      </div>
      <HighchartsReact
        highcharts={Highcharts}
        constructorType="stockChart"
        options={chartOptions}
        ref={chartRef}
        containerProps={{ style: { flexGrow: 1 } }}
      />
    </div>
  );
};

export default TradingChart;
