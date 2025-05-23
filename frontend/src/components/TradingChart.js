import React, { useEffect, useState, useRef, useCallback } from 'react';
import Highcharts from 'highcharts/highstock';
import HighchartsReact from 'highcharts-react-official';

const SYMBOLS = ['AAPL', 'NFLX', 'GOOG', 'AMZN', 'TSLA'];
const DEFAULT_VISIBLE_COLUMNS = {
  c1: true, c2: true, c3: true, c4: true, c5: true, c6: true
};
const DEFAULT_TIMEFRAME = '1min';
const DEFAULT_YSCALE = 'linear';



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
    case 'd': return value * oneDay;
    default: return value;
  }
}

const generateDayBands = (min, max) => {
  const bands = [];
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
  let time = Math.floor(min / oneDay) * oneDay;
  while (time <= max) {
    lines.push({ value: time, color: '#888', width: 1, dashStyle: 'ShortDash', zIndex: 5 });
    time += oneDay;
  }
  return lines;
};

const timeframeMinMs = { '1ms':1 , '10ms':10, '100ms':100,'1s': 1000, '1min': 60000, '5min': 300000, '1h': 3600000, '1d': oneDay };
const COLORS = ['#007bff', '#28a745', '#ffc107', '#dc3545', '#6f42c1', '#17a2b8'];
const COLUMN_KEYS = ['c1', 'c2', 'c3', 'c4', 'c5', 'c6'];

