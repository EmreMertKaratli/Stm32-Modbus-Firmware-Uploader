from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
    QLabel, QTextEdit, QProgressBar, QComboBox, QListWidget,
    QListWidgetItem
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject

from utils.config import Config
from utils.logger import get_logger
from device import DeviceManager
from workers import ScanWorker, UploadWorker
from signals import AppSignals


class MainWindow(QWidget):
    log_message = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("STM32 Modbus OTA Uploader")
        self.setMinimumWidth(700)

        self._config = Config()
        self._logger = get_logger()
        self._signals = AppSignals()

        self._port = None
        self._baudrate = 115200
        self._file_path = None
        self._firmware_data = None
        self._crc = None

        self._scan_worker: ScanWorker = None
        self._upload_worker: UploadWorker = None
        self._scanning = False
        self._uploading = False
        self._found_devices = []

        self._init_ui()
        self._init_signals()
        self._start_timers()

    def _init_ui(self):
        layout = QVBoxLayout()

        port_layout = QHBoxLayout()
        self.port_combo = QComboBox()
        self._refresh_ports()
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self._refresh_ports)
        port_layout.addWidget(self.port_combo)
        port_layout.addWidget(self.btn_refresh)

        self.baud_combo = QComboBox()
        self.baud_combo.addItems(self._config.baudrates)
        self.baud_combo.setCurrentText("115200")
        self.baud_combo.setEditable(True)

        self.device_list = QListWidget()
        self.device_list.setSelectionMode(QListWidget.MultiSelection)

        self.btn_scan = QPushButton("Scan Devices")
        self.btn_scan.clicked.connect(self._start_scan)
        self.btn_stop_scan = QPushButton("Stop Scan")
        self.btn_stop_scan.clicked.connect(self._stop_scan)
        self.btn_stop_scan.setEnabled(False)

        self.file_label = QLabel("No file selected")
        self.btn_file = QPushButton("Select Firmware")
        self.btn_file.clicked.connect(self._select_file)

        self.progress = QProgressBar()
        self.speed_label = QLabel("Speed: 0 KB/s")

        self.btn_upload = QPushButton("Upload (A/B + Resume)")
        self.btn_upload.clicked.connect(self._start_upload)
        self.btn_stop_upload = QPushButton("Stop Upload")
        self.btn_stop_upload.clicked.connect(self._stop_upload)
        self.btn_stop_upload.setEnabled(False)

        self.btn_ping = QPushButton("Ping")
        self.btn_ping.clicked.connect(self._start_ping)

        self.log = QTextEdit()
        self.log.setReadOnly(True)

        layout.addLayout(port_layout)
        layout.addWidget(QLabel("Baud"))
        layout.addWidget(self.baud_combo)

        scan_layout = QHBoxLayout()
        scan_layout.addWidget(self.btn_scan)
        scan_layout.addWidget(self.btn_stop_scan)
        layout.addLayout(scan_layout)

        layout.addWidget(self.device_list)
        layout.addWidget(self.btn_file)
        layout.addWidget(self.file_label)
        layout.addWidget(self.progress)
        layout.addWidget(self.speed_label)

        upload_layout = QHBoxLayout()
        upload_layout.addWidget(self.btn_upload)
        upload_layout.addWidget(self.btn_stop_upload)
        layout.addLayout(upload_layout)

        layout.addWidget(self.btn_ping)
        layout.addWidget(self.log)

        self.setLayout(layout)

    def _init_signals(self):
        self.log_message.connect(self._append_log)

    def _start_timers(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_speed_display)
        self.timer.start(500)

    def _refresh_ports(self):
        self.port_combo.clear()
        ports = DeviceManager.get_available_ports()
        for p in ports:
            self.port_combo.addItem(p)

    def _get_selected_devices(self) -> list:
        ids = []
        for i in range(self.device_list.count()):
            item = self.device_list.item(i)
            if item.checkState() == Qt.Checked:
                ids.append(int(item.text().split()[1]))
        return ids

    def _start_scan(self):
        self._port = self.port_combo.currentText()
        if not self._port:
            self._log("No port selected")
            return

        self._baudrate = int(self.baud_combo.currentText())
        self.device_list.clear()
        self._found_devices = []

        self._scan_worker = ScanWorker(self._port, self._baudrate)
        self._scan_worker.device_found.connect(self._on_device_found)
        self._scan_worker.scan_progress.connect(self._on_scan_progress)
        self._scan_worker.scan_finished.connect(self._on_scan_finished)
        self._scan_worker.scan_error.connect(self._on_scan_error)
        self._scan_worker.log_message.connect(self._on_log_message)
        self._scan_worker.start()

        self._scanning = True
        self.btn_scan.setEnabled(False)
        self.btn_stop_scan.setEnabled(True)
        self.baud_combo.setEnabled(True)
        self.btn_file.setEnabled(True)
        self.btn_refresh.setEnabled(True)

    def _stop_scan(self):
        if self._scan_worker and self._scan_worker.isRunning():
            self._scan_worker.cancel()
            self._scan_worker.wait()

        self._scanning = False
        self.btn_scan.setEnabled(True)
        self.btn_stop_scan.setEnabled(False)
        self._log("Scan stopped")

    def _on_device_found(self, slave_id: int):
        self._found_devices.append(slave_id)
        item = QListWidgetItem(f"Device {slave_id}")
        item.setCheckState(Qt.Checked)
        self.device_list.addItem(item)
        self._log(f"Found device {slave_id}")

    def _on_scan_progress(self, current: int, total: int):
        pass

    def _on_scan_finished(self, device_ids: list):
        self._scanning = False
        self.btn_scan.setEnabled(True)
        self.btn_stop_scan.setEnabled(False)
        self._log(f"Scan complete: {len(device_ids)} device(s) found")

    def _on_scan_error(self, error: str):
        self._scanning = False
        self.btn_scan.setEnabled(True)
        self.btn_stop_scan.setEnabled(False)
        self._log(f"Scan error: {error}")

    def _select_file(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Select Firmware", "", "(*.bin *.hex)"
        )
        if file:
            self._file_path = file
            self.file_label.setText(file)
            self._load_firmware(file)
            self._log(f"Selected: {file}")

    def _load_firmware(self, path: str):
        from utils.hex_parser import read_firmware
        from utils.crc import calculate_crc32
        self._firmware_data = read_firmware(path)
        self._crc = calculate_crc32(self._firmware_data)
        self._log(f"Firmware loaded: {len(self._firmware_data)} bytes, CRC: {hex(self._crc)}")

    def _start_upload(self):
        if not self._file_path or not self._firmware_data:
            self._log("No firmware file selected")
            return

        port = self.port_combo.currentText()
        if not port:
            self._log("No port selected")
            return

        devices = self._get_selected_devices()
        if not devices:
            self._log("No devices selected")
            return

        self._port = port
        self._baudrate = int(self.baud_combo.currentText())

        for dev in devices:
            self._start_upload_to_device(dev)
            break

    def _start_upload_to_device(self, device_id: int):
        self._upload_worker = UploadWorker(self._port, device_id, self._baudrate)
        self._upload_worker.set_firmware(self._file_path, self._firmware_data)
        self._upload_worker.upload_progress.connect(self._on_upload_progress)
        self._upload_worker.upload_finished.connect(self._on_upload_finished)
        self._upload_worker.upload_error.connect(self._on_upload_error)
        self._upload_worker.log_message.connect(self._on_log_message)
        self._upload_worker.start()

        self._uploading = True
        self.btn_upload.setEnabled(False)
        self.btn_stop_upload.setEnabled(True)
        self.baud_combo.setEnabled(True)
        self.btn_scan.setEnabled(True)

    def _stop_upload(self):
        if self._upload_worker and self._upload_worker.isRunning():
            self._upload_worker.cancel()
            self._upload_worker.wait()

        self._uploading = False
        self.btn_upload.setEnabled(True)
        self.btn_stop_upload.setEnabled(False)
        self._log("Upload stopped")

    def _on_upload_progress(self, written: int, total: int, speed: float):
        percent = int(written / total * 100) if total > 0 else 0
        self.progress.setValue(percent)
        self.speed_label.setText(f"Speed: {speed:.2f} KB/s")

    def _on_upload_finished(self, device_id: int, success: bool):
        self._uploading = False
        self.btn_upload.setEnabled(True)
        self.btn_stop_upload.setEnabled(False)

        if success:
            self._log(f"Device {device_id} DONE")
        else:
            self._log(f"Device {device_id} FAILED")

    def _on_upload_error(self, device_id: int, error: str):
        self._uploading = False
        self.btn_upload.setEnabled(True)
        self.btn_stop_upload.setEnabled(False)
        self._log(f"Device {device_id} error: {error}")

    def _start_ping(self):
        port = self.port_combo.currentText()
        if not port:
            return

        baudrate = int(self.baud_combo.currentText())
        manager = DeviceManager(port, baudrate)

        devices = self._get_selected_devices()
        for dev in devices:
            if manager.ping_device(dev):
                self._log(f"Device {dev} OK")
            else:
                self._log(f"Device {dev} FAIL")

    def _update_speed_display(self):
        pass

    def _log(self, msg: str):
        self.log_message.emit(msg)

    def _on_log_message(self, msg: str, level: str):
        self._log(msg)

    def _append_log(self, msg: str):
        self.log.append(msg)

    def closeEvent(self, event):
        self._stop_scan()
        self._stop_upload()
        event.accept()