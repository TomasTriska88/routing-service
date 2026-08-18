class Hass:
    """Minimal AppDaemon compatibility shim used by the standalone PND runner."""

    def __init__(self, *args, **kwargs):
        self.args = {}
        self._states = {}

    def listen_event(self, *args, **kwargs):
        return None

    def set_state(self, entity_id, state=None, attributes=None, **kwargs):
        value = {
            "state": state,
            "attributes": dict(attributes or {}),
        }
        self._states[entity_id] = value
        return value
