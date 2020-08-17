"""
Sort and edit photos
"""
import sys
from PySide2 import QtWidgets


class PhotoBee(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('photobee')
        self.show()

def main():
    app = QtWidgets.QApplication(sys.argv)
    main_window = PhotoBee()
    sys.exit(app.exec_())
