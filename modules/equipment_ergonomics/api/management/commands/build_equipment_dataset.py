"""
Сборка общего датасета модуля equipment_ergonomics.

Загружает данные из открытых источников (OWID Energy), сохраняет сырой ответ и
нормализованные показатели в БД, при необходимости экспортирует датасет в CSV.

Использование:
  ergoms api build_equipment_dataset
  ergoms api build_equipment_dataset --export-default   # экспорт в modules/equipment_ergonomics/data/equipment_dataset.csv
  ergoms api build_equipment_dataset --export path/to/dataset.csv
  ergoms api build_equipment_dataset --export dataset.csv --no-raw
  ergoms api build_equipment_dataset --import path/to/existing.csv
  ergoms api build_equipment_dataset --export-only path/to/export.csv
  ergoms api build_equipment_dataset --backfill-owid   # заполнить единицы и класс у уже загруженных OWID
  ergoms api build_equipment_dataset --source world_bank   # только World Bank API
  ergoms api build_equipment_dataset --source all --export-default   # OWID + World Bank + экспорт в data/
  ergoms api build_equipment_dataset --file-import modules/equipment_ergonomics/data/raw/ewaste.csv --file-source ewaste
  # Локальный World Bank (CSV в data/raw модуля или legacy core/data/raw):
  ergoms api build_equipment_dataset --world-bank-from-raw
  ergoms api build_equipment_dataset --world-bank-from-raw --world-bank-raw-dir path/to/raw
"""

