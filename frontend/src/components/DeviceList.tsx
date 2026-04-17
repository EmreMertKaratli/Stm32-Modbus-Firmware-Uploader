import type { Device } from '../services/types'

interface Props {
  devices: Device[]
  selected: number[]
  onSelect: (ids: number[]) => void
}

export default function DeviceList({ devices, selected, onSelect }: Props) {
  const toggle = (id: number) => {
    if (selected.includes(id)) {
      onSelect(selected.filter(d => d !== id))
    } else {
      onSelect([...selected, id])
    }
  }

  return (
    <div className="device-list">
      <h3>Devices</h3>
      {devices.length === 0 ? (
        <p>No devices found</p>
      ) : (
        <ul>
          {devices.map(d => (
            <li key={d.slave_id}>
              <label>
                <input
                  type="checkbox"
                  checked={selected.includes(d.slave_id)}
                  onChange={() => toggle(d.slave_id)}
                />
                Device {d.slave_id}
              </label>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}