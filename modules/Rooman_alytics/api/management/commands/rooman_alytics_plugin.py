from __future__ import annotations

import json

from django.core.management.base import BaseCommand

from src.core.cms.adp.menu.models import MenuItem


MODULE_SOURCE = 'modules/Rooman_alytics'
ROOT_ROUTE = 'AnalyticsModule'
ROOT_NAME = 'Модуль анализа помещения'
ROOT_ICON = 'Armchair'

ANALYSIS_GROUP = ('Анализ помещения', 'AnalyzePage')
ANALYSIS_ROUTES = (
    ('Анализ помещения', 'AnalyzePage'),
    ('Разметить план помещения', 'LoadPlan'),
    ('Пройти анкетирование', 'SurveyStart'),
)
ADMIN_GROUP = ('Аналитические инструменты', 'ModelEditor')
ADMIN_ROUTES = (
    ('Кластеризационный анализ', 'ClusteringAnalysis'),
    ('Загрузка моделей', 'DataUpload'),
    ('Редактировать мат. модель', 'ModelEditor'),
)


def _ensure_menu_items_active() -> None:
    manager = MenuItem.objects  # type: ignore[attr-defined]
    root = manager.filter(module_source=MODULE_SOURCE, route_name=ROOT_ROUTE, parent__isnull=True).first()
    if root is None:
        root = manager.create(
            name=ROOT_NAME,
            route_name=ROOT_ROUTE,
            icon=ROOT_ICON,
            item_type='route',
            module_source=MODULE_SOURCE,
            is_active=True,
        )
    else:
        root.name = ROOT_NAME
        root.icon = ROOT_ICON
        root.item_type = 'route'
        root.module_source = MODULE_SOURCE
        root.is_active = True
        root.save(update_fields=['name', 'icon', 'item_type', 'module_source', 'is_active', 'updated_at'])

    analysis_group = _get_or_create_menu_item(
        name=ANALYSIS_GROUP[0],
        route_name=ANALYSIS_GROUP[1],
        parent=root,
        is_admin_only=False,
    )
    for item_name, route_name in ANALYSIS_ROUTES:
        _get_or_create_menu_item(
            name=item_name,
            route_name=route_name,
            parent=analysis_group,
            is_admin_only=False,
        )

    admin_group = _get_or_create_menu_item(
        name=ADMIN_GROUP[0],
        route_name=ADMIN_GROUP[1],
        parent=root,
        is_admin_only=True,
    )
    for item_name, route_name in ADMIN_ROUTES:
        _get_or_create_menu_item(
            name=item_name,
            route_name=route_name,
            parent=admin_group,
            is_admin_only=True,
        )

    manager.filter(module_source=MODULE_SOURCE).update(is_active=True)


def _deactivate_menu_items() -> int:
    manager = MenuItem.objects  # type: ignore[attr-defined]
    return manager.filter(module_source=MODULE_SOURCE, is_active=True).update(is_active=False)


def _get_or_create_menu_item(*, name: str, route_name: str, parent: MenuItem, is_admin_only: bool) -> MenuItem:
    manager = MenuItem.objects  # type: ignore[attr-defined]
    item = manager.filter(module_source=MODULE_SOURCE, route_name=route_name, parent=parent).first()
    if item is None:
        return manager.create(
            name=name,
            route_name=route_name,
            icon=None,
            item_type='route',
            parent=parent,
            module_source=MODULE_SOURCE,
            is_admin_only=is_admin_only,
            is_active=True,
        )

    item.name = name
    item.item_type = 'route'
    item.module_source = MODULE_SOURCE
    item.is_admin_only = is_admin_only
    item.is_active = True
    item.save(update_fields=['name', 'item_type', 'module_source', 'is_admin_only', 'is_active', 'updated_at'])
    return item


class Command(BaseCommand):
    help = 'Управление плагином rooman_alytics: status|enable|disable.'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            type=str,
            choices=('status', 'enable', 'disable'),
            help='Действие: status, enable, disable.',
        )

    def handle(self, *args, **options):
        from modules.Rooman_alytics.api.services.plugin_state import (
            get_snapshot,
            is_forced_disabled,
            set_enabled,
        )

        action = options['action']

        if action == 'status':
            snap = get_snapshot()
            self.stdout.write(json.dumps(snap.__dict__, ensure_ascii=False, indent=2))
            if snap.forced_disabled:
                self.stdout.write('ENV override активен: плагин принудительно выключен.')
            return

        if action == 'enable':
            if is_forced_disabled():
                self.stdout.write(
                    'ENV override активен (ROOMAN_ALYTICS_FORCE_DISABLED=true): '
                    'включение в БД сохранится, но плагин останется выключенным до снятия override.'
                )
            set_enabled(True)
            _ensure_menu_items_active()
            snap = get_snapshot()
            self.stdout.write(f'Плагин включен: {snap.is_enabled} (forced_disabled={snap.forced_disabled})')
            self.stdout.write('Пункты меню модуля активированы.')
            return

        set_enabled(False)
        deactivated_count = _deactivate_menu_items()
        snap = get_snapshot()
        self.stdout.write(f'Плагин выключен: {not snap.is_enabled} (forced_disabled={snap.forced_disabled})')
        self.stdout.write(f'Пункты меню модуля скрыты: {deactivated_count}')
