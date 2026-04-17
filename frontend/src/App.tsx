import { useState, useEffect, useRef } from 'react'
import { API_BASE, WS_URL } from './services/api'
import type { Device, UploadProgress } from './services/types'
import DeviceList from './components/DeviceList'
import UploadPanel from './components/UploadPanel'
import LogConsole from './components/LogConsole'
import './App.css'

function App() {
  const [ports, setPorts] = useState<string[]>([])
  const [selectedPort, setSelectedPort] = useState('')
  const [baudrate, setBaudrate] = useState('115200')
  const [devices, setDevices] = useState<Device[]>([])
  const [selectedDevices, setSelectedDevices] = useState<number[]>([])
  const [firmwareFile, setFirmwareFile] = useState<string | null>(null)
  const [firmwareInfo, setFirmwareInfo] = useState<{size: number, chunks: number, crc: string} | null>(null)
  const [progress, setProgress] = useState<UploadProgress | null>(null)
  const [logs, setLogs] = useState<{message: string, level: string}[]>([])
  const [uploading, setUploading] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    fetchPorts()
    connectWebSocket()
    return () => wsRef.current?.close()
  }, [])

  const connectWebSocket = () => {
    const ws = new WebSocket(WS_URL)
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data)
      if (data.type === 'log') {
        setLogs(prev => [...prev, { message: data.message, level: data.level }])
      } else if (data.type === 'progress') {
        setProgress(data)
      }
    }
    wsRef.current = ws
  }

  const fetchPorts = async () => {
    try {
      const res = await fetch(`${API_BASE}/ports`)
      const data = await res.json()
      setPorts(data)
      if (data.length && !selectedPort) setSelectedPort(data[0])
    } catch (e) { console.error(e) }
  }

  const scanDevices = async () => {
    if (!selectedPort) return
    addLog('Scanning devices...', 'INFO')
    try {
      const res = await fetch(`${API_BASE}/scan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ port: selectedPort, baudrate: parseInt(baudrate) })
      })
      const data = await res.json()
      setDevices(data)
      setSelectedDevices(data.map((d: Device) => d.slave_id))
      addLog(`Found ${data.length} device(s)`, 'INFO')
    } catch (e) { addLog(`Scan failed: ${e}`, 'ERROR') }
  }

  const uploadFirmware = async () => {
    if (!firmwareFile || !selectedDevices.length) return
    setUploading(true)
    addLog('Starting upload...', 'INFO')
    try {
      const res = await fetch(`${API_BASE}/upload/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          port: selectedPort,
          baudrate: parseInt(baudrate),
          device_ids: selectedDevices
        })
      })
      const data = await res.json()
      addLog(`Upload complete: ${JSON.stringify(data.results)}`, 'INFO')
    } catch (e) { addLog(`Upload failed: ${e}`, 'ERROR') }
    setUploading(false)
  }

  const addLog = (message: string, level: string) => {
    setLogs(prev => [...prev, { message, level }])
  }

  return (
    <div className="app">
      <header><h1>STM32 OTA Firmware Updater</h1></header>
      <main>
        <div className="panel">
          <div className="controls">
            <select value={selectedPort} onChange={e => setSelectedPort(e.target.value)}>
              {ports.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
            <button onClick={fetchPorts}>Refresh</button>
            <select value={baudrate} onChange={e => setBaudrate(e.target.value)}>
              <option>9600</option><option>19200</option><option>38400</option>
              <option>57600</option><option>115200</option>
              <option>230400</option><option>460800</option><option>921600</option>
            </select>
            <button onClick={scanDevices}>Scan</button>
          </div>
          <DeviceList devices={devices} selected={selectedDevices} onSelect={setSelectedDevices} />
          <UploadPanel
            file={firmwareFile}
            onFileChange={(f, info) => { setFirmwareFile(f); setFirmwareInfo(info) }}
          />
          {firmwareInfo && <div className="firmware-info">
            Size: {firmwareInfo.size} bytes | Chunks: {firmwareInfo.chunks} | CRC: {firmwareInfo.crc}
          </div>}
          <div className="progress-section">
            <progress value={progress?.percent || 0} max={100} />
            <span>Speed: {progress?.speed_kb_s?.toFixed(2) || 0} KB/s</span>
          </div>
          <button onClick={uploadFirmware} disabled={uploading || !firmwareFile || !selectedDevices.length}>
            {uploading ? 'Uploading...' : 'Upload'}
          </button>
        </div>
        <LogConsole logs={logs} />
      </main>
    </div>
  )
}

export default App