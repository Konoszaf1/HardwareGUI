from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QAction
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QScrollArea, 
    QPushButton, QHBoxLayout, QFileDialog, QSizePolicy
)
import shutil
import os

class ImageViewerDialog(QDialog):
    """
    A dialog to view an image in full size and optionally save it.
    """
    def __init__(self, image_path: str, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.setWindowTitle(f"Image Viewer - {os.path.basename(image_path)}")
        self.resize(800, 600)

        # Main layout
        layout = QVBoxLayout(self)

        # Scroll area for the image
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.image_label.setScaledContents(False)
        
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            self.image_label.setPixmap(pixmap)
        else:
            self.image_label.setText("Failed to load image.")

        self.scroll_area.setWidget(self.image_label)
        layout.addWidget(self.scroll_area)

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

    def _on_save(self):
        """Save the current image to a user-selected location."""
        if not self.image_path or not os.path.exists(self.image_path):
            return

        file_name, _ = QFileDialog.getSaveFileName(
            self, 
            "Save Image", 
            os.path.basename(self.image_path), 
            "Images (*.png *.jpg *.bmp)"
        )
        
        if file_name:
            try:
                shutil.copy2(self.image_path, file_name)
            except Exception as e:
                print(f"Error saving image: {e}")
