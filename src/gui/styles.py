"""Centralized stylesheet definitions for the application.

This module contains all style constants used across the GUI,
following a dark/grey/white color scheme with blue accent.

Color Palette:
    Dark backgrounds:    #1e1e2e (darkest), #21222c (dark), #282a36 (base), #2f3140 (elevated)
    Grey borders:        #44475a (subtle), #5a5e72 (visible)
    White text:          #f8f8f2 (primary), #c0c0c0 (muted)
    Blue accent:         #6ea8fe (primary), #4a8fe7 (hover), #3d7dd9 (active)
    Status colors:       #6ea8fe (info/connected), #888888 (disconnected/muted)
"""


class Colors:
    """Application color palette.

    Attributes:
        BG_DARKEST: Darkest background color, used for sidebars and tooltips.
        BG_DARK: Dark background, used for main panels and status bars.
        BG_BASE: Base background color, used for output areas.
        BG_ELEVATED: Lightest background, used for cards (elevated).
        BORDER_SUBTLE: Subtle border color.
        BORDER_VISIBLE: More visible border.
        TEXT_PRIMARY: Primary text color.
        TEXT_MUTED: Muted text color.
        ACCENT: Primary accent (blue).
        ACCENT_HOVER: Hover state for accent.
        ACCENT_ACTIVE: Active state for accent.
        ACCENT_DIM: Dimmed accent.
        STATUS_CONNECTED: Color for connected/success status.
        STATUS_DISCONNECTED: Color for disconnected/neutral status.
    """

    # Backgrounds (dark to light)
    BG_DARKEST = "#1e1e2e"
    BG_DARK = "#21222c"
    BG_BASE = "#282a36"
    BG_ELEVATED = "#2f3140"

    # Borders
    BORDER_SUBTLE = "#44475a"
    BORDER_VISIBLE = "#5a5e72"

    # Text
    TEXT_PRIMARY = "#f8f8f2"
    TEXT_MUTED = "#a0a0a0"

    # Blue accent (primary interaction color)
    ACCENT = "#6ea8fe"
    ACCENT_HOVER = "#4a8fe7"
    ACCENT_ACTIVE = "#3d7dd9"
    ACCENT_DIM = "#4a6785"

    # Status (minimal, blue-based)
    STATUS_CONNECTED = "#6ea8fe"  # Blue - connected/success
    STATUS_DISCONNECTED = "#888888"  # Grey - disconnected/neutral


