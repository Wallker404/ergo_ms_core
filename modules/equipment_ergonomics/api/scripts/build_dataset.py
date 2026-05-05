"""
Сборка общего датасета для модуля equipment_ergonomics.

Поток по DATA_SOURCES_AND_CSV.md:
- Загрузка из открытых источников (OWID Energy, при необходимости World Bank и др.)
- Сохранение сырого ответа в ExternalDataFetch
- Разбор и запись нормализованных показателей в EquipmentMetricByCountry
- Экспорт общего датасета в CSV для дальнейшей работы в модуле
"""

import csv
import io
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen, Request

from django.db import transaction

logger = logging.getLogger(__name__)

# --- Источники данных: API и файлы (CSV/JSON/Excel) ---
# Все ответы API сохраняются в ExternalDataFetch; нормализованные показатели — в EquipmentMetricByCountry.
# Файлы загружаются по пути или через импорт, при необходимости сырое содержимое можно сохранить в БД.

# URL открытых датасетов (OWID Energy — агрегированные показатели по странам/годам)
OWID_ENERGY_CSV_URL = (
    'https://nyc3.digitaloceanspaces.com/owid-public/data/energy/owid-energy-data.csv'
)

# Колонки OWID, которые не являются числовыми показателями (пропускаем при разборе)
OWID_SKIP_COLUMNS = {'country', 'year', 'iso_code', 'population', 'gdp'}

# Единицы измерения по показателям OWID (явный маппинг + вывод по имени, см. _owid_unit_from_name)
OWID_INDICATOR_UNITS = {
    'electricity_demand': 'TWh',
    'electricity_demand_per_capita': 'kWh',
    'electricity_generation': 'TWh',
    'electricity_share_energy': '%',
    'energy_per_capita': 'kWh',
    'energy_per_gdp': 'kWh/$',
    'primary_energy_consumption': 'TWh',
    'coal_consumption': 'TWh',
    'coal_production': 'TWh',
    'coal_share_elec': '%',
    'coal_share_energy': '%',
    'gas_consumption': 'TWh',
    'gas_production': 'TWh',
    'gas_share_elec': '%',
    'gas_share_energy': '%',
    'oil_consumption': 'TWh',
    'oil_production': 'TWh',
    'oil_share_elec': '%',
    'oil_share_energy': '%',
    'nuclear_consumption': 'TWh',
    'nuclear_share_elec': '%',
    'nuclear_share_energy': '%',
    'hydro_consumption': 'TWh',
    'hydro_share_elec': '%',
    'hydro_share_energy': '%',
    'solar_consumption': 'TWh',
    'solar_share_elec': '%',
    'solar_share_energy': '%',
    'wind_consumption': 'TWh',
    'wind_share_elec': '%',
    'wind_share_energy': '%',
    'renewables_consumption': 'TWh',
    'renewables_share_elec': '%',
    'renewables_share_energy': '%',
    'renewable_consumption': 'TWh',
    'low_carbon_consumption': 'TWh',
    'low_carbon_share_elec': '%',
    'low_carbon_share_energy': '%',
    'fossil_fuel_consumption': 'TWh',
    'fossil_share_elec': '%',
    'fossil_share_energy': '%',
    'biofuel_consumption': 'TWh',
    'biofuel_share_elec': '%',
    'biofuel_share_energy': '%',
    'other_renewable_consumption': 'TWh',
    'other_renewable_electricity': 'TWh',
    'other_renewables_share_elec': '%',
    'other_renewables_share_energy': '%',
    'carbon_intensity_elec': 'g CO₂/kWh',
    'greenhouse_gas_emissions': 'Mt CO₂',
    'net_elec_imports': 'TWh',
    'net_elec_imports_share_demand': '%',
    'per_capita_electricity': 'kWh',
}

# Класс техники по умолчанию для общих показателей энергии (первичная энергия, энергия на душу и т.д.)
OWID_ENERGY_CLASS_CODE = 'energy_aggregate'

# Подклассы энергетики для разбивки показателей OWID (в фильтрах и таблице отображаются отдельно)
OWID_ENERGY_SUBCLASSES = (
    'energy_coal',      # уголь
    'energy_gas',       # газ
    'energy_oil',       # нефть
    'energy_nuclear',   # ядерная
    'energy_renewables', # ВИЭ (гидро, солнце, ветер, биотопливо, прочие ВИЭ)
    'energy_fossil',    # ископаемое топливо
    'energy_low_carbon', # низкоуглеродная
    'energy_electricity', # электроэнергия (спрос, выработка)
    'energy_emissions',  # выбросы ПГ, углеродоёмкость
)


