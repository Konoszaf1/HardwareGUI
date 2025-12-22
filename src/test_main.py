# gallery_mre.py
from __future__ import annotations
import os, sys

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QImageReader, QPixmap, QIcon, QAction
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QListWidget, QListWidgetItem,
    QSplitter, QLabel, QVBoxLayout, QFileDialog, QToolBar, QDialog,
    QDialogButtonBox, QSizePolicy
)

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff"}

class ImagePreviewDialog(QDialog):
    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(os.path.basename(path))
        self.label = QLabel(alignment=Qt.AlignCenter)
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.label.setMinimumSize(640, 480)

        reader = QImageReader(path)
        reader.setAutoTransform(True)
        img = reader.read()
        if img.isNull():
            self.label.setText("Failed to load image")
        else:
            self.label.setPixmap(QPixmap.fromImage(img))

        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.addWidget(btns)
        self.resize(900, 700)

class GalleryWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Gallery MRE")
        self.resize(1200, 800)

        # toolbar
        tb = QToolBar("Main")
        self.addToolBar(tb)
        act_open = QAction("Open Folder…", self)
        act_open.triggered.connect(self.open_folder_dialog)
        tb.addAction(act_open)

        # UI: splitter with thumbnail grid + preview
        self.list = QListWidget()
        self.list.setViewMode(QListWidget.IconMode)
        self.list.setResizeMode(QListWidget.Adjust)
        self.list.setWrapping(False)
        self.list.setMovement(QListWidget.Static)
        self.list.setUniformItemSizes(False)
        self.list.setIconSize(QSize(160, 160))
        self.list.setSpacing(8)
        self.list.itemSelectionChanged.connect(self.update_preview)
        self.list.itemActivated.connect(self.open_fullscreen)

        self.preview = QLabel("Open a folder, then select an image", alignment=Qt.AlignCenter)
        self.preview.setMinimumWidth(320)
        self.preview.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        split = QSplitter()
        split.addWidget(self.list)
        split.addWidget(self.preview)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 0)

        c = QWidget()
        lay = QVBoxLayout(c)
        lay.addWidget(split)
        self.setCentralWidget(c)

    # ---- actions ----
    def open_folder_dialog(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if folder:
            self.load_folder(folder)

    def load_folder(self, folder: str):
        self.list.clear()
        for name in sorted(os.listdir(folder)):
            path = os.path.join(folder, name)
            if not os.path.isfile(path):
                continue
            if os.path.splitext(name)[1].lower() not in IMAGE_EXTS:
                continue
            item = QListWidgetItem(os.path.basename(path))
            item.setData(Qt.UserRole, path)
            # make thumbnail icon
            icon = self.make_thumbnail_icon(path, 160)
            item.setIcon(icon)
            # optional: fixed size hint for consistent grid cells
            item.setSizeHint(QSize(180, 200))
            self.list.addItem(item)

        if self.list.count() > 0:
            self.list.setCurrentRow(0)

    # ---- helpers ----
    def make_thumbnail_icon(self, path: str, size: int) -> QIcon:
        reader = QImageReader(path)
        reader.setAutoTransform(True)
        reader.setScaledSize(QSize(size, size))  # decode scaled for speed
        img = reader.read()
        if img.isNull():
            pm = QPixmap(size, size)
            pm.fill(Qt.lightGray)
            return QIcon(pm)
        pm = QPixmap.fromImage(img).scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        return QIcon(pm)

    def update_preview(self):
        items = self.list.selectedItems()
        if not items:
            self.preview.setText("Select an image")
            self.preview.setPixmap(QPixmap())
            return
        path = items[0].data(Qt.UserRole)
        self.set_preview(path)

    def set_preview(self, path: str):
        reader = QImageReader(path)
        reader.setAutoTransform(True)
        # medium-ish preview; Qt keeps aspect ratio when we scale after
        img = reader.read()
        if img.isNull():
            self.preview.setText("Failed to load image")
            self.preview.setPixmap(QPixmap())
            return
        pm = QPixmap.fromImage(img)
        # scale nicely to the preview label width (height adjusts automatically)
        w = max(400, self.preview.width())
        pm = pm.scaled(w, w, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.preview.setPixmap(pm)

    def open_fullscreen(self, item: QListWidgetItem):
        path = item.data(Qt.UserRole)
        if path:
            ImagePreviewDialog(path, self).exec()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = GalleryWindow()
    w.show()
    sys.exit(app.exec())
