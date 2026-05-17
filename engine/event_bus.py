"""
Simple publish/subscribe event system.
Screens and systems communicate by posting events rather than calling
each other directly — keeps everything decoupled.
"""
from collections import defaultdict
from typing import Callable, Any


class EventBus:
    def __init__(self):
        self._listeners: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: str, callback: Callable) -> None:
        self._listeners[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        self._listeners[event_type].remove(callback)

    def post(self, event_type: str, **data: Any) -> None:
        for callback in self._listeners[event_type]:
            callback(**data)


bus = EventBus()