def _owid_equipment_class_code(indicator_name: str) -> str:
    """Определяет код класса техники по имени показателя OWID."""
    name = indicator_name.lower()
    if name.startswith('coal_'):
        return 'energy_coal'
    if name.startswith('gas_'):
        return 'energy_gas'
    if name.startswith('oil_'):
        return 'energy_oil'
    if name.startswith('nuclear_'):
        return 'energy_nuclear'
    if name.startswith('hydro_') or name.startswith('solar_') or name.startswith('wind_'):
        return 'energy_renewables'
    if name.startswith('biofuel_') or name.startswith('other_renewable') or name.startswith('other_renewables_'):
        return 'energy_renewables'
    if name.startswith('renewables_') or name in ('renewable_consumption',):
        return 'energy_renewables'
    if name.startswith('fossil_'):
        return 'energy_fossil'
    if name.startswith('low_carbon_'):
        return 'energy_low_carbon'
    if name.startswith('electricity_') or name in ('per_capita_electricity',) or name.startswith('net_elec_'):
        return 'energy_electricity'
    if 'greenhouse_gas' in name or 'carbon_intensity' in name:
        return 'energy_emissions'
    # первичная энергия, энергия на душу, изменение потребления и т.д.
    return OWID_ENERGY_CLASS_CODE


def _owid_unit_from_name(indicator_name: str) -> str:
    """Выводит единицу измерения по имени показателя OWID, если нет в OWID_INDICATOR_UNITS."""
    name = indicator_name.lower()
    if '_change_pct' in name or '_share_' in name or name.endswith('_pct'):
        return '%'
    if '_change_twh' in name:
        return 'TWh'
    if '_per_capita' in name or '_elec_per_capita' in name or name == 'per_capita_electricity':
        return 'kWh'
    if '_consumption' in name or '_electricity' in name or '_production' in name or 'net_elec_imports' in name:
        return 'TWh'
    if 'carbon_intensity' in name:
        return 'g CO₂/kWh'
    if 'greenhouse_gas' in name:
        return 'Mt CO₂'
    if 'share' in name:
        return '%'
    return ''


def _owid_unit(indicator_name: str) -> str:
    """Единица для показателя: явный маппинг или вывод по имени."""
    return OWID_INDICATOR_UNITS.get(indicator_name) or _owid_unit_from_name(indicator_name)


def _fetch_url(url: str, timeout: int = 60) -> bytes:
    """Загружает содержимое по URL."""
    req = Request(url, headers={'User-Agent': 'ErgoEquipmentDataset/1.0'})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_owid_energy() -> str:
    """
    Загружает OWID Energy CSV по URL, возвращает содержимое как строку (UTF-8).
    """
    raw = _fetch_url(OWID_ENERGY_CSV_URL)
    return raw.decode('utf-8', errors='replace')


def save_raw_fetch(source_name: str, request_url: str, response_body: str, status_code: int = 200):
    """
    Сохраняет сырой ответ в ExternalDataFetch. Возвращает созданную запись.
    """
    from ..models import ExternalDataFetch
    return ExternalDataFetch.objects.create(
        source_name=source_name,
        request_url=request_url,
        response_body=response_body,
        status_code=status_code,
    )


def _is_numeric_value(s: str) -> bool:
    if not s or not str(s).strip():
        return False
    try:
        float(str(s).replace(',', '.'))
        return True
    except ValueError:
        return False


def parse_owid_csv_to_metrics(
    csv_content: str,
    source_fetch_id: int | None = None,
    max_rows: int | None = None,
    skip_zero_values: bool = True,
) -> int:
    """
    Разбирает OWID Energy CSV и создаёт/обновляет записи EquipmentMetricByCountry.

    - Строки без iso_code (агрегаты континентов и т.п.) пропускаются.
    - Для каждой тройки (страна, год, показатель) одна запись (update_or_create).
    - Нулевые значения при skip_zero_values=True не записываются.
    Возвращает количество обработанных записей (созданных или обновлённых).
    """
    from ..models import EquipmentMetricByCountry, ElectricalEquipmentClass

    reader = csv.DictReader(io.StringIO(csv_content))
    if not reader.fieldnames:
        return 0

    numeric_columns = [
        c for c in reader.fieldnames
        if c not in OWID_SKIP_COLUMNS and c not in ('country', 'iso_code', 'year')
    ]

    source_fetch = None
    if source_fetch_id:
        from ..models import ExternalDataFetch
        source_fetch = ExternalDataFetch.objects.filter(pk=source_fetch_id).first()

    # Кэш классов техники по коду
    class_cache = {}
    processed = 0

    for row in reader:
        if max_rows is not None and processed >= max_rows:
            break
        iso = (row.get('iso_code') or '').strip()
        if not iso or len(iso) != 3:
            continue
        try:
            year = int(row.get('year') or 0)
        except (ValueError, TypeError):
            continue
        if year < 1990 or year > 2030:
            continue

        for col in numeric_columns:
            val_str = (row.get(col) or '').strip()
            if not _is_numeric_value(val_str):
                continue
            try:
                value = float(val_str.replace(',', '.'))
            except ValueError:
                continue
            if skip_zero_values and value == 0:
                continue

            # Класс техники по типу показателя (уголь, газ, ВИЭ, электроэнергия и т.д.)
            class_code = _owid_equipment_class_code(col)
            if class_code not in class_cache:
                class_cache[class_code] = ElectricalEquipmentClass.objects.filter(code=class_code).first()
            equipment_class = class_cache[class_code]

            unit = _owid_unit(col)

            EquipmentMetricByCountry.objects.update_or_create(
                country_code=iso,
                year=year,
                indicator_name=col,
                defaults={
                    'value': value,
                    'unit': unit,
                    'source_fetch': source_fetch,
                    'source_notes': 'OWID Energy',
                    'equipment_class': equipment_class,
                },
            )
            processed += 1
    return processed


