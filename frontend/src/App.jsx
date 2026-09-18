import React, { useState, useEffect, useCallback, useRef } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet'
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts'
import L from 'leaflet'

const API = 'http://localhost:8000'

const CLASS_COLORS = {
  industrial: '#ef4444',
  forest: '#22c55e',
  agricultural: '#f59e0b',
  other: '#94a3b8',
  unclassified: '#64748b',
  null: '#64748b',
}

const CLASS_LABELS = {
  industrial: '🏭 Industrial',
  forest: '🌲 Forest',
  agricultural: '🌾 Agricultural',
  other: '⚪ Other',
}

function FlyTo({ coords }) {
  const map = useMap()
  useEffect(() => { if (coords) map.flyTo(coords, 10, { duration: 1.2 }) }, [coords])
  return null
}

function HeatmapLayer({ hotspots, visible }) {
  const map = useMap()
  const canvasRef = useRef(null)

  useEffect(() => {
    // Remove previous canvas
    if (canvasRef.current) {
      try {
        map.getPanes().overlayPane.removeChild(canvasRef.current)
      } catch (e) { }

      canvasRef.current = null
    }

    if (!visible || !hotspots || hotspots.length === 0) {
      return
    }

    // ==========================================
    // SETTINGS
    // ==========================================

    const GRID_SIZE_METERS = 1000

    const DENSITY_WEIGHT = 0.60
    const FRP_WEIGHT = 0.40

    const HEAT_RADIUS = 38

    // ==========================================
    // BUILD 1 KM GRID
    // ==========================================

    const grid = new Map()

    hotspots.forEach(feature => {
      try {
        const coords = feature?.geometry?.coordinates

        if (!coords || coords.length < 2) return

        const lon = Number(coords[0])
        const lat = Number(coords[1])

        if (
          !Number.isFinite(lat) ||
          !Number.isFinite(lon)
        ) {
          return
        }

        const frp = Math.max(
          0,
          Number(feature?.properties?.frp) || 0
        )

        // Lat/Lon → projected meter coordinates
        const projected = map.options.crs.project(
          L.latLng(lat, lon)
        )

        // 1000m × 1000m grid
        const gridX = Math.floor(
          projected.x / GRID_SIZE_METERS
        )

        const gridY = Math.floor(
          projected.y / GRID_SIZE_METERS
        )

        const key = `${gridX}:${gridY}`

        if (!grid.has(key)) {
          grid.set(key, {
            gridX,
            gridY,
            count: 0,
            totalFRP: 0,
            sumX: 0,
            sumY: 0,
            facilities: {}
          })
        }

        const cell = grid.get(key)

        cell.count += 1
        cell.totalFRP += frp

        const facility =
          feature?.properties?.facility

        if (facility && facility !== 'Unknown Facility') {
          cell.facilities[facility] =
            (cell.facilities[facility] || 0) + 1
        }

        cell.sumX += projected.x
        cell.sumY += projected.y

      } catch (error) {
        console.error(
          'Grid calculation error:',
          error
        )
      }
    })

    // ==========================================
    // GLOBAL MAXIMUMS
    // ==========================================

    let maxCount = 1
    let maxFRP = 1

    grid.forEach(cell => {
      maxCount = Math.max(
        maxCount,
        cell.count
      )

      maxFRP = Math.max(
        maxFRP,
        cell.totalFRP
      )
    })

    // ==========================================
    // CALCULATE CELL SCORE
    // ==========================================

    const getCellScore = cell => {
      const densityScore =
        cell.count / maxCount

      const frpScore =
        cell.totalFRP / maxFRP

      return (
        densityScore * DENSITY_WEIGHT +
        frpScore * FRP_WEIGHT
      )
    }

    // ==========================================
    // CANVAS
    // ==========================================

    const canvas = document.createElement('canvas')

    canvas.style.position = 'absolute'
    canvas.style.top = '0'
    canvas.style.left = '0'
    canvas.style.pointerEvents = 'none'
    canvas.style.zIndex = '400'
    canvas.style.opacity = '0.78'

    map.getPanes().overlayPane.appendChild(canvas)

    canvasRef.current = canvas

    // ==========================================
    // DRAW HEATMAP
    // ==========================================

    const drawHeatmap = () => {
      const size = map.getSize()

      canvas.width = size.x
      canvas.height = size.y

      const ctx = canvas.getContext('2d')

      if (!ctx) return

      ctx.clearRect(
        0,
        0,
        canvas.width,
        canvas.height
      )

      grid.forEach(cell => {

        // Geographic/projected center of cell
        const centerX =
          cell.gridX * GRID_SIZE_METERS +
          GRID_SIZE_METERS / 2

        const centerY =
          cell.gridY * GRID_SIZE_METERS +
          GRID_SIZE_METERS / 2

        // Projected meters → Lat/Lon
        const latLng =
          map.options.crs.unproject(
            L.point(centerX, centerY)
          )

        // Lat/Lon → Leaflet layer pixels
        const point =
          map.latLngToLayerPoint(latLng)

        if (
          point.x < -HEAT_RADIUS ||
          point.y < -HEAT_RADIUS ||
          point.x > size.x + HEAT_RADIUS ||
          point.y > size.y + HEAT_RADIUS
        ) {
          return
        }

        const score =
          getCellScore(cell)

        const heatRadius =
          20 + score * HEAT_RADIUS

        // ======================================
        // COLOR
        // ======================================

        const gradient =
          ctx.createRadialGradient(
            point.x,
            point.y,
            0,
            point.x,
            point.y,
            heatRadius
          )

        if (score >= 0.75) {

          gradient.addColorStop(
            0,
            'rgba(255, 0, 0, 0.95)'
          )

          gradient.addColorStop(
            0.35,
            'rgba(255, 70, 0, 0.75)'
          )

          gradient.addColorStop(
            0.70,
            'rgba(255, 170, 0, 0.35)'
          )

          gradient.addColorStop(
            1,
            'rgba(255, 200, 0, 0)'
          )

        } else if (score >= 0.50) {

          gradient.addColorStop(
            0,
            'rgba(255, 100, 0, 0.90)'
          )

          gradient.addColorStop(
            0.40,
            'rgba(255, 180, 0, 0.65)'
          )

          gradient.addColorStop(
            0.75,
            'rgba(255, 230, 0, 0.25)'
          )

          gradient.addColorStop(
            1,
            'rgba(255, 255, 0, 0)'
          )

        } else if (score >= 0.25) {

          gradient.addColorStop(
            0,
            'rgba(0, 180, 255, 0.85)'
          )

          gradient.addColorStop(
            0.45,
            'rgba(0, 220, 180, 0.50)'
          )

          gradient.addColorStop(
            0.75,
            'rgba(100, 255, 100, 0.20)'
          )

          gradient.addColorStop(
            1,
            'rgba(0, 255, 255, 0)'
          )

        } else {

          gradient.addColorStop(
            0,
            'rgba(0, 80, 255, 0.70)'
          )

          gradient.addColorStop(
            0.50,
            'rgba(0, 180, 255, 0.35)'
          )

          gradient.addColorStop(
            1,
            'rgba(0, 220, 255, 0)'
          )
        }

        ctx.beginPath()

        ctx.fillStyle = gradient

        ctx.arc(
          point.x,
          point.y,
          heatRadius,
          0,
          Math.PI * 2
        )

        ctx.fill()
      })
    }

    // ==========================================
    // CLICK CELL → SHOW STATISTICS
    // ==========================================

    const handleMapClick = e => {

      const lat = e.latlng.lat
      const lon = e.latlng.lng

      // Clicked location → projected meters
      const projected =
        map.options.crs.project(
          L.latLng(lat, lon)
        )

      // Determine clicked 1 km cell
      const gridX =
        Math.floor(
          projected.x / GRID_SIZE_METERS
        )

      const gridY =
        Math.floor(
          projected.y / GRID_SIZE_METERS
        )

      const key = `${gridX}:${gridY}`

      const cell = grid.get(key)

      // No fire detections in this cell
      if (!cell) {
        L.popup()
          .setLatLng(e.latlng)
          .setContent(`
            <div style="
              min-width:220px;
              font-family:Arial,sans-serif;
            ">
              <strong>🔥 Fire Density Cell</strong>

              <hr style="margin:8px 0">

              <div style="color:#666">
                No detected fires in this
                1 km × 1 km cell.
              </div>
            </div>
          `)
          .openOn(map)

        return
      }

      // ========================================
      // CELL STATISTICS
      // ========================================

      const score =
        getCellScore(cell)
      const facilityEntries =
        Object.entries(cell.facilities || {})

      facilityEntries.sort(
        (a, b) => b[1] - a[1]
      )

      const nearestFacility =
        facilityEntries.length > 0
          ? facilityEntries[0][0]
          : null

      const CELL_AREA_KM2 = 1

      const density =
        cell.count / CELL_AREA_KM2

      const totalFRP =
        cell.totalFRP

      const frpPerKm2 =
        totalFRP / CELL_AREA_KM2

      let riskLevel = 'LOW'

      if (score >= 0.75) {
        riskLevel = 'VERY HIGH'
      } else if (score >= 0.50) {
        riskLevel = 'HIGH'
      } else if (score >= 0.25) {
        riskLevel = 'MEDIUM'
      }

      // ========================================
      // POPUP
      // ========================================

      setTimeout(() => {
        L.popup({
          maxWidth: 300,
          closeButton: true
        })
          .setLatLng(e.latlng)
          .setContent(`
          <div style="
            min-width:250px;
            font-family:Arial,sans-serif;
          ">

            <div style="
              font-size:17px;
              font-weight:700;
              margin-bottom:10px;
            ">
              🔥 Fire Density Cell
            </div>
            ${nearestFacility ? `
              <div style="
                background:#fff7ed;
                padding:8px;
                border-radius:6px;
                margin-bottom:10px;
                border:1px solid #fed7aa;
              ">
                <strong>🏭 Nearest Plant / Facility</strong><br>
                <span style="color:#c2410c;">
                  ${nearestFacility}
                </span>
              </div>
            ` : ''}

            <div style="
              background:#f3f4f6;
              padding:8px;
              border-radius:6px;
              margin-bottom:10px;
            ">
              <strong>Grid Area</strong><br>
              1 km × 1 km
            </div>

            <div style="
              display:flex;
              justify-content:space-between;
              padding:5px 0;
              border-bottom:1px solid #eee;
            ">
              <span>Fire detections</span>
              <strong>${density}</strong>
            </div>

            <div style="
              display:flex;
              justify-content:space-between;
              padding:5px 0;
              border-bottom:1px solid #eee;
            ">
              <span>Fire density</span>
              <strong>${density} fires/km²</strong>
            </div>

            <div style="
              display:flex;
              justify-content:space-between;
              padding:5px 0;
              border-bottom:1px solid #eee;
            ">
              <span>Total FRP</span>
              <strong>${totalFRP.toFixed(2)} MW</strong>
            </div>

            <div style="
              display:flex;
              justify-content:space-between;
              padding:5px 0;
              border-bottom:1px solid #eee;
            ">
              <span>FRP intensity</span>
              <strong>${frpPerKm2.toFixed(2)} MW/km²</strong>
            </div>

            <div style="
              display:flex;
              justify-content:space-between;
              padding:5px 0;
              border-bottom:1px solid #eee;
            ">
              <span>Density weight</span>
              <strong>60%</strong>
            </div>

            <div style="
              display:flex;
              justify-content:space-between;
              padding:5px 0;
              border-bottom:1px solid #eee;
            ">
              <span>FRP weight</span>
              <strong>40%</strong>
            </div>

            <div style="
              display:flex;
              justify-content:space-between;
              padding:7px 0;
              margin-top:3px;
            ">
              <span><strong>Heat score</strong></span>
              <strong>${score.toFixed(3)}</strong>
            </div>

            <div style="
              text-align:center;
              padding:8px;
              border-radius:6px;
              background:${score >= 0.75
              ? '#fee2e2'
              : score >= 0.50
                ? '#ffedd5'
                : score >= 0.25
                  ? '#fef9c3'
                  : '#dbeafe'
            };
              color:${score >= 0.75
              ? '#dc2626'
              : score >= 0.50
                ? '#ea580c'
                : score >= 0.25
                  ? '#ca8a04'
                  : '#2563eb'
            };
              font-weight:700;
              margin-top:5px;
            ">
              ${riskLevel}
            </div>

          </div>
        `)
          .openOn(map)
      }, 100)
    }

    // ==========================================
    // INITIAL DRAW
    // ==========================================

    drawHeatmap()

    // Redraw when map changes
    map.on(
      'move zoom resize',
      drawHeatmap
    )

    // Click inspector
    map.on(
      'click',
      handleMapClick
    )

    // ==========================================
    // CLEANUP
    // ==========================================

    return () => {

      map.off(
        'move zoom resize',
        drawHeatmap
      )

      map.off(
        'click',
        handleMapClick
      )

      if (canvasRef.current) {
        try {
          map
            .getPanes()
            .overlayPane
            .removeChild(
              canvasRef.current
            )
        } catch (e) { }

        canvasRef.current = null
      }
    }

  }, [hotspots, visible, map])

  return null
}
export default function App() {
  const [dataStatus, setDataStatus] = useState(null)
  const [hotspots, setHotspots] = useState([])
  const [stats, setStats] = useState(null)
  const [trend, setTrend] = useState([])
  const [sources, setSources] = useState([])
  const [selected, setSelected] = useState(null)
  const [riskData, setRiskData] = useState(null)
  const [riskLoading, setRiskLoading] = useState(false)
  const [mlPrediction, setMlPrediction] = useState(null)
  const [mlPredictionLoading, setMlPredictionLoading] = useState(false)
  const [showMLPrediction, setShowMLPrediction] = useState(false)
  const [showPredictionEngine, setShowPredictionEngine] = useState(false)

  const [predictionForm, setPredictionForm] = useState({
    sourceName: 'Custom Sensor Site',
    latitude: '',
    longitude: '',
    activeDays: 45,
    nighttimeFraction: 0.7,
    meanFrp: 60,
    firmsType2Flag: 0.5,
  })

  const [sourceHistory, setSourceHistory] = useState(null)
  const [sourceHistoryLoading, setSourceHistoryLoading] = useState(false)
  const [selectedSource, setSelectedSource] = useState(null)
  const [sourceAnomaly, setSourceAnomaly] = useState(null)
  const [sourceAnomalyLoading, setSourceAnomalyLoading] = useState(false)
  const [explanation, setExplanation] = useState(null)
  const [explainLoading, setExplainLoading] = useState(false)
  const [showExplainability, setShowExplainability] = useState(false)

  const [flyTo, setFlyTo] = useState(null)
  const [activeClass, setActiveClass] = useState('all')
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState('trend')
  const [showHeatmap, setShowHeatmap] = useState(false)

  const [replayDate, setReplayDate] = useState(null)
  const [replayPlaying, setReplayPlaying] = useState(false)
  const [replaySpeed, setReplaySpeed] = useState(1)
  const [showReplay, setShowReplay] = useState(false)

  const fetchHotspots = useCallback(async (cls) => {
    setLoading(true)
    try {
      const url = cls && cls !== 'all' ? `${API}/hotspots?cls=${cls}` : `${API}/hotspots`
      const res = await fetch(url)
      const geo = await res.json()
      setHotspots(geo.features || [])
    } catch (e) { console.error('hotspots:', e) }
    setLoading(false)
  }, [])

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API}/stats`)
      const data = await res.json()
      setStats(data)
    } catch (e) { console.error('stats:', e) }
  }, [])

  const fetchTrend = useCallback(async () => {
    try {
      const res = await fetch(`${API}/trend`)
      const data = await res.json()
      const formatted = (data.trend || []).map(row => ({
        ...row,
        date: new Date(row.date).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })
      }))
      setTrend(formatted)
    } catch (e) { console.error('trend:', e) }
  }, [])

  const fetchSources = useCallback(async () => {
    try {
      const res = await fetch(`${API}/persistent-sources`)
      const data = await res.json()
      setSources(data.sources || [])
    } catch (e) {
      console.error('sources:', e)
    }
  }, [])
  const fetchSourceHistory = useCallback(async (facility) => {
    if (!facility) return

    setSourceHistoryLoading(true)
    setSourceHistory(null)

    try {
      const res = await fetch(
        `${API}/persistent-source-history?facility=${encodeURIComponent(facility)}`
      )

      if (!res.ok) {
        throw new Error('Failed to fetch source history')
      }

      const data = await res.json()

      setSourceHistory(data)

      setSourceAnomalyLoading(true)

      try {
        const anomalyRes = await fetch(
          `${API}/persistent-source-anomaly?facility=${encodeURIComponent(facility)}`
        )

        if (!anomalyRes.ok) {
          throw new Error('Failed to fetch source anomaly')
        }

        const anomalyData = await anomalyRes.json()
        setSourceAnomaly(anomalyData)
      } catch (error) {
        console.error('source anomaly:', error)
        setSourceAnomaly(null)
      } finally {
        setSourceAnomalyLoading(false)
      }
    } catch (error) {
      console.error('source history:', error)
      setSourceHistory(null)
    } finally {
      setSourceHistoryLoading(false)
    }
  }, [])

  const replayDates = [...new Set(
    hotspots
      .map(f => f?.properties?.date)
      .filter(Boolean)
  )].sort()

  useEffect(() => {
    if (replayDates.length > 0 && !replayDate) {
      setReplayDate(replayDates[replayDates.length - 1])
    }
  }, [replayDates.length, replayDate])
  useEffect(() => {
    if (!replayPlaying || replayDates.length === 0) {
      return
    }

    const intervalMs = 1200 / replaySpeed

    const timer = setInterval(() => {
      setReplayDate(currentDate => {
        const currentIndex = replayDates.indexOf(currentDate)

        if (currentIndex === -1) {
          return replayDates[0]
        }

        if (currentIndex >= replayDates.length - 1) {
          setReplayPlaying(false)
          return replayDates[replayDates.length - 1]
        }

        return replayDates[currentIndex + 1]
      })
    }, intervalMs)

    return () => clearInterval(timer)
  }, [replayPlaying, replaySpeed, replayDates])

  const fetchExplanation = useCallback(async (hotspotId) => {
    if (!hotspotId) return

    setExplainLoading(true)
    setExplanation(null)

    try {
      const res = await fetch(
        `${API}/hotspots/${hotspotId}/explain`
      )

      if (!res.ok) {
        throw new Error('Failed to fetch explanation')
      }

      const data = await res.json()
      setExplanation(data)
    } catch (e) {
      console.error('explainability:', e)
      setExplanation(null)
    } finally {
      setExplainLoading(false)
    }
  }, [])
  const fetchRisk = useCallback(async (hotspotId) => {
    if (!hotspotId) return

    setRiskLoading(true)
    setRiskData(null)

    try {
      const res = await fetch(`${API}/hotspots/${hotspotId}/risk`)

      if (!res.ok) {
        throw new Error('Failed to fetch risk')
      }

      const data = await res.json()
      setRiskData(data)
    } catch (error) {
      console.error('risk:', error)
      setRiskData(null)
    } finally {
      setRiskLoading(false)
    }
  }, [])
  const fetchMLPrediction = useCallback(async (hotspotId) => {
    if (!hotspotId) return

    setMlPredictionLoading(true)
    setMlPrediction(null)

    try {
      const res = await fetch(
        `${API}/ml/predict/${hotspotId}`
      )

      if (!res.ok) {
        throw new Error('Failed to fetch ML prediction')
      }

      const data = await res.json()
      setMlPrediction(data)
    } catch (error) {
      console.error('ML prediction:', error)
      setMlPrediction(null)
    } finally {
      setMlPredictionLoading(false)
    }
  }, [])
  const fetchDataStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API}/data-status`)

      if (!res.ok) {
        throw new Error('Failed to fetch data status')
      }

      const data = await res.json()
      setDataStatus(data)
    } catch (error) {
      console.error('Data status error:', error)
    }
  }, [])

  useEffect(() => {
    fetchDataStatus()

    const interval = setInterval(fetchDataStatus, 30000)

    return () => clearInterval(interval)
  }, [fetchDataStatus])

  useEffect(() => {
    fetchStats()
    fetchTrend()
    fetchSources()
    fetchHotspots('all')
  }, [])

  const handleClassFilter = (cls) => { setActiveClass(cls); fetchHotspots(cls); setSelected(null) }
  const replayHotspots =
    showReplay && replayDate
      ? hotspots.filter(
        f => f?.properties?.date === replayDate
      )
      : hotspots

  const alerts = hotspots
    .filter(f => f.properties.class === 'industrial' && f.properties.frp > 40)
    .slice(0, 10)
    .map(f => ({
      id: f.properties.id, frp: f.properties.frp,
      facility: f.properties.facility || 'Unknown Facility',
      date: f.properties.date,
      lat: f.geometry.coordinates[1], lon: f.geometry.coordinates[0],
      severity: f.properties.frp > 60 ? 'HIGH' : 'MEDIUM',
    }))

  return (
    <div
      className="fire-app"
      style={{
        display: 'flex',
        height: '100vh',
        background: '#0f1117',
        color: '#e2e8f0',
        fontFamily: 'Inter, sans-serif'
      }}
    >
      {showPredictionEngine && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 5000,
            background: 'rgba(2,6,23,0.78)',
            backdropFilter: 'blur(6px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 20,
          }}
        >
          <div
            style={{
              width: 'min(560px, 100%)',
              maxHeight: '90vh',
              overflowY: 'auto',
              background: '#0f172a',
              border: '1px solid #334155',
              borderRadius: 14,
              boxShadow: '0 24px 70px rgba(0,0,0,0.55)',
            }}
          >
            {/* Header */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '16px 18px',
                borderBottom: '1px solid #1e293b',
              }}
            >
              <div>
                <div
                  style={{
                    fontSize: 15,
                    fontWeight: 800,
                    color: '#f8fafc',
                  }}
                >
                  🧠 Interactive Prediction Engine
                </div>

                <div
                  style={{
                    marginTop: 4,
                    fontSize: 10,
                    color: '#64748b',
                    lineHeight: 1.5,
                  }}
                >
                  Test behavioral fire-source characteristics
                  using the current XGBoost prediction pipeline.
                </div>
              </div>

              <button
                onClick={() => setShowPredictionEngine(false)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#64748b',
                  fontSize: 20,
                  cursor: 'pointer',
                }}
              >
                ×
              </button>
            </div>

            {/* Test presets */}
            <div
              style={{
                padding: '14px 18px',
                borderBottom: '1px solid #1e293b',
                background: '#111827',
              }}
            >
              <div
                style={{
                  fontSize: 10,
                  color: '#64748b',
                  fontWeight: 700,
                  marginBottom: 8,
                }}
              >
                TEST PRESETS
              </div>

              <div
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: 6,
                }}
              >
                {[
                  {
                    name: 'Jamnagar Petrochem Flare',
                    latitude: 22.4707,
                    longitude: 70.0577,
                    activeDays: 45,
                    nighttimeFraction: 0.7,
                    meanFrp: 60,
                    firmsType2Flag: 0.5,
                  },
                  {
                    name: 'Mumbai High Offshore Platform Flare',
                    latitude: 19.1,
                    longitude: 71.0,
                    activeDays: 60,
                    nighttimeFraction: 0.85,
                    meanFrp: 80,
                    firmsType2Flag: 0.8,
                  },
                  {
                    name: 'Punjab Seasonal Crop Stubble Burning',
                    latitude: 30.9,
                    longitude: 75.8,
                    activeDays: 12,
                    nighttimeFraction: 0.2,
                    meanFrp: 18,
                    firmsType2Flag: 0.3,
                  },
                  {
                    name: 'Barpeta Semi-Industrial Brick Kiln',
                    latitude: 26.3,
                    longitude: 91.0,
                    activeDays: 35,
                    nighttimeFraction: 0.65,
                    meanFrp: 35,
                    firmsType2Flag: 0.6,
                  },
                ].map((preset) => (
                  <button
                    key={preset.name}
                    onClick={() => {
                      setPredictionForm({
                        sourceName: preset.name,
                        latitude: preset.latitude,
                        longitude: preset.longitude,
                        activeDays: preset.activeDays,
                        nighttimeFraction: preset.nighttimeFraction,
                        meanFrp: preset.meanFrp,
                        firmsType2Flag: preset.firmsType2Flag,
                      })
                    }}
                    style={{
                      background: '#0b2940',
                      border: '1px solid #075985',
                      color: '#38bdf8',
                      borderRadius: 6,
                      padding: '5px 8px',
                      fontSize: 10,
                      cursor: 'pointer',
                    }}
                  >
                    {preset.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Form */}
            <div
              style={{
                padding: 18,
                display: 'grid',
                gap: 12,
              }}
            >
              <div>
                <label style={{
                  display: 'block',
                  fontSize: 10,
                  color: '#94a3b8',
                  marginBottom: 5,
                }}>
                  LOCATION / SOURCE NAME
                </label>

                <input
                  value={predictionForm.sourceName}
                  onChange={e =>
                    setPredictionForm(prev => ({
                      ...prev,
                      sourceName: e.target.value,
                    }))
                  }
                  style={{
                    width: '100%',
                    boxSizing: 'border-box',
                    background: '#020617',
                    color: '#e2e8f0',
                    border: '1px solid #1e293b',
                    borderRadius: 6,
                    padding: '9px 10px',
                    outline: 'none',
                  }}
                />
              </div>

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: 10,
                }}
              >
                {[
                  ['latitude', 'LATITUDE (°N)'],
                  ['longitude', 'LONGITUDE (°E)'],
                ].map(([key, label]) => (
                  <div key={key}>
                    <label style={{
                      display: 'block',
                      fontSize: 10,
                      color: '#94a3b8',
                      marginBottom: 5,
                    }}>
                      {label}
                    </label>

                    <input
                      type="number"
                      value={predictionForm[key]}
                      onChange={e =>
                        setPredictionForm(prev => ({
                          ...prev,
                          [key]: e.target.value,
                        }))
                      }
                      style={{
                        width: '100%',
                        boxSizing: 'border-box',
                        background: '#020617',
                        color: '#e2e8f0',
                        border: '1px solid #1e293b',
                        borderRadius: 6,
                        padding: '9px 10px',
                      }}
                    />
                  </div>
                ))}
              </div>

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: 10,
                }}
              >
                <div>
                  <label style={{
                    display: 'block',
                    fontSize: 10,
                    color: '#94a3b8',
                    marginBottom: 5,
                  }}>
                    ACTIVE DAYS COUNT
                  </label>

                  <input
                    type="number"
                    value={predictionForm.activeDays}
                    onChange={e =>
                      setPredictionForm(prev => ({
                        ...prev,
                        activeDays: Number(e.target.value),
                      }))
                    }
                    style={{
                      width: '100%',
                      boxSizing: 'border-box',
                      background: '#020617',
                      color: '#e2e8f0',
                      border: '1px solid #1e293b',
                      borderRadius: 6,
                      padding: '9px 10px',
                    }}
                  />
                </div>

                <div>
                  <label style={{
                    display: 'block',
                    fontSize: 10,
                    color: '#94a3b8',
                    marginBottom: 5,
                  }}>
                    NIGHTTIME FLARING FRACTION (0–1)
                  </label>

                  <input
                    type="number"
                    min="0"
                    max="1"
                    step="0.1"
                    value={predictionForm.nighttimeFraction}
                    onChange={e =>
                      setPredictionForm(prev => ({
                        ...prev,
                        nighttimeFraction: Number(e.target.value),
                      }))
                    }
                    style={{
                      width: '100%',
                      boxSizing: 'border-box',
                      background: '#020617',
                      color: '#e2e8f0',
                      border: '1px solid #1e293b',
                      borderRadius: 6,
                      padding: '9px 10px',
                    }}
                  />
                </div>
              </div>

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: 10,
                }}
              >
                <div>
                  <label style={{
                    display: 'block',
                    fontSize: 10,
                    color: '#94a3b8',
                    marginBottom: 5,
                  }}>
                    MEAN FIRE RADIATIVE POWER (MW)
                  </label>

                  <input
                    type="number"
                    value={predictionForm.meanFrp}
                    onChange={e =>
                      setPredictionForm(prev => ({
                        ...prev,
                        meanFrp: Number(e.target.value),
                      }))
                    }
                    style={{
                      width: '100%',
                      boxSizing: 'border-box',
                      background: '#020617',
                      color: '#e2e8f0',
                      border: '1px solid #1e293b',
                      borderRadius: 6,
                      padding: '9px 10px',
                    }}
                  />
                </div>

                <div>
                  <label style={{
                    display: 'block',
                    fontSize: 10,
                    color: '#94a3b8',
                    marginBottom: 5,
                  }}>
                    FIRMS TYPE 2 FLAG (0–1)
                  </label>

                  <input
                    type="number"
                    min="0"
                    max="1"
                    step="0.1"
                    value={predictionForm.firmsType2Flag}
                    onChange={e =>
                      setPredictionForm(prev => ({
                        ...prev,
                        firmsType2Flag: Number(e.target.value),
                      }))
                    }
                    style={{
                      width: '100%',
                      boxSizing: 'border-box',
                      background: '#020617',
                      color: '#e2e8f0',
                      border: '1px solid #1e293b',
                      borderRadius: 6,
                      padding: '9px 10px',
                    }}
                  />
                </div>
              </div>

              <div
                style={{
                  marginTop: 4,
                  padding: 10,
                  background: '#111827',
                  borderRadius: 7,
                  fontSize: 10,
                  color: '#64748b',
                  lineHeight: 1.5,
                }}
              >
                Prototype inputs are mapped to the current behavioral
                XGBoost pipeline. The model is weakly supervised and
                should be treated as decision support, not ground truth.
              </div>
            </div>
            {/* ML RESULT */}
            {mlPredictionLoading ? (
              <div
                style={{
                  margin: '0 18px 14px',
                  padding: 12,
                  borderRadius: 8,
                  background: '#111827',
                  border: '1px solid #334155',
                  color: '#94a3b8',
                  fontSize: 11,
                }}
              >
                🧠 Running XGBoost prediction...
              </div>
            ) : mlPrediction && !mlPrediction.error ? (
              <div
                style={{
                  margin: '0 18px 14px',
                  padding: 14,
                  borderRadius: 10,
                  background:
                    mlPrediction.decision === 'YES'
                      ? 'rgba(59,130,246,0.10)'
                      : 'rgba(100,116,139,0.10)',
                  border:
                    mlPrediction.decision === 'YES'
                      ? '1px solid rgba(59,130,246,0.35)'
                      : '1px solid rgba(100,116,139,0.35)',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <div>
                    <div
                      style={{
                        fontSize: 10,
                        color: '#64748b',
                        fontWeight: 700,
                        letterSpacing: 0.8,
                      }}
                    >
                      🧠 ML PREDICTION
                    </div>

                    <div
                      style={{
                        marginTop: 4,
                        fontSize: 17,
                        fontWeight: 800,
                        color:
                          mlPrediction.decision === 'YES'
                            ? '#60a5fa'
                            : '#94a3b8',
                      }}
                    >
                      {mlPrediction.decision === 'YES'
                        ? 'Anthropogenic Source'
                        : 'Non-industrial / Natural'}
                    </div>
                  </div>

                  <div
                    style={{
                      fontSize: 22,
                      fontWeight: 800,
                      color: '#f8fafc',
                    }}
                  >
                    {(mlPrediction.anthropogenic_probability * 100).toFixed(1)}%
                  </div>
                </div>

                <div
                  style={{
                    marginTop: 6,
                    fontSize: 10,
                    color: '#64748b',
                  }}
                >
                  Decision threshold: 50% · XGBoost
                </div>
                {mlPrediction.source_type_prediction && (
                  <div
                    style={{
                      marginTop: 16,
                      padding: 12,
                      border: '1px solid rgba(255,255,255,0.12)',
                      borderRadius: 8,
                      background: 'rgba(255,255,255,0.03)',
                    }}
                  >
                    <div
                      style={{
                        fontSize: 10,
                        color: '#64748b',
                        fontWeight: 700,
                        marginBottom: 6,
                      }}
                    >
                      SOURCE TYPE
                    </div>

                    <div style={{ fontSize: 20, fontWeight: 800 }}>
                      {mlPrediction.source_type_prediction.predicted_source_type === 'flare' && '🔥 '}
                      {mlPrediction.source_type_prediction.predicted_source_type === 'industrial' && '🏭 '}
                      {mlPrediction.source_type_prediction.predicted_source_type === 'crop_burning' && '🌾 '}
                      {mlPrediction.source_type_prediction.predicted_source_type === 'other' && '⚪ '}

                      {mlPrediction.source_type_prediction.predicted_source_type
                        .replace('_', ' ')
                        .toUpperCase()}
                    </div>

                    <div
                      style={{
                        marginTop: 5,
                        fontSize: 10,
                        color: '#94a3b8',
                      }}
                    >
                      Confidence:{' '}
                      {(mlPrediction.source_type_prediction.confidence * 100).toFixed(2)}%
                    </div>
                  </div>
                )}
                {mlPrediction.top_features?.length > 0 && (
                  <div style={{ marginTop: 10 }}>
                    <div
                      style={{
                        fontSize: 10,
                        color: '#64748b',
                        fontWeight: 700,
                        marginBottom: 6,
                      }}
                    >
                      TOP CONTRIBUTING FEATURES
                    </div>

                    {mlPrediction.top_features
                      .slice(0, 5)
                      .map((item, index) => (
                        <div
                          key={index}
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            fontSize: 10,
                            color: '#94a3b8',
                            marginBottom: 4,
                          }}
                        >
                          <span>✓ {item.feature}</span>
                          <span style={{ color: '#64748b' }}>
                            {Number(item.importance).toFixed(3)}
                          </span>
                        </div>
                      ))}
                  </div>
                )}

                <div
                  style={{
                    marginTop: 9,
                    fontSize: 9,
                    color: '#475569',
                    lineHeight: 1.4,
                  }}
                >
                  Weakly supervised prototype. This result is decision
                  support, not ground truth.
                </div>
              </div>
            ) : mlPrediction?.error ? (
              <div
                style={{
                  margin: '0 18px 14px',
                  padding: 10,
                  borderRadius: 8,
                  background: 'rgba(239,68,68,0.08)',
                  border: '1px solid rgba(239,68,68,0.3)',
                  color: '#f87171',
                  fontSize: 10,
                }}
              >
                ML prediction failed: {mlPrediction.error}
              </div>
            ) : null}

            {/* Footer */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'flex-end',
                gap: 8,
                padding: '12px 18px',
                borderTop: '1px solid #1e293b',
              }}
            >
              <button
                onClick={() => setShowPredictionEngine(false)}
                style={{
                  background: '#172033',
                  border: '1px solid #334155',
                  color: '#94a3b8',
                  borderRadius: 7,
                  padding: '8px 14px',
                  cursor: 'pointer',
                  fontSize: 11,
                }}
              >
                Cancel
              </button>

              <button
                onClick={async () => {
                  setMlPredictionLoading(true)

                  try {
                    const res = await fetch(`${API}/ml/predict-custom`, {
                      method: 'POST',
                      headers: {
                        'Content-Type': 'application/json',
                      },
                      body: JSON.stringify(predictionForm),
                    })

                    if (!res.ok) {
                      throw new Error('Custom ML prediction failed')
                    }

                    const data = await res.json()

                    setMlPrediction(data)
                  } catch (error) {
                    console.error('custom ML prediction:', error)
                    setMlPrediction(null)
                  } finally {
                    setMlPredictionLoading(false)
                  }
                }}
                style={{
                  background: '#0ea5e9',
                  border: '1px solid #0284c7',
                  color: '#fff',
                  borderRadius: 7,
                  padding: '8px 16px',
                  cursor: 'pointer',
                  fontSize: 11,
                  fontWeight: 700,
                }}
              >
                ⚡ Run ML Model & Predict
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── MAP ── */}
      <div
        className="map-shell"
        style={{ flex: 1, position: 'relative' }}
      >
        <MapContainer center={[30.5, 75.8]} zoom={7} style={{ height: '100%', width: '100%' }} zoomControl={true}>
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; OpenStreetMap contributors'
          />
          {flyTo && <FlyTo coords={flyTo} />}
          <HeatmapLayer
            hotspots={replayHotspots}
            visible={showHeatmap}
          />

          {replayHotspots.map((f, i) => {
            const [lon, lat] = f.geometry.coordinates
            const p = f.properties
            const cls = p.class || 'unclassified'

            const color =
              cls === 'industrial'
                ? CLASS_COLORS.industrial
                : cls === 'agricultural'
                  ? CLASS_COLORS.agricultural
                  : cls === 'forest'
                    ? CLASS_COLORS.forest
                    : '#64748b'
            const isSelected = selected?.id === p.id
            return (
              <CircleMarker
                key={p.id || i}
                center={[lat, lon]}
                radius={isSelected ? 10 : p.frp > 40 ? 7 : 5}
                pathOptions={{
                  color: isSelected ? '#fff' : color,
                  fillColor: color,
                  fillOpacity: 0.85,
                  weight: isSelected ? 2 : 1
                }}
                eventHandlers={
                  showHeatmap
                    ? {}
                    : {
                      click: () => {
                        setSelected({ ...p, lat, lon })
                        setFlyTo([lat, lon])
                        setExplanation(null)
                        setShowExplainability(false)
                        fetchRisk(p.id)
                        fetchMLPrediction(p.id)
                      }
                    }
                }
              >
                {!showHeatmap && (
                  <Popup>
                    <div style={{ minWidth: 180 }}>
                      <b>{CLASS_LABELS[cls] || cls}</b><br />

                      FRP: {p.frp} MW &nbsp;|&nbsp;
                      Brightness: {p.brightness} K<br />

                      {p.facility && (
                        <>
                          <b>Facility:</b> {p.facility}<br />
                        </>
                      )}

                      {p.distance_m && (
                        <>
                          <b>Distance:</b> {Math.round(p.distance_m)}m<br />
                        </>
                      )}

                      <b>Land use:</b> {p.landuse || 'unknown'}<br />
                      <b>Date:</b> {p.date}
                    </div>
                  </Popup>
                )}
              </CircleMarker>
            )
          })}
        </MapContainer>

        {showReplay && replayDates.length > 0 && (
          <div
            style={{
              position: 'absolute',
              left: 20,
              right: 20,
              bottom: 18,
              zIndex: 1000,
              background: 'rgba(15,17,23,0.96)',
              border: '1px solid #334155',
              borderRadius: 12,
              padding: '12px 16px',
              boxShadow: '0 8px 30px rgba(0,0,0,0.35)',
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: 8,
              }}
            >
              <div>
                <div
                  style={{
                    fontSize: 11,
                    color: '#64748b',
                    fontWeight: 700,
                    letterSpacing: 0.8,
                  }}
                >
                  TEMPORAL REPLAY
                </div>

                <div
                  style={{
                    fontSize: 14,
                    color: '#f1f5f9',
                    fontWeight: 700,
                    marginTop: 2,
                  }}
                >
                  {replayDate || 'Select date'}
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <button
                  onClick={() => setReplayPlaying(p => !p)}
                  style={{
                    background: '#172033',
                    border: '1px solid #334155',
                    color: '#60a5fa',
                    borderRadius: 7,
                    padding: '6px 10px',
                    cursor: 'pointer',
                    fontSize: 12,
                    fontWeight: 700,
                  }}
                >
                  {replayPlaying ? '⏸ Pause' : '▶ Play'}
                </button>

                <select
                  value={replaySpeed}
                  onChange={e => setReplaySpeed(Number(e.target.value))}
                  style={{
                    background: '#172033',
                    color: '#e2e8f0',
                    border: '1px solid #334155',
                    borderRadius: 7,
                    padding: '6px 8px',
                    fontSize: 11,
                  }}
                >
                  <option value={0.5}>0.5×</option>
                  <option value={1}>1×</option>
                  <option value={2}>2×</option>
                  <option value={4}>4×</option>
                </select>
              </div>
            </div>

            <input
              type="range"
              min="0"
              max={Math.max(replayDates.length - 1, 0)}
              value={Math.max(replayDates.indexOf(replayDate), 0)}
              onChange={e => {
                const index = Number(e.target.value)
                setReplayDate(replayDates[index])
              }}
              style={{
                width: '100%',
                cursor: 'pointer',
              }}
            />

            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                marginTop: 5,
              }}
            >
              <span style={{ fontSize: 9, color: '#64748b' }}>
                {replayDates[0]}
              </span>

              <span
                style={{
                  fontSize: 10,
                  color: '#94a3b8',
                  fontWeight: 600,
                }}
              >
                {replayDates.length} observation days
              </span>

              <span style={{ fontSize: 9, color: '#64748b' }}>
                {replayDates[replayDates.length - 1]}
              </span>
            </div>
          </div>
        )}

        {/* Filter panel */}
        <div style={{ position: 'absolute', top: 12, left: 12, zIndex: 1000, background: 'rgba(15,17,23,0.92)', borderRadius: 10, padding: '10px 14px', border: '1px solid #1e293b' }}>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 6, fontWeight: 600, letterSpacing: 1 }}>FILTER CLASS</div>
          {['all', 'industrial', 'agricultural', 'forest', 'other'].map(c => (
            <button key={c} onClick={() => handleClassFilter(c)} style={{
              display: 'block', width: '100%', textAlign: 'left',
              background: activeClass === c ? '#1e293b' : 'transparent',
              border: 'none', color: c === 'all' ? '#e2e8f0' : CLASS_COLORS[c] || '#e2e8f0',
              padding: '4px 8px', borderRadius: 6, cursor: 'pointer',
              fontSize: 13, marginBottom: 2, fontWeight: activeClass === c ? 700 : 400,
            }}>
              {c === 'all' ? '⬤ All Classes' : CLASS_LABELS[c]}
            </button>
          ))}
          {/* Heatmap toggle */}
          <div style={{ borderTop: '1px solid #1e293b', marginTop: 6, paddingTop: 6 }}>
            <button onClick={() => setShowHeatmap(h => !h)} style={{
              display: 'block', width: '100%', textAlign: 'left',
              background: showHeatmap ? '#1e293b' : 'transparent',
              border: 'none', color: showHeatmap ? '#3b82f6' : '#64748b',
              padding: '4px 8px', borderRadius: 6, cursor: 'pointer',
              fontSize: 13, fontWeight: showHeatmap ? 700 : 400,
            }}>
              🌡️ Heatmap
            </button>
          </div>

          {/* PASTE TEMPORAL REPLAY HERE */}
          <div style={{ borderTop: '1px solid #1e293b', marginTop: 6, paddingTop: 6 }}>
            <button
              onClick={() => {
                setShowReplay(r => !r)

                if (!showReplay && replayDates.length > 0) {
                  setReplayDate(replayDates[0])
                }
              }}
              style={{
                display: 'block',
                width: '100%',
                textAlign: 'left',
                background: showReplay ? '#1e293b' : 'transparent',
                border: 'none',
                color: showReplay ? '#60a5fa' : '#64748b',
                padding: '4px 8px',
                borderRadius: 6,
                cursor: 'pointer',
                fontSize: 13,
                fontWeight: showReplay ? 700 : 400,
              }}
            >
              ⏱️ Temporal Replay
            </button>
          </div>
          <div
            style={{
              borderTop: '1px solid #1e293b',
              marginTop: 6,
              paddingTop: 6,
            }}
          >
            <button
              onClick={() => setShowPredictionEngine(true)}
              style={{
                display: 'block',
                width: '100%',
                textAlign: 'left',
                background: 'transparent',
                border: 'none',
                color: '#a78bfa',
                padding: '4px 8px',
                borderRadius: 6,
                cursor: 'pointer',
                fontSize: 13,
                fontWeight: 600,
              }}
            >
              🧠 ML Prediction Engine
            </button>
          </div>

        </div>   // line 907 — keep this


        {loading && (
          <div style={{ position: 'absolute', bottom: 12, left: '50%', transform: 'translateX(-50%)', zIndex: 1000, background: 'rgba(15,17,23,0.9)', borderRadius: 8, padding: '6px 16px', fontSize: 13, color: '#94a3b8' }}>
            Loading hotspots…
          </div>
        )}

        {/* Legend */}
        <div style={{ position: 'absolute', bottom: 12, left: 12, zIndex: 1000, background: 'rgba(15,17,23,0.92)', borderRadius: 8, padding: '8px 12px', border: '1px solid #1e293b', fontSize: 12 }}>
          {Object.entries(CLASS_LABELS).map(([k, v]) => (
            <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
              <div style={{ width: 10, height: 10, borderRadius: '50%', background: CLASS_COLORS[k] }} />
              <span style={{ color: '#94a3b8' }}>{v}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── DASHBOARD ── */}
      <div style={{ width: 380, background: '#0f1117', borderLeft: '1px solid #1e293b', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

        <div style={{ padding: '16px 20px', borderBottom: '1px solid #1e293b' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 8,
            }}
          >
            <div
              style={{
                fontSize: 15,
                fontWeight: 700,
                color: '#f1f5f9',
              }}
            >
              🔥 PS162 Fire Intelligence
            </div>

            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                padding: '4px 8px',
                borderRadius: 999,
                fontSize: 10,
                fontWeight: 700,
                whiteSpace: 'nowrap',
                background:
                  dataStatus?.mode === 'LIVE'
                    ? 'rgba(34,197,94,0.12)'
                    : dataStatus?.mode === 'DEMO'
                      ? 'rgba(245,158,11,0.12)'
                      : 'rgba(148,163,184,0.12)',
                color:
                  dataStatus?.mode === 'LIVE'
                    ? '#22c55e'
                    : dataStatus?.mode === 'DEMO'
                      ? '#f59e0b'
                      : '#94a3b8',
                border:
                  dataStatus?.mode === 'LIVE'
                    ? '1px solid rgba(34,197,94,0.3)'
                    : dataStatus?.mode === 'DEMO'
                      ? '1px solid rgba(245,158,11,0.3)'
                      : '1px solid rgba(148,163,184,0.25)',
              }}
            >
              {dataStatus?.mode === 'LIVE'
                ? '🟢 LIVE — NASA FIRMS'
                : dataStatus?.mode === 'DEMO'
                  ? '🟡 DEMO — Synthetic'
                  : '⚪ STATUS — Loading'}
            </div>
          </div>
          <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>Punjab · Haryana · Live Pipeline</div>
        </div>

        {stats && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1, background: '#1e293b' }}>
            {[
              { label: 'Total Detections', value: stats.total, color: '#e2e8f0' },
              { label: '🏭 Industrial', value: stats.class_counts.industrial || 0, color: '#ef4444' },
              { label: '🌾 Agricultural', value: stats.class_counts.agricultural || 0, color: '#f59e0b' },
              { label: '🌲 Forest', value: stats.class_counts.forest || 0, color: '#22c55e' },
            ].map(s => (
              <div key={s.label} style={{ background: '#0f1117', padding: '12px 16px' }}>
                <div style={{ fontSize: 20, fontWeight: 700, color: s.color }}>{s.value.toLocaleString()}</div>
                <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>{s.label}</div>
              </div>
            ))}
          </div>
        )}

        <div style={{ display: 'flex', borderBottom: '1px solid #1e293b' }}>
          {[['trend', 'Trend'], ['sources', 'Sources'], ['alerts', 'Alerts']].map(([key, label]) => (
            <button key={key} onClick={() => setTab(key)} style={{
              flex: 1, padding: '10px 0', background: 'none',
              border: 'none', borderBottom: tab === key ? '2px solid #3b82f6' : '2px solid transparent',
              color: tab === key ? '#3b82f6' : '#64748b',
              cursor: 'pointer', fontSize: 13, fontWeight: tab === key ? 600 : 400,
            }}>{label}</button>
          ))}
        </div>

        <div style={{ flex: 1, overflow: 'auto', padding: '16px' }}>

          {tab === 'trend' && (
            <>
              <div style={{ fontSize: 12, color: '#64748b', marginBottom: 10, fontWeight: 600 }}>30-DAY DETECTION TREND</div>
              {trend.length === 0
                ? <div style={{ color: '#475569', fontSize: 13, textAlign: 'center', paddingTop: 20 }}>Loading trend…</div>
                : (
                  <ResponsiveContainer width="100%" height={160}>
                    <LineChart data={trend} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                      <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 9 }} interval={4} />
                      <YAxis tick={{ fill: '#64748b', fontSize: 9 }} />
                      <Tooltip contentStyle={{ background: '#1e293b', border: 'none', fontSize: 11 }} />
                      <Legend wrapperStyle={{ fontSize: 10 }} />
                      <Line type="monotone" dataKey="industrial" stroke="#ef4444" dot={false} strokeWidth={2} />
                      <Line type="monotone" dataKey="agricultural" stroke="#f59e0b" dot={false} strokeWidth={2} />
                      <Line type="monotone" dataKey="forest" stroke="#22c55e" dot={false} strokeWidth={2} />
                      <Line type="monotone" dataKey="other" stroke="#94a3b8" dot={false} strokeWidth={1} />
                    </LineChart>
                  </ResponsiveContainer>
                )
              }
              <div style={{ fontSize: 12, color: '#64748b', margin: '16px 0 10px', fontWeight: 600 }}>TOTAL DETECTIONS BY CLASS</div>
              {stats && (
                <ResponsiveContainer width="100%" height={120}>
                  <BarChart data={Object.entries(stats.class_counts).map(([k, v]) => ({ name: k, count: v }))} margin={{ top: 0, right: 4, bottom: 0, left: -20 }}>
                    <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 10 }} />
                    <YAxis tick={{ fill: '#64748b', fontSize: 10 }} />
                    <Tooltip contentStyle={{ background: '#1e293b', border: 'none', fontSize: 11 }} />
                    <Bar dataKey="count" fill="#3b82f6" radius={[3, 3, 0, 0]} isAnimationActive={false} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </>
          )}

          {tab === 'sources' && (
            <>
              <div
                style={{
                  fontSize: 12,
                  color: '#64748b',
                  marginBottom: 10,
                  fontWeight: 600
                }}
              >
                TOP PERSISTENT INDUSTRIAL SOURCES
              </div>

              {sources.length === 0 && (
                <div
                  style={{
                    color: '#475569',
                    fontSize: 13,
                    textAlign: 'center',
                    paddingTop: 40
                  }}
                >
                  No persistent sources found
                </div>
              )}

              {sources.map((s, i) => {

                const tierColor =
                  s.tier === 'A'
                    ? '#22c55e'
                    : s.tier === 'B'
                      ? '#f59e0b'
                      : s.tier === 'C'
                        ? '#f97316'
                        : '#94a3b8'

                return (
                  <div
                    key={i}
                    onClick={() => {
                      setFlyTo([s.lat, s.lon])
                      setSelectedSource(s)
                      fetchSourceHistory(s.facility)
                    }}
                    style={{
                      background: '#1e293b',
                      borderRadius: 10,
                      padding: '12px',
                      marginBottom: 10,
                      cursor: 'pointer',
                      border: '1px solid #334155',
                      borderLeft: `4px solid ${tierColor}`,
                      transition: 'border-color 0.2s'
                    }}
                    onMouseEnter={e => {
                      e.currentTarget.style.borderColor = tierColor
                    }}
                    onMouseLeave={e => {
                      e.currentTarget.style.borderColor = '#334155'
                    }}
                  >
                    {/* Header */}
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'flex-start',
                        gap: 8
                      }}
                    >
                      <div
                        style={{
                          fontSize: 13,
                          fontWeight: 700,
                          color: '#f1f5f9'
                        }}
                      >
                        🏭 {s.facility || 'Industrial Source'}
                      </div>

                      <div
                        style={{
                          minWidth: 28,
                          height: 28,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          borderRadius: 7,
                          background: `${tierColor}22`,
                          border: `1px solid ${tierColor}66`,
                          color: tierColor,
                          fontSize: 13,
                          fontWeight: 800
                        }}
                      >
                        {s.tier || '—'}
                      </div>
                    </div>

                    {/* Tier + score */}
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginTop: 8
                      }}
                    >
                      <span
                        style={{
                          fontSize: 11,
                          color: tierColor,
                          fontWeight: 700
                        }}
                      >
                        Tier {s.tier || '—'} — {s.tier_label || 'Unknown'}
                      </span>

                      <span
                        style={{
                          fontSize: 11,
                          color: '#e2e8f0',
                          fontWeight: 700
                        }}
                      >
                        Score: {s.source_score?.toFixed(3) ?? '—'}
                      </span>
                    </div>

                    {/* Metrics */}
                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns: '1fr 1fr',
                        gap: 6,
                        marginTop: 10
                      }}
                    >
                      <div
                        style={{
                          background: '#0f172a',
                          borderRadius: 6,
                          padding: '7px 8px'
                        }}
                      >
                        <div style={{ fontSize: 9, color: '#64748b' }}>
                          ACTIVE DAYS
                        </div>
                        <div
                          style={{
                            fontSize: 13,
                            color: '#f1f5f9',
                            fontWeight: 700,
                            marginTop: 2
                          }}
                        >
                          {s.active_days}
                        </div>
                      </div>

                      <div
                        style={{
                          background: '#0f172a',
                          borderRadius: 6,
                          padding: '7px 8px'
                        }}
                      >
                        <div style={{ fontSize: 9, color: '#64748b' }}>
                          DETECTIONS
                        </div>
                        <div
                          style={{
                            fontSize: 13,
                            color: '#f1f5f9',
                            fontWeight: 700,
                            marginTop: 2
                          }}
                        >
                          {s.detection_count ?? '—'}
                        </div>
                      </div>

                      <div
                        style={{
                          background: '#0f172a',
                          borderRadius: 6,
                          padding: '7px 8px'
                        }}
                      >
                        <div style={{ fontSize: 9, color: '#64748b' }}>
                          AVG FRP
                        </div>
                        <div
                          style={{
                            fontSize: 13,
                            color: '#ef4444',
                            fontWeight: 700,
                            marginTop: 2
                          }}
                        >
                          {s.avg_frp} MW
                        </div>
                      </div>

                      <div
                        style={{
                          background: '#0f172a',
                          borderRadius: 6,
                          padding: '7px 8px'
                        }}
                      >
                        <div style={{ fontSize: 9, color: '#64748b' }}>
                          PEAK FRP
                        </div>
                        <div
                          style={{
                            fontSize: 13,
                            color: '#f59e0b',
                            fontWeight: 700,
                            marginTop: 2
                          }}
                        >
                          {s.max_frp} MW
                        </div>
                      </div>
                    </div>

                    {/* Explainability */}
                    {s.reasons?.length > 0 && (
                      <div style={{ marginTop: 10 }}>
                        <div
                          style={{
                            fontSize: 10,
                            color: '#64748b',
                            marginBottom: 5,
                            fontWeight: 600
                          }}
                        >
                          WHY THIS SOURCE SCORED HIGH
                        </div>

                        {s.reasons.map((reason, index) => (
                          <div
                            key={index}
                            style={{
                              fontSize: 10,
                              color: '#94a3b8',
                              marginBottom: 3
                            }}
                          >
                            ✓ {reason}
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Coordinates */}
                    <div
                      style={{
                        fontSize: 10,
                        color: '#475569',
                        marginTop: 8
                      }}
                    >
                      {s.lat?.toFixed(4)}°N, {s.lon?.toFixed(4)}°E
                    </div>
                  </div>
                )
              })}


              {/* SOURCE HISTORY */}
              {selectedSource && (
                <div
                  style={{
                    marginTop: 12,
                    background: '#111827',
                    border: '1px solid #334155',
                    borderRadius: 10,
                    padding: 12,
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: 10,
                    }}
                  >
                    <div>
                      <div
                        style={{
                          fontSize: 11,
                          color: '#64748b',
                          fontWeight: 700,
                          letterSpacing: 0.8,
                        }}
                      >
                        📈 SOURCE HISTORY
                      </div>
                      {sourceAnomalyLoading ? (
                        <div
                          style={{
                            fontSize: 10,
                            color: '#64748b',
                            marginTop: 6,
                          }}
                        >
                          Checking anomaly...
                        </div>
                      ) : sourceAnomaly && (
                        <div
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 5,
                            marginTop: 6,
                            padding: '4px 8px',
                            borderRadius: 999,
                            background:
                              sourceAnomaly.severity === 'HIGH'
                                ? 'rgba(239,68,68,0.12)'
                                : sourceAnomaly.severity === 'MEDIUM'
                                  ? 'rgba(245,158,11,0.12)'
                                  : 'rgba(34,197,94,0.12)',
                            border:
                              sourceAnomaly.severity === 'HIGH'
                                ? '1px solid rgba(239,68,68,0.35)'
                                : sourceAnomaly.severity === 'MEDIUM'
                                  ? '1px solid rgba(245,158,11,0.35)'
                                  : '1px solid rgba(34,197,94,0.35)',
                            color:
                              sourceAnomaly.severity === 'HIGH'
                                ? '#ef4444'
                                : sourceAnomaly.severity === 'MEDIUM'
                                  ? '#f59e0b'
                                  : '#22c55e',
                            fontSize: 10,
                            fontWeight: 700,
                          }}
                        >
                          {sourceAnomaly.severity === 'HIGH'
                            ? '🚨 HIGH ANOMALY'
                            : sourceAnomaly.severity === 'MEDIUM'
                              ? '⚠️ MEDIUM ANOMALY'
                              : '🟢 NORMAL'}
                        </div>
                      )}

                      <div
                        style={{
                          fontSize: 14,
                          color: '#f8fafc',
                          fontWeight: 700,
                          marginTop: 4,
                        }}
                      >
                        {selectedSource.facility}
                      </div>
                    </div>

                    <button
                      onClick={() => {
                        setSelectedSource(null)
                        setSourceHistory(null)
                      }}
                      style={{
                        background: 'transparent',
                        border: '1px solid #334155',
                        color: '#94a3b8',
                        borderRadius: 6,
                        padding: '4px 8px',
                        cursor: 'pointer',
                      }}
                    >
                      ✕
                    </button>
                  </div>

                  {sourceHistoryLoading ? (
                    <div style={{ color: '#94a3b8', fontSize: 12 }}>
                      Loading source history...
                    </div>
                  ) : sourceHistory?.history?.length > 0 ? (
                    <>
                      <div
                        style={{
                          display: 'grid',
                          gridTemplateColumns: '1fr 1fr',
                          gap: 8,
                          marginBottom: 12,
                        }}
                      >
                        <div
                          style={{
                            background: '#0f172a',
                            borderRadius: 8,
                            padding: 8,
                          }}
                        >
                          <div style={{ fontSize: 10, color: '#64748b' }}>
                            OBSERVATIONS
                          </div>
                          <div
                            style={{
                              fontSize: 18,
                              fontWeight: 700,
                              color: '#f8fafc',
                            }}
                          >
                            {sourceHistory.history.length}
                          </div>
                        </div>

                        <div
                          style={{
                            background: '#0f172a',
                            borderRadius: 8,
                            padding: 8,
                          }}
                        >
                          <div style={{ fontSize: 10, color: '#64748b' }}>
                            PEAK FRP
                          </div>
                          <div
                            style={{
                              fontSize: 18,
                              fontWeight: 700,
                              color: '#ef4444',
                            }}
                          >
                            {Math.max(
                              ...sourceHistory.history.map(h => h.max_frp || 0)
                            ).toFixed(2)} MW
                          </div>
                        </div>
                      </div>

                      <ResponsiveContainer width="100%" height={180}>
                        <LineChart data={sourceHistory.history}>
                          <XAxis
                            dataKey="date"
                            tick={{ fill: '#64748b', fontSize: 9 }}
                            tickFormatter={(value) => value?.slice(5)}
                          />

                          <YAxis
                            tick={{ fill: '#64748b', fontSize: 9 }}
                          />

                          <Tooltip
                            contentStyle={{
                              background: '#0f172a',
                              border: '1px solid #334155',
                              borderRadius: 8,
                            }}
                            labelStyle={{ color: '#f8fafc' }}
                            formatter={(value) => [`${value} MW`, 'Avg FRP']}
                          />

                          <Line
                            type="monotone"
                            dataKey="avg_frp"
                            stroke="#ef4444"
                            strokeWidth={2}
                            dot={false}
                            isAnimationActive={false}
                          />
                        </LineChart>
                      </ResponsiveContainer>

                      <div
                        style={{
                          marginTop: 8,
                          fontSize: 10,
                          color: '#64748b',
                          lineHeight: 1.4,
                        }}
                      >
                        Source behavior is derived from repeated FIRMS observations
                        associated with this facility.
                      </div>
                    </>
                  ) : (
                    <div style={{ color: '#64748b', fontSize: 12 }}>
                      No historical observations found.
                    </div>
                  )}
                </div>
              )}

            </>
          )}

          {tab === 'alerts' && (
            <>
              <div style={{ fontSize: 12, color: '#64748b', marginBottom: 10, fontWeight: 600 }}>ANOMALY ALERTS — HIGH FRP INDUSTRIAL</div>
              {alerts.length === 0 && (
                <div style={{ color: '#475569', fontSize: 13, textAlign: 'center', paddingTop: 40 }}>No high-FRP anomalies in current view</div>
              )}
              {alerts.map((a, i) => (
                <div key={i} onClick={() => {
                  const hotspot = hotspots.find(
                    f => f.properties.id === a.id
                  )

                  if (hotspot) {
                    const [lon, lat] = hotspot.geometry.coordinates

                    setSelected({
                      ...hotspot.properties,
                      lat,
                      lon
                    })

                    setFlyTo([lat, lon])
                    setExplanation(null)
                    setShowExplainability(false)
                    fetchRisk(hotspot.properties.id)
                    fetchMLPrediction(hotspot.properties.id)
                  }
                }}
                  style={{ background: '#1e293b', borderRadius: 8, padding: '10px 12px', marginBottom: 8, cursor: 'pointer', border: '1px solid #334155', borderLeft: `3px solid ${a.severity === 'HIGH' ? '#ef4444' : '#f59e0b'}` }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#f1f5f9' }}>{a.severity === 'HIGH' ? '🚨' : '⚠️'} FRP Spike</div>
                    <span style={{ fontSize: 10, color: a.severity === 'HIGH' ? '#ef4444' : '#f59e0b', fontWeight: 700 }}>{a.severity}</span>
                  </div>
                  <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 3 }}>{a.facility.slice(0, 32)}</div>
                  <div style={{ fontSize: 11, color: '#64748b', marginTop: 3 }}>FRP: {a.frp?.toFixed(1)} MW · {a.date}</div>
                </div>
              ))}
            </>
          )}
        </div>

        {selected && (
          <div style={{
            borderTop: '1px solid #1e293b',
            background: '#0a0d14',
            padding: '14px 16px',
            maxHeight: 360,
            overflow: 'auto'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: CLASS_COLORS[selected.class] || '#e2e8f0' }}>
                {CLASS_LABELS[selected.class] || selected.class} — Detail
              </div>
              <button onClick={() => {
                setSelected(null)
                setRiskData(null)
              }} style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: 16 }}>×</button>
            </div>
            {riskLoading ? (
              <div
                style={{
                  marginBottom: 10,
                  padding: 10,
                  borderRadius: 8,
                  background: '#111827',
                  border: '1px solid #1e293b',
                  color: '#64748b',
                  fontSize: 11,
                }}
              >
                Calculating response priority...
              </div>
            ) : riskData && (
              <div
                style={{
                  marginBottom: 10,
                  padding: 10,
                  borderRadius: 8,
                  background:
                    riskData.priority === 'CRITICAL'
                      ? 'rgba(239,68,68,0.10)'
                      : riskData.priority === 'HIGH'
                        ? 'rgba(245,158,11,0.10)'
                        : riskData.priority === 'MEDIUM'
                          ? 'rgba(59,130,246,0.10)'
                          : 'rgba(34,197,94,0.10)',
                  border:
                    riskData.priority === 'CRITICAL'
                      ? '1px solid rgba(239,68,68,0.35)'
                      : riskData.priority === 'HIGH'
                        ? '1px solid rgba(245,158,11,0.35)'
                        : riskData.priority === 'MEDIUM'
                          ? '1px solid rgba(59,130,246,0.35)'
                          : '1px solid rgba(34,197,94,0.35)',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <div>
                    <div
                      style={{
                        fontSize: 10,
                        color: '#64748b',
                        fontWeight: 700,
                        letterSpacing: 0.7,
                      }}
                    >
                      RESPONSE PRIORITY
                    </div>

                    <div
                      style={{
                        fontSize: 16,
                        fontWeight: 800,
                        marginTop: 3,
                        color:
                          riskData.priority === 'CRITICAL'
                            ? '#ef4444'
                            : riskData.priority === 'HIGH'
                              ? '#f59e0b'
                              : riskData.priority === 'MEDIUM'
                                ? '#3b82f6'
                                : '#22c55e',
                      }}
                    >
                      {riskData.priority === 'CRITICAL'
                        ? '🚨 CRITICAL'
                        : riskData.priority === 'HIGH'
                          ? '⚠️ HIGH'
                          : riskData.priority === 'MEDIUM'
                            ? '🟡 MEDIUM'
                            : '🟢 LOW'}
                    </div>
                  </div>

                  <div
                    style={{
                      fontSize: 20,
                      fontWeight: 800,
                      color: '#f8fafc',
                    }}
                  >
                    {riskData.risk_score}/100
                  </div>
                </div>

                {riskData.reasons?.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    {riskData.reasons.map((reason, index) => (
                      <div
                        key={index}
                        style={{
                          fontSize: 10,
                          color: '#94a3b8',
                          marginBottom: 3,
                        }}
                      >
                        ✓ {reason}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            {/* ML PREDICTION */}
            {mlPredictionLoading ? (
              <div
                style={{
                  marginBottom: 10,
                  padding: 10,
                  borderRadius: 8,
                  background: '#111827',
                  border: '1px solid #1e293b',
                  color: '#64748b',
                  fontSize: 11,
                }}
              >
                🧠 Running ML prediction...
              </div>
            ) : mlPrediction && (
              <div
                style={{
                  marginBottom: 10,
                  padding: 10,
                  borderRadius: 8,
                  background: mlPrediction.decision === 'YES'
                    ? 'rgba(59,130,246,0.10)'
                    : 'rgba(100,116,139,0.10)',
                  border: mlPrediction.decision === 'YES'
                    ? '1px solid rgba(59,130,246,0.35)'
                    : '1px solid rgba(100,116,139,0.35)',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <div>
                    <div
                      style={{
                        fontSize: 10,
                        color: '#64748b',
                        fontWeight: 700,
                        letterSpacing: 0.8,
                      }}
                    >
                      🧠 ML PREDICTION
                    </div>

                    <div
                      style={{
                        fontSize: 15,
                        fontWeight: 800,
                        color: mlPrediction.decision === 'YES'
                          ? '#60a5fa'
                          : '#94a3b8',
                        marginTop: 3,
                      }}
                    >
                      {mlPrediction.decision === 'YES'
                        ? 'Anthropogenic Source'
                        : 'Non-industrial / Natural'}
                    </div>
                  </div>

                  <div
                    style={{
                      fontSize: 19,
                      fontWeight: 800,
                      color: '#f8fafc',
                    }}
                  >
                    {(mlPrediction.anthropogenic_probability * 100).toFixed(1)}%
                  </div>
                </div>

                <div
                  style={{
                    marginTop: 6,
                    fontSize: 10,
                    color: '#64748b',
                  }}
                >
                  Threshold: {(mlPrediction.threshold * 100).toFixed(0)}%
                  {' · '}
                  XGBoost
                </div>
                {mlPrediction.source_type_prediction && (
                  <div
                    style={{
                      marginTop: 16,
                      padding: 14,
                      border: '1px solid rgba(255,255,255,0.12)',
                      borderRadius: 10,
                      background: 'rgba(255,255,255,0.03)',
                    }}
                  >
                    <div
                      style={{
                        fontSize: 10,
                        color: '#64748b',
                        fontWeight: 700,
                        marginBottom: 6,
                      }}
                    >
                      SOURCE TYPE
                    </div>

                    <div
                      style={{
                        fontSize: 22,
                        fontWeight: 800,
                      }}
                    >
                      {mlPrediction.source_type_prediction.predicted_source_type === 'flare' && '🔥 '}
                      {mlPrediction.source_type_prediction.predicted_source_type === 'industrial' && '🏭 '}
                      {mlPrediction.source_type_prediction.predicted_source_type === 'crop_burning' && '🌾 '}
                      {mlPrediction.source_type_prediction.predicted_source_type === 'other' && '⚪ '}

                      {mlPrediction.source_type_prediction.predicted_source_type
                        .replace('_', ' ')
                        .toUpperCase()}
                    </div>

                    <div
                      style={{
                        marginTop: 6,
                        fontSize: 12,
                        color: '#94a3b8',
                      }}
                    >
                      Confidence:{' '}
                      {(mlPrediction.source_type_prediction.confidence * 100).toFixed(2)}%
                    </div>
                  </div>
                )}
                {mlPrediction.top_features?.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    <div
                      style={{
                        fontSize: 10,
                        color: '#64748b',
                        fontWeight: 700,
                        marginBottom: 5,
                      }}
                    >
                      TOP CONTRIBUTING FEATURES
                    </div>

                    {mlPrediction.top_features.slice(0, 4).map((item, index) => (
                      <div
                        key={index}
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          fontSize: 10,
                          color: '#94a3b8',
                          marginBottom: 3,
                        }}
                      >
                        <span>
                          ✓ {item.feature}
                        </span>
                        <span style={{ color: '#64748b' }}>
                          {Number(item.importance).toFixed(3)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                <div
                  style={{
                    marginTop: 7,
                    fontSize: 9,
                    color: '#475569',
                    lineHeight: 1.4,
                  }}
                >
                  Weakly supervised XGBoost prototype. Prediction is
                  based on the current 29-feature training subset.
                </div>
              </div>
            )}
            <div style={{ marginBottom: 10 }}>
              <button
                onClick={() => {
                  const next = !showExplainability
                  setShowExplainability(next)

                  if (
                    next &&
                    selected?.id &&
                    !explanation &&
                    !explainLoading
                  ) {
                    fetchExplanation(selected.id)
                  }
                }}
                style={{
                  width: '100%',
                  background: '#172033',
                  border: '1px solid #334155',
                  color: '#60a5fa',
                  borderRadius: 7,
                  padding: '9px 10px',
                  cursor: 'pointer',
                  fontSize: 11,
                  fontWeight: 700,
                }}
              >
                {showExplainability
                  ? '▲ Hide AI Explainability'
                  : '🧠 Why was this classified?'}
              </button>
            </div>
            {[
              ['FRP', `${selected.frp} MW`],
              ['Brightness', `${selected.brightness} K`],
              ['Confidence', selected.confidence],
              ['Land Use', selected.landuse || 'unknown'],
              ['Facility', selected.facility || '—'],
              ['Distance', selected.distance_m ? `${Math.round(selected.distance_m)} m` : '—'],
              ['Date', selected.date],
              ['Coordinates', `${selected.lat?.toFixed(4)}°N, ${selected.lon?.toFixed(4)}°E`],
            ].map(([k, v]) => (
              <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderBottom: '1px solid #1e293b' }}>
                <span style={{ fontSize: 11, color: '#64748b' }}>{k}</span>
                <span style={{ fontSize: 11, color: '#e2e8f0', maxWidth: 200, textAlign: 'right' }}>{v}</span>
              </div>

            ))}


            {showExplainability && (
              <div
                style={{
                  marginTop: 10,
                  background: '#111827',
                  border: '1px solid #263449',
                  borderRadius: 9,
                  padding: 10
                }}
              >
                {explainLoading && (
                  <div
                    style={{
                      fontSize: 11,
                      color: '#94a3b8',
                      textAlign: 'center',
                      padding: 12
                    }}
                  >
                    🧠 Analysing classification factors...
                  </div>
                )}

                {!explainLoading && explanation && (
                  <>
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: 8
                      }}
                    >
                      <div
                        style={{
                          fontSize: 11,
                          color: '#f1f5f9',
                          fontWeight: 700
                        }}
                      >
                        WHY THIS CLASSIFICATION
                      </div>

                      <div
                        style={{
                          fontSize: 10,
                          color: '#22c55e',
                          fontWeight: 700
                        }}
                      >
                        {(explanation.confidence * 100).toFixed(2)}%
                      </div>
                    </div>

                    {explanation.factors?.map((factor, index) => {
                      const impact = Math.max(
                        0,
                        Math.min(1, Number(factor.impact) || 0)
                      )

                      return (
                        <div
                          key={index}
                          style={{
                            marginBottom: 9
                          }}
                        >
                          <div
                            style={{
                              display: 'flex',
                              justifyContent: 'space-between',
                              marginBottom: 4
                            }}
                          >
                            <span
                              style={{
                                fontSize: 10,
                                color: '#cbd5e1',
                                fontWeight: 600
                              }}
                            >
                              {factor.name}
                            </span>

                            <span
                              style={{
                                fontSize: 10,
                                color: '#64748b'
                              }}
                            >
                              {factor.value}
                            </span>
                          </div>

                          <div
                            style={{
                              height: 6,
                              background: '#1e293b',
                              borderRadius: 999,
                              overflow: 'hidden'
                            }}
                          >
                            <div
                              style={{
                                width: `${impact * 100}%`,
                                height: '100%',
                                background:
                                  impact >= 0.75
                                    ? '#ef4444'
                                    : impact >= 0.5
                                      ? '#f59e0b'
                                      : '#64748b',
                                borderRadius: 999
                              }}
                            />
                          </div>

                          <div
                            style={{
                              fontSize: 9,
                              color: '#64748b',
                              marginTop: 3
                            }}
                          >
                            {factor.reason}
                          </div>
                        </div>
                      )
                    })}

                    <div
                      style={{
                        marginTop: 10,
                        paddingTop: 8,
                        borderTop: '1px solid #1e293b'
                      }}
                    >
                      <div
                        style={{
                          fontSize: 10,
                          color: '#64748b',
                          fontWeight: 700,
                          marginBottom: 5
                        }}
                      >
                        KEY REASONS
                      </div>

                      {explanation.reasons?.map((reason, index) => (
                        <div
                          key={index}
                          style={{
                            fontSize: 10,
                            color: '#94a3b8',
                            marginBottom: 3
                          }}
                        >
                          ✓ {reason}
                        </div>
                      ))}
                    </div>

                    <div
                      style={{
                        marginTop: 8,
                        fontSize: 9,
                        lineHeight: 1.4,
                        color: '#475569'
                      }}
                    >
                      {explanation.model_note}
                    </div>
                  </>
                )}

                {!explainLoading && !explanation && (
                  <div
                    style={{
                      fontSize: 10,
                      color: '#64748b',
                      textAlign: 'center',
                      padding: 8
                    }}
                  >
                    Explainability data unavailable
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div >
  )
}