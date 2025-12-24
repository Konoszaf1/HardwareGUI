"""Centralized stylesheet definitions for the application.

This module contains all style constants used across the GUI,
following the Dracula color theme for consistency.
"""


class Styles:
    """Application-wide style constants."""

    # Console widget (Dracula theme)
    CONSOLE = """
        QPlainTextEdit {
            background-color: #282a36;
            color: #f8f8f2;
            font-family: 'Consolas', 'Monospace';
            font-size: 10pt;
            border: 1px solid #44475a;
            border-radius: 4px;
            padding: 4px;
        }
    """

    # Test card container
    TEST_CARD = """
        QFrame {
            background-color: #44475a;
            border-radius: 8px;
            border: 1px solid #6272a4;
        }
        QLabel {
            border: none;
            color: #f8f8f2;
        }
    """

    # Test card title
    CARD_TITLE = "font-weight: bold; font-size: 11pt; color: #8be9fd;"

    # Test card info line
    CARD_INFO = "color: #bd93f9; font-size: 9pt;"

    # Button states
    BUTTON_SUCCESS = "background-color: #50fa7b; color: #282a36; font-weight: bold;"
    BUTTON_ERROR = "background-color: #ff5555; color: white; font-weight: bold;"
    BUTTON_ACCENT = "background-color: #6272a4; color: white; font-weight: bold;"

    # Sidebar tooltip (VS Code-like style with Dracula theme)
    SIDEBAR_TOOLTIP = """
        QLabel {
            background-color: #1e1e2e;
            color: #f8f8f2;
            border: none;
            border-left: 3px solid #8be9fd;
            padding: 4px 8px;
            font-size: 10pt;
        }
    """
