import { useState } from 'react'
import { initUpload } from '../services/api'
import type { FirmwareInfo } from '../services/types'

interface Props {
  file: string | null
  onFileChange: (file: string, info: FirmwareInfo) => void
}

export default function UploadPanel({ file, onFileChange }: Props) {
  const [loading, setLoading] = useState(false)

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0]
    if (!selected) return

    setLoading(true)
    try {
      const info = await initUpload(selected)
      onFileChange(selected.name, info)
    } catch (err) {
      console.error('Upload init failed:', err)
    }
    setLoading(false)
  }

  return (
    <div className="upload-panel">
      <h3>Firmware</h3>
      <input type="file" accept=".bin,.hex" onChange={handleFile} disabled={loading} />
      {file && <p>Selected: {file}</p>}
    </div>
  )
}