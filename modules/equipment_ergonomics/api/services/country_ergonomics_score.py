from __future__ import annotations

import math
from typing import Any

from django.db.models import Max, Min

from ..models import EquipmentMetricByCountry
from ..serializers import INDICATOR_LABELS, INDICATOR_UNITS

"""
Композитная оценка 0–100 по стране на основе доступных в БД энерго-экологических показателей.
Интерпретация: энергетический контекст страны для эксплуатации техники — электроснабжение,
баланс ископаемого и низкоуглеродного потребления, доля импорта энергоносителей, климатическая нагрузка.
"""

_SCORE_COMPONENTS: tuple[dict[str, Any], ...] = (
    {
        'indicator_name': 'wb_eg_elc_accs_zs',
        'direction': 1,
        'weight': 0.18,
        'label': 'Доступ населения к электроэнергии',
    },
    {
        'indicator_name': 'wb_eg_fec_rnew_zs',
        'direction': 1,
        'weight': 0.16,
        'label': 'Доля возобновляемых источников в потреблении (WB)',
    },
    {
        'indicator_name': 'carbon_intensity_elec',
        'direction': -1,
        'weight': 0.16,
        'label': 'Углеродоёмкость электроэнергии (ниже — лучше)',
    },
    {
        'indicator_name': 'wb_en_atm_co2e_pc',
        'direction': -1,
        'weight': 0.12,
        'label': 'Выбросы CO₂ на душу населения (ниже — лучше)',
    },
    {
        'indicator_name': 'wb_eg_imp_cons_zs',
        'direction': -1,
        'weight': 0.14,
        'label': 'Импорт энергоносителей, % потребления (ниже — лучше)',
    },
    {
        'indicator_name': 'fossil_fuel_consumption',
        'direction': -1,
        'weight': 0.12,
        'label': 'Потребление ископаемого топлива (ниже — лучше; нормировка по странам)',
    },
    {
        'indicator_name': 'low_carbon_consumption',
        'direction': 1,
        'weight': 0.12,
        'label': 'Низкоуглеродное потребление энергии (выше — лучше; нормировка по странам)',
    },
)

_CRITERIA_DEFS: tuple[dict[str, Any], ...] = (
    {
        'key': 'safety',
        'label': 'Безопасность',
        'components': (
            {'indicator_name': 'carbon_intensity_elec', 'direction': -1, 'weight': 0.45},
            {'indicator_name': 'wb_en_atm_co2e_pc', 'direction': -1, 'weight': 0.35},
            {'indicator_name': 'greenhouse_gas_emissions', 'direction': -1, 'weight': 0.20},
        ),
    },
    {
        'key': 'comfort',
        'label': 'Комфорт',
        'components': (
            {'indicator_name': 'wb_eg_elc_accs_zs', 'direction': 1, 'weight': 0.50},
            {'indicator_name': 'wb_eg_use_elec_kh_pc', 'direction': 1, 'weight': 0.30},
            {'indicator_name': 'energy_per_capita', 'direction': 1, 'weight': 0.20},
        ),
    },
    {
        'key': 'functionality',
        'label': 'Функциональность',
        'components': (
            {'indicator_name': 'wb_eg_elc_accs_zs', 'direction': 1, 'weight': 0.40},
            {'indicator_name': 'electricity_demand_per_capita', 'direction': 1, 'weight': 0.35},
            {'indicator_name': 'primary_energy_consumption', 'direction': 1, 'weight': 0.25},
        ),
    },
    {
        'key': 'controllability',
        'label': 'Управляемость',
        'components': (
            {'indicator_name': 'wb_eg_imp_cons_zs', 'direction': -1, 'weight': 0.55},
            {'indicator_name': 'wb_eg_fec_rnew_zs', 'direction': 1, 'weight': 0.45},
        ),
    },
    {
        'key': 'habitability',
        'label': 'Обитаемость',
        'components': (
            {'indicator_name': 'wb_en_atm_co2e_pc', 'direction': -1, 'weight': 0.50},
            {'indicator_name': 'greenhouse_gas_emissions', 'direction': -1, 'weight': 0.30},
            {'indicator_name': 'carbon_intensity_elec', 'direction': -1, 'weight': 0.20},
        ),
    },
    {
        'key': 'learnability',
        'label': 'Освояемость',
        'components': (
            {'indicator_name': 'wb_eg_elc_accs_zs', 'direction': 1, 'weight': 0.60},
            {'indicator_name': 'wb_eg_use_elec_kh_pc', 'direction': 1, 'weight': 0.40},
        ),
    },
)


