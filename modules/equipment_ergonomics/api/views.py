import os
import tempfile
import uuid

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet
from rest_framework.permissions import IsAuthenticated

from .models import (
    ElectricalEquipmentClass,
    EquipmentMetricByCountry,
    AnalysisCoefficient,
    AnalysisMetric,
    CustomDataset,
    AnalysisRun,
)
from .serializers import (
    ElectricalEquipmentClassSerializer,
    EquipmentMetricByCountrySerializer,
    INDICATOR_LABELS,
    INDICATOR_UNITS,
    AnalysisCoefficientSerializer,
    AnalysisMetricSerializer,
    CustomDatasetCreateSerializer,
    CustomDatasetListSerializer,
    AnalysisRunSerializer,
    AnalysisResultSerializer,
)
from .services.plugin_state import is_enabled, get_snapshot


CSV_MAX_BYTES = 64 * 1024 * 1024


class DatasetPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 500


class PluginGatedViewSetMixin:
    """
    Делает модуль «невидимым» при выключенном плагине.
    """

    def initial(self, request, *args, **kwargs):
        if not is_enabled():
            raise NotFound()
        return super().initial(request, *args, **kwargs)


class ElectricalEquipmentClassViewSet(ReadOnlyModelViewSet):
    """Справочник классов электротехники (в т.ч. неэкологичные)."""

    queryset = ElectricalEquipmentClass.objects.all()
    serializer_class = ElectricalEquipmentClassSerializer
    filterset_fields = ('is_non_eco', 'code')


