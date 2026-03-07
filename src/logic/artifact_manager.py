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

        Files are sorted by prefix priority (output, ramp, transient first),
        then by name (which includes timestamp, so newest last within group).

        Args:
            relative_path: Relative path within base_dir.

        Returns:
            List of absolute paths to artifact files, deduplicated.
        """
        artifact_dir = self.get_artifact_dir(relative_path)
        all_pngs = sorted(glob.glob(os.path.join(artifact_dir, "*.png")))

        # Group by prefix priority
        priority_prefixes = ("output", "ramp", "transient")
        prioritized: list[str] = []
        rest: list[str] = []

        for p in all_pngs:
            basename = os.path.basename(p).lower()
            if any(basename.startswith(pfx) for pfx in priority_prefixes):
                prioritized.append(p)
            else:
                rest.append(p)

        # Sort prioritized by prefix order, then by name within each group
        def _priority_key(path: str) -> tuple[int, str]:
            basename = os.path.basename(path).lower()
            for i, pfx in enumerate(priority_prefixes):
                if basename.startswith(pfx):
                    return (i, basename)
            return (len(priority_prefixes), basename)

        prioritized.sort(key=_priority_key)
        return prioritized + rest