from pathlib import Path

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Сборка датасета: загрузка из API (OWID, World Bank) и/или импорт из файлов (CSV/JSON), экспорт в CSV.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force-when-disabled',
            action='store_true',
            help='Разрешить сборку/импорт даже если плагин выключен (используйте осознанно).',
        )
        parser.add_argument(
            '--export',
            type=str,
            default=None,
            help='После загрузки экспортировать датасет в указанный CSV.',
        )
        parser.add_argument(
            '--export-default',
            action='store_true',
            help=(
                'Если не задан --export: после загрузки экспортировать в '
                'modules/equipment_ergonomics/data/equipment_dataset.csv'
            ),
        )
        parser.add_argument(
            '--export-only',
            type=str,
            default=None,
            help='Только экспорт текущих данных из БД в CSV (без загрузки OWID).',
        )
        parser.add_argument(
            '--import',
            dest='import_path',
            type=str,
            default=None,
            help='Импортировать датасет из CSV в БД (колонки: country_code, year, indicator_name, value, ...).',
        )
        parser.add_argument(
            '--no-raw',
            action='store_true',
            help='Не сохранять сырой ответ API в ExternalDataFetch.',
        )
        parser.add_argument(
            '--max-rows',
            type=int,
            default=None,
            help='Максимум строк из OWID для разбора (для теста).',
        )
        parser.add_argument(
            '--backfill-owid',
            action='store_true',
            help='Только заполнить единицы и класс техники у уже загруженных записей OWID (без загрузки).',
        )
        parser.add_argument(
            '--source',
            type=str,
            default='owid',
            choices=('owid', 'world_bank', 'all'),
            help='Источник загрузки: owid (по умолчанию), world_bank, all (OWID + World Bank).',
        )
        parser.add_argument(
            '--file-import',
            type=str,
            default=None,
            help='Импорт из готового файла по конфигу FILE_SOURCE_CONFIG (см. build_dataset.py).',
        )
        parser.add_argument(
            '--file-source',
            type=str,
            default=None,
            help='Ключ источника в FILE_SOURCE_CONFIG (обязателен при --file-import).',
        )
        parser.add_argument(
            '--file-save-raw',
            action='store_true',
            help='При импорте из файла сохранить сырое содержимое в ExternalDataFetch.',
        )
        parser.add_argument(
            '--world-bank-from-raw',
            action='store_true',
            help=(
                'Загружать World Bank не через API, а из локальных CSV (API_*_DS2_*.csv): '
                'сначала modules/equipment_ergonomics/data/raw, затем legacy core/data/raw.'
            ),
        )
        parser.add_argument(
            '--world-bank-raw-dir',
            type=str,
            default=None,
            help='Один каталог для поиска CSV World Bank (вместо списка по умолчанию).',
        )

    def handle(self, *args, **options):
        from modules.equipment_ergonomics.api.services.plugin_state import is_enabled

        if not is_enabled() and not options.get('force_when_disabled'):
            self.stderr.write(
                self.style.ERROR(
                    'Плагин equipment_ergonomics выключен. '
                    'Включите его (ergoms api equipment_ergonomics_plugin enable) '
                    'или используйте --force-when-disabled.'
                )
            )
            return

        from modules.equipment_ergonomics.api.scripts.build_dataset import (
            run_build_full,
            run_fetch_world_bank_and_save,
            run_import_world_bank_from_raw,
            export_dataset_to_csv,
            import_dataset_from_csv,
            import_from_structured_file,
            backfill_owid_units_and_class,
            get_default_dataset_csv_path,
        )

        import_path = options.get('import_path')
        export_only = options.get('export_only')
        export_path = options.get('export')
        if options.get('export_default') and not export_path:
            export_path = str(get_default_dataset_csv_path())
        no_raw = options.get('no_raw')
        max_rows = options.get('max_rows')
        backfill_owid = options.get('backfill_owid')
        source = options.get('source', 'owid')
        file_import_path = options.get('file_import')
        file_source_key = options.get('file_source')
        file_save_raw = options.get('file_save_raw', False)
        world_bank_from_raw = options.get('world_bank_from_raw', False)
        world_bank_raw_dir = options.get('world_bank_raw_dir')

        if file_import_path:
            path = Path(file_import_path)
            if not path.exists():
                self.stderr.write(self.style.ERROR(f'Файл не найден: {path}'))
                return
            if not file_source_key:
                self.stderr.write(self.style.ERROR('Укажите --file-source (ключ из FILE_SOURCE_CONFIG).'))
                return
            self.stdout.write(f'Импорт из файла {path} (источник: {file_source_key}) ...')
            try:
                created, skipped = import_from_structured_file(
                    path, file_source_key, save_raw_to_db=file_save_raw,
                )
                self.stdout.write(self.style.SUCCESS(f'Импорт: создано {created}, пропущено {skipped}'))
            except Exception as e:
                self.stderr.write(self.style.ERROR(str(e)))
            return

        if backfill_owid:
            self.stdout.write('Заполнение единиц и класса техники у записей OWID ...')
            try:
                updated, total = backfill_owid_units_and_class()
                self.stdout.write(
                    self.style.SUCCESS(f'Обновлено записей: {updated} из {total} OWID.')
                )
            except Exception as e:
                self.stderr.write(self.style.ERROR(str(e)))
            return

        if import_path:
            path = Path(import_path)
            if not path.exists():
                self.stderr.write(self.style.ERROR(f'Файл не найден: {path}'))
                return
            self.stdout.write(f'Импорт из {path} ...')
            try:
                created, skipped = import_dataset_from_csv(path)
                self.stdout.write(self.style.SUCCESS(f'Импорт: создано {created}, пропущено {skipped}'))
            except Exception as e:
                self.stderr.write(self.style.ERROR(str(e)))
            return

        if export_only:
            path = Path(export_only)
            self.stdout.write(f'Экспорт в {path} ...')
            try:
                n = export_dataset_to_csv(path)
                self.stdout.write(self.style.SUCCESS(f'Экспортировано строк: {n}'))
            except Exception as e:
                self.stderr.write(self.style.ERROR(str(e)))
            return

        total_created = 0
        if source in ('owid', 'all'):
            self.stdout.write('Загрузка OWID Energy и сохранение в БД ...')
            result = run_build_full(
                export_path=None,
                save_raw=not no_raw,
                max_owid_rows=max_rows,
            )
            if result.get('error'):
                self.stderr.write(self.style.ERROR(result['error']))
            else:
                total_created += result.get('rows_created', 0)
                self.stdout.write(self.style.SUCCESS(f"OWID: загружено записей {result.get('rows_created', 0)}."))
        if source in ('world_bank', 'all'):
            if world_bank_from_raw:
                self.stdout.write(
                    'Импорт World Bank из локальных CSV (модуль data/raw и при отсутствии — core/data/raw) ...'
                )
                raw_dirs_kw = Path(world_bank_raw_dir) if world_bank_raw_dir else None
                wb_result = run_import_world_bank_from_raw(
                    save_raw_to_db=not no_raw,
                    raw_dirs=raw_dirs_kw,
                )
            else:
                self.stdout.write('Загрузка World Bank API и сохранение в БД ...')
                wb_result = run_fetch_world_bank_and_save(save_raw=not no_raw)
            if wb_result.get('error'):
                self.stderr.write(self.style.ERROR(wb_result['error']))
            else:
                total_created += wb_result.get('rows_created', 0)
                self.stdout.write(self.style.SUCCESS(f"World Bank: загружено записей {wb_result.get('rows_created', 0)}."))
        if export_path:
            path = Path(export_path)
            self.stdout.write(f'Экспорт в {path} ...')
            try:
                n = export_dataset_to_csv(path)
                self.stdout.write(self.style.SUCCESS(f'Экспортировано строк: {n}'))
            except Exception as e:
                self.stderr.write(self.style.ERROR(str(e)))
        if total_created and not export_path:
            self.stdout.write(self.style.SUCCESS(f'Всего загружено записей: {total_created}.'))
