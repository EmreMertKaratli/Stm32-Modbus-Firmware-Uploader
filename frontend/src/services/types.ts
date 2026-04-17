export interface Device {
  slave_id: number
  port: string
  baudrate: number
}

export interface UploadProgress {
  device_id: number
  bytes_written: number
  total_bytes: number
  speed_kb_s: number
  percent: number
}

export interface LogEntry {
  message: string
  level: string
  timestamp?: string
}

export interface FirmwareInfo {
  size: number
  chunks: number
  crc: string
}