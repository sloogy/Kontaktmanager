"""Signal-Bus fuer die UI-Synchronisierung (Muster aus FPM).

Ein Widget committet, emittiert ein Signal, alle bereits geoeffneten Widgets
aktualisieren sich. Ohne Qt faellt der Bus auf eine minimale Eigenimplementierung
zurueck, damit Logik- und Servicetests headless laufen.
"""
from __future__ import annotations

try:
    from PySide6.QtCore import QObject, Signal
except ModuleNotFoundError:  # pragma: no cover - headless
    class QObject:
        pass

    class _BoundSignal:
        def __init__(self):
            self._slots = []

        def connect(self, slot):
            if callable(slot):
                self._slots.append(slot)

        def emit(self, *args, **kwargs):
            for slot in list(self._slots):
                try:
                    slot(*args, **kwargs)
                except TypeError:
                    slot()

    class _SignalDescriptor:
        def __init__(self, *args, **kwargs):
            self._name = None

        def __set_name__(self, owner, name):
            self._name = f"_{name}_fallback"

        def __get__(self, instance, owner):
            if instance is None:
                return self
            sig = getattr(instance, self._name, None)
            if sig is None:
                sig = _BoundSignal()
                setattr(instance, self._name, sig)
            return sig

    def Signal(*args, **kwargs):
        return _SignalDescriptor(*args, **kwargs)


class AppEventBus(QObject):
    """Singleton. Immer ueber ``instance()`` ansprechen."""

    contacts_changed = Signal()
    interactions_changed = Signal()
    activities_changed = Signal()
    focus_changed = Signal()
    settings_changed = Signal()

    _instance: "AppEventBus | None" = None

    @classmethod
    def instance(cls) -> "AppEventBus":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def emit_contacts(self) -> None:
        self.contacts_changed.emit()
        self.focus_changed.emit()

    def emit_interactions(self) -> None:
        self.interactions_changed.emit()
        self.focus_changed.emit()

    def emit_activities(self) -> None:
        self.activities_changed.emit()
        self.focus_changed.emit()

    def emit_all(self) -> None:
        self.contacts_changed.emit()
        self.interactions_changed.emit()
        self.activities_changed.emit()
        self.settings_changed.emit()
        self.focus_changed.emit()
