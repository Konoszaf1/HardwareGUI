"""Tests for src/logic/model/actions_model.py Qt model and proxy."""

from PySide6.QtCore import Qt, QModelIndex

from src.logic.model.actions_model import ActionModel, ActionsByHardwareProxy


class TestActionModelBasics:
    """Test ActionModel basic functionality."""

    def test_row_count_matches_actions(self, sample_actions):
        """RowCount should match the number of actions."""
        model = ActionModel(sample_actions)

        assert model.rowCount() == len(sample_actions)

    def test_row_count_with_parent(self, sample_actions):
        """RowCount with valid parent should return 0 (flat model)."""
        model = ActionModel(sample_actions)
        parent = model.index(0, 0)

        # Flat model, so children of any item should be 0
        assert model.rowCount(parent) == 0

    def test_row_count_empty_model(self):
        """RowCount for empty model should be 0."""
        model = ActionModel([])

        assert model.rowCount() == 0


class TestActionModelData:
    """Test ActionModel data retrieval by role."""

    def test_data_display_role(self, sample_actions):
        """DisplayRole should return the action label."""
        model = ActionModel(sample_actions)
        index = model.index(0, 0)

        result = model.data(index, Qt.ItemDataRole.DisplayRole)

        assert result == "Session & Coeffs"

    def test_data_id_role(self, sample_actions):
        """id_role should return the action ID."""
        model = ActionModel(sample_actions)
        index = model.index(0, 0)

        result = model.data(index, ActionModel.id_role)

        assert result == 1

    def test_data_hardware_id_role(self, sample_actions):
        """hardware_id_role should return the hardware ID."""
        model = ActionModel(sample_actions)
        index = model.index(0, 0)

        result = model.data(index, ActionModel.hardware_id_role)

        assert result == 1

    def test_data_page_id_role(self, sample_actions):
        """page_id_role should return the page ID."""
        model = ActionModel(sample_actions)
        index = model.index(0, 0)

        result = model.data(index, ActionModel.page_id_role)

        assert result == "workbench"

    def test_data_label_role(self, sample_actions):
        """label_role should return the action label (same as DisplayRole)."""
        model = ActionModel(sample_actions)
        index = model.index(0, 0)

        result = model.data(index, ActionModel.label_role)

        assert result == "Session & Coeffs"

    def test_data_invalid_index(self, sample_actions):
        """Data with invalid index should return None."""
        model = ActionModel(sample_actions)
        invalid_index = QModelIndex()

        result = model.data(invalid_index, Qt.ItemDataRole.DisplayRole)

        assert result is None


class TestActionModelRoleNames:
    """Test ActionModel roleNames() method."""

    def test_role_names_contains_all_roles(self, sample_actions):
        """RoleNames should contain all custom role mappings."""
        model = ActionModel(sample_actions)
        result = model.roleNames()

        assert model.id_role in result
        assert model.hardware_id_role in result
        assert model.label_role in result
        assert model.page_id_role in result


class TestActionsByHardwareProxy:
    """Test ActionsByHardwareProxy filtering."""

    def test_filter_by_hardware_id(self, sample_actions):
        """Proxy should filter actions by hardware_id."""
        model = ActionModel(sample_actions)
        proxy = ActionsByHardwareProxy()
        proxy.setSourceModel(model)

        # Filter for hardware_id=1
        proxy.set_hardware_id(1)

        # Should only show actions with hardware_id=1
        assert proxy.rowCount() == 2

    def test_filter_by_different_hardware_id(self, sample_actions):
        """Proxy should update when hardware_id changes."""
        model = ActionModel(sample_actions)
        proxy = ActionsByHardwareProxy()
        proxy.setSourceModel(model)

        # Filter for hardware_id=2
        proxy.set_hardware_id(2)

        # Should only show actions with hardware_id=2
        assert proxy.rowCount() == 1

    def test_filter_no_hardware_id(self, sample_actions):
        """Proxy with None hardware_id should show no actions (default state)."""
        model = ActionModel(sample_actions)
        proxy = ActionsByHardwareProxy()
        proxy.setSourceModel(model)

        # No filter = no actions shown (user must select hardware first)
        proxy.set_hardware_id(None)

        assert proxy.rowCount() == 0

    def test_filter_nonexistent_hardware_id(self, sample_actions):
        """Proxy with non-existent hardware_id should show no actions."""
        model = ActionModel(sample_actions)
        proxy = ActionsByHardwareProxy()
        proxy.setSourceModel(model)

        # Filter for hardware_id that doesn't exist
        proxy.set_hardware_id(999)

        assert proxy.rowCount() == 0

    def test_proxy_data_access_returns_correct_values(self, sample_actions):
        """Data accessed through proxy should return correct source model data."""
        model = ActionModel(sample_actions)
        proxy = ActionsByHardwareProxy()
        proxy.setSourceModel(model)
        proxy.set_hardware_id(1)

        # Access data through proxy index
        proxy_index = proxy.index(0, 0)
        label = proxy.data(proxy_index, Qt.ItemDataRole.DisplayRole)
        page_id = proxy.data(proxy_index, ActionModel.page_id_role)

        # Should get data from filtered model
        assert label in ["Session & Coeffs", "Calibration"]
        assert page_id in ["workbench", "calibration"]

    def test_filter_switching_updates_correctly(self, sample_actions):
        """Switching hardware_id filter should update row count correctly."""
        model = ActionModel(sample_actions)
        proxy = ActionsByHardwareProxy()
        proxy.setSourceModel(model)

        # Start with hardware_id=1
        proxy.set_hardware_id(1)
        assert proxy.rowCount() == 2

        # Switch to hardware_id=2
        proxy.set_hardware_id(2)
        assert proxy.rowCount() == 1

        # Switch back to hardware_id=1
        proxy.set_hardware_id(1)
        assert proxy.rowCount() == 2
