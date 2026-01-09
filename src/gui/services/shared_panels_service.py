"""Singleton service for managing shared panels per hardware.

Maintains one SharedPanelsWidget instance per hardware ID,
allowing panel state to persist when switching between hardware selections.
"""

from src.gui.shared_panels_widget import SharedPanelsWidget


class SharedPanelsService:
    """Singleton managing SharedPanelsWidget instances per hardware ID.

    Each hardware device gets its own panel instance, preserving logs and
    artifacts when switching between hardware selections.

    Panel visibility state is owned by each SharedPanelsWidget instance,
    not by this service. Query current_panels() for the authoritative state.
    """

    _instance: "SharedPanelsService | None" = None

    def __init__(self):
        if SharedPanelsService._instance is not None:
            raise RuntimeError("Use SharedPanelsService.instance() instead")
        self._panels: dict[int, SharedPanelsWidget] = {}
        self._current_hardware_id: int | None = None
        self._last_action_per_hardware: dict[int, str] = {}  # Track last action per hardware

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
            # New panels start collapsed (default state in SharedPanelsWidget)
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

    # ---- Last action tracking ----

    def set_last_action(self, hardware_id: int, page_id: str) -> None:
        """Store the last selected action for a hardware.

        Args:
            hardware_id: Hardware ID.
            page_id: The page ID of the selected action.
        """
        self._last_action_per_hardware[hardware_id] = page_id

    def get_last_action(self, hardware_id: int) -> str | None:
        """Get the last selected action for a hardware.

        Args:
            hardware_id: Hardware ID.

        Returns:
            The page_id of the last action, or None if none selected.
        """
        return self._last_action_per_hardware.get(hardware_id)

    # ---- Panel visibility (queries current panel state) ----

    @property
    def console_visible(self) -> bool:
        """Return console visibility of current panels."""
        panels = self.current_panels()
        return panels.is_console_visible() if panels else False

    @property
    def artifacts_visible(self) -> bool:
        """Return artifacts visibility of current panels."""
        panels = self.current_panels()
        return panels.is_artifacts_visible() if panels else False