def run_fetch_owid_and_save(save_raw: bool = True, max_rows: int | None = None) -> dict:
    """
    Загружает OWID Energy CSV, при необходимости сохраняет сырой ответ в БД,
    разбирает и заполняет EquipmentMetricByCountry.

    Returns:
        dict с ключами: raw_saved (bool), fetch_id (int | None), rows_created (int), error (str | None).
    """
    result = {'raw_saved': False, 'fetch_id': None, 'rows_created': 0, 'error': None}
    try:
        content = fetch_owid_energy()
    except Exception as e:
        logger.exception('OWID fetch failed')
        result['error'] = str(e)
        return result

    if save_raw:
        try:
            fetch = save_raw_fetch(
                source_name='OWID Energy',
                request_url=OWID_ENERGY_CSV_URL,
                response_body=content,
                status_code=200,
            )
            result['raw_saved'] = True
            result['fetch_id'] = fetch.pk
        except Exception as e:
            logger.warning('Could not save raw fetch: %s', e)

    with transaction.atomic():
        try:
            # Удаляем старые записи OWID, чтобы при повторном запуске не было дублей и устаревших строк
            from ..models import EquipmentMetricByCountry
            deleted, _ = EquipmentMetricByCountry.objects.filter(source_notes='OWID Energy').delete()
            if deleted:
                logger.info('Cleared %d existing OWID metric records.', deleted)
            result['rows_created'] = parse_owid_csv_to_metrics(
                content,
                source_fetch_id=result.get('fetch_id'),
                max_rows=max_rows,
            )
        except Exception as e:
            logger.exception('Parse OWID to metrics failed')
            result['error'] = str(e)
    return result


def export_dataset_to_csv(
    filepath: str | Path,
    *,
    delimiter: str = ',',
    include_equipment_class_code: bool = True,
) -> int:
    """
    Экспортирует все записи EquipmentMetricByCountry в CSV.
    Формат: country_code, year, indicator_name, value, unit, equipment_class_code, source_notes.

    Возвращает количество записанных строк (без заголовка).
    """
    from ..models import EquipmentMetricByCountry

    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = ['country_code', 'year', 'indicator_name', 'value', 'unit', 'source_notes']
    if include_equipment_class_code:
        fieldnames.insert(5, 'equipment_class_code')

    qs = EquipmentMetricByCountry.objects.all().order_by('country_code', 'year', 'indicator_name')
    count = 0
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()
        for rec in qs.iterator(chunk_size=2000):
            row = {
                'country_code': rec.country_code,
                'year': rec.year or '',
                'indicator_name': rec.indicator_name,
                'value': rec.value if rec.value is not None else '',
                'unit': rec.unit or '',
                'source_notes': rec.source_notes or '',
            }
            if include_equipment_class_code:
                row['equipment_class_code'] = rec.equipment_class.code if rec.equipment_class_id else ''
            writer.writerow(row)
            count += 1
    return count


