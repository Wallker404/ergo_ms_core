from src.core.integrations import bridge

from .services.plugin_state import is_enabled


@bridge.provide_op('equipment_ergonomics.is_enabled')
def _equipment_ergonomics_is_enabled():
    return bool(is_enabled())
