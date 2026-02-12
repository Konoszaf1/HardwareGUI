"""Artifact collection and management for calibration outputs.

This module provides a dedicated class for managing artifact files
generated during calibration, following Single Responsibility Principle.
"""

import glob
import os


class ArtifactManager:
    """Manages artifact file collection from calibration directories.

    Separates artifact handling logic from the main service, making it
    easier to test and modify independently.
    """

    def __init__(self, base_dir: str = "."):
        """Initialize the artifact manager.

        Args:
            base_dir: Base directory for artifact storage. Defaults to current dir.
        """
        self._base_dir = base_dir

    def get_artifact_dir(self, relative_path: str) -> str:
        """Get the artifact directory path for the given relative path.

        Args:
            relative_path: Relative path within base_dir (e.g. 'calibration_vu1').

        Returns:
            Absolute path to the artifact directory.
        """
        return os.path.abspath(os.path.join(self._base_dir, relative_path))

    def collect_artifacts(self, relative_path: str) -> list[str]:
        """Collect all PNG artifacts from the given artifact directory.

        Priority files (output.png, ramp.png, transient.png) are listed first,
        followed by any other PNG files in alphabetical order.

        Args:
            relative_path: Relative path within base_dir.

        Returns:
            List of absolute paths to artifact files, deduplicated.
        """
        artifact_dir = self.get_artifact_dir(relative_path)
        paths: list[str] = []

        # Priority files first
        for name in ("output.png", "ramp.png", "transient.png"):
            p = os.path.join(artifact_dir, name)
            if os.path.exists(p):
                paths.append(p)

        # Add any other PNGs
        paths.extend(sorted(glob.glob(os.path.join(artifact_dir, "*.png"))))

        # Deduplicate while preserving order
        seen = set()
        unique: list[str] = []
        for p in paths:
            if p not in seen:
                unique.append(p)
                seen.add(p)

        return unique