def import_dataset_from_csv(
    filepath: str | Path,
    *,
    delimiter: str = ',',
    skip_duplicates: bool = True,
    source_notes_override: str = 'CSV import',
) -> tuple[int, int]:
    """
    Импортирует общий датасет из CSV в EquipmentMetricByCountry.

    Ожидаемые колонки: country_code, year, indicator_name, value [, unit [, equipment_class_code [, source_notes ]]]

    Returns:
        (created_count, updated_or_skipped_count)
    """
    from ..models import EquipmentMetricByCountry, ElectricalEquipmentClass

    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(str(filepath))

    created = 0
    skipped = 0
    batch_size = 2000
    class_cache = ElectricalEquipmentClass.objects.in_bulk(field_name='code')

    def resolve_class(class_code: str):
        if not class_code:
            return None
        return class_cache.get(class_code)

    with open(filepath, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        if not reader.fieldnames:
            return 0, 0

        # Быстрый режим массового upsert для больших CSV.
        if not skip_duplicates:
            batch = []
            for row in reader:
                country_code = (row.get('country_code') or '').strip()
                indicator_name = (row.get('indicator_name') or '').strip()
                if not country_code or not indicator_name:
                    skipped += 1
                    continue
                try:
                    year = int(row.get('year') or 0) if row.get('year') else None
                except (ValueError, TypeError):
                    year = None
                try:
                    value = float((row.get('value') or '').replace(',', '.')) if row.get('value') else None
                except (ValueError, TypeError):
                    value = None
                unit = (row.get('unit') or '').strip()[:64]
                source_notes = (row.get('source_notes') or source_notes_override).strip()[:512]
                class_code = (row.get('equipment_class_code') or '').strip()
                equipment_class = resolve_class(class_code)

                batch.append(
                    EquipmentMetricByCountry(
                        country_code=country_code,
                        year=year,
                        indicator_name=indicator_name,
                        value=value,
                        unit=unit,
                        source_notes=source_notes,
                        equipment_class=equipment_class,
                    )
                )
                if len(batch) >= batch_size:
                    EquipmentMetricByCountry.objects.bulk_create(
                        batch,
                        batch_size=batch_size,
                        update_conflicts=True,
                        update_fields=['value', 'unit', 'source_notes', 'equipment_class'],
                        unique_fields=['country_code', 'year', 'indicator_name'],
                    )
                    created += len(batch)
                    batch.clear()

            if batch:
                EquipmentMetricByCountry.objects.bulk_create(
                    batch,
                    batch_size=batch_size,
                    update_conflicts=True,
                    update_fields=['value', 'unit', 'source_notes', 'equipment_class'],
                    unique_fields=['country_code', 'year', 'indicator_name'],
                )
                created += len(batch)
            return created, skipped

        for row in reader:
            country_code = (row.get('country_code') or '').strip()
            indicator_name = (row.get('indicator_name') or '').strip()
            if not country_code or not indicator_name:
                skipped += 1
                continue
            try:
                year = int(row.get('year') or 0) if row.get('year') else None
            except (ValueError, TypeError):
                year = None
            try:
                value = float((row.get('value') or '').replace(',', '.')) if row.get('value') else None
            except (ValueError, TypeError):
                value = None
            unit = (row.get('unit') or '').strip()[:64]
            source_notes = (row.get('source_notes') or source_notes_override).strip()[:512]
            class_code = (row.get('equipment_class_code') or '').strip()
            equipment_class = resolve_class(class_code)

            if skip_duplicates:
                if EquipmentMetricByCountry.objects.filter(
                    country_code=country_code,
                    year=year,
                    indicator_name=indicator_name,
                ).exists():
                    skipped += 1
                    continue

            EquipmentMetricByCountry.objects.update_or_create(
                country_code=country_code,
                year=year,
                indicator_name=indicator_name,
                defaults={
                    'value': value,
                    'unit': unit,
                    'source_notes': source_notes,
                    'equipment_class': equipment_class,
                },
            )
            created += 1

    return created, skipped


def backfill_owid_units_and_class() -> tuple[int, int]:
    """
    Заполняет единицы измерения и класс техники у уже загруженных записей OWID,
    у которых unit пустой или equipment_class не задан. Класс назначается по имени показателя.

    Returns:
        (updated_count, total_owid_count)
    """
    from ..models import EquipmentMetricByCountry, ElectricalEquipmentClass

    # Кэш классов по коду (в т.ч. energy_aggregate и подклассы)
    all_codes = [OWID_ENERGY_CLASS_CODE] + list(OWID_ENERGY_SUBCLASSES)
    class_cache = {
        c.code: c
        for c in ElectricalEquipmentClass.objects.filter(code__in=all_codes)
    }

    qs = EquipmentMetricByCountry.objects.filter(source_notes='OWID Energy')
    total = qs.count()
    to_update = []
    for rec in qs.iterator(chunk_size=5000):
        need_save = False
        if not rec.unit:
            rec.unit = _owid_unit(rec.indicator_name)
            need_save = True
        class_code = _owid_equipment_class_code(rec.indicator_name)
        target_class = class_cache.get(class_code)
        if target_class and rec.equipment_class_id != target_class.id:
            rec.equipment_class = target_class
            need_save = True
        if need_save:
            to_update.append(rec)
    if to_update:
        EquipmentMetricByCountry.objects.bulk_update(
            to_update, ['unit', 'equipment_class'], batch_size=2000
        )
    return len(to_update), total


# ============== World Bank API ==============
WB_API_BASE = 'https://api.worldbank.org/v2'
# Коды регионов/агрегатов World Bank (не страны) — исключаем из выборки
WB_EXCLUDE_COUNTRY_CODES = frozenset({
    'AFE', 'AFW', 'ARB', 'CEB', 'CEU', 'CSS', 'EAS', 'ECS', 'EMU', 'EUU',
    'FCS', 'HIC', 'HPC', 'IBD', 'IBT', 'IDA', 'IDB', 'IDX', 'INX', 'LAC',
    'LCN', 'LDC', 'LMY', 'LIC', 'LMC', 'MEA', 'MNA', 'MIC', 'NAC', 'INX',
    'OED', 'OSS', 'PSS', 'PST', 'PRE', 'SAS', 'SSF', 'SSA', 'SST', 'TEA',
    'TEC', 'TLA', 'TMN', 'TSA', 'TSS', 'UMC', 'WLD',
})
# Показатели World Bank для загрузки: id, единица, класс техники
WB_INDICATORS = (
    {'id': 'EG.USE.ELEC.KH.PC', 'unit': 'kWh', 'equipment_class': 'energy_electricity'},
    {'id': 'EG.USE.PCAP.KG.OE', 'unit': 'kg oil eq', 'equipment_class': 'energy_aggregate'},
    {'id': 'EG.ELC.ACCS.ZS', 'unit': '%', 'equipment_class': 'energy_electricity'},
    {'id': 'EG.FEC.RNEW.ZS', 'unit': '%', 'equipment_class': 'energy_renewables'},
    {'id': 'EG.IMP.CONS.ZS', 'unit': '%', 'equipment_class': 'energy_aggregate'},
    {'id': 'EN.ATM.CO2E.PC', 'unit': 't CO2', 'equipment_class': 'energy_emissions'},
)


def fetch_world_bank_indicator(indicator_id: str, date_range: str = '2000:2030') -> str:
    """Загружает один показатель World Bank API (JSON), возвращает строку JSON."""
    url = f'{WB_API_BASE}/country/all/indicator/{indicator_id}?format=json&date={date_range}&per_page=10000'
    raw = _fetch_url(url, timeout=120)
    return raw.decode('utf-8', errors='replace')


def parse_world_bank_json(
    json_content: str,
    indicator_id: str,
    unit: str,
    equipment_class_code: str,
    source_fetch_id: int | None = None,
) -> int:
    """
    Разбирает ответ World Bank API (JSON), создаёт записи EquipmentMetricByCountry.
    Учитываются только страны (исключаются регионы из WB_EXCLUDE_COUNTRY_CODES).
    """
    from ..models import EquipmentMetricByCountry, ElectricalEquipmentClass

    try:
        data = json.loads(json_content)
    except json.JSONDecodeError as e:
        logger.warning('World Bank JSON parse error: %s', e)
        return 0
    if not isinstance(data, list) or len(data) < 2:
        return 0
    # data[0] = pagination, data[1] = list of observations
    observations = data[1] if len(data) > 1 else []
    equipment_class = None
    if equipment_class_code:
        equipment_class = ElectricalEquipmentClass.objects.filter(code=equipment_class_code).first()

    # Уникальный indicator_name для нашего датасета (чтобы не конфликтовать с OWID)
    indicator_name = f'wb_{indicator_id.lower().replace(".", "_")}'
    created = 0
    for obs in observations:
        country_code = (obs.get('countryiso3code') or '').strip()
        if not country_code or country_code in WB_EXCLUDE_COUNTRY_CODES:
            continue
        try:
            year = int(obs.get('date') or 0)
        except (ValueError, TypeError):
            continue
        if year < 1990 or year > 2030:
            continue
        val = obs.get('value')
        if val is None:
            continue
        try:
            value = float(val)
        except (TypeError, ValueError):
            continue

        EquipmentMetricByCountry.objects.update_or_create(
            country_code=country_code,
            year=year,
            indicator_name=indicator_name,
            defaults={
                'value': value,
                'unit': unit,
                'source_fetch_id': source_fetch_id,
                'source_notes': 'World Bank',
                'equipment_class': equipment_class,
            },
        )
        created += 1
    return created


def run_fetch_world_bank_and_save(save_raw: bool = True) -> dict:
    """
    Загружает показатели World Bank по API, сохраняет сырой ответ в БД, разбирает в EquipmentMetricByCountry.
    Не удаляет старые записи World Bank — использует update_or_create по (country_code, year, indicator_name).
    """
    result = {'rows_created': 0, 'fetch_ids': [], 'error': None}
    from ..models import EquipmentMetricByCountry

    for ind in WB_INDICATORS:
        indicator_id = ind['id']
        url = f'{WB_API_BASE}/country/all/indicator/{indicator_id}?format=json&date=2000:2030&per_page=10000'
        try:
            content = fetch_world_bank_indicator(indicator_id)
        except Exception as e:
            logger.exception('World Bank fetch failed for %s', indicator_id)
            result['error'] = result['error'] or str(e)
            continue
        fetch_id = None
        if save_raw:
            try:
                fetch = save_raw_fetch(
                    source_name='World Bank',
                    request_url=url,
                    response_body=content[:500000],  # ограничение размера в БД
                    status_code=200,
                )
                fetch_id = fetch.pk
                result['fetch_ids'].append(fetch_id)
            except Exception as e:
                logger.warning('Could not save raw World Bank fetch: %s', e)
        try:
            n = parse_world_bank_json(
                content,
                indicator_id=indicator_id,
                unit=ind['unit'],
                equipment_class_code=ind['equipment_class'],
                source_fetch_id=fetch_id,
            )
            result['rows_created'] += n
        except Exception as e:
            logger.exception('Parse World Bank failed for %s', indicator_id)
            result['error'] = result['error'] or str(e)
    return result


def _get_module_root() -> Path:
    """
    Корень модуля equipment_ergonomics (каталог с data/, api/, client/).
    Файл: <repo>/modules/equipment_ergonomics/api/scripts/build_dataset.py
    """
    return Path(__file__).resolve().parents[2]


def _get_repo_root() -> Path:
    """
    Корень репозитория ergo_ms_core.
    """
    return Path(__file__).resolve().parents[4]


def _module_data_dir() -> Path:
    """Каталог данных модуля: modules/equipment_ergonomics/data"""
    return _get_module_root() / 'data'


def _module_raw_dir() -> Path:
    """Сырые файлы: modules/equipment_ergonomics/data/raw"""
    return _module_data_dir() / 'raw'


def _module_processed_dir() -> Path:
    """Обработанные файлы: modules/equipment_ergonomics/data/processed"""
    return _module_data_dir() / 'processed'


def get_default_dataset_csv_path() -> Path:
    """
    Путь CSV датасета по умолчанию (рядом с данными модуля).
    """
    p = _module_data_dir() / 'equipment_dataset.csv'
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _world_bank_raw_search_dirs() -> list[Path]:
    """
    Каталоги для поиска локальных CSV World Bank (API_*_DS2_*.csv).

    1) modules/equipment_ergonomics/data/raw — основной;
    2) core/data/raw — legacy (старые инструкции / миграция).
    """
    return [
        _module_raw_dir(),
        _get_repo_root() / 'core' / 'data' / 'raw',
    ]


def _find_world_bank_raw_file(
    indicator_id: str,
    raw_dirs: list[Path] | None = None,
) -> Path | None:
    """
    Ищет локальный CSV World Bank по шаблону API_<ID>_DS2_*.csv.
    Просматривает каталоги по порядку (см. _world_bank_raw_search_dirs).
    """
    dirs = raw_dirs if raw_dirs is not None else _world_bank_raw_search_dirs()
    pattern = f'API_{indicator_id}_DS2_*.csv'
    for raw_dir in dirs:
        if not raw_dir.is_dir():
            continue
        matches = sorted(raw_dir.glob(pattern))
        if not matches:
            continue
        if len(matches) > 1:
            logger.info('Multiple World Bank raw CSV files for %s, using %s', indicator_id, matches[0])
        return matches[0]
    searched = ', '.join(str(d) for d in dirs)
    logger.warning(
        'World Bank raw CSV for %s not found (pattern %s). Проверены каталоги: %s',
        indicator_id,
        pattern,
        searched,
    )
    return None


def import_world_bank_from_raw_csv(
    filepath: str | Path,
    *,
    indicator_id: str,
    unit: str,
    equipment_class_code: str,
) -> int:
    """
    Импортирует один CSV World Bank в "широком" формате (строка = страна, колонки = года).

    Формат файлов API_*.csv:
    - несколько строк метаданных
    - строка заголовка: Country Name, Country Code, Indicator Name, Indicator Code, 1960, 1961, ...
    - далее по строке на страну/регион.
    """
    from ..models import EquipmentMetricByCountry, ElectricalEquipmentClass

    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(str(filepath))

    indicator_name = f'wb_{indicator_id.lower().replace(".", "_")}'
    equipment_class = None
    if equipment_class_code:
        equipment_class = ElectricalEquipmentClass.objects.filter(code=equipment_class_code).first()

    created = 0
    with filepath.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        header = None
        # Пропускаем метаданные до строки с "Country Name"
        for row in reader:
            if row and row[0] == 'Country Name':
                header = row
                break
        if not header:
            logger.warning('World Bank raw CSV %s: header with "Country Name" not found', filepath)
            return 0

        # Определяем индексы годов (начиная с 4-й колонки)
        year_columns: list[tuple[int, int]] = []
        for idx in range(4, len(header)):
            year_str = (header[idx] or '').strip()
            if not year_str:
                continue
            try:
                year = int(year_str)
            except ValueError:
                continue
            if 1990 <= year <= 2030:
                year_columns.append((idx, year))

        for row in reader:
            if not row or len(row) < 4:
                continue
            country_code = (row[1] or '').strip()
            if not country_code or country_code in WB_EXCLUDE_COUNTRY_CODES:
                continue
            for col_idx, year in year_columns:
                if col_idx >= len(row):
                    continue
                val_str = (row[col_idx] or '').strip()
                if not val_str:
                    continue
                try:
                    value = float(val_str)
                except ValueError:
                    continue
                EquipmentMetricByCountry.objects.update_or_create(
                    country_code=country_code,
                    year=year,
                    indicator_name=indicator_name,
                    defaults={
                        'value': value,
                        'unit': unit,
                        'source_notes': 'World Bank CSV',
                        'equipment_class': equipment_class,
                    },
                )
                created += 1
    return created


def run_import_world_bank_from_raw(
    save_raw_to_db: bool = False,
    raw_dirs: str | Path | list[Path] | None = None,
) -> dict:
    """
    Импортирует показатели World Bank из локальных CSV (downloadformat=csv).

    По умолчанию ищет файлы в:
    - modules/equipment_ergonomics/data/raw
    - (legacy) core/data/raw

    - Каждая запись в WB_INDICATORS ищет файл API_<ID>_DS2_*.csv.
    - Данные записываются в EquipmentMetricByCountry с indicator_name = wb_<id>.
    - Старые записи не удаляются: используется update_or_create по (country_code, year, indicator_name).

    raw_dirs: один каталог (str/Path) или список каталогов для поиска (порядок важен).
    """
    result = {'rows_created': 0, 'files': [], 'error': None}
    if raw_dirs is None:
        search_dirs: list[Path] | None = None
    elif isinstance(raw_dirs, (str, Path)):
        search_dirs = [Path(raw_dirs)]
    else:
        search_dirs = list(raw_dirs)

    for ind in WB_INDICATORS:
        indicator_id = ind['id']
        path = _find_world_bank_raw_file(indicator_id, search_dirs)
        if not path:
            continue
        if save_raw_to_db:
            try:
                raw = path.read_bytes().decode('utf-8', errors='replace')
                fetch = save_raw_fetch(
                    source_name='World Bank CSV',
                    request_url=str(path),
                    response_body=raw[:500000],
                    status_code=200,
                )
                result.setdefault('fetch_ids', []).append(fetch.pk)
            except Exception as e:
                logger.warning('Could not save raw World Bank CSV %s: %s', path, e)
        try:
            n = import_world_bank_from_raw_csv(
                path,
                indicator_id=indicator_id,
                unit=ind['unit'],
                equipment_class_code=ind['equipment_class'],
            )
            result['rows_created'] += n
            result['files'].append(str(path))
        except Exception as e:
            logger.exception('Import World Bank raw CSV failed for %s from %s', indicator_id, path)
            result['error'] = result['error'] or str(e)
    return result


# ============== Структурированный импорт из файлов (CSV / JSON) ==============
# Конфигурация именованных источников: файл по пути, маппинг колонок → наши поля, класс техники по умолчанию.
# Добавьте сюда запись для каждого готового датасета (e-waste, ртуть, охлаждение и т.д.),
# затем: ergoms api build_equipment_dataset --file-import modules/equipment_ergonomics/data/raw/....csv --file-source ключ

FILE_SOURCE_CONFIG = {
    # Пример: если в CSV колонки называются иначе — укажите маппинг. Иначе можно использовать
    # стандартные имена (country_code, year, indicator_name, value) и обычный --import.
    # 'ewaste': {
    #     'name': 'Global E-waste (example)',
    #     'format': 'csv',
    #     'delimiter': ',',
    #     'columns': {
    #         'country_code': 'Country Code',  # имя колонки в файле
    #         'year': 'Year',
    #         'indicator_name': 'Indicator',
    #         'value': 'Value',
    #         'unit': 'Unit',
    #         'equipment_class_code': 'Class',
    #     },
    #     'default_equipment_class_code': 'e_waste_hazardous',
    #     'default_unit': 'kt',
    # },
}


def import_from_structured_file(
    filepath: str | Path,
    source_key: str,
    *,
    source_name_override: str | None = None,
    save_raw_to_db: bool = False,
) -> tuple[int, int]:
    """
    Импортирует данные из готового файла (CSV или JSON) по конфигу FILE_SOURCE_CONFIG.

    - filepath: путь к файлу (CSV/JSON).
    - source_key: ключ в FILE_SOURCE_CONFIG (определяет маппинг колонок и класс техники).
    - source_name_override: если задан, используется как source_notes вместо config['name'].
    - save_raw_to_db: сохранить сырое содержимое файла в ExternalDataFetch (для аудита).

    Returns:
        (created_count, skipped_count)
    """
    from ..models import EquipmentMetricByCountry, ElectricalEquipmentClass, ExternalDataFetch

    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(str(filepath))
    config = FILE_SOURCE_CONFIG.get(source_key)
    if not config:
        raise ValueError(f'Unknown file source key: {source_key}. Known: {list(FILE_SOURCE_CONFIG)}')
    name = source_name_override or config.get('name', source_key)
    fmt = config.get('format', 'csv').lower()
    columns = config.get('columns', {})
    default_class_code = config.get('default_equipment_class_code', '')
    default_unit = config.get('default_unit', '')
    delimiter = config.get('delimiter', ',')

    if save_raw_to_db:
        try:
            raw = filepath.read_bytes().decode('utf-8', errors='replace')
            save_raw_fetch(
                source_name=name,
                request_url=str(filepath),
                response_body=raw[:500000],
                status_code=200,
            )
        except Exception as e:
            logger.warning('Could not save raw file to DB: %s', e)

    equipment_class = None
    if default_class_code:
        equipment_class = ElectricalEquipmentClass.objects.filter(code=default_class_code).first()

    created = 0
    skipped = 0
    if fmt == 'csv':
        with open(filepath, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            if not reader.fieldnames:
                return 0, 0
            for row in reader:
                country_code = (row.get(columns.get('country_code', 'country_code')) or '').strip()
                indicator_name = (row.get(columns.get('indicator_name', 'indicator_name')) or '').strip()
                if not country_code or not indicator_name:
                    skipped += 1
                    continue
                try:
                    year = int(row.get(columns.get('year', 'year')) or 0)
                except (ValueError, TypeError):
                    year = None
                try:
                    value = float((row.get(columns.get('value', 'value')) or '').replace(',', '.'))
                except (ValueError, TypeError):
                    value = None
                unit = (row.get(columns.get('unit', 'unit')) or default_unit).strip()[:64]
                class_code = (row.get(columns.get('equipment_class_code', 'equipment_class_code')) or default_class_code).strip()
                eq_class = equipment_class
                if class_code:
                    eq_class = ElectricalEquipmentClass.objects.filter(code=class_code).first() or equipment_class

                EquipmentMetricByCountry.objects.update_or_create(
                    country_code=country_code,
                    year=year,
                    indicator_name=indicator_name,
                    defaults={
                        'value': value,
                        'unit': unit or default_unit,
                        'source_notes': name,
                        'equipment_class': eq_class,
                    },
                )
                created += 1
    elif fmt == 'json':
        raw = filepath.read_text(encoding='utf-8', errors='replace')
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f'Invalid JSON: {e}') from e
        # Ожидаем список объектов или объект с массивом по ключу (напр. "data")
        items = data if isinstance(data, list) else data.get('data', data.get('rows', []))
        if not isinstance(items, list):
            items = [data]
        for row in items:
            if not isinstance(row, dict):
                skipped += 1
                continue
            country_code = (str(row.get(columns.get('country_code', 'country_code')) or '')).strip()
            indicator_name = (str(row.get(columns.get('indicator_name', 'indicator_name')) or '')).strip()
            if not country_code or not indicator_name:
                skipped += 1
                continue
            try:
                year = int(row.get(columns.get('year', 'year')) or 0)
            except (ValueError, TypeError):
                year = None
            try:
                value = float(row.get(columns.get('value', 'value')))
            except (TypeError, ValueError):
                value = None
            unit = (str(row.get(columns.get('unit', 'unit')) or default_unit)).strip()[:64]
            class_code = (str(row.get(columns.get('equipment_class_code', 'equipment_class_code')) or default_class_code)).strip()
            eq_class = equipment_class
            if class_code:
                eq_class = ElectricalEquipmentClass.objects.filter(code=class_code).first() or equipment_class

            EquipmentMetricByCountry.objects.update_or_create(
                country_code=country_code,
                year=year,
                indicator_name=indicator_name,
                defaults={
                    'value': value,
                    'unit': unit or default_unit,
                    'source_notes': name,
                    'equipment_class': eq_class,
                },
            )
            created += 1
    else:
        raise ValueError(f'Unsupported format: {fmt}')
    return created, skipped


def run_build_full(
    export_path: str | Path | None = None,
    save_raw: bool = True,
    max_owid_rows: int | None = None,
) -> dict:
    """
    Полный цикл: загрузка OWID → сохранение в БД (сырое + нормализованное) → при указании export_path экспорт в CSV.

    Returns:
        dict с ключами: fetch_result, rows_created, export_path, export_rows, error.
    """
    out = {'fetch_result': None, 'rows_created': 0, 'export_path': None, 'export_rows': 0, 'error': None}
    fetch_result = run_fetch_owid_and_save(save_raw=save_raw, max_rows=max_owid_rows)
    out['fetch_result'] = fetch_result
    if fetch_result.get('error'):
        out['error'] = fetch_result['error']
        return out
    out['rows_created'] = fetch_result.get('rows_created', 0)

    if export_path:
        try:
            out['export_rows'] = export_dataset_to_csv(export_path)
            out['export_path'] = str(Path(export_path).resolve())
        except Exception as e:
            logger.exception('Export to CSV failed')
            out['error'] = str(e)
    return out


# ============== Plugin archive / purge helpers ==============

def get_default_archive_root() -> Path:
    """
    Каталог архивов плагина: modules/equipment_ergonomics/data/archives/<timestamp>
    """
    ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    root = _module_data_dir() / 'archives' / ts
    root.mkdir(parents=True, exist_ok=True)
    return root


def archive_plugin_data(archive_root: str | Path | None = None) -> dict:
    """
    Архивирует формализованные данные плагина в файлы внутри модуля.
    Сейчас архивируются:
      - EquipmentMetricByCountry (CSV)
      - ExternalDataFetch (JSONL)
    """
    from ..models import EquipmentMetricByCountry, ExternalDataFetch

    root = Path(archive_root) if archive_root else get_default_archive_root()
    root.mkdir(parents=True, exist_ok=True)

    metrics_csv = root / 'equipment_metric_by_country.csv'
    fetches_jsonl = root / 'external_data_fetch.jsonl'

    export_rows = export_dataset_to_csv(metrics_csv)

    fetch_count = 0
    with fetches_jsonl.open('w', encoding='utf-8') as f:
        qs = ExternalDataFetch.objects.all().order_by('id')
        for rec in qs.iterator(chunk_size=1000):
            payload = {
                'id': rec.id,
                'source_name': rec.source_name,
                'request_url': rec.request_url,
                'fetched_at': rec.fetched_at.isoformat() if rec.fetched_at else None,
                'status_code': rec.status_code,
                'error_message': rec.error_message,
                'response_body': rec.response_body,
            }
            f.write(json.dumps(payload, ensure_ascii=False) + '\n')
            fetch_count += 1

    meta = {
        'archive_root': str(root.resolve()),
        'created_at': datetime.now(timezone.utc).isoformat(),
        'counts': {
            'equipment_metric_by_country': EquipmentMetricByCountry.objects.count(),
            'external_data_fetch': fetch_count,
        },
        'files': {
            'metrics_csv': str(metrics_csv),
            'fetches_jsonl': str(fetches_jsonl),
        },
        'export_rows': export_rows,
    }
    (root / 'archive_meta.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    return meta


def purge_plugin_data() -> dict:
    """
    Удаляет формализованные данные плагина из БД.
    Использовать только после архивации.
    """
    from ..models import EquipmentMetricByCountry, ExternalDataFetch

    deleted_metrics, _ = EquipmentMetricByCountry.objects.all().delete()
    deleted_fetches, _ = ExternalDataFetch.objects.all().delete()
    return {
        'deleted': {
            'equipment_metric_by_country': deleted_metrics,
            'external_data_fetch': deleted_fetches,
        }
    }
