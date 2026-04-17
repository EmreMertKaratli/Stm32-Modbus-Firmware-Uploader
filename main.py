import sys
from PySide6.QtWidgets import QApplication

from ui import MainWindow
from utils.logger import Logger


def main():
    Logger("stm32_uploader")

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()