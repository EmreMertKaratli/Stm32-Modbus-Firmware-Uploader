import type { LogEntry } from '../services/types'

interface Props {
  logs: LogEntry[]
}

export default function LogConsole({ logs }: Props) {
  return (
    <div className="log-console">
      <h3>Logs</h3>
      <div className="log-entries">
        {logs.map((log, i) => (
          <div key={i} className={`log-entry ${log.level.toLowerCase()}`}>
            [{log.level}] {log.message}
          </div>
        ))}
      </div>
    </div>
  )
}