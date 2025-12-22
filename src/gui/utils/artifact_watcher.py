"""File system watcher for automatic thumbnail updates from artifact directory."""
import os
import glob
from PySide6.QtCore import QObject, QFileSystemWatcher, QTimer
from PySide6.QtWidgets import QListWidget

from src.gui.utils.gui_helpers import add_thumbnail_item


class ArtifactWatcher(QObject):
    """Watches artifact directory and updates thumbnail list when files change."""
    
    def __init__(self, list_widget: QListWidget, parent=None):
        super().__init__(parent)
        self.list_widget = list_widget
        self._artifact_dir = None
        self._file_watcher = None
        self._refresh_timer = None
        self._known_artifacts = set()
        
    def setup(self, artifact_dir: str) -> None:
        """Setup file watcher for the given artifact directory."""
        if self._file_watcher:
            # Clean up existing watcher
            self._file_watcher.deleteLater()
            
        self._artifact_dir = artifact_dir
        
        # Create directory if it doesn't exist
        os.makedirs(self._artifact_dir, exist_ok=True)
        
        # Setup file watcher
        self._file_watcher = QFileSystemWatcher(self)
        self._file_watcher.addPath(self._artifact_dir)
        self._file_watcher.directoryChanged.connect(self._on_directory_changed)
        
        # Setup refresh timer (debounce rapid file changes)
        if not self._refresh_timer:
            self._refresh_timer = QTimer(self)
            self._refresh_timer.setSingleShot(True)
            self._refresh_timer.timeout.connect(self.refresh_thumbnails)
            self._refresh_timer.setInterval(500)  # 500ms debounce
        
        # Initial refresh
        self.refresh_thumbnails()
        
    def _on_directory_changed(self, path: str) -> None:
        """Handle directory change event."""
        if self._refresh_timer:
            self._refresh_timer.start()
    
    def refresh_thumbnails(self) -> None:
        """Refresh thumbnails from artifact directory."""
        if not self._artifact_dir:
            return
            
        # Get all PNG files in artifact directory
        pattern = os.path.join(self._artifact_dir, "*.png")
        current_files = set(glob.glob(pattern))
        
        # Check if files changed
        if current_files != self._known_artifacts:
            self._known_artifacts = current_files
            
            # Clear and re-add all thumbnails in sorted order
            self.list_widget.clear()
            for filepath in sorted(current_files):
                add_thumbnail_item(self.list_widget, filepath)
