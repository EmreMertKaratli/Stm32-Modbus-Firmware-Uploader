from PySide6.QtCore import Signal, QObject


class AppSignals(QObject):
    scan_started = Signal()
    scan_progress = Signal(int, int)
    scan_finished = Signal(list)
    scan_error = Signal(str)

    device_found = Signal(int)
    no_devices_found = Signal()

    upload_started = Signal(int)
    upload_progress = Signal(int, int, float)
    upload_finished = Signal(int, bool)
    upload_error = Signal(int, str)

    log_message = Signal(str, str)

    ports_refreshed = Signal(list)

    operation_cancelled = Signal()