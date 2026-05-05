from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand


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
            snap = get_snapshot()
            self.stdout.write(f'Плагин включен: {snap.is_enabled} (forced_disabled={snap.forced_disabled})')
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
        snap = get_snapshot()
        self.stdout.write(f'Плагин выключен: {not snap.is_enabled} (forced_disabled={snap.forced_disabled})')

