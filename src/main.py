import sys
from PySide6.QtWidgets import QApplication
import qt_material
from src.gui.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    qt_material.apply_stylesheet(app, "dark_blue.xml")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
