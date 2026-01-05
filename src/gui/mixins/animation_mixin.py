"""Mixin classes providing standardized animation behavior for Qt widgets.

This module provides reusable animation functionality using configuration values
from the application config. It eliminates repetitive animation setup code and
handles signal connection/disconnection cleanly.
"""

import contextlib
from collections.abc import Callable

from PySide6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QPropertyAnimation,
    QVariantAnimation,
)
from PySide6.QtWidgets import QWidget

from src.config import config


class AnimatedWidgetMixin:
    """Mixin providing standardized animation behavior using config values.

    This mixin can be used with QWidget subclasses to add consistent animation
    capabilities. It manages a QVariantAnimation with proper signal handling.

    Attributes:
        _variant_animation: The internal QVariantAnimation instance.
        _value_changed_callback: Currently connected value changed callback.
    """

    _variant_animation: QVariantAnimation | None = None
    _value_changed_callback: Callable | None = None

    def setup_variant_animation(self: QWidget) -> QVariantAnimation:
        """Create and configure a QVariantAnimation with config-based settings.

        Returns:
            Configured QVariantAnimation ready for use.
        """
        self._variant_animation = QVariantAnimation(self)
        self._variant_animation.setDuration(config.ui.animation_duration_ms)
        self._variant_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        return self._variant_animation

    def animate_value(
        self: QWidget,
        start_value: int,
        end_value: int,
        on_value_changed: Callable[[int], None],
    ) -> None:
        """Start animation from start_value to end_value.

        Properly disconnects any previously connected callback before connecting
        the new one, avoiding the need for manual connection tracking.

        Args:
            start_value: Starting value for the animation.
            end_value: Ending value for the animation.
            on_value_changed: Callback invoked with each animation value update.
        """
        if self._variant_animation is None:
            self.setup_variant_animation()

        # Safely disconnect previous callback if one exists
        if self._value_changed_callback is not None:
            with contextlib.suppress(RuntimeError):
                self._variant_animation.valueChanged.disconnect(self._value_changed_callback)

        self._variant_animation.setStartValue(start_value)
        self._variant_animation.setEndValue(end_value)
        self._variant_animation.valueChanged.connect(on_value_changed)
        self._value_changed_callback = on_value_changed
        self._variant_animation.start()

    def stop_variant_animation(self: QWidget) -> None:
        """Stop any running animation safely."""
        if (
            self._variant_animation is not None
            and self._variant_animation.state() == QAbstractAnimation.State.Running
        ):
            self._variant_animation.stop()

    @property
    def is_animation_running(self: QWidget) -> bool:
        """Check if the animation is currently running."""
        if self._variant_animation is None:
            return False
        return self._variant_animation.state() == QAbstractAnimation.State.Running


class AnimatedPropertyMixin:
    """Mixin for QPropertyAnimation-based animations.

    Use this for animating Qt properties like minimumWidth, geometry, etc.
    """

    _property_animation: QPropertyAnimation | None = None
    _finished_callback: Callable | None = None

    def setup_property_animation(self: QWidget, target_property: bytes) -> QPropertyAnimation:
        """Create and configure a QPropertyAnimation with config-based settings.

        Args:
            target_property: The property to animate (e.g., b"minimumWidth").

        Returns:
            Configured QPropertyAnimation ready for use.
        """
        self._property_animation = QPropertyAnimation(self, target_property)
        self._property_animation.setDuration(config.ui.animation_duration_ms)
        self._property_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        return self._property_animation

    def animate_property(
        self: QWidget,
        start_value: int,
        end_value: int,
        on_finished: Callable[[], None] | None = None,
    ) -> None:
        """Start property animation from start_value to end_value.

        Args:
            start_value: Starting value for the animation.
            end_value: Ending value for the animation.
            on_finished: Optional callback invoked when animation completes.
        """
        if self._property_animation is None:
            raise RuntimeError(
                "Property animation not initialized. Call setup_property_animation first."
            )

        # Safely disconnect previous callback
        if self._finished_callback is not None:
            with contextlib.suppress(RuntimeError):
                self._property_animation.finished.disconnect(self._finished_callback)

        self._property_animation.setStartValue(start_value)
        self._property_animation.setEndValue(end_value)

        if on_finished is not None:
            self._property_animation.finished.connect(on_finished)
            self._finished_callback = on_finished

        self._property_animation.start()

    def stop_property_animation(self: QWidget) -> None:
        """Stop any running property animation safely."""
        if (
            self._property_animation is not None
            and self._property_animation.state() == QAbstractAnimation.State.Running
        ):
            self._property_animation.stop()
