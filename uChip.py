import pathlib

from PySide6 import QtWidgets
from UI.MainWindow import MainWindow
from UI.DebugWindow import DebugWindow
import sys

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.OpenChipPath(pathlib.Path("ScreenSeq.ucp"))
    app.exec()

