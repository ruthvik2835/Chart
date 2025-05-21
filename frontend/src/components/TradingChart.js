
import { useEffect, useState, useRef, useCallback } from "react"
import Highcharts from "highcharts/highstock"
import HighchartsReact from "highcharts-react-official"
import { ArrowLeft, ArrowRight, Maximize, ZoomOut } from "lucide-react"

const SYMBOLS = ["AAPL", "NFLX", "GOOG", "AMZN", "TSLA"]
const DEFAULT_VISIBLE_COLUMNS = {
  c1: true,
  c2: true,
  c3: true,
  c4: true,
  c5: true,
  c6: true,
}
const DEFAULT_TIMEFRAME = "1min"
const DEFAULT_YSCALE = "linear"

const oneDay = 24 * 3600 * 1000
function parseTimeGapToSeconds(timeStr) {
  const match = /^([\d.]+)\s*(ms|s|min|h|d)?$/.exec(timeStr.trim())
  if (!match) return Number.NaN
  const value = Number.parseFloat(match[1])
  const unit = match[2] || "s"
  switch (unit) {
    case "ms":
      return value / 1000
    case "s":
      return value
    case "min":
      return value * 60
    case "h":
      return value * 3600
    case "d":
      return value * oneDay
    default:
      return value
  }
}

const generateDayBands = (min, max) => {
  const bands = []
  let start = Math.floor(min / oneDay) * oneDay
  while (start < max) {
    const end = start + oneDay
    bands.push({
      from: start,
      to: end,
      color: start % (oneDay * 2) === 0 ? "rgba(200, 200, 200, 0.1)" : "rgba(150, 150, 150, 0.05)",
    })
    start = end
  }
  return bands
}

const generateDaySeparators = (min, max) => {
  const lines = []
  let time = Math.floor(min / oneDay) * oneDay
  while (time <= max) {
    lines.push({ value: time, color: "#888", width: 1, dashStyle: "ShortDash", zIndex: 5 })
    time += oneDay
  }
  return lines
}