const TradingChart = () => {
  const chartRef = useRef(null);
  const [symbol, setSymbol] = useState('AMZN');
  const chartContainerRef = useRef(null);
  const [seriesData, setSeriesData] = useState([]);
  const [rawSeries, setRawSeries] = useState([]); // Store raw data for toggling visibility
  const [timeframe, setTimeframe] = useState('1min');
  const [yScale, setYScale] = useState('linear');
  const [visibleRange, setVisibleRange] = useState({ min: null, max: null });
  const [loadedRange, setLoadedRange] = useState({ min: null, max: null });
  const [isLoading, setIsLoading] = useState(false);

  // New: Track which columns are visible
  const [visibleColumns, setVisibleColumns] = useState({
    c1: true, c2: true, c3: true, c4: true, c5: true, c6: true
  });

  // Fetch and format all 6 series (c1-c6)
  const fetchData = useCallback(async (min, max) => {
    setIsLoading(true);
    try {
      const starttime=performance.now();
      const d = max-min;
      const startISO = new Date(min-d).toISOString();
      const endISO = new Date(max+d).toISOString();
      console.log(startISO,endISO);
      const resp = await fetch(
        `/api/items/e/?symbol=${symbol}&time_gap=${parseTimeGapToSeconds(timeframe)}&start_date=${startISO}&end_date=${endISO}&N=5000`
      );
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();

      // Prepare arrays for c1-c6
      const c1 = [], c2 = [], c3 = [], c4 = [], c5 = [], c6 = [];
      data.forEach(item => {
        const t = new Date(item.time).getTime();
        c1.push([t, Number(item.c1)]);
        c2.push([t, Number(item.c2)]);
        c3.push([t, Number(item.c3)]);
        c4.push([t, Number(item.c4)]);
        c5.push([t, Number(item.c5)]);
        c6.push([t, Number(item.c6)]);
      });
      // console.log(ArrayBuffer.byteLength(c1));
      // Store raw series for toggling
      const raw = [
        { name: 'c1', data: c1, type: 'line', color: COLORS[0] },
        { name: 'c2', data: c2, type: 'line', color: COLORS[1] },
        { name: 'c3', data: c3, type: 'line', color: COLORS[2] },
        { name: 'c4', data: c4, type: 'line', color: COLORS[3] },
        { name: 'c5', data: c5, type: 'line', color: COLORS[4] },
        { name: 'c6', data: c6, type: 'line', color: COLORS[5] }
      ];
      setRawSeries(raw);
      console.log(c1.length);
      // Set seriesData with visibility
      setSeriesData(
        raw.map((s, i) => ({ ...s, visible: visibleColumns[s.name],boostThreshold:1 }))
      );
      // console.log(min,max);
      setLoadedRange({ min: min-d, max: max+d });
      console.log("time of fetch: " ,performance.now()-starttime)
    } catch (err) {
      console.error('Fetch error:', err);
    } finally {
      setIsLoading(false);
    }
  // Add visibleColumns as dependency so toggling works after fetch
  }, [timeframe, symbol, visibleColumns]);

  // Update seriesData when visibleColumns or rawSeries changes
  useEffect(() => {
    setSeriesData(
      rawSeries.map(s => ({ ...s, visible: visibleColumns[s.name],boostThreshold:1 }))
    );
  }, [visibleColumns,symbol, rawSeries]);

  const handleAfterSetExtremes = e => {
    const { min, max, trigger } = e;
    if (isLoading || trigger === 'init') return;
    setVisibleRange({ min :min, max: max });
    // console.log(trigger);
    const span = max - min;
    const nowspan = loadedRange.max - loadedRange.min;
    if (trigger!='zoomout'&&span <= nowspan * 0.3) {
      console.log(trigger);
      const unit = timeframeMinMs[timeframe];
      const alignedMin = Math.floor(min / unit) * unit;
      const alignedMax = Math.ceil(max / unit) * unit;
      fetchData(alignedMin, alignedMax);
      return;
    }
    console.log("hello",trigger);
    if(trigger=="pan"){
      console.log("arrow cause pan trigger");
      const diff= Math.floor((loadedRange.max-loadedRange.min)/5);
      if((max>=loadedRange.max-diff)|| (min<=loadedRange.min+diff)){
       const unit = timeframeMinMs[timeframe];
        const alignedMin = Math.floor(min / unit) * unit;
        const alignedMax = Math.ceil(max / unit) * unit;
        fetchData(alignedMin, alignedMax);
      }      
      return;
    }
    if(trigger=='zoomout'){
      console.log("wheel cause zoomout");
      const diff= Math.floor((loadedRange.max-loadedRange.min)/5);
      console.log(min,max, diff, loadedRange.min, loadedRange.max);
      if((max>=loadedRange.max-diff)|| (min<=loadedRange.min+diff)){
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
    if(trigger==undefined){
      console.log("handling undefined trigger");    
      return;
    }
    console.log(trigger);
    if (loadedRange.min != null && loadedRange.max != null)  {
      if (min >= loadedRange.min && max <= loadedRange.max) {
        console.log("Within range: skipping fetch");
        return;
      }
      const newMin = Math.min(min, loadedRange.min);
      const newMax = Math.max(max, loadedRange.max);
      const unit = timeframeMinMs[timeframe];
      fetchData(newMin, newMax);
    } else {
      fetchData(min, max);
    }
  };

  function instantZoomOut(chart, factor = 1.2) {
    if (!chart || !chart.xAxis || !chart.xAxis[0]) return;
    const min0 = chart.xAxis[0].min;
    const max0 = chart.xAxis[0].max;
    if (min0 == null || max0 == null) return;
    const center = Math.floor((min0 + max0) / 2);
    const range0 = max0 - min0;
    const range1 = range0 * factor;
    const newMin = center - Math.ceil(range1 / 2);
    const newMax = center + Math.ceil(range1 / 2);
   chart.xAxis[0].setExtremes(
      newMin,
      newMax,
      true,
      true,
      { trigger: 'zoomout' }
    );
  }

  const handleZoomOut = () => {
    const chart = chartRef.current?.chart;
    instantZoomOut(chart);
  };

  useEffect(() => {
    const container = chartContainerRef.current;
    if (!container) return;
    const onWheel = (e) => {
      if (e.ctrlKey || e.metaKey) return;
      if (e.deltaY > 0) {
        handleZoomOut();
        e.preventDefault();
      }
    };
    container.addEventListener('wheel', onWheel, { passive: false });
    return () => container.removeEventListener('wheel', onWheel);
  }, [handleZoomOut]);

  const toggleFullScreen = () => {
    const el = chartContainerRef.current;
    if (!document.fullscreenElement) el.requestFullscreen().catch(console.error);
    else document.exitFullscreen();
  };

  useEffect(() => {
    console.log("Initial fetch!")
    const now = Date.now();
    const initialMin = now - 60 * 60 * 1000 * 10000;
    const initialMax = now;
    setVisibleRange({ min: initialMin, max: initialMax });
    fetchData(initialMin, initialMax);
  }, []);
  useEffect(() => {
    console.log("Symbol Change!")
    setLoadedRange({ min: null, max: null });
    setSeriesData([]);
    setRawSeries([]);
    setTimeframe(DEFAULT_TIMEFRAME);
    setYScale(DEFAULT_YSCALE);
    setVisibleColumns(DEFAULT_VISIBLE_COLUMNS);
    const now = Date.now();
    const initialMin = now - 60 * 60 * 1000 * 10000;
    const initialMax = now;
    console.log(initialMin,initialMax)
    setVisibleRange({ min: initialMin, max: initialMax });
    fetchData(initialMin, initialMax);
  }, [symbol]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      const chart = chartRef.current?.chart;
      if (!chart) return;
      console.log("loaded range", loadedRange);
      console.log("arrowpressed");
      const visibleSpan = chart.xAxis[0].max - chart.xAxis[0].min;
      const panAmount = visibleSpan * 0.05;
      if (e.key === 'ArrowLeft') {
        const newMin = Math.max(chart.xAxis[0].min - panAmount, -8640000000000000);
        const newMax = Math.max(chart.xAxis[0].max - panAmount, newMin + 1000);
         chart.xAxis[0].setExtremes(
          newMin,
          newMax,
          true,
          false,
          { trigger: 'pan' }
        );
      } else if (e.key === 'ArrowRight') {
        const newMax = Math.min(chart.xAxis[0].max + panAmount, 8640000000000000);
        const newMin = Math.min(chart.xAxis[0].min + panAmount, newMax - 1000);
        chart.xAxis[0].setExtremes(
          newMin,
          newMax,
          true,
          false,
          { trigger: 'pan' }
        );      
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const chartOptions = {
    chart: { zoomType: 'x', panning: true, panKey: 'shift', animation: false },
    title: { text: `Trading Chart (${timeframe})` },
    xAxis: {
      type: 'datetime',
      ordinal: false,
      minRange: timeframeMinMs[timeframe],
      events: { afterSetExtremes: handleAfterSetExtremes },
      plotBands: visibleRange.min != null ? generateDayBands(visibleRange.min, visibleRange.max) : [],
      plotLines: visibleRange.min != null ? generateDaySeparators(visibleRange.min, visibleRange.max) : []
    },
    yAxis: { type: yScale, title: { text: 'Price' } },
    tooltip: { shared: true, xDateFormat: '%Y-%m-%d %H:%M:%S' },
    dataGrouping:{enabled:false},
    // console.log(seriesData);
    series: seriesData,
    boost: {
        useGPUTranslations: true,
        // Chart-level boost when there are more than 5 series in the chart
        seriesThreshold: 1
    },
    plotOptions: {
      line: { marker: { enabled: false } }
    },
    navigator: { enabled: true },
    scrollbar: { enabled: true },
    credits: { enabled: false },
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
    },
    
    
  };

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