class Styles:
    """Application-wide style constants.

    Attributes:
        CONSOLE: Stylesheet for the console widget.
        TEST_CARD: Stylesheet for test card frames.
        CARD_TITLE: Inline style for test card titles.
        CARD_INFO: Inline style for test card info lines.
        BUTTON_SUCCESS: Inline style for success buttons.
        BUTTON_ERROR: Inline style for error buttons.
        BUTTON_ACCENT: Inline style for accent buttons.
        SIDEBAR_TOOLTIP: Stylesheet for the sidebar tooltip.
        STATUS_BAR: Stylesheet for the status bar.
        SCOPE_CONNECTED: Inline style for connected scope label.
        SCOPE_DISCONNECTED: Inline style for disconnected scope label.
        MENU_BAR: Stylesheet for the QMenuBar and QMenu.
        TITLE_BAR: Stylesheet for the title bar widget.
        COLLAPSIBLE_PANEL: Stylesheet for collapsible panels.
        PANEL_TOGGLE_BUTTON: Stylesheet for panel toggle buttons.
        PANEL_TOGGLE_BUTTON_VERTICAL: Stylesheet for vertical panel toggle buttons.
    """

    # Console widget
    CONSOLE = f"""
        QPlainTextEdit {{
            background-color: {Colors.BG_BASE};
            color: {Colors.TEXT_PRIMARY};
            font-family: 'Consolas', 'Monospace';
            font-size: 10pt;
            border: 1px solid {Colors.BORDER_SUBTLE};
            border-radius: 4px;
            padding: 4px;
        }}
    """

    # Test card container
    TEST_CARD = f"""
        QFrame {{
            background-color: {Colors.BG_ELEVATED};
            border-radius: 8px;
            border: 1px solid {Colors.BORDER_SUBTLE};
        }}
        QLabel {{
            border: none;
            color: {Colors.TEXT_PRIMARY};
        }}
    """

    # Test card title
    CARD_TITLE = f"font-weight: bold; font-size: 11pt; color: {Colors.ACCENT};"

    # Test card info line
    CARD_INFO = f"color: {Colors.TEXT_MUTED}; font-size: 9pt;"

    # Button states
    BUTTON_SUCCESS = (
        f"background-color: {Colors.ACCENT}; color: {Colors.BG_DARKEST}; font-weight: bold;"
    )
    BUTTON_ERROR = (
        f"background-color: {Colors.BORDER_VISIBLE};color: {Colors.TEXT_PRIMARY};font-weight: bold;"
    )
    BUTTON_ACCENT = (
        f"background-color: {Colors.ACCENT_DIM}; color: {Colors.TEXT_PRIMARY}; font-weight: bold;"
    )

    # Sidebar tooltip
    SIDEBAR_TOOLTIP = f"""
        QLabel {{
            background-color: {Colors.BG_DARKEST};
            color: {Colors.TEXT_PRIMARY};
            border: none;
            border-left: 3px solid {Colors.ACCENT};
            padding: 4px 8px;
            font-size: 10pt;
        }}
    """

    # Status bar
    STATUS_BAR = f"""
        QStatusBar {{
            background-color: {Colors.BG_DARK};
            color: {Colors.TEXT_PRIMARY};
            border-top: 1px solid {Colors.BORDER_SUBTLE};
            font-size: 9pt;
            padding: 2px 8px;
        }}
        QStatusBar::item {{
            border: none;
        }}
    """

    # Status bar scope label styles
    SCOPE_CONNECTED = f"color: {Colors.STATUS_CONNECTED}; padding: 0 8px;"
    SCOPE_DISCONNECTED = f"color: {Colors.STATUS_DISCONNECTED}; padding: 0 8px;"

    # Menu bar (matching qt-material dark_blue theme)
    # Theme colors: primary=#448aff, secondary=#232629, secondaryLight=#4f5b62
    MENU_BAR = """
        QMenuBar {
            background-color: transparent;
            color: #ffffff;
            border: none;
            padding: 0;
        }
        QMenuBar::item {
            background-color: transparent;
            padding: 8px 12px;
            border-radius: 4px;
        }
        QMenuBar::item:selected {
            background-color: #4f5b62;
        }
        QMenuBar::item:!selected {
            background-color: transparent;
        }
        QMenu {
            background-color: #31363b;
            color: #ffffff;
            border: 1px solid #4f5b62;
            padding: 4px;
        }
        QMenu::item {
            padding: 6px 24px;
            border-radius: 4px;
        }
        QMenu::item:selected {
            background-color: #448aff;
        }
        QMenu::separator {
            height: 1px;
            background-color: #4f5b62;
            margin: 4px 8px;
        }
    """

    # Title bar (contains menu bar and window buttons)
    TITLE_BAR = f"""
        QWidget {{
            background-color: {Colors.BG_DARK};
        }}
        QPushButton {{
            background-color: transparent;
            border: none;
            padding: 8px 12px;
            border-radius: 4px;
        }}
        QPushButton:hover {{
            background-color: {Colors.ACCENT_DIM};
        }}
        QPushButton:pressed {{
            background-color: {Colors.ACCENT};
        }}
    """

    TITLE_BAR_BUTTON = f"""
        QPushButton {{
            background-color: transparent;
            border: none;
            padding: 8px 12px;
            border-radius: 4px;
        }}
        QPushButton:hover {{
            background-color: {Colors.ACCENT_DIM};
        }}
        QPushButton:pressed {{
            background-color: {Colors.ACCENT};
        }}
    """

    # Collapsible panel container
    COLLAPSIBLE_PANEL = f"""
        background-color: {Colors.BG_DARK};
        border: none;
    """

    # Panel toggle button
    PANEL_TOGGLE_BUTTON = f"""
        QPushButton {{
            background-color: {Colors.BG_DARK};
            color: {Colors.TEXT_MUTED};
            border: none;
            border-bottom: 1px solid {Colors.BORDER_SUBTLE};
            font-size: 9pt;
            font-weight: bold;
            text-align: left;
            padding: 4px 8px;
        }}
        QPushButton:hover {{
            background-color: {Colors.BG_ELEVATED};
            color: {Colors.TEXT_PRIMARY};
        }}
    """

    # Vertical panel toggle button (for side panels)
    PANEL_TOGGLE_BUTTON_VERTICAL = f"""
        QPushButton {{
            background-color: {Colors.BG_DARK};
            color: {Colors.TEXT_MUTED};
            border: none;
            border-left: 1px solid {Colors.BORDER_SUBTLE};
            font-size: 9pt;
            font-weight: bold;
            text-align: left;
            padding: 4px;
        }}
        QPushButton:hover {{
            background-color: {Colors.BG_ELEVATED};
            color: {Colors.TEXT_PRIMARY};
        }}
    """
