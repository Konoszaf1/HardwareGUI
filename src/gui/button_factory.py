# views/button_builder.py
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget

from src.gui.sidebar_button import SidebarButton


def build_toolbuttons(parent: QWidget, buttons):
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
