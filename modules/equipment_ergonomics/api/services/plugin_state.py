from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from django.utils import timezone

from ..models import EquipmentErgonomicsPluginState


PLUGIN_KEY = 'equipment_ergonomics'
ENV_FORCE_DISABLED = 'EQUIPMENT_ERGONOMICS_FORCE_DISABLED'


@dataclass(frozen=True)
class PluginStateSnapshot:
    plugin_key: str
    is_enabled: bool
    forced_disabled: bool
    updated_at: str | None
    disabled_at: str | None
    last_archive_path: str | None
    last_archive_meta: dict[str, Any] | None


def _env_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {'1', 'true', 'yes', 'y', 'on'}


def is_forced_disabled() -> bool:
    return _env_truthy(os.getenv(ENV_FORCE_DISABLED))


def get_or_create_state() -> EquipmentErgonomicsPluginState:
    state, _ = EquipmentErgonomicsPluginState.objects.get_or_create(
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
        last_archive_path=state.last_archive_path or None,
        last_archive_meta=state.last_archive_meta or None,
    )


def set_enabled(enabled: bool, *, archive_path: str | None = None, archive_meta: dict[str, Any] | None = None) -> EquipmentErgonomicsPluginState:
    state = get_or_create_state()
    state.is_enabled = bool(enabled)
    if enabled:
        state.disabled_at = None
    else:
        state.disabled_at = timezone.now()
    if archive_path is not None:
        state.last_archive_path = archive_path
    if archive_meta is not None:
        state.last_archive_meta = archive_meta
    state.save(update_fields=['is_enabled', 'disabled_at', 'last_archive_path', 'last_archive_meta', 'updated_at'])
    return state

