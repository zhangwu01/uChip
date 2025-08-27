from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import QTimer


class DebugWindow(QWidget):
    def __init__(self, target: QWidget):
        super().__init__()
        self.target = target
        self.setLayout(QVBoxLayout())
        self.label = QLabel()
        self.layout().addWidget(self.label)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.Update)
        self.timer.start(1000)
        self.show()

    def Update(self):
        def db(w: QWidget, i):
            if i > 2:
                return ""
            t = "\t" * i + str(type(w)) + "\t"*(5-i) + "%s\t%s\t%s\t%s" % (
                w.sizePolicy().horizontalPolicy(), w.sizePolicy().verticalPolicy(),
                w.sizeHint(), w.size()) + "\n"
            return t + "".join([db(c, i + 1) for c in w.children() if isinstance(c, QWidget)])

        self.label.setText(db(self.target, 0))
        self.adjustSize()
