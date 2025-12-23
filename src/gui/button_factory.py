"""Factory utilities for constructing sidebar hardware buttons."""

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget

from src.gui.sidebar_button import SidebarButton


def build_tool_buttons(parent: QWidget, buttons):
    """Create a sidebar QPushButton from hardware descriptor metadata.

    Args:
        parent (QWidget): Widget that will own the generated buttons.
        buttons (Iterable): Sequence of descriptor objects exposing "label",
            "id", "order", and optional "icon_path" attributes.

    Returns:
        list[SidebarButton]: Instantiated buttons configured for the sidebar.
    """
    button_objs = []
    for button in buttons:
        button_obj = SidebarButton(parent)
        button_obj.setObjectName(button.label)
        button_obj.setText(button.label)
        if getattr(button, "icon_path", None):
            button_obj.setIcon(QIcon(button.icon_path))
        button_obj.setProperty("id", button.id)
        button_obj.setProperty("order", button.order)
        button_objs.append(button_obj)

    return button_objs
