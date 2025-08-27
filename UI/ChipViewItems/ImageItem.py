import typing
import pathlib
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget, QPushButton, QLineEdit, QFileDialog
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import QRectF
from UI.CustomGraphicsView import CustomGraphicsViewItem
from Data.Chip import Image
from UI.UIMaster import UIMaster


class ImageItem(CustomGraphicsViewItem):
    def __init__(self, image: Image):
        self.image = image

        # Used to detect when the displayed image is out of date.
        self.qtImage: typing.Optional[QImage] = None
        self.lastModifiedTime = None
        self.lastPath = None

        # The widget is just an image.
        self.imageWidget = QLabel()

        # The inspector has a path/browse field, and reports any errors in loading.
        inspector = QWidget()
        inspector.setLayout(QVBoxLayout())
        inspector.layout().addWidget(QLabel("Path:"))
        self.pathWidget = QLineEdit()
        self.pathWidget.textChanged.connect(self.RecordChanges)
        self.browseButton = QPushButton("Browse...")
        self.browseButton.clicked.connect(self.BrowseForItem)
        inspector.layout().addWidget(self.pathWidget)
        inspector.layout().addWidget(self.browseButton)
        self.errorLabel = QLabel()
        inspector.layout().addWidget(self.errorLabel)
        self.errorLabel.setStyleSheet("color: red")
        super().__init__("Image", self.imageWidget, inspector)
        super().SetRect(QRectF(*image.rect))

    @staticmethod
    def Browse(parent: QWidget):
        imageToAdd = QFileDialog.getOpenFileName(parent, "Browse for image",
                                                 filter="Images (*.png *.bmp *.gif *.jpg *.jpeg)")
        if imageToAdd[0]:
            return pathlib.Path(imageToAdd[0])

    def BrowseForItem(self):
        path = self.Browse(self.imageWidget)
        if path:
            self.image.path = path

    def RecordChanges(self):
        if self.isUpdating:
            return
        self.image.path = pathlib.Path(self.pathWidget.text())

        rect = self.GetRect()
        self.image.rect = [rect.x(), rect.y(), rect.width(), rect.height()]
        UIMaster.Instance().modified = True

    def SetEnabled(self, state):
        return

    def Update(self):
        try:
            if self.image.path != self.lastPath or \
                    self.image.path.stat().st_mtime != self.lastModifiedTime:
                self.qtImage = QImage(str(self.image.path))
                self.lastPath = self.image.path
                self.lastModifiedTime = self.image.path.stat().st_mtime
                self.RefreshImage()
            if self.imageWidget.pixmap().size() != self.GetRect().size().toSize():
                self.RefreshImage()
            if self.pathWidget.text() != str(self.image.path.absolute()):
                self.pathWidget.setText(str(self.image.path.absolute()))
        except Exception as e:
            self.qtImage = QImage("Assets/Images/helpIcon.png")
            self.errorLabel.setText(str(e))
            self.lastPath = self.image.path
            self.RefreshImage()
        else:
            self.errorLabel.setText("")

    def RefreshImage(self):
        pixmap = QPixmap(self.qtImage).scaled(self.GetRect().size().toSize())
        self.imageWidget.setPixmap(pixmap)

    def Duplicate(self):
        newImage = Image()
        newImage.path = self.image.path
        UIMaster.Instance().currentChip.images.append(newImage)
        UIMaster.Instance().modified = True
        return ImageItem(newImage)

    def SetRect(self, rect: QRectF):
        super().SetRect(rect)
        self.RecordChanges()

    def OnRemoved(self):
        UIMaster.Instance().currentChip.images.remove(self.image)
        UIMaster.Instance().modified = True
