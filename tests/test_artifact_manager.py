"""Tests for src/logic/artifact_manager.py artifact collection logic."""

import os

from src.logic.artifact_manager import ArtifactManager


class TestArtifactManagerCollect:
    """Test artifact collection and ordering."""

    def test_collect_artifacts_returns_list(self, temp_artifact_dir):
        """collect_artifacts should return a list of file paths."""
        manager = ArtifactManager(base_dir=str(temp_artifact_dir))
        artifacts = manager.collect_artifacts(vu_serial=123)

        assert isinstance(artifacts, list)

    def test_collect_artifacts_finds_files(self, temp_artifact_dir):
        """collect_artifacts should find PNG files in the directory."""
        manager = ArtifactManager(base_dir=str(temp_artifact_dir))
        artifacts = manager.collect_artifacts(vu_serial=123)

        assert len(artifacts) == 4
        for path in artifacts:
            assert path.endswith(".png")

    def test_collect_artifacts_priority_order(self, temp_artifact_dir):
        """Priority files should appear first in exact order."""
        manager = ArtifactManager(base_dir=str(temp_artifact_dir))
        artifacts = manager.collect_artifacts(vu_serial=123)

        names = [os.path.basename(p) for p in artifacts]
        priority_files = ["output.png", "ramp.png", "transient.png"]

        # Priority files should be first, in exact order
        assert (
            names[:3] == priority_files
        ), f"Expected priority order {priority_files}, got {names[:3]}"
        # Non-priority files should come after priority files
        for name in names[3:]:
            assert name not in priority_files, f"Priority file {name} found after position 3"

    def test_collect_artifacts_no_duplicates(self, temp_artifact_dir):
        """collect_artifacts should not return duplicate paths."""
        manager = ArtifactManager(base_dir=str(temp_artifact_dir))
        artifacts = manager.collect_artifacts(vu_serial=123)

        assert len(artifacts) == len(set(artifacts)), "Duplicate paths found"

    def test_collect_artifacts_empty_for_missing_dir(self, tmp_path):
        """collect_artifacts should return empty list for non-existent directory."""
        manager = ArtifactManager(base_dir=str(tmp_path))
        artifacts = manager.collect_artifacts(vu_serial=999)

        assert artifacts == []

    def test_collect_artifacts_excludes_non_png_files(self, tmp_path):
        """collect_artifacts should only collect PNG files, ignoring other types."""
        vu_dir = tmp_path / "calibration_vu456"
        vu_dir.mkdir()

        # Create mixed file types
        (vu_dir / "image.png").write_bytes(b"PNG_DATA")
        (vu_dir / "data.csv").write_text("col1,col2")
        (vu_dir / "notes.txt").write_text("some notes")
        (vu_dir / "config.json").write_text("{}")

        manager = ArtifactManager(base_dir=str(tmp_path))
        artifacts = manager.collect_artifacts(vu_serial=456)

        assert len(artifacts) == 1
        assert artifacts[0].endswith("image.png")


class TestArtifactManagerPaths:
    """Test artifact directory path construction."""

    def test_get_artifact_dir_format(self, tmp_path):
        """get_artifact_dir should return correctly formatted path."""
        manager = ArtifactManager(base_dir=str(tmp_path))
        path = manager.get_artifact_dir(vu_serial=42)

        assert "calibration_vu42" in path

    def test_get_artifact_dir_different_serials(self, tmp_path):
        """get_artifact_dir should produce different paths for different serials."""
        manager = ArtifactManager(base_dir=str(tmp_path))
        path1 = manager.get_artifact_dir(vu_serial=100)
        path2 = manager.get_artifact_dir(vu_serial=200)

        assert path1 != path2
        assert "100" in path1
        assert "200" in path2
