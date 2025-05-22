import React, { useEffect, useState, useRef, useCallback } from 'react';
import Highcharts from 'highcharts/highstock';
import HighchartsReact from 'highcharts-react-official';
import Boost from 'highcharts/modules/boost';


const SYMBOLS = ['AAPL', 'NFLX', 'GOOG', 'AMZN', 'TSLA', 'MSFT']; // Added MSFT for more options
const DEFAULT_VISIBLE_COLUMNS = {
  c1: true, c2: true, c3: true, c4: true, c5: true, c6: true
};
const DEFAULT_TIMEFRAME = '1min';
const DEFAULT_YSCALE = 'linear';
const DEFAULT_SELECTED_SYMBOLS = ['AMZN']; // Default to AMZN

const oneDay = 24 * 3600 * 1000;
function parseTimeGapToSeconds(timeStr) {
  const match = /^([\d.]+)\s*(ms|s|min|h|d)?$/.exec(timeStr.trim());
  if (!match) return NaN;
  const value = parseFloat(match[1]);
  const unit = match[2] || 's';
  switch (unit) {
    case 'ms': return value / 1000;
    case 's': return value;
    case 'min': return value * 60;
    case 'h': return value * 3600;
    case 'd': return value * oneDay; // Note: oneDay here is in ms, API might expect seconds for 'd'
    default: return value;
  }
}

const generateDayBands = (min, max) => {
  const bands = [];
  if (min == null || max == null) return bands;
  let start = Math.floor(min / oneDay) * oneDay;
  while (start < max) {
    const end = start + oneDay;
    bands.push({
      from: start,
      to: end,
      color: start % (oneDay * 2) === 0 ? 'rgba(200, 200, 200, 0.1)' : 'rgba(150, 150, 150, 0.05)'
    });
    start = end;
  }
  return bands;
};

const generateDaySeparators = (min, max) => {
  const lines = [];
  if (min == null || max == null) return lines;
  let time = Math.floor(min / oneDay) * oneDay;
  while (time <= max) {
    lines.push({ value: time, color: '#888', width: 1, dashStyle: 'ShortDash', zIndex: 5 });
    time += oneDay;
  }
  return lines;
};

const timeframeMinMs = { '1ms':1, '10ms':10, '100ms':100,'1s': 1000, '1min': 60000, '5min': 300000, '1h': 3600000, '1d': oneDay };
const COLORS = ['#007bff', '#28a745', '#ffc107', '#dc3545', '#6f42c1', '#17a2b8', '#fd7e14', '#20c997', '#6610f2', '#e83e8c']; // Expanded colors for more series
const COLUMN_KEYS = ['c1', 'c2', 'c3', 'c4', 'c5', 'c6'];

