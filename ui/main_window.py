from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
    QLabel, QTextEdit, QProgressBar, QComboBox, QListWidget,
    QListWidgetItem
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QThread

from utils.config import Config
from utils.logger import get_logger, LogSignalEmitter
from core import FirmwareUploaderEngine, StateManager
from device import DeviceManager


class UploadWorker(QThread):
    progress_signal = Signal(object)
    finished_signal = Signal(bool, str)
    log_signal = Signal(str)

    def __init__(self, engine: FirmwareUploaderEngine, device_id: int):
        super().__init__()
        self._engine = engine
        self._device_id = device_id

    def run(self):
        try:
            def callback(progress):
                self.progress_signal.emit(progress)

            success = self._engine.upload(self._device_id, callback)
            self.finished_signal.emit(success, f"Device {self._device_id}")
        except Exception as e:
            self.finished_signal.emit(False, str(e))


class MainWindow(QWidget):
    log_message = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("STM32 Modbus OTA Uploader")
        self.setMinimumWidth(700)

        self._config = Config()
        self._logger = get_logger()
        self._state_manager = StateManager()
        self._engine: FirmwareUploaderEngine = None
        self._worker: UploadWorker = None

        self._port = None
        self._baudrate = 115200
        self._file_path = None

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
        self.btn_scan.clicked.connect(self._scan_devices)

        self.file_label = QLabel("No file selected")
        self.btn_file = QPushButton("Select Firmware")
        self.btn_file.clicked.connect(self._select_file)

        self.progress = QProgressBar()
        self.speed_label = QLabel("Speed: 0 KB/s")

        self.btn_upload = QPushButton("Upload (A/B + Resume)")
        self.btn_upload.clicked.connect(self._start_upload)

        self.btn_ping = QPushButton("Ping")
        self.btn_ping.clicked.connect(self._ping_devices)

        self.log = QTextEdit()
        self.log.setReadOnly(True)

        layout.addLayout(port_layout)
        layout.addWidget(QLabel("Baud"))
        layout.addWidget(self.baud_combo)
        layout.addWidget(self.btn_scan)
        layout.addWidget(self.device_list)
        layout.addWidget(self.btn_file)
        layout.addWidget(self.file_label)
        layout.addWidget(self.progress)
        layout.addWidget(self.speed_label)
        layout.addWidget(self.btn_upload)
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

    def _scan_devices(self):
        self.device_list.clear()
        port = self.port_combo.currentText()
        if not port:
            self._log("No port selected")
            return

        baudrate = int(self.baud_combo.currentText())
        manager = DeviceManager(port, baudrate)

        self._log(f"Scanning on {port}...")
        devices = manager.scan()

        for dev in devices:
            item = QListWidgetItem(f"Device {dev.slave_id}")
            item.setCheckState(Qt.Checked)
            self.device_list.addItem(item)

        self._log(f"Found {len(devices)} device(s)")

    def _select_file(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Select Firmware", "", "(*.bin *.hex)"
        )
        if file:
            self._file_path = file
            self.file_label.setText(file)
            self._log(f"Selected: {file}")

    def _get_selected_devices(self) -> list:
        ids = []
        for i in range(self.device_list.count()):
            item = self.device_list.item(i)
            if item.checkState() == Qt.Checked:
                ids.append(int(item.text().split()[1]))
        return ids

    def _start_upload(self):
        if not self._file_path:
            self._log("No firmware file selected")
            return

        port = self.port_combo.currentText()
        if not port:
            self._log("No port selected")
            return

        self._port = port
        self._baudrate = int(self.baud_combo.currentText())

        self._engine = FirmwareUploaderEngine(
            self._port,
            self._baudrate,
            self._state_manager
        )
        self._engine.load_firmware(self._file_path)
        self._engine.compute_chunks()

        self._log(f"CRC32: {hex(self._engine.get_crc())}")

        devices = self._get_selected_devices()
        if not devices:
            self._log("No devices selected")
            return

        for dev in devices:
            self._log(f"Uploading to device {dev}...")
            self._worker = UploadWorker(self._engine, dev)
            self._worker.progress_signal.connect(self._on_progress)
            self._worker.finished_signal.connect(self._on_finished)
            self._worker.log_signal.connect(self._append_log)
            self._worker.start()
            break

    def _on_progress(self, progress):
        self.progress.setValue(progress.percent)
        self.speed_label.setText(f"Speed: {progress.speed_kb_s:.2f} KB/s")

    def _on_finished(self, success: bool, msg: str):
        if success:
            self._log(f"{msg} DONE")
        else:
            self._log(f"Error: {msg}")
        self._log("ALL DONE")

    def _ping_devices(self):
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

    def _append_log(self, msg: str):
        self.log.append(msg)

    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait()
        event.accept()