def _grade_for_score(score: float) -> str:
    if score >= 80:
        return 'высокая'
    if score >= 65:
        return 'хорошая'
    if score >= 50:
        return 'удовлетворительная'
    if score >= 35:
        return 'низкая'
    return 'очень низкая'


def _country_value_for_indicator(
    country_code: str,
    indicator_name: str,
    year: int,
) -> tuple[float | None, int | None]:
    rec = (
        EquipmentMetricByCountry.objects.filter(
            country_code=country_code,
            indicator_name=indicator_name,
            year=year,
            value__isnull=False,
        )
        .order_by('-year')
        .first()
    )
    if rec:
        return float(rec.value), int(rec.year)
    rec = (
        EquipmentMetricByCountry.objects.filter(
            country_code=country_code,
            indicator_name=indicator_name,
            year__lte=year,
            value__isnull=False,
        )
        .order_by('-year')
        .first()
    )
    if rec:
        return float(rec.value), int(rec.year)
    return None, None


def _global_min_max_indicator(
    indicator_name: str,
    year: int,
    *,
    max_lookback: int = 5,
) -> tuple[float, float, int] | None:
    """Мин/макс по странам для одного показателя в одном календарном году (с откатом назад до max_lookback лет)."""
    for y in range(year, year - max_lookback - 1, -1):
        qs = EquipmentMetricByCountry.objects.filter(
            indicator_name=indicator_name,
            year=y,
            value__isnull=False,
        ).values_list('value', flat=True)
        vals = [float(v) for v in qs]
        if len(vals) >= 2:
            return min(vals), max(vals), y
    return None


def _pick_base_year(country_code: str, year: int | None) -> int | None:
    if year is not None:
        return int(year)
    agg = EquipmentMetricByCountry.objects.filter(
        country_code=country_code,
        indicator_name__in=[c['indicator_name'] for c in _SCORE_COMPONENTS],
        value__isnull=False,
    ).aggregate(m=Max('year'))
    y = agg.get('m')
    return int(y) if y is not None else None


def _normalize_weight_overrides(raw: Any) -> dict[str, float] | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        return None
    allowed = {c['indicator_name'] for c in _SCORE_COMPONENTS}
    out: dict[str, float] = {}
    for key, val in raw.items():
        ind = str(key or '').strip()
        if ind not in allowed:
            continue
        try:
            w = float(val)
        except (TypeError, ValueError):
            continue
        if w < 0 or math.isnan(w):
            continue
        out[ind] = w
    return out or None


