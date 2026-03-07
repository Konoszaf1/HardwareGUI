"""Image viewer dialog for displaying artifact images."""

import os
import shutil

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from src.logging_config import get_logger

logger = get_logger(__name__)


class ImageViewerDialog(QDialog):
    """A dialog to view an image scaled to fit, with optional save."""

    def __init__(self, image_path: str, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.setWindowTitle(f"Image Viewer - {os.path.basename(image_path)}")

        self._original_pixmap = QPixmap(image_path)

        # Main layout
        layout = QVBoxLayout(self)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        if self._original_pixmap.isNull():
            self.image_label.setText("Failed to load image.")
        layout.addWidget(self.image_label, 1)

        # Buttons
        btn_layout = QHBoxLayout()

        self.btn_save = QPushButton("Save As...")
        self.btn_save.clicked.connect(self._on_save)

        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.accept)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_close)

        layout.addLayout(btn_layout)

        # Size dialog to fit the image
        self._size_to_image()

    def _size_to_image(self) -> None:
        """Resize dialog to fit the image, capped at 90% of screen."""
        if self._original_pixmap.isNull():
            self.resize(800, 600)
            return

        screen = self.screen()
        if screen:
            avail = screen.availableGeometry()
            max_w = int(avail.width() * 0.9)
            max_h = int(avail.height() * 0.9)
        else:
            max_w, max_h = 1200, 900

        img_w = self._original_pixmap.width()
        img_h = self._original_pixmap.height()

        # Reserve space for buttons and layout margins
        chrome_h = 80

        scale = min(max_w / max(img_w, 1), (max_h - chrome_h) / max(img_h, 1), 1.0)
        dialog_w = max(int(img_w * scale) + 40, 400)
        dialog_h = max(int(img_h * scale) + chrome_h, 300)

        self.resize(dialog_w, dialog_h)

    def _update_pixmap(self) -> None:
        """Scale pixmap to fit the label while keeping aspect ratio."""
        if self._original_pixmap.isNull():
            return
        label_size = self.image_label.size()
        scaled = self._original_pixmap.scaled(
            label_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled)

    def showEvent(self, event):
        super().showEvent(event)
        self._update_pixmap()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_pixmap()

    def _on_save(self):
        """Save the current image to a user-selected location."""
        if not self.image_path or not os.path.exists(self.image_path):
            return

        file_name, _ = QFileDialog.getSaveFileName(
            self, "Save Image", os.path.basename(self.image_path), "Images (*.png *.jpg *.bmp)"
        )

        if file_name:
            try:
                shutil.copy2(self.image_path, file_name)
                logger.info(f"Image saved to: {file_name}")
            except (OSError, PermissionError) as e:
                logger.error(f"Failed to save image to {file_name}: {e}")
                QMessageBox.warning(self, "Save Error", f"Could not save image: {e}")
            except Exception as e:
                logger.exception(f"Unexpected error saving image to {file_name}")
                QMessageBox.critical(self, "Error", f"Unexpected error: {e}")