class EquipmentMetricByCountryViewSet(PluginGatedViewSetMixin, ReadOnlyModelViewSet):
    """
    Показатели по странам/годам — датасет из БД.
    Фильтры: country_code, year, equipment_class (id), equipment_class_code.
    """

    MAX_CSV_IMPORT_BYTES = CSV_MAX_BYTES
    MAX_CSV_CLEAN_BYTES = CSV_MAX_BYTES

    queryset = EquipmentMetricByCountry.objects.select_related('equipment_class').all()
    serializer_class = EquipmentMetricByCountrySerializer
    pagination_class = DatasetPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ('country_code', 'year', 'equipment_class')
    ordering_fields = ('country_code', 'year', 'indicator_name', 'value')
    ordering = ('country_code', 'year', 'indicator_name')

    def get_queryset(self):
        qs = super().get_queryset()
        # Фильтр по коду класса техники (вместо id)
        class_code = self.request.query_params.get('equipment_class_code')
        if class_code:
            qs = qs.filter(equipment_class__code=class_code)
        return qs

    @action(detail=False, methods=['get'], url_path='chart-data')
    def chart_data(self, request):
        """
        Данные для графиков сравнения стран.
        Параметры: indicator_name (обязательно), country_codes (через запятую, например RUS,USA,DEU),
        year_from, year_to (опционально).
        Возвращает: years, datasets (массив { country_code, label, data }), indicator_label, unit.
        """
        indicator_name = (request.query_params.get('indicator_name') or '').strip()
        if not indicator_name:
            return Response(
                {'error': 'Укажите indicator_name.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        country_codes_str = (request.query_params.get('country_codes') or '').strip()
        if not country_codes_str:
            return Response(
                {'error': 'Укажите country_codes (через запятую, например RUS,USA,DEU).'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        country_codes = [c.strip().upper() for c in country_codes_str.split(',') if c.strip()]
        if not country_codes:
            return Response(
                {'error': 'Укажите хотя бы один код страны.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            year_from = int(request.query_params.get('year_from') or 1990)
        except (ValueError, TypeError):
            year_from = 1990
        try:
            year_to = int(request.query_params.get('year_to') or 2030)
        except (ValueError, TypeError):
            year_to = 2030

        qs = (
            EquipmentMetricByCountry.objects.filter(
                indicator_name=indicator_name,
                country_code__in=country_codes,
                year__gte=year_from,
                year__lte=year_to,
            )
            .order_by('country_code', 'year')
        )
        # Собираем годы и данные по странам
        years_set = set()
        by_country = {c: [] for c in country_codes}
        for rec in qs:
            years_set.add(rec.year)
            if rec.country_code in by_country:
                by_country[rec.country_code].append({'year': rec.year, 'value': rec.value})
        years_ordered = sorted(years_set)
        # Для каждой страны — массив значений по годам (null если нет данных)
        year_to_idx = {y: i for i, y in enumerate(years_ordered)}
        datasets = []
        for code in country_codes:
            values_by_year = {r['year']: r['value'] for r in by_country[code]}
            data = [values_by_year.get(y) for y in years_ordered]
            datasets.append({
                'country_code': code,
                'label': code,
                'data': data,
            })
        return Response({
            'indicator_name': indicator_name,
            'indicator_label': INDICATOR_LABELS.get(indicator_name) or indicator_name.replace('_', ' ').title(),
            'unit': INDICATOR_UNITS.get(indicator_name) or '',
            'years': years_ordered,
            'datasets': datasets,
        })

    @action(detail=False, methods=['get'], url_path='country-ergonomics-score')
    def country_ergonomics_score(self, request):
        """
        Оценка эргономичности энергосистемы страны (0–100) и уровень по компонентам.
        Параметры:
          - country_code (ISO3, обязательно)
          - year (опционально — якорный год; данные могут браться с откатом)
          - details (1/0, по умолчанию 1): вернуть расширенный профиль и критерии.
        """
        from .services.country_ergonomics_score import build_country_ergonomics_score

        country_code = (request.query_params.get('country_code') or '').strip()
        year_raw = (request.query_params.get('year') or '').strip()
        year = None
        if year_raw:
            try:
                year = int(year_raw)
            except (ValueError, TypeError):
                return Response(
                    {'error': 'Некорректный year.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        include_details = str(request.query_params.get('details', '1')).lower() not in ('0', 'false', 'no')
        payload = build_country_ergonomics_score(country_code, year, include_details=include_details)
        if payload.get('error'):
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        return Response(payload)

    @action(detail=False, methods=['get'], url_path='country-ergonomics-score-series')
    def country_ergonomics_score_series(self, request):
        """
        Динамика индекса эргономичности по годам для одной страны.
        Параметры: country_code (ISO3), year_from, year_to.
        """
        from .services.country_ergonomics_score import build_country_ergonomics_score_series

        country_code = (request.query_params.get('country_code') or '').strip()
        try:
            year_from = int(request.query_params.get('year_from') or 2000)
        except (ValueError, TypeError):
            year_from = 2000
        try:
            year_to = int(request.query_params.get('year_to') or 2022)
        except (ValueError, TypeError):
            year_to = 2022

        payload = build_country_ergonomics_score_series(country_code, year_from, year_to)
        if payload.get('error'):
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        return Response(payload)

    @action(detail=False, methods=['post'], url_path='country-ergonomics-score-custom')
    def country_ergonomics_score_custom(self, request):
        """
        Итоговый индекс с пользовательскими весами показателей (JSON).
        Тело: country_code (обяз.), year (опц.), weights — объект { indicator_name: число >= 0 }.
        Нулевой вес исключает показатель из среднего; отсутствующие ключи — вес по умолчанию модели.
        Блок criteria по-прежнему считается по внутренним весам модели.
        """
        from .services.country_ergonomics_score import build_country_ergonomics_score

        country_code = (request.data.get('country_code') or '').strip()
        year_raw = request.data.get('year')
        year = None
        if year_raw is not None and year_raw != '':
            try:
                year = int(year_raw)
            except (ValueError, TypeError):
                return Response({'error': 'Некорректный year.'}, status=status.HTTP_400_BAD_REQUEST)

        weights = request.data.get('weights')
        overrides = weights if isinstance(weights, dict) else None

        payload = build_country_ergonomics_score(
            country_code,
            year,
            include_details=True,
            weight_overrides=overrides,
        )
        if payload.get('error'):
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        return Response(payload)

    @action(
        detail=False,
        methods=['post'],
        url_path='import-csv',
        permission_classes=[IsAuthenticated],
        parser_classes=[MultiPartParser, FormParser],
    )
    def import_csv(self, request):
        """
        Импорт датасета из CSV в БД.
        Ожидаемый файл: country_code, year, indicator_name, value [, unit [, equipment_class_code [, source_notes ]]]
        Query: apply_cleaning=1 — предобработка (дубликаты, типы, пропуски, признаки, нормализация).
        """
        csv_file = request.FILES.get('file') or request.FILES.get('csv')
        if not csv_file:
            return Response(
                {'error': 'Передайте файл в поле file или csv.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        raw = csv_file.read()
        if len(raw) > self.MAX_CSV_IMPORT_BYTES:
            return Response(
                {'error': f'Файл слишком большой (лимит {self.MAX_CSV_IMPORT_BYTES // (1024 * 1024)} MB).'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        apply_clean = str(request.query_params.get('apply_cleaning', '')).lower() in ('1', 'true', 'yes')
        try:
            thr = float(request.query_params.get('near_duplicate_threshold', '0.8'))
        except (ValueError, TypeError):
            thr = 0.8
        thr = max(0.5, min(1.0, thr))

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='wb',
                suffix=f'-{uuid.uuid4().hex}.csv',
                delete=False,
            ) as tmp:
                tmp.write(raw)
                tmp_path = tmp.name

            from .tasks.csv_import import import_dataset_csv_task

            task = import_dataset_csv_task.delay(
                source_path=tmp_path,
                apply_cleaning=apply_clean,
                near_duplicate_threshold=thr,
            )
        except Exception as e:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                'task_id': task.id,
                'status': 'queued',
                'message': 'Импорт CSV запущен в фоне.',
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=False, methods=['get'], url_path='import-csv-status', permission_classes=[IsAuthenticated])
    def import_csv_status(self, request):
        task_id = (request.query_params.get('task_id') or '').strip()
        if not task_id:
            return Response({'error': 'Укажите task_id.'}, status=status.HTTP_400_BAD_REQUEST)

        from celery.result import AsyncResult

        result = AsyncResult(task_id)
        state = (result.state or '').lower()
        payload = {'task_id': task_id, 'status': state}
        if state == 'success':
            payload['result'] = result.result or {}
        elif state == 'failure':
            payload['error'] = str(result.result)
        return Response(payload)

    @action(
        detail=False,
        methods=['post'],
        url_path='clean-csv',
        permission_classes=[IsAuthenticated],
        parser_classes=[MultiPartParser, FormParser],
    )
    def clean_csv(self, request):
        """
        Очистка CSV без записи в БД: дубликаты (в т.ч. ~80%+ схожесть строк), типы, заполнение пропусков
        средним по показателю, колонка value_imputed, производные и нормализация value по показателю.
        """
        csv_file = request.FILES.get('file') or request.FILES.get('csv')
        if not csv_file:
            return Response(
                {'error': 'Передайте файл в поле file или csv.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        raw = csv_file.read()
        if len(raw) > self.MAX_CSV_CLEAN_BYTES:
            return Response(
                {'error': f'Файл слишком большой (лимит {self.MAX_CSV_CLEAN_BYTES // (1024 * 1024)} MB).'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            thr = float(request.query_params.get('near_duplicate_threshold', '0.8'))
        except (ValueError, TypeError):
            thr = 0.8
        thr = max(0.5, min(1.0, thr))
        try:
            from .services.csv_cleaning import clean_csv_bytes

            outcome = clean_csv_bytes(raw, near_duplicate_threshold=thr)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'report': outcome.report, 'cleaned_csv': outcome.csv_text})


class EquipmentErgonomicsPluginStatusViewSet(ReadOnlyModelViewSet):
    """
    Публичный endpoint статуса плагина.
    Нужен фронту для показа/скрытия пункта «приложения», даже когда плагин выключен.
    """

    http_method_names = ['get']
    queryset = EquipmentMetricByCountry.objects.none()
    serializer_class = EquipmentMetricByCountrySerializer

    def list(self, request, *args, **kwargs):
        snap = get_snapshot()
        return Response(
            {
                'plugin_key': snap.plugin_key,
                'is_enabled': snap.is_enabled,
                'forced_disabled': snap.forced_disabled,
                'updated_at': snap.updated_at,
                'disabled_at': snap.disabled_at,
                'last_archive_path': snap.last_archive_path,
                'last_archive_meta': snap.last_archive_meta,
            }
        )


class AnalysisCoefficientViewSet(PluginGatedViewSetMixin, ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = AnalysisCoefficient.objects.all()
    serializer_class = AnalysisCoefficientSerializer
    lookup_field = 'id'


class AnalysisMetricViewSet(PluginGatedViewSetMixin, ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = AnalysisMetric.objects.all()
    serializer_class = AnalysisMetricSerializer
    lookup_field = 'id'


class CustomDatasetViewSet(PluginGatedViewSetMixin, ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = CustomDataset.objects.all()

    MAX_CSV_BYTES = CSV_MAX_BYTES

    def get_queryset(self):
        return super().get_queryset().filter(created_by=self.request.user)

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return CustomDatasetListSerializer
        return CustomDatasetCreateSerializer

    def create(self, request, *args, **kwargs):
        content = (request.data or {}).get('content_csv') or ''
        if content and len(str(content).encode('utf-8')) > self.MAX_CSV_BYTES:
            return Response(
                {'error': f'CSV слишком большой (лимит {self.MAX_CSV_BYTES // (1024 * 1024)} MB).'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().create(request, *args, **kwargs)


class AnalysisRunViewSet(PluginGatedViewSetMixin, ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = AnalysisRun.objects.select_related('dataset_ref', 'reused_from').all()
    serializer_class = AnalysisRunSerializer
    lookup_field = 'run_id'

    def get_queryset(self):
        return super().get_queryset().filter(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        """
        Создает запуск анализа и ставит Celery задачу в очередь.
        """
        from .services.analytics.run import create_or_reuse_run_and_enqueue

        payload = request.data or {}
        run = create_or_reuse_run_and_enqueue(user=request.user, payload=payload)
        return Response(AnalysisRunSerializer(run).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='status')
    def run_status(self, request, run_id=None):
        run = self.get_object()
        return Response({'run_id': str(run.run_id), 'status': run.status, 'error_message': run.error_message})

    @action(detail=True, methods=['get'], url_path='result')
    def run_result(self, request, run_id=None):
        run = self.get_object()
        if hasattr(run, 'result') and run.result is not None:
            return Response(AnalysisResultSerializer(run.result).data)

        # MVP: при переиспользовании run может не иметь result-отношение,
        # тогда пробуем взять result из reused_from (если оно есть).
        reused = getattr(run, 'reused_from', None)
        if reused is not None and hasattr(reused, 'result') and reused.result is not None:
            return Response(AnalysisResultSerializer(reused.result).data)

        return Response({'error': 'Результат ещё не готов.'}, status=status.HTTP_404_NOT_FOUND)


class AnalysisDashboardViewSet(PluginGatedViewSetMixin, ReadOnlyModelViewSet):
    """
    MVP дашборд: базовые агрегаты по датасету.
    """
    permission_classes = [IsAuthenticated]
    queryset = EquipmentMetricByCountry.objects.none()
    serializer_class = EquipmentMetricByCountrySerializer

    def list(self, request, *args, **kwargs):
        from django.db.models import Count

        metrics_total = EquipmentMetricByCountry.objects.count()
        countries = EquipmentMetricByCountry.objects.values('country_code').distinct().count()
        indicators = EquipmentMetricByCountry.objects.values('indicator_name').distinct().count()
        by_class = (
            EquipmentMetricByCountry.objects.values('equipment_class__code')
            .annotate(count=Count('id'))
            .order_by('-count')[:20]
        )
        return Response(
            {
                'metrics_total': metrics_total,
                'countries': countries,
                'indicators': indicators,
                'top_classes': list(by_class),
            }
        )
