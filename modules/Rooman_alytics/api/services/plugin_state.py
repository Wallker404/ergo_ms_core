from __future__ import annotations

import os
from dataclasses import dataclass

from django.utils import timezone

from ..models import RoomAnalyticsPluginState


PLUGIN_KEY = 'rooman_alytics'
ENV_FORCE_DISABLED = 'ROOMAN_ALYTICS_FORCE_DISABLED'


@dataclass(frozen=True)
class PluginStateSnapshot:
    plugin_key: str
    is_enabled: bool
    forced_disabled: bool
    updated_at: str | None
    disabled_at: str | None


def _env_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {'1', 'true', 'yes', 'y', 'on'}


def is_forced_disabled() -> bool:
    return _env_truthy(os.getenv(ENV_FORCE_DISABLED))


def get_or_create_state() -> RoomAnalyticsPluginState:
    state, _ = RoomAnalyticsPluginState.objects.get_or_create(
        plugin_key=PLUGIN_KEY,
        defaults={'is_enabled': False},
    )
    return state


def is_enabled() -> bool:
    if is_forced_disabled():
        return False
    state = get_or_create_state()
    return bool(state.is_enabled)


def get_snapshot() -> PluginStateSnapshot:
    state = get_or_create_state()
    forced = is_forced_disabled()
    enabled = bool(state.is_enabled) and not forced
    return PluginStateSnapshot(
        plugin_key=state.plugin_key,
        is_enabled=enabled,
        forced_disabled=forced,
        updated_at=state.updated_at.isoformat() if state.updated_at else None,
        disabled_at=state.disabled_at.isoformat() if state.disabled_at else None,
    )


def set_enabled(enabled: bool) -> RoomAnalyticsPluginState:
    state = get_or_create_state()
    state.is_enabled = bool(enabled)
    state.disabled_at = None if enabled else timezone.now()
    state.save(update_fields=['is_enabled', 'disabled_at', 'updated_at'])
    return state
