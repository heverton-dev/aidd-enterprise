import uuid
import datetime
from collections import defaultdict
from typing import Callable, Any, Dict, Optional


class EventBus:
    """EventBus Pub/Sub com enriquecimento de metadados, tracing UUID e isolamento de erros."""
    def __init__(self):
        self._listeners = defaultdict(list)

    def on(self, event_name: str, handler: Callable[[Any], None]):
        self._listeners[event_name].append(handler)

    def emit(self, event_name: str, data: Any = None, origin_module: str = "system") -> Dict[str, Any]:
        payload = data if isinstance(data, dict) else ({"value": data} if data is not None else {})
        if isinstance(payload, dict):
            if "event_id" not in payload:
                payload["event_id"] = uuid.uuid4().hex[:12]
            if "event_name" not in payload:
                payload["event_name"] = event_name
            if "origin_module" not in payload:
                payload["origin_module"] = origin_module
            if "timestamp" not in payload:
                payload["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

        for handler in self._listeners.get(event_name, []):
            try:
                handler(payload)
            except Exception as e:
                print(f"[EVENT_ERROR] Falha ao processar evento '{event_name}': {e}")
        return payload
