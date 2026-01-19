"""Animation utility functions for the GUI.

This module provides reusable helper functions for creating and managing
Qt animations, following the DRY principle.
"""

from collections.abc import Callable

from PySide6.QtCore import QEasingCurve, QObject, QVariantAnimation

from src.config import config


def animate_value(
    parent: QObject,
    start: float,
    end: float,
    callback: Callable[[float], None],
    on_finished: Callable[[], None] | None = None,
    duration: int | None = None,
    easing: QEasingCurve.Type | None = None,
) -> QVariantAnimation:
    """Create and start a value animation properly configured with defaults.

    Args:
        parent: The parent object for the animation (memory management).
        start: The starting value.
        end: The target value.
        callback: Function to call on value change.
        on_finished: Optional function to call when animation finishes.
        duration: Animation duration in ms. Defaults to config if None.
        easing: Easing curve type. Defaults to config if None.

    Returns:
        The created (and started) QVariantAnimation object.
        Caller should store this reference to prevent garbage collection
        or to stop it prematurely.
    """
    if duration is None:
        duration = config.ui.panel_animation_duration_ms

    if easing is None:
        easing = getattr(
            QEasingCurve.Type,
            config.ui.panel_animation_easing,
            QEasingCurve.Type.InOutQuad,
        )

    animation = QVariantAnimation(parent)
    animation.setDuration(duration)
    animation.setEasingCurve(easing)  # type: ignore # PySide6 typing quirk
    animation.setStartValue(start)
    animation.setEndValue(end)

    # We need to wrap the callback because valueChanged emits variants,
    # but QVariantAnimation handles the casting for float/int ranges mostly.
    # However, strict typing suggests we receive the value.
    animation.valueChanged.connect(callback)  # type: ignore

    if on_finished:
        animation.finished.connect(on_finished)

    animation.start()
    return animation