def build_country_ergonomics_score(
    country_code: str,
    year: int | None = None,
    *,
    include_details: bool = True,
    weight_overrides: dict[str, float] | None = None,
) -> dict[str, Any]:
    cc = (country_code or '').strip().upper()
    if len(cc) != 3:
        return {'error': 'Укажите код страны ISO3 (3 символа, например RUS).'}

    base_year = _pick_base_year(cc, year)
    if base_year is None:
        return {
            'error': f'Нет данных по показателям оценки для страны {cc}.',
            'country_code': cc,
        }

    components_out: list[dict[str, Any]] = []
    weighted_sum = 0.0
    weight_used = 0.0
    missing: list[str] = []
    indicator_cache: dict[tuple[str, int], dict[str, Any] | None] = {}

    def resolve_indicator_score(indicator_name: str, direction: int, ref_year: int) -> dict[str, Any] | None:
        cache_key = (indicator_name, direction)
        if cache_key in indicator_cache:
            return indicator_cache[cache_key]

        mm = _global_min_max_indicator(indicator_name, ref_year)
        if mm is None:
            indicator_cache[cache_key] = None
            return None
        mn, mx, pool_year = mm
        raw, year_used = _country_value_for_indicator(cc, indicator_name, pool_year)
        if raw is None:
            indicator_cache[cache_key] = None
            return None

        if mx <= mn:
            sub = 50.0
        else:
            t = (raw - mn) / (mx - mn)
            t = max(0.0, min(1.0, float(t)))
            sub = 100.0 * t if direction == 1 else 100.0 * (1.0 - t)
        sub = max(0.0, min(100.0, float(sub)))

        payload = {
            'indicator_name': indicator_name,
            'label_catalog': INDICATOR_LABELS.get(indicator_name) or indicator_name,
            'unit': INDICATOR_UNITS.get(indicator_name) or '',
            'raw_value': raw,
            'year_used': year_used,
            'comparison_pool_year': pool_year,
            'subscore': round(float(sub), 2),
            'direction': int(direction),
        }
        indicator_cache[cache_key] = payload
        return payload

    overrides = _normalize_weight_overrides(weight_overrides)

    for comp in _SCORE_COMPONENTS:
        ind = comp['indicator_name']
        direction = int(comp['direction'])
        base_w = float(comp['weight'])
        if overrides is not None and ind in overrides:
            w = float(overrides[ind])
        else:
            w = base_w
        if w <= 0:
            continue
        scored = resolve_indicator_score(ind, direction, base_year)
        if scored is None:
            missing.append(ind)
            continue
        weighted_sum += float(scored['subscore']) * w
        weight_used += w
        components_out.append(
            {
                'indicator_name': ind,
                'label': comp['label'],
                'label_catalog': scored['label_catalog'],
                'unit': scored['unit'],
                'raw_value': scored['raw_value'],
                'year_used': scored['year_used'],
                'reference_year': base_year,
                'comparison_pool_year': scored['comparison_pool_year'],
                'subscore': scored['subscore'],
                'weight': w,
                'weight_default': base_w,
                'direction': scored['direction'],
            }
        )

    if weight_used <= 0:
        return {
            'error': 'Недостаточно данных для расчёта (нет пересечения показателей и годов).',
            'country_code': cc,
            'reference_year': base_year,
            'missing_indicators': missing,
        }

    total = weighted_sum / weight_used
    total = max(0.0, min(100.0, total))

    breakdown_terms: list[dict[str, Any]] = []
    for item in components_out:
        sub_f = float(item['subscore'])
        w_f = float(item['weight'])
        breakdown_terms.append(
            {
                'indicator_name': item['indicator_name'],
                'label': item['label'],
                'subscore': item['subscore'],
                'weight': item['weight'],
                'weighted_product': round(sub_f * w_f, 4),
            }
        )

    score_breakdown: dict[str, Any] = {
        'formula': '(Σ wᵢ·Sᵢ) / Σ wᵢ',
        'description_ru': (
            'Sᵢ — суббалл показателя i на шкале 0–100 (нормировка значения страны к min–max по всем странам '
            'за пул годов с откатом до 5 лет). wᵢ — вес показателя в итоговом индексе '
            '(электро, климатические метрики WB, импорт топлива, ископаемое и низкоуглеродное потребление). '
            'В расчёт входят только показатели с данными для страны; веса суммируются только по ним.'
        ),
        'terms': breakdown_terms,
        'sum_weights': round(weight_used, 6),
        'sum_weighted_subscores': round(weighted_sum, 6),
        'score': round(total, 2),
        'custom_weights_applied': overrides is not None,
    }

    payload: dict[str, Any] = {
        'country_code': cc,
        'reference_year': base_year,
        'score': round(total, 2),
        'grade': _grade_for_score(total),
        'components': components_out,
        'missing_indicators': missing,
        'weight_coverage': round(weight_used, 4),
        'score_breakdown': score_breakdown,
        'method_note': (
            'Оценка 0–100: взвешенное среднее суббаллов Sᵢ (нормировка значения страны к min–max по всем странам за пул лет). '
            'В индекс входят электроснабжение и доля ВИЭ (WB), углеродность электроэнергии и CO₂ на душу, '
            'зависимость от импорта топлива (WB), а также объёмы ископаемого и низкоуглеродного потребления (агрегаты TWh). '
            'Учитываются только показатели с данными для страны; не хватает данных — см. missing_indicators.'
        ),
    }

    if not include_details:
        return payload

    criteria: list[dict[str, Any]] = []
    for criterion_def in _CRITERIA_DEFS:
        csum = 0.0
        cweight = 0.0
        cparts = []
        for comp in criterion_def['components']:
            scored = resolve_indicator_score(comp['indicator_name'], int(comp['direction']), base_year)
            if scored is None:
                continue
            w = float(comp['weight'])
            csum += float(scored['subscore']) * w
            cweight += w
            cparts.append(
                {
                    'indicator_name': scored['indicator_name'],
                    'label': scored['label_catalog'],
                    'subscore': scored['subscore'],
                    'raw_value': scored['raw_value'],
                    'unit': scored['unit'],
                    'weight': w,
                }
            )
        if cweight <= 0:
            score = None
            grade = 'н/д'
        else:
            score = max(0.0, min(100.0, csum / cweight))
            score = round(score, 2)
            grade = _grade_for_score(score)
        criteria.append(
            {
                'key': criterion_def['key'],
                'label': criterion_def['label'],
                'score': score,
                'grade': grade,
                'weight_coverage': round(cweight, 4),
                'components': cparts,
            }
        )

    profile_agg = EquipmentMetricByCountry.objects.filter(country_code=cc).aggregate(
        first_year=Min('year'),
        last_year=Max('year'),
    )
    profile = {
        'country_code': cc,
        'reference_year': base_year,
        'records_total': EquipmentMetricByCountry.objects.filter(country_code=cc).count(),
        'indicators_total': EquipmentMetricByCountry.objects.filter(country_code=cc)
        .values('indicator_name')
        .distinct()
        .count(),
        'first_year': profile_agg.get('first_year'),
        'last_year': profile_agg.get('last_year'),
    }

    payload['country_profile'] = profile
    payload['criteria'] = criteria
    payload['criteria_note'] = (
        'Критерии рассчитаны как прокси по доступным энергетическим и экологическим индикаторам страны; '
        'при отсутствии части индикаторов критерий считается по доступному подмножеству.'
    )
    return payload


def build_country_ergonomics_score_series(
    country_code: str,
    year_from: int,
    year_to: int,
) -> dict[str, Any]:
    """Индекс эргономичности по календарным годам (для графика динамики)."""
    cc = (country_code or '').strip().upper()
    if len(cc) != 3:
        return {'error': 'Укажите код страны ISO3 (3 символа, например RUS).'}

    y0 = int(year_from)
    y1 = int(year_to)
    if y0 > y1:
        y0, y1 = y1, y0

    points: list[dict[str, Any]] = []
    for y in range(y0, y1 + 1):
        row = build_country_ergonomics_score(cc, y, include_details=False)
        if row.get('error'):
            points.append(
                {
                    'year': y,
                    'score': None,
                    'grade': None,
                    'weight_coverage': None,
                    'missing_indicators': row.get('missing_indicators') or [],
                }
            )
            continue
        points.append(
            {
                'year': y,
                'score': row.get('score'),
                'grade': row.get('grade'),
                'weight_coverage': row.get('weight_coverage'),
                'missing_indicators': row.get('missing_indicators') or [],
            }
        )

    return {
        'country_code': cc,
        'year_from': y0,
        'year_to': y1,
        'points': points,
    }
