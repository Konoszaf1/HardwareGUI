"""Singleton service for managing shared panels per hardware.

Maintains one SharedPanelsWidget instance per hardware ID,
allowing panel state to persist when switching between hardware selections.
"""

from src.gui.shared_panels_widget import SharedPanelsWidget


class SharedPanelsService:
    """Singleton managing SharedPanelsWidget instances per hardware ID.

    Each hardware device gets its own panel instance, preserving logs and
    artifacts when switching between hardware selections.
    """

    _instance: "SharedPanelsService | None" = None

    def __init__(self):
        if SharedPanelsService._instance is not None:
            raise RuntimeError("Use SharedPanelsService.instance() instead")
        self._panels: dict[int, SharedPanelsWidget] = {}
        self._current_hardware_id: int | None = None
        self._console_visible: bool = False  # Start collapsed
        self._artifacts_visible: bool = False  # Start collapsed

    @classmethod
    def instance(cls) -> "SharedPanelsService":
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def init(cls) -> "SharedPanelsService":
        """Initialize the singleton (alias for instance())."""
        return cls.instance()

    def get_panels(self, hardware_id: int) -> SharedPanelsWidget:
        """Get or create panels for a hardware ID."""
        if hardware_id not in self._panels:
            panels = SharedPanelsWidget()
            # Apply current visibility state to new panels
            panels.show_console(self._console_visible)
            panels.show_artifacts(self._artifacts_visible)
            self._panels[hardware_id] = panels
        return self._panels[hardware_id]

    def switch_hardware(self, hardware_id: int) -> SharedPanelsWidget:
        """Switch to panels for the given hardware ID.

        Returns the panels for the new hardware. Previous panels remain
        in memory with their logs preserved.
        """
        self._current_hardware_id = hardware_id
        return self.get_panels(hardware_id)

    def current_panels(self) -> SharedPanelsWidget | None:
        """Return the currently active panels, or None if no hardware selected."""
        if self._current_hardware_id is None:
            return None
        return self._panels.get(self._current_hardware_id)

    def toggle_console(self, visible: bool | None = None) -> bool:
        """Toggle or set console visibility across all panels.

        Args:
            visible: If None, toggles current state. Otherwise sets state.

        Returns:
            New visibility state.
        """
        if visible is None:
            visible = not self._console_visible
        self._console_visible = visible
        for panels in self._panels.values():
            panels.show_console(visible)
        return visible

    def toggle_artifacts(self, visible: bool | None = None) -> bool:
        """Toggle or set artifacts visibility across all panels.

        Args:
            visible: If None, toggles current state. Otherwise sets state.

        Returns:
            New visibility state.
        """
        if visible is None:
            visible = not self._artifacts_visible
        self._artifacts_visible = visible
        for panels in self._panels.values():
            panels.show_artifacts(visible)
        return visible

    @property
    def console_visible(self) -> bool:
        return self._console_visible

    @property
    def artifacts_visible(self) -> bool:
        return self._artifacts_visible