const TradingChart = () => {
  const chartRef = useRef(null);
  const [selectedSymbols, setSelectedSymbols] = useState(DEFAULT_SELECTED_SYMBOLS);
  const chartContainerRef = useRef(null);
  const [seriesData, setSeriesData] = useState([]);
  const [rawSeries, setRawSeries] = useState([]);
  const [timeframe, setTimeframe] = useState(DEFAULT_TIMEFRAME);
  const [yScale, setYScale] = useState(DEFAULT_YSCALE);
  const [visibleRange, setVisibleRange] = useState({ min: null, max: null });
  const [loadedRange, setLoadedRange] = useState({ min: null, max: null });
  const [isLoading, setIsLoading] = useState(false);
  const [visibleColumns, setVisibleColumns] = useState(DEFAULT_VISIBLE_COLUMNS);
  const [initialLoadDone, setInitialLoadDone] = useState(false);


  const fetchData = useCallback(async (min, max, symbolsToFetch) => {
    if (!symbolsToFetch || symbolsToFetch.length === 0) {
      setRawSeries([]);
      // seriesData will be cleared by its own useEffect reacting to rawSeries change
      setLoadedRange({ min: null, max: null });
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    try {
      const startTimeMs = performance.now();
      const dataWindowRange = max - min; // "d" in original code
      // Fetch a bit more data than currently visible to allow some panning without immediate refetch
      const fetchStartDate = new Date(min - dataWindowRange);
      const fetchEndDate = new Date(max + dataWindowRange);
      
      const startISO = fetchStartDate.toISOString();
      const endISO = fetchEndDate.toISOString();

      console.log(`Workspaceing for symbols: ${symbolsToFetch.join(', ')} from ${startISO} to ${endISO} with timeframe ${timeframe}`);

      const promises = symbolsToFetch.map(currentSymbol =>
        fetch(
          `/api/items/e/?symbol=${currentSymbol}&time_gap=${parseTimeGapToSeconds(timeframe)}&start_date=${startISO}&end_date=${endISO}&N=500`
        ).then(async resp => {
          if (!resp.ok) {
            const errorBody = await resp.text();
            throw new Error(`HTTP ${resp.status} for symbol ${currentSymbol}: ${errorBody}`);
          }
          return resp.json().then(data => ({ symbol: currentSymbol, data }));
        })
      );

      const results = await Promise.all(promises);

      const newRawSeries = [];
      let colorIndex = 0; // For assigning colors if we have many symbol-column combinations

      results.forEach(result => {
        const { symbol: currentSymbol, data: symbolSpecificData } = result;
        // Prepare arrays for c1-c6 for the current symbol
        const symbolColumnData = { c1: [], c2: [], c3: [], c4: [], c5: [], c6: [] };

        symbolSpecificData.forEach(item => {
          const t = new Date(item.time).getTime();
          COLUMN_KEYS.forEach(colKey => {
            if (item[colKey] !== undefined && item[colKey] !== null) {
                 symbolColumnData[colKey].push([t, Number(item[colKey])]);
            }
          });
        });
        
        COLUMN_KEYS.forEach((colKey, colIdx) => {
          // Use a combination of symbol and column for color if needed, or cycle through COLORS
          // For now, stick to column-based coloring, but ensure series names are unique.
          const seriesColor = COLORS[colIdx % COLORS.length];

          newRawSeries.push({
            name: `${currentSymbol} ${colKey}`, // e.g., "AAPL c1"
            data: symbolColumnData[colKey],
            type: 'line',
            color: seriesColor,
            symbol: currentSymbol, // Store original symbol
            column: colKey,       // Store original column key (c1, c2, etc.)
            boostThreshold: 1,    // Enable boost for series
            turboThreshold: 2000  // For line series, default is 1000. Can be increased.
          });
          colorIndex++;
        });
      });
      
      setRawSeries(newRawSeries);
      setLoadedRange({ min: fetchStartDate.getTime(), max: fetchEndDate.getTime() });
      console.log(`Workspace successful for ${symbolsToFetch.join(', ')}. Time taken: ${performance.now() - startTimeMs}ms. Series count: ${newRawSeries.length}`);

    } catch (err) {
      console.error('Fetch error:', err);
      // Potentially clear only the data for symbols that failed, or show a global error
      // For simplicity, we might let rawSeries be partially updated or leave as is on error.
      // Or setRawSeries([]) to clear everything on any error.
    } finally {
      setIsLoading(false);
    }
  }, [timeframe]); // timeframe is a key dependency for parseTimeGapToSeconds and API query

  // Effect for initial data load
  useEffect(() => {
    if (!initialLoadDone && selectedSymbols.length > 0) {
      console.log("Initial chart setup and fetch!");
      const now = Date.now();
      const initialMin = now - (7 * oneDay); // Default to 7 days back
      const initialMax = now;
      
      setVisibleRange({ min: initialMin, max: initialMax });
      fetchData(initialMin, initialMax, selectedSymbols);
      setInitialLoadDone(true);
    }
  }, [selectedSymbols, fetchData, initialLoadDone]);

  // Effect for changes in selected symbols
  useEffect(() => {
    if (!initialLoadDone) return; // Don't run on initial mount if initialLoadDone handles it

    console.log("Selected Symbols Changed:", selectedSymbols);
    setLoadedRange({ min: null, max: null }); // Reset loaded range
    
    // Clear data immediately for responsiveness
    setRawSeries([]); 
    // setSeriesData([]); // This will be updated by the effect below

    if (selectedSymbols.length > 0) {
      let fetchMin = visibleRange.min;
      let fetchMax = visibleRange.max;

      if (fetchMin === null || fetchMax === null) { // If no range, set a default
        const now = Date.now();
        fetchMin = now - (7 * oneDay);
        fetchMax = now;
        setVisibleRange({ min: fetchMin, max: fetchMax });
      }
      fetchData(fetchMin, fetchMax, selectedSymbols);
    } else {
      setIsLoading(false); // Ensure loading is off if no symbols
    }
  }, [selectedSymbols, initialLoadDone]); // fetchData is not needed here as it's stable or this effect re-runs if fetchData changes via initialLoadDone changing selectedSymbols

   // Effect for changes in timeframe
  useEffect(() => {
    if (!initialLoadDone) return; // Don't run on initial mount

    console.log("Timeframe Changed:", timeframe);
    setLoadedRange({ min: null, max: null });
    setRawSeries([]);
    // setSeriesData([]); // Handled by effect below

    if (selectedSymbols.length > 0 && visibleRange.min !== null && visibleRange.max !== null) {
      fetchData(visibleRange.min, visibleRange.max, selectedSymbols);
    } else if (selectedSymbols.length > 0) {
        // Fallback if visibleRange is somehow not set
        const now = Date.now();
        const defaultMin = now - (7 * oneDay);
        const defaultMax = now;
        setVisibleRange({min: defaultMin, max: defaultMax});
        fetchData(defaultMin, defaultMax, selectedSymbols);
    }
  }, [timeframe, initialLoadDone]); // Similar to above, selectedSymbols ensures fetchData is called with symbols

  // Update seriesData (plotted data) when rawSeries or visibleColumns change
  useEffect(() => {
    setSeriesData(
      rawSeries.map(s => ({ ...s, visible: visibleColumns[s.column] }))
    );
  }, [rawSeries, visibleColumns]);


  const handleAfterSetExtremes = useCallback(e => {
    const { min, max, trigger } = e;
    
    if (isLoading || trigger === 'navigator' || trigger === 'rangeSelectorButton') {
        // More precise condition to avoid fetching when navigator itself is updated by chart extremes
        if(chartRef.current && chartRef.current.chart && chartRef.current.chart.navigator) {
            const nav = chartRef.current.chart.navigator;
            if(nav.fixedWidth && (trigger === 'navigator' || trigger === 'pan')){ // crude check
                 // console.log("Likely navigator update, skip fetch for now to avoid loop");
                 // return; // Be cautious with this, might prevent some valid navigator initiated fetches
            }
        }
    }
    if (isLoading) return;


    // Update visible range for plotBands/Lines
    // Debounce or throttle this if it causes too many re-renders for plotBands
    setVisibleRange({ min, max });


    if (trigger === 'zoom' || trigger === 'pan' || trigger === undefined || trigger === 'zoomout') {
        const currentVisibleSpan = max - min;
        const currentLoadedSpan = loadedRange.max - loadedRange.min;

        // Check if current view is mostly outside the already loaded data window
        // Fetch if less than 20% of the loaded data is available on either side of the new view
        const bufferRatio = 0.2; 
        const loadThresholdMin = loadedRange.min + currentLoadedSpan * bufferRatio;
        const loadThresholdMax = loadedRange.max - currentLoadedSpan * bufferRatio;

        // Fetch if panning or zooming near the edges of loaded data
        // or if zooming out significantly beyond current loaded data
        let needsFetch = false;
        if (loadedRange.min === null || loadedRange.max === null) { // Initial load or data cleared
            needsFetch = true;
        } else if (min < loadThresholdMin || max > loadThresholdMax) {
            needsFetch = true;
        } else if (trigger === 'zoomout' && (min < loadedRange.min || max > loadedRange.max)) {
             // If zoom out results in a range outside current loadedRange.
            needsFetch = true;
        }
        
        // Also consider fetching if the resolution of data might need to change (e.g. zoomed way in)
        // For simplicity, current logic primarily focuses on data window.
        // The span check below helps with zooming in a lot.
        const currentUnitMs = timeframeMinMs[timeframe];
        const alignedMin = Math.floor(min / currentUnitMs) * currentUnitMs;
        const alignedMax = Math.ceil(max / currentUnitMs) * currentUnitMs;

        if (currentVisibleSpan <= currentLoadedSpan * 0.3 && trigger !== 'zoomout') { // Zoomed in significantly
             console.log("Zoomed in significantly, refetching for higher detail or closer window", trigger);
             if (selectedSymbols.length > 0) fetchData(alignedMin, alignedMax, selectedSymbols);
             return;
        }


        if (needsFetch && selectedSymbols.length > 0) {
            console.log(`AfterSetExtremes (${trigger}): Fetching new data. Range: ${new Date(alignedMin).toISOString()} to ${new Date(alignedMax).toISOString()}`);
            fetchData(alignedMin, alignedMax, selectedSymbols);
        } else {
            // console.log(`AfterSetExtremes (${trigger}): Data within loaded range or no fetch needed.`);
        }
    }
  }, [isLoading, loadedRange, selectedSymbols, fetchData, timeframe]); // Include all dependencies used

  function instantZoomOut(chart, factor = 1.2) {
    if (!chart || !chart.xAxis || !chart.xAxis[0]) return;
    const xAxis = chart.xAxis[0];
    const min0 = xAxis.min;
    const max0 = xAxis.max;
    if (min0 == null || max0 == null) return;
    
    const center = (min0 + max0) / 2;
    const range0 = max0 - min0;
    const range1 = Math.max(range0 * factor, timeframeMinMs[timeframe] * 10); // Ensure range is not too small
    
    const newMin = Math.floor(center - range1 / 2);
    const newMax = Math.ceil(center + range1 / 2);

    xAxis.setExtremes(newMin, newMax, true, true, { trigger: 'zoomout' });
  }

  const handleZoomOut = useCallback(() => {
    const chart = chartRef.current?.chart;
    instantZoomOut(chart);
  }, [timeframe]); // timeframe for minRange in instantZoomOut

  useEffect(() => {
    const container = chartContainerRef.current;
    if (!container) return;
    const onWheel = (e) => {
      if (e.ctrlKey || e.metaKey) return; // Allow default pinch-zoom
      if (e.deltaY > 0) { // Zoom out on scroll down
        handleZoomOut();
        e.preventDefault();
      } else if (e.deltaY < 0) { // Zoom in on scroll up (Highcharts default zoomType: 'x' handles this if mouse over axis)
        // To make scroll up zoom in on chart area:
        const chart = chartRef.current?.chart;
        if (chart) {
            // A factor < 1 zooms in. E.g. 1/1.2
            instantZoomOut(chart, 1/1.2);
            e.preventDefault();
        }
      }
    };
    container.addEventListener('wheel', onWheel, { passive: false });
    return () => container.removeEventListener('wheel', onWheel);
  }, [handleZoomOut]); // handleZoomOut is stable due to its own useCallback

  const toggleFullScreen = () => {
    const el = chartContainerRef.current;
    if (!el) return;
    if (!document.fullscreenElement) {
      el.requestFullscreen().catch(err => console.error(`Error attempting to enable full-screen mode: ${err.message} (${err.name})`));
    } else {
      document.exitFullscreen();
    }
  };
  
  useEffect(() => {
    const handleKeyDown = (e) => {
      const chart = chartRef.current?.chart;
      if (!chart || !chart.xAxis || !chart.xAxis[0]) return;

      const xAxis = chart.xAxis[0];
      if (xAxis.min == null || xAxis.max == null) return;

      const visibleSpan = xAxis.max - xAxis.min;
      const panAmount = visibleSpan * 0.1; // Pan 10% of visible range

      let newMin, newMax;

      if (e.key === 'ArrowLeft') {
        newMin = xAxis.min - panAmount;
        newMax = xAxis.max - panAmount;
      } else if (e.key === 'ArrowRight') {
        newMin = xAxis.min + panAmount;
        newMax = xAxis.max + panAmount;
      } else {
        return; // Not an arrow key we handle
      }
      
      // Prevent panning beyond reasonable limits (JS Date limits)
      newMin = Math.max(newMin, -8640000000000000);
      newMax = Math.min(newMax, 8640000000000000);
      if (newMax - newMin < timeframeMinMs[timeframe]) { // Prevent over-panning into too small range
          if (e.key === 'ArrowLeft') newMax = newMin + timeframeMinMs[timeframe];
          else newMin = newMax - timeframeMinMs[timeframe];
      }

      xAxis.setExtremes(newMin, newMax, true, e.shiftKey, { trigger: 'pan' }); // true for redraw, e.shiftKey for animation
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [timeframe]); // timeframe for minRange check

  const chartOptions = {
    chart: {
      zoomType: 'x',
      panning: true,
      panKey: 'shift',
      animation: false, // Consider true for smoother zoom/pan, but can impact performance
      events: {
        // load: function() { this.showLoading(); }, // Example: show loading on initial chart load
      }
    },
    title: { text: `Trading Chart (${selectedSymbols.join(', ') || 'No Symbol Selected'} - ${timeframe})` },
    xAxis: {
      type: 'datetime',
      ordinal: false, // Important for time series data that might have gaps
      minRange: timeframeMinMs[timeframe], // Minimum zoom level
      events: { afterSetExtremes: handleAfterSetExtremes },
      plotBands: generateDayBands(visibleRange.min, visibleRange.max),
      plotLines: generateDaySeparators(visibleRange.min, visibleRange.max),
    },
    yAxis: {
      type: yScale,
      title: { text: 'Price' },
      opposite: false, // Main Y-axis on the left
      // Allow multiple y-axes if needed in future for different types of data
    },
    tooltip: {
      shared: true,
      xDateFormat: '%Y-%m-%d %H:%M:%S.%L', // Millisecond precision
      valueDecimals: 2, // Adjust as needed for price precision
    },
    legend: {
        enabled: true,
        // layout: 'vertical',
        // align: 'right',
        // verticalAlign: 'top',
        // itemHoverStyle: { color: '#FF0000'},
    },
    series: seriesData,
    boost: {
        useGPUTranslations: true,
        seriesThreshold: 1, // Apply boost if there's at least 1 series
        // Consider adjusting if performance issues arise with many series/points
    },
    plotOptions: {
      series: { // Apply to all series types
        animation: false, // Disable animation for data updates for performance
        marker: { enabled: false, states: { hover: { enabled: true, radius: 4 }}},
        // connectNulls: true, // Whether to connect points across nulls
        states: { hover: { lineWidthPlus: 1 } },
        // turboThreshold: 5000 // Default 1000, points over this skip processing like sorting
      },
      line: { // Specific to line series
        // marker: { enabled: false } // Already in series
      }
    },
    navigator: {
      enabled: true,
      adaptToUpdatedData: false, // Important: let main series drive navigator updates through setExtremes
      series: { // You might want a simplified series for navigator for performance
          // data: navigatorData (a downsampled version of one of the series)
      }
    },
    scrollbar: { enabled: true, liveRedraw: false }, // liveRedraw false can improve panning performance
    credits: { enabled: false },
    rangeSelector: {
        enabled: true, // Enable the range selector
        buttons: [{
            type: 'minute', count: 60, text: '1h'
        }, {
            type: 'minute', count: 60*3, text: '3h'
        },{
            type: 'hour', count: 8, text: '8h'
        }, {
            type: 'day', count: 1, text: '1d'
        }, {
            type: 'week', count: 1, text: '1w'
        }, {
            type: 'month', count: 1, text: '1m'
        }, {
            type: 'all', text: 'All'
        }],
        selected: 2, // Default to e.g. 8h
        inputEnabled: true
    },
    stockTools: { // Highcharts Stock Tools GUI
        gui: {
            enabled: true, // Set to false to disable
            buttons: [ /* default buttons: fullScreen, indicators, currentPriceIndicator, separator, lines, crookedLines, measure, advanced, typeChange, zoomChange, saveChart */
                'indicators', 'separator', 'zoomChange', 'fullScreen', 'toggleAnnotations', 'separator',
                'measureXY', 'fibonacci', 'elliottWave', 'pitchfork', 'separator',
                'verticalLine', 'horizontalLine', 'parallelChannel', 'separator',
                'label', 
            ],
             definitions: {
                label: {
                    className: 'highcharts-label-annotation' // Example for custom styling
                }
            }
        },
        bindingsClassName: 'tools-container' // Optional: class for styling the toolbar
    },
  };
  if (isLoading) { // Show loading indicator on chart
    // chartOptions.chart.events.load = function() { this.showLoading('Loading data...'); }; // Doesn't work well for dynamic loading
    // A better way is to use chart.showLoading() / chart.hideLoading() directly
    if (chartRef.current && chartRef.current.chart) {
        chartRef.current.chart.showLoading('Updating data...');
    }
  } else {
    if (chartRef.current && chartRef.current.chart) {
        chartRef.current.chart.hideLoading();
    }
  }


  const handleSymbolChange = (symbolClicked) => {
    setSelectedSymbols(prev =>
      prev.includes(symbolClicked)
        ? prev.filter(s => s !== symbolClicked)
        : [...prev, symbolClicked]
    );
  };

  return (
    <div ref={chartContainerRef} style={{ height: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: '#fff' }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '8px', padding: '12px', backgroundColor: '#f8f9fa', borderBottom: '1px solid #dee2e6' }}>
        {/* Symbol Selection */}
        <div style={{ fontWeight: 'bold', marginRight: '8px' }}>Symbols:</div>
        {SYMBOLS.map(sym => (
          <label key={sym} style={{ display: 'inline-flex', alignItems: 'center', cursor: 'pointer', padding: '4px 8px', border: '1px solid #ced4da', borderRadius: '4px', backgroundColor: selectedSymbols.includes(sym) ? '#007bff' : '#fff', color: selectedSymbols.includes(sym) ? '#fff' : '#000', marginRight: '4px' }}>
            <input
              type="checkbox"
              checked={selectedSymbols.includes(sym)}
              onChange={() => handleSymbolChange(sym)}
              style={{ marginRight: '4px' }}
            /> {sym}
          </label>
        ))}
        <div style={{width: '100%', height: '8px'}}></div> {/* Spacer for next row on wrap */}

        {/* Timeframe Buttons */}
        {['1ms','10ms','100ms','1s', '1min', '5min', '1h', '1d'].map(tf => (
          <button key={tf} onClick={() => setTimeframe(tf)} style={{
            background: timeframe === tf ? '#007bff' : '#e2e6ea',
            color: timeframe === tf ? '#fff' : '#000',
            border: '1px solid #ced4da', padding: '6px 10px', borderRadius: '4px', cursor: 'pointer'
          }}>{tf}</button>
        ))}
        <select value={yScale} onChange={e => setYScale(e.target.value)} style={{ padding: '7px', borderRadius: '4px', border: '1px solid #ced4da' }}>
          <option value="linear">Y-Scale: Linear</option>
          <option value="logarithmic">Y-Scale: Logarithmic</option>
        </select>
        
        {/* Column visibility checkboxes */}
        <div style={{ marginLeft: 16, display: 'flex', alignItems: 'center', gap: '8px', borderLeft: '1px solid #ccc', paddingLeft: '12px' }}>
          <span style={{fontWeight: 'bold'}}>Cols:</span>
          {COLUMN_KEYS.map((col, idx) => (
            <label key={col} style={{ display: 'flex', alignItems: 'center', fontWeight: 500, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={visibleColumns[col]}
                onChange={() =>
                  setVisibleColumns(v => ({ ...v, [col]: !v[col] }))
                }
                style={{ marginRight: 4 }}
              />
              <span style={{ color: COLORS[idx % COLORS.length] }}>{col.toUpperCase()}</span>
            </label>
          ))}
        </div>
        
        <div style={{ flexGrow: 1, minWidth: '10px' }} /> {/* Spacer */}
        <button onClick={handleZoomOut} title="Zoom Out (Mouse Wheel Down)" style={{
          padding: '6px 12px', borderRadius: '4px', border: '1px solid #ced4da', cursor: 'pointer', background: '#ffc107', color: '#000'
        }}>Zoom Out</button>
        <button onClick={toggleFullScreen} title="Toggle Fullscreen" style={{
          padding: '6px 12px', borderRadius: '4px', border: '1px solid #ced4da', cursor: 'pointer', background: '#6c757d', color: '#fff'
        }}>Fullscreen</button>
      </div>
      <div style={{ flexGrow: 1, position: 'relative' }}>
        <HighchartsReact
          highcharts={Highcharts}
          constructorType="stockChart"
          options={chartOptions}
          ref={chartRef}
          containerProps={{ style: { height: '100%' } }}
        />
      </div>
    </div>
  );
};

export default TradingChart;