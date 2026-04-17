const API_BASE = 'http://localhost:8000/api'
const WS_URL = 'ws://localhost:8000/ws'

export { API_BASE, WS_URL }
export const getPorts = () => fetch(`${API_BASE}/ports`).then(r => r.json())
export const scanDevices = (port: string, baudrate: number) =>
  fetch(`${API_BASE}/scan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ port, baudrate })
  }).then(r => r.json())

export const initUpload = async (file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${API_BASE}/upload/init`, {
    method: 'POST',
    body: formData
  })
  return res.json()
}

export const startUpload = (port: string, baudrate: number, deviceIds: number[]) =>
  fetch(`${API_BASE}/upload/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ port, baudrate, device_ids: deviceIds })
  }).then(r => r.json())