const timeframeMinMs = {
  "1ms": 1,
  "10ms": 10,
  "100ms": 100,
  "1s": 1000,
  "1min": 60000,
  "5min": 300000,
  "1h": 3600000,
  "1d": oneDay,
}
const COLORS = ["#0ea5e9", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"]
const COLUMN_KEYS = ["c1", "c2", "c3", "c4", "c5", "c6"]

const TradingChart = () => {
  const chartRef = useRef(null)
  const [symbol, setSymbol] = useState("AMZN")
  const chartContainerRef = useRef(null)
  const [seriesData, setSeriesData] = useState([])
  const [rawSeries, setRawSeries] = useState([]) // Store raw data for toggling visibility
  const [timeframe, setTimeframe] = useState("1min")
  const [yScale, setYScale] = useState("linear")
  const [visibleRange, setVisibleRange] = useState({ min: null, max: null })
  const [loadedRange, setLoadedRange] = useState({ min: null, max: null })
  const [isLoading, setIsLoading] = useState(false)

  // New: Track which columns are visible
  const [visibleColumns, setVisibleColumns] = useState({
    c1: true,
    c2: true,
    c3: true,
    c4: true,
    c5: true,
    c6: true,
  })

  // Fetch and format all 6 series (c1-c6)
  const fetchData = useCallback(
    async (min, max) => {
      setIsLoading(true)
      try {
        const starttime = performance.now()
        const startISO = new Date(min).toISOString()
        const endISO = new Date(max).toISOString()
        console.log(startISO, endISO)
        const resp = await fetch(
          `/api/items/e/?symbol=${symbol}&time_gap=${parseTimeGapToSeconds(timeframe)}&start_date=${startISO}&end_date=${endISO}&N=1000`,
        )
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
        const data = await resp.json()

        // Prepare arrays for c1-c6
        const c1 = [],
          c2 = [],
          c3 = [],
          c4 = [],
          c5 = [],
          c6 = []
        data.forEach((item) => {
          const t = new Date(item.time).getTime()
          c1.push([t, Number(item.c1)])
          c2.push([t, Number(item.c2)])
          c3.push([t, Number(item.c3)])
          c4.push([t, Number(item.c4)])
          c5.push([t, Number(item.c5)])
          c6.push([t, Number(item.c6)])
        })
        console.log(c1.length)
        // Store raw series for toggling
        const raw = [
          { name: "c1", data: c1, type: "line", color: COLORS[0] },
          { name: "c2", data: c2, type: "line", color: COLORS[1] },
          { name: "c3", data: c3, type: "line", color: COLORS[2] },
          { name: "c4", data: c4, type: "line", color: COLORS[3] },
          { name: "c5", data: c5, type: "line", color: COLORS[4] },
          { name: "c6", data: c6, type: "line", color: COLORS[5] },
        ]
        setRawSeries(raw)
        console.log(raw.length)
        // Set seriesData with visibility
        setSeriesData(raw.map((s, i) => ({ ...s, visible: visibleColumns[s.name], boostThreshold: 1 })))
        setLoadedRange({ min, max })
        console.log("time of fetch: ", performance.now() - starttime)
      } catch (err) {
        console.error("Fetch error:", err)
      } finally {
        setIsLoading(false)
      }
      // Add visibleColumns as dependency so toggling works after fetch
    },
    [timeframe, symbol, visibleColumns],
  )

  // Update seriesData when visibleColumns or rawSeries changes
  useEffect(() => {
    setSeriesData(rawSeries.map((s) => ({ ...s, visible: visibleColumns[s.name], boostThreshold: 1 })))
  }, [visibleColumns, symbol, rawSeries])

  const handleAfterSetExtremes = (e) => {
    const { min, max, trigger } = e
    if (isLoading || trigger === "init") return
    setVisibleRange({ min, max })
    const span = max - min
    const nowspan = loadedRange.max - loadedRange.min
    if (span <= nowspan * 0.5) {
      const unit = timeframeMinMs[timeframe]
      const alignedMin = Math.floor(min / unit) * unit
      const alignedMax = Math.ceil(max / unit) * unit
      fetchData(alignedMin, alignedMax)
      return
    }
    if (trigger == "pan") {
      fetchData(min, max)
      return
    }
    if (loadedRange.min != null && loadedRange.max != null) {
      if (min >= loadedRange.min && max <= loadedRange.max) {
        console.log("Within range: skipping fetch")
        return
      }
      const newMin = Math.min(min, loadedRange.min)
      const newMax = Math.max(max, loadedRange.max)
      fetchData(newMin, newMax)
    } else {
      fetchData(min, max)
    }
  }

  function smoothZoomOut(chart, factor = 2, steps = 10, duration = 400) {
    if (!chart || !chart.xAxis || !chart.xAxis[0]) return
    const axis = chart.xAxis[0]
    const min0 = axis.min
    const max0 = axis.max
    const center = (min0 + max0) / 2
    const range0 = max0 - min0
    const range1 = range0 * factor
    const min1 = center - range1 / 2
    const max1 = center + range1 / 2

    let step = 0
    const minStep = (min1 - min0) / steps
    const maxStep = (max1 - max0) / steps

    function animateStep() {
      step++
      const newMin = min0 + minStep * step
      const newMax = max0 + maxStep * step
      axis.setExtremes(newMin, newMax, true, false, { trigger: "zoom" })
      if (step < steps) {
        setTimeout(animateStep, duration / steps)
      }
    }
    animateStep()
  }

  function instantZoomOut(chart, factor = 2) {
    if (!chart || !chart.xAxis || !chart.xAxis[0]) return
    const axis = chart.xAxis[0]
    const extremes = axis.getExtremes()
    const min0 = extremes.min
    const max0 = extremes.max
    if (min0 == null || max0 == null) return
    const center = (min0 + max0) / 2
    const range0 = max0 - min0
    const range1 = range0 * factor
    const min1 = center - range1 / 2
    const max1 = center + range1 / 2
    axis.setExtremes(min1, max1, true, false, { trigger: "zoom" })
  }

  const handleZoomOut = () => {
    const chart = chartRef.current?.chart
    instantZoomOut(chart, 2)
  }

  useEffect(() => {
    const container = chartContainerRef.current
    if (!container) return
    const onWheel = (e) => {
      if (e.ctrlKey || e.metaKey) return
      if (e.deltaY > 0) {
        handleZoomOut()
        e.preventDefault()
      }
    }
    container.addEventListener("wheel", onWheel, { passive: false })
    return () => container.removeEventListener("wheel", onWheel)
  }, []) // Removed handleZoomOut from dependency array

  const toggleFullScreen = () => {
    const el = chartContainerRef.current
    if (!document.fullscreenElement) el.requestFullscreen().catch(console.error)
    else document.exitFullscreen()
  }

  useEffect(() => {
    console.log("Initial fetch!")
    const now = Date.now()
    const initialMin = now - 60 * 60 * 1000 * 10000
    const initialMax = now
    setVisibleRange({ min: initialMin, max: initialMax })
    fetchData(initialMin, initialMax)
  }, [])
  useEffect(() => {
    console.log("Symbol Change!")
    setLoadedRange({ min: null, max: null })
    setSeriesData([])
    setRawSeries([])
    setTimeframe(DEFAULT_TIMEFRAME)
    setYScale(DEFAULT_YSCALE)
    setVisibleColumns(DEFAULT_VISIBLE_COLUMNS)
    const now = Date.now()
    const initialMin = now - 60 * 60 * 1000 * 10000
    const initialMax = now
    console.log(initialMin, initialMax)
    setVisibleRange({ min: initialMin, max: initialMax })
    fetchData(initialMin, initialMax)
  }, [symbol])

  useEffect(() => {
    const handleKeyDown = (e) => {
      const chart = chartRef.current?.chart
      if (!chart) return
      const visibleSpan = chart.xAxis[0].max - chart.xAxis[0].min
      const panAmount = visibleSpan * 0.1
      if (e.key === "ArrowLeft") {
        const newMin = Math.max(chart.xAxis[0].min - panAmount, -8640000000000000)
        const newMax = Math.max(chart.xAxis[0].max - panAmount, newMin + 1000)
        chart.xAxis[0].setExtremes(newMin, newMax, true, false, { trigger: "pan" })
      } else if (e.key === "ArrowRight") {
        const newMax = Math.min(chart.xAxis[0].max + panAmount, 8640000000000000)
        const newMin = Math.min(chart.xAxis[0].min + panAmount, newMax - 1000)
        chart.xAxis[0].setExtremes(newMin, newMax, true, false, { trigger: "pan" })
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [])

  const chartOptions = {
    chart: {
      zoomType: "x",
      panning: true,
      panKey: "shift",
      animation: false,
      backgroundColor: "transparent",
      style: {
        fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
      },
    },
    title: {
      text: `${symbol} Trading Chart (${timeframe})`,
      style: {
        color: "#1e293b",
        fontWeight: "600",
        fontSize: "18px",
      },
    },
    xAxis: {
      type: "datetime",
      ordinal: false,
      minRange: timeframeMinMs[timeframe],
      events: { afterSetExtremes: handleAfterSetExtremes },
      plotBands: visibleRange.min != null ? generateDayBands(visibleRange.min, visibleRange.max) : [],
      plotLines: visibleRange.min != null ? generateDaySeparators(visibleRange.min, visibleRange.max) : [],
      labels: {
        style: {
          color: "#64748b",
        },
      },
      lineColor: "#e2e8f0",
      tickColor: "#e2e8f0",
    },
    yAxis: {
      type: yScale,
      title: {
        text: "Price",
        style: {
          color: "#64748b",
          fontWeight: "500",
        },
      },
      labels: {
        style: {
          color: "#64748b",
        },
      },
      gridLineColor: "#e2e8f0",
    },
    tooltip: {
      shared: true,
      xDateFormat: "%Y-%m-%d %H:%M:%S",
      backgroundColor: "rgba(255, 255, 255, 0.95)",
      borderColor: "#e2e8f0",
      borderRadius: 8,
      shadow: true,
      style: {
        color: "#1e293b",
      },
    },
    dataGrouping: { enabled: false },
    series: seriesData,
    boost: {
      useGPUTranslations: true,
      seriesThreshold: 1,
    },
    plotOptions: {
      line: {
        marker: { enabled: false },
        lineWidth: 2,
      },
    },
    navigator: {
      enabled: true,
      outlineColor: "#cbd5e1",
      handles: {
        backgroundColor: "#fff",
        borderColor: "#64748b",
      },
      xAxis: {
        labels: {
          style: {
            color: "#64748b",
          },
        },
      },
    },
    scrollbar: {
      enabled: true,
      barBackgroundColor: "#cbd5e1",
      barBorderColor: "#94a3b8",
      buttonBackgroundColor: "#fff",
      buttonBorderColor: "#94a3b8",
      trackBackgroundColor: "#f1f5f9",
      trackBorderColor: "#e2e8f0",
    },
    credits: { enabled: false },
    navigation: {
      buttonOptions: {
        theme: {
          fill: "#fff",
          stroke: "#e2e8f0",
          states: {
            hover: {
              fill: "#f1f5f9",
            },
            select: {
              fill: "#e2e8f0",
            },
          },
        },
      },
      stockTools: {
        gui: {
          enabled: true,
          buttons: [
            "fullScreen",
            "indicators",
            "separator",
            "crookedLines",
            "measure",
            "typeChange",
            "zoomChange",
            "annotations",
            "verticalLabels",
            "flags",
            "fibonacci",
            "toggleAnnotations",
          ],
        },
      },
    },
  }

  return (
    <div ref={chartContainerRef} className="h-screen flex flex-col bg-white">
      {/* Header Controls */}
      <div className="flex flex-wrap items-center gap-2 p-3 bg-gray-50 border-b border-gray-200 shadow-sm">
        {/* Timeframe Buttons */}
        <div className="flex items-center gap-1.5">
          {["1ms", "10ms", "100ms", "1s", "1min", "5min", "1h", "1d"].map((tf) => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                timeframe === tf ? "bg-sky-500 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              {tf}
            </button>
          ))}
        </div>

        {/* Y-Scale Selector */}
        <select
          value={yScale}
          onChange={(e) => setYScale(e.target.value)}
          className="px-3 py-1.5 text-sm bg-white border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500"
        >
          <option value="linear">Y-Scale: Linear</option>
          <option value="logarithmic">Y-Scale: Logarithmic</option>
        </select>

        {/* Column Visibility Toggles */}
        <div className="flex flex-wrap items-center gap-2 ml-2 p-1.5 bg-white border border-gray-200 rounded-md">
          {COLUMN_KEYS.map((col, idx) => (
            <label key={col} className="flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={visibleColumns[col]}
                onChange={() => setVisibleColumns((v) => ({ ...v, [col]: !v[col] }))}
                className="w-3.5 h-3.5 mr-1.5 rounded border-gray-300 text-sky-600 focus:ring-sky-500"
              />
              <span className="text-xs font-medium" style={{ color: COLORS[idx] }}>
                {col}
              </span>
            </label>
          ))}
        </div>

        {/* Symbol Selector */}
        <select
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          className="px-3 py-1.5 text-sm bg-white border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500"
        >
          {SYMBOLS.map((sym) => (
            <option value={sym} key={sym}>
              {sym}
            </option>
          ))}
        </select>

        {/* Loading Indicator */}
        {isLoading && (
          <div className="ml-2 flex items-center">
            <div className="animate-spin h-4 w-4 border-2 border-sky-500 border-t-transparent rounded-full mr-2"></div>
            <span className="text-xs text-gray-600">Loading data...</span>
          </div>
        )}

        <div className="flex-grow"></div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleZoomOut}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-amber-500 text-white rounded-md hover:bg-amber-600 transition-colors"
          >
            <ZoomOut className="w-4 h-4" />
            <span>Zoom Out</span>
          </button>
          <button
            onClick={toggleFullScreen}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-gray-700 text-white rounded-md hover:bg-gray-800 transition-colors"
          >
            <Maximize className="w-4 h-4" />
            <span>Fullscreen</span>
          </button>
        </div>
      </div>

      {/* Chart Container */}
      <div className="relative flex-grow">
        {/* Navigation Hints */}
        <div className="absolute top-4 right-4 z-10 flex items-center gap-2 bg-white/80 backdrop-blur-sm px-3 py-1.5 rounded-md shadow-sm border border-gray-200 text-xs text-gray-600">
          <span className="flex items-center gap-1">
            <ArrowLeft className="w-3.5 h-3.5" /> <ArrowRight className="w-3.5 h-3.5" />
            <span>to navigate</span>
          </span>
          <span className="text-gray-300">|</span>
          <span>Scroll to zoom</span>
        </div>

        {/* Highcharts Component */}
        <HighchartsReact
          highcharts={Highcharts}
          constructorType="stockChart"
          options={chartOptions}
          ref={chartRef}
          containerProps={{ className: "w-full h-full" }}
        />
      </div>
    </div>
  )
}

export default TradingChart
