# STM32 Modbus RTU OTA Firmware Uploader

A desktop application for over-the-air (OTA) firmware updates to STM32 microcontrollers via Modbus RTU over RS485.

## Features

- **Device Discovery**: Auto-scan Modbus devices (IDs 1-20)
- **Multi-Device Upload**: Upload firmware to multiple devices simultaneously
- **Dual Bank Support**: A/B slot layout (APP_SLOT_A / APP_SLOT_B)
- **Chunked Transfer**: 128-byte chunks with progress tracking
- **Resume Support**: Persists upload state for resume after interruption
- **CRC32 Verification**: Validates firmware integrity
- **Retry Mechanism**: 3 retries per Modbus frame
- **Real-time Speed**: KB/s transfer rate display
- **Thread-safe**: Background worker threads for non-blocking UI

## Hardware Requirements

- STM32F103 (or similar) device with Modbus RTU bootloader
- RS485 USB adapter (e.g., FTDI, CH340)
- Supported baudrates: 9600 - 921600

## STM32 Register Map

| Register | Name | Description |
|----------|------|------------|
| 0x0000 | CMD | Command (1=bootloader, 2=write, 3=verify, 4=complete) |
| 0x0001 | ADDR_HIGH | Flash address high 16 bits |
| 0x0002 | ADDR_LOW | Flash address low 16 bits |
| 0x0003 | LENGTH | Chunk length |
| 0x0010 | DATA | Data buffer (64 registers = 128 bytes) |
| 0x0020 | CRC_LOW | CRC32 low 16 bits |
| 0x0021 | CRC_HIGH | CRC32 high 16 bits |
| 0x0030 | RECOVERY | Recovery flag (0xA5A5) |

## Installation

### 1. Clone or extract the project

### 2. Create virtual environment (recommended)

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. Install dependencies

```bash
.venv\Scripts\python.exe -m pip install PySide6 minimalmodbus pyserial
```

### 4. Run

```bash
.venv\Scripts\python.exe main.py
```

## Usage

1. **Connect RS485 adapter** to PC
2. **Select COM port** from dropdown
3. **Choose baudrate** (default: 115200)
4. **Click "Scan Devices"** to discover Modbus devices
5. **Select devices** from the list (checkboxes)
6. **Click "Select Firmware"** to load .bin or .hex file
7. **Click "Upload"** to begin firmware update

## Project Structure

```
.
├── main.py                 # Entry point
├── ui/
│   └── main_window.py      # PySide6 GUI
├── workers/
│   ├── scan_worker.py   # Device scanning thread
│   └── upload_worker.py # Firmware upload thread
├── signals/
│   └── app_signals.py  # Qt signals
├── device/
│   └── device_manager.py
├── protocol/
│   └── modbus_client.py
├── core/
│   ├── config.py       # Constants
│   └── state_manager.py
└── utils/
    ├── logger.py
    ├── crc.py
    ├── hex_parser.py
    └── config.py
```

## Configuration

Edit `utils/config.py` to customize:

- `CHUNK_SIZE`: Transfer chunk size (default: 128)
- `STATE_FILE`: Resume state file (default: upload_state.json)
- `APP_SLOT_A/B`: Flash memory addresses
- `scan_range_start/end`: Modbus ID scan range (1-20)

## Troubleshooting

### "No port selected"
- Ensure RS485 adapter is connected
- Click "Refresh" to rescan COM ports

### "Scan finds no devices"
- Verify wiring (A-A, B-B for RS485)
- Check baudrate matches device
- Ensure device has Modbus bootloader

### "Upload failed"
- Check device power
- Verify correct .bin/.hex file
- Try lower baudrate

### UI freezes during scan
- This is normal; scan runs in background thread
- Use "Stop Scan" to cancel

## License

MIT