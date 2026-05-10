from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from src.core.cms.adp.menu.models import MenuItem


MODULE_SOURCE = 'modules/equipment_ergonomics'
ROOT_ROUTE = 'EquipmentErgonomics'
ANALYSIS_ROUTE = 'EquipmentErgonomicsAnalysis'
ROOT_NAME = 'Эргономика техники'
ANALYSIS_NAME = 'Анализ данных'
ROOT_ICON = 'Wrench'


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
        root.is_active = True
        root.module_source = MODULE_SOURCE
        root.save(update_fields=['name', 'icon', 'item_type', 'is_active', 'module_source', 'updated_at'])

    child = manager.filter(module_source=MODULE_SOURCE, route_name=ANALYSIS_ROUTE, parent=root).first()
    if child is None:
        manager.create(
            name=ANALYSIS_NAME,
            route_name=ANALYSIS_ROUTE,
            icon=None,
            item_type='route',
            parent=root,
            module_source=MODULE_SOURCE,
            is_active=True,
        )
    else:
        child.name = ANALYSIS_NAME
        child.item_type = 'route'
        child.is_active = True
        child.module_source = MODULE_SOURCE
        child.save(update_fields=['name', 'item_type', 'is_active', 'module_source', 'updated_at'])

    manager.filter(module_source=MODULE_SOURCE).exclude(id__in=[root.id]).update(is_active=True)


def _deactivate_menu_items() -> int:
    manager = MenuItem.objects  # type: ignore[attr-defined]
    return manager.filter(module_source=MODULE_SOURCE, is_active=True).update(is_active=False)


class Command(BaseCommand):
    help = 'Управление плагином equipment_ergonomics: status|enable|disable (archive/purge).'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            type=str,
            choices=('status', 'enable', 'disable'),
            help='Действие: status, enable, disable.',
        )
        parser.add_argument(
            '--archive',
            action='store_true',
            help='При disable: сначала архивировать данные в modules/equipment_ergonomics/data/archives.',
        )
        parser.add_argument(
            '--archive-dir',
            type=str,
            default=None,
            help='Явный каталог архива (если не задан, используется timestamp внутри data/archives).',
        )
        parser.add_argument(
            '--purge-db',
            action='store_true',
            help='При disable: после успешного архива удалить данные из БД (опасно).',
        )

    def handle(self, *args, **options):
        from modules.equipment_ergonomics.api.services.plugin_state import (
            get_snapshot,
            set_enabled,
            is_forced_disabled,
        )
        from modules.equipment_ergonomics.api.scripts.build_dataset import (
            archive_plugin_data,
            purge_plugin_data,
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
                    'ENV override активен (EQUIPMENT_ERGONOMICS_FORCE_DISABLED=true): '
                    'включение в БД сохранится, но плагин останется выключенным до снятия override.'
                )
            set_enabled(True)
            _ensure_menu_items_active()
            snap = get_snapshot()
            self.stdout.write(f'Плагин включен: {snap.is_enabled} (forced_disabled={snap.forced_disabled})')
            self.stdout.write('Пункты меню модуля активированы.')
            return

        # disable
        archive_meta = None
        archive_path = None
        if options.get('archive'):
            archive_dir = options.get('archive_dir')
            root = Path(archive_dir) if archive_dir else None
            archive_meta = archive_plugin_data(root)
            archive_path = archive_meta.get('archive_root')
            self.stdout.write(f'Архив создан: {archive_path}')

        if options.get('purge_db'):
            if not options.get('archive'):
                raise SystemExit('Refusing to purge DB without --archive. Сначала создайте архив.')
            purge_result = purge_plugin_data()
            self.stdout.write(f'Данные удалены из БД: {purge_result}')

        set_enabled(False, archive_path=archive_path, archive_meta=archive_meta)
        deactivated_count = _deactivate_menu_items()
        snap = get_snapshot()
        self.stdout.write(f'Плагин выключен: {not snap.is_enabled} (forced_disabled={snap.forced_disabled})')
        self.stdout.write(f'Пункты меню модуля скрыты: {deactivated_count}')

