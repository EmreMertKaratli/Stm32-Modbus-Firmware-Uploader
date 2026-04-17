import sys
import time
import json
import zlib
import serial
import minimalmodbus
from serial.tools import list_ports

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog,
    QLabel, QTextEdit, QProgressBar, QComboBox, QHBoxLayout, QListWidget,
    QListWidgetItem
)
from PySide6.QtCore import Qt, QTimer

CHUNK_SIZE = 128
STATE_FILE = "upload_state.json"

# Dual bank layout (STM32F1 simulated A/B slots)
APP_SLOT_A = 0x08008000
APP_SLOT_B = 0x08018000

class FirmwareUploader(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("STM32 Modbus OTA Uploader (PRO v2)")
        self.setMinimumWidth(700)

        self.file_path = None
        self.devices = []
        self.speed_history = []
        self.start_time = None
        self.last_bytes = 0

        layout = QVBoxLayout()

        # PORTS
        port_layout = QHBoxLayout()
        self.port_input = QComboBox()
        self.refresh_ports()
        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.refresh_ports)
        port_layout.addWidget(self.port_input)
        port_layout.addWidget(btn_refresh)

        # BAUD
        self.baud_input = QComboBox()
        self.baud_input.addItems(["9600","19200","38400","57600","115200","230400","460800","921600"])
        self.baud_input.setCurrentText("115200")
        self.baud_input.setEditable(True)

        # DEVICE LIST
        self.device_list = QListWidget()
        self.device_list.setSelectionMode(QListWidget.MultiSelection)

        btn_scan = QPushButton("Scan Devices")
        btn_scan.clicked.connect(self.scan_devices)

        # FILE
        self.file_label = QLabel("No file")
        btn_file = QPushButton("Select Firmware")
        btn_file.clicked.connect(self.select_file)

        # ACTIONS
        btn_upload = QPushButton("Upload (A/B + Delta + Resume)")
        btn_ping = QPushButton("Ping")
        btn_upload.clicked.connect(self.upload)
        btn_ping.clicked.connect(self.ping)

        # UI
        self.progress = QProgressBar()
        self.log = QTextEdit()
        self.speed_label = QLabel("Speed: 0 KB/s")
        self.graph_label = QLabel("[speed graph]")

        layout.addLayout(port_layout)
        layout.addWidget(QLabel("Baud"))
        layout.addWidget(self.baud_input)
        layout.addWidget(btn_scan)
        layout.addWidget(self.device_list)
        layout.addWidget(btn_file)
        layout.addWidget(self.file_label)
        layout.addWidget(self.progress)
        layout.addWidget(self.speed_label)
        layout.addWidget(self.graph_label)
        layout.addWidget(btn_upload)
        layout.addWidget(btn_ping)
        layout.addWidget(self.log)

        self.setLayout(layout)

        # timer for speed graph
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_speed)
        self.timer.start(500)

    # ---------------- UI ----------------

    def log_print(self, msg):
        self.log.append(msg)
        QApplication.processEvents()

    # ---------------- PORTS ----------------

    def refresh_ports(self):
        self.port_input.clear()
        ports = list(list_ports.comports())
        for p in ports:
            self.port_input.addItem(p.device)

    # ---------------- DEVICE SCAN ----------------

    def scan_devices(self):
        self.device_list.clear()
        inst = self.connect(1)

        for sid in range(1, 20):
            try:
                inst.address = sid
                inst.read_register(0x0000, 0)
                item = QListWidgetItem(f"Device {sid}")
                item.setCheckState(Qt.Checked)
                self.device_list.addItem(item)
            except:
                pass

    # ---------------- FILE ----------------

    def select_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "Firmware", "", "(*.bin *.hex)")
        if file:
            self.file_path = file
            self.file_label.setText(file)

    def hex_to_bin(self, path):
        data = bytearray()
        with open(path) as f:
            for line in f:
                if line.startswith(":"):
                    length = int(line[1:3],16)
                    rectype = int(line[7:9],16)
                    if rectype == 0:
                        for i in range(length):
                            data.append(int(line[9+i*2:11+i*2],16))
        return bytes(data)

    # ---------------- CONNECT ----------------

    def connect(self, slave):
        inst = minimalmodbus.Instrument(self.port_input.currentText(), slave)
        inst.serial.baudrate = int(self.baud_input.currentText())
        inst.serial.timeout = 1
        inst.mode = minimalmodbus.MODE_RTU
        return inst

    # ---------------- SPEED ----------------

    def update_speed(self):
        if self.start_time is None:
            return
        elapsed = time.time() - self.start_time
        if elapsed <= 0:
            return
        kb = self.last_bytes / 1024
        speed = kb / elapsed
        self.speed_label.setText(f"Speed: {speed:.2f} KB/s")

    # ---------------- PING ----------------

    def ping(self):
        for dev in self.selected_devices():
            try:
                inst = self.connect(dev)
                inst.read_register(0x0000,0)
                self.log_print(f"Device {dev} OK")
            except:
                self.log_print(f"Device {dev} FAIL")

    # ---------------- DEVICE SELECT ----------------

    def selected_devices(self):
        ids = []
        for i in range(self.device_list.count()):
            it = self.device_list.item(i)
            if it.checkState() == Qt.Checked:
                ids.append(int(it.text().split()[1]))
        return ids

    # ---------------- DELTA FW ----------------

    def delta_chunks(self, data):
        return [data[i:i+CHUNK_SIZE] for i in range(0, len(data), CHUNK_SIZE)]

    # ---------------- STATE ----------------

    def load_state(self):
        try:
            data = json.load(open(STATE_FILE))
            return {"o": data.get("o", 0), "a": data.get("a", 0)}
        except:
            return None

    def save_state(self, offset, addr):
        json.dump({"o": offset, "a": addr}, open(STATE_FILE, "w"))

    # ---------------- UPLOAD ----------------

    def upload(self):
        if not self.file_path:
            return

        data = open(self.file_path,"rb").read() if not self.file_path.endswith(".hex") else self.hex_to_bin(self.file_path)

        crc = zlib.crc32(data) & 0xFFFFFFFF
        self.log_print(f"CRC32 {hex(crc)}")

        for dev in self.selected_devices():
            self.log_print(f"Device {dev}")
            inst = self.connect(dev)

            # AUTO SLOT SELECTION (A/B)
            slot = APP_SLOT_A if dev % 2 == 0 else APP_SLOT_B

            inst.write_register(0x0000,1)

            state = self.load_state()
            offset = state["o"] if state else 0
            start_chunk = offset // CHUNK_SIZE

            self.start_time = time.time()
            self.last_bytes = 0

            chunks = self.delta_chunks(data)
            addr = slot + offset

            for c in chunks[start_chunk:]:

                regs = [c[i] | (c[i+1]<<8) if i+1<len(c) else c[i] for i in range(0,len(c),2)]

                inst.write_registers(0x0010,regs)
                inst.write_register(0x0001,(addr>>16)&0xFFFF)
                inst.write_register(0x0002,addr&0xFFFF)
                inst.write_register(0x0003,len(c))

                inst.write_register(0x0000,2)

                offset += CHUNK_SIZE
                addr += CHUNK_SIZE

                self.last_bytes += len(c)
                self.progress.setValue(int(offset/len(data)*100))

                self.save_state(offset,addr)

            # CRC VERIFY
            inst.write_register(0x0020, crc & 0xFFFF)
            inst.write_register(0x0021, (crc>>16)&0xFFFF)
            inst.write_register(0x0000,3)

            # AUTO RECOVERY FLAG
            inst.write_register(0x0030, 0xA5A5)

            inst.write_register(0x0000,4)

            self.log_print(f"Device {dev} DONE")

        self.log_print("ALL DONE")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = FirmwareUploader()
    w.show()
    sys.exit(app.exec())