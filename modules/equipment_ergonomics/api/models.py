from django.db import models
from django.contrib.auth.models import User
import uuid


class EquipmentErgonomicsPluginState(models.Model):
    """
    Состояние плагина equipment_ergonomics.

    Источник истины: БД (is_enabled), но может быть принудительно выключен через ENV.
    По умолчанию: выключен.
    """

    plugin_key = models.SlugField('Ключ плагина', max_length=64, unique=True, default='equipment_ergonomics')
    is_enabled = models.BooleanField('Включен', default=False)
    disabled_at = models.DateTimeField('Дата выключения', null=True, blank=True)
    last_archive_path = models.TextField('Путь последнего архива', blank=True)
    last_archive_meta = models.JSONField('Метаданные последнего архива', null=True, blank=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        app_label = 'equipment_ergonomics'
        verbose_name = 'Состояние плагина ergonomics'
        verbose_name_plural = 'Состояние плагина ergonomics'

    def __str__(self):
        return f'{self.plugin_key}: {"enabled" if self.is_enabled else "disabled"}'


class AnalysisCoefficient(models.Model):
    key = models.SlugField('Ключ', max_length=64, unique=True)
    name = models.CharField('Название', max_length=255)
    value = models.FloatField('Значение', default=1.0)
    is_active = models.BooleanField('Активен', default=True)
    version = models.IntegerField('Версия', default=1)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        app_label = 'equipment_ergonomics'
        verbose_name = 'Коэффициент анализа'
        verbose_name_plural = 'Коэффициенты анализа'
        ordering = ['key']


class AnalysisMetric(models.Model):
    METRIC_SOURCE = 'source'
    METRIC_PROXY = 'proxy'
    METRIC_CUSTOM = 'custom'
    METRIC_TYPE_CHOICES = [
        (METRIC_SOURCE, 'Источник'),
        (METRIC_PROXY, 'Proxy/расчет'),
        (METRIC_CUSTOM, 'Пользовательский'),
    ]

    key = models.SlugField('Ключ', max_length=64, unique=True)
    name = models.CharField('Название', max_length=255)
    description = models.TextField('Описание', blank=True)
    metric_type = models.CharField('Тип', max_length=16, choices=METRIC_TYPE_CHOICES, default=METRIC_SOURCE)
    formula_json = models.JSONField('Формула/настройки', null=True, blank=True)
    is_active = models.BooleanField('Активен', default=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        app_label = 'equipment_ergonomics'
        verbose_name = 'Показатель анализа'
        verbose_name_plural = 'Показатели анализа'
        ordering = ['key']


class CustomDataset(models.Model):
    """
    Кастомные данные, введенные пользователем.
    Храним CSV как текст (MVP).
    """
    name = models.CharField('Название', max_length=255)
    schema_json = models.JSONField('Схема', null=True, blank=True)
    content_csv = models.TextField('CSV содержимое')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='equipment_custom_datasets')
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        app_label = 'equipment_ergonomics'
        verbose_name = 'Кастомный датасет'
        verbose_name_plural = 'Кастомные датасеты'
        ordering = ['-created_at']


class AnalysisRun(models.Model):
    STATUS_QUEUED = 'queued'
    STATUS_RUNNING = 'running'
    STATUS_DONE = 'done'
    STATUS_ERROR = 'error'
    STATUS_CHOICES = [
        (STATUS_QUEUED, 'В очереди'),
        (STATUS_RUNNING, 'Выполняется'),
        (STATUS_DONE, 'Готово'),
        (STATUS_ERROR, 'Ошибка'),
    ]

    run_id = models.UUIDField('Run ID', default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField('Статус', max_length=16, choices=STATUS_CHOICES, default=STATUS_QUEUED)
    task_id = models.CharField('Celery task id', max_length=128, blank=True)
    method = models.SlugField('Метод', max_length=64)
    config_json = models.JSONField('Конфигурация', null=True, blank=True)
    config_hash = models.CharField('Хэш конфигурации', max_length=64, blank=True, db_index=True)
    dataset_ref = models.ForeignKey(CustomDataset, null=True, blank=True, on_delete=models.SET_NULL, related_name='analysis_runs')
    reused_from = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='reused_runs')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='equipment_analysis_runs')
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    started_at = models.DateTimeField('Старт', null=True, blank=True)
    finished_at = models.DateTimeField('Финиш', null=True, blank=True)
    error_message = models.TextField('Ошибка', blank=True)

    class Meta:
        app_label = 'equipment_ergonomics'
        verbose_name = 'Запуск анализа'
        verbose_name_plural = 'Запуски анализа'
        ordering = ['-created_at']


class AnalysisResult(models.Model):
    run = models.OneToOneField(AnalysisRun, on_delete=models.CASCADE, related_name='result')
    metrics_json = models.JSONField('Метрики качества', null=True, blank=True)
    charts_json = models.JSONField('Данные графиков', null=True, blank=True)
    explanation_json = models.JSONField('Вывод 1/2/3', null=True, blank=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        app_label = 'equipment_ergonomics'
        verbose_name = 'Результат анализа'
        verbose_name_plural = 'Результаты анализа'


class ElectricalEquipmentClass(models.Model):
    """
    Класс электротехники для аналитики и трендов.
    is_non_eco=True — заведомо неэкологичная техника (вред здоровью или среде: хладагенты, ртуть, тяжёлые металлы, ПФАС и т.д.).
    """

    NON_ECO_COOLING = 'cooling'
    NON_ECO_MERCURY = 'mercury_containing'
    NON_ECO_HEAVY_METALS = 'heavy_metals_batteries'
    NON_ECO_HALOGENATED_PFAS = 'halogenated_pfas'
    NON_ECO_E_WASTE = 'e_waste_hazardous'
    NON_ECO_CODE_CHOICES = [
        (NON_ECO_COOLING, 'Охлаждающее оборудование (хладагенты)'),
        (NON_ECO_MERCURY, 'Ртутьсодержащее оборудование'),
        (NON_ECO_HEAVY_METALS, 'Оборудование с тяжёлыми металлами и батареями'),
        (NON_ECO_HALOGENATED_PFAS, 'Оборудование с галогенированными веществами / ПФАС'),
        (NON_ECO_E_WASTE, 'Электроника с опасными веществами при утилизации'),
    ]

    name = models.CharField('Название', max_length=255)
    code = models.SlugField('Код', max_length=64, unique=True)
    is_non_eco = models.BooleanField('Неэкологичная (вред здоровью/среде)', default=False)
    non_eco_reason = models.CharField(
        'Причина неэкологичности',
        max_length=32,
        choices=NON_ECO_CODE_CHOICES,
        blank=True,
    )
    description = models.TextField('Описание', blank=True)
    order = models.IntegerField('Порядок', default=0)

    class Meta:
        app_label = 'equipment_ergonomics'
        verbose_name = 'Класс электротехники'
        verbose_name_plural = 'Классы электротехники'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class ExternalDataFetch(models.Model):
    """
    Кэш ответов внешних API. Все получаемые при запросах данные сохраняются в БД.
    """
    source_name = models.CharField('Источник', max_length=128)
    request_url = models.TextField('URL или идентификатор запроса', blank=True)
    fetched_at = models.DateTimeField('Дата запроса', auto_now_add=True)
    response_body = models.TextField('Тело ответа (JSON/текст)', blank=True)
    status_code = models.IntegerField('HTTP-код ответа', null=True, blank=True)
    error_message = models.TextField('Сообщение об ошибке', blank=True)

    class Meta:
        app_label = 'equipment_ergonomics'
        verbose_name = 'Запрос к внешнему API'
        verbose_name_plural = 'Запросы к внешним API'
        ordering = ['-fetched_at']


class EquipmentMetricByCountry(models.Model):
    """
    Нормализованные показатели по странам/годам/классам техники (из внешних API или CSV).
    Итоговая работа ведётся в т.ч. через экспорт/импорт CSV.
    """
    country_code = models.CharField('Код страны (ISO)', max_length=8, db_index=True)
    year = models.IntegerField('Год', null=True, blank=True, db_index=True)
    equipment_class = models.ForeignKey(
        ElectricalEquipmentClass,
        on_delete=models.PROTECT,
        related_name='metric_records',
        verbose_name='Класс техники',
        null=True,
        blank=True,
    )
    indicator_name = models.CharField('Наименование показателя', max_length=255, db_index=True)
    value = models.FloatField('Значение', null=True, blank=True)
    unit = models.CharField('Единица измерения', max_length=64, blank=True)
    source_fetch = models.ForeignKey(
        ExternalDataFetch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='metric_records',
        verbose_name='Источник (запрос к API)',
    )
    source_notes = models.CharField('Примечание к источнику', max_length=512, blank=True)

    class Meta:
        app_label = 'equipment_ergonomics'
        verbose_name = 'Показатель по стране'
        verbose_name_plural = 'Показатели по странам'
        ordering = ['country_code', 'year', 'indicator_name']
        constraints = [
            models.UniqueConstraint(
                fields=['country_code', 'year', 'indicator_name'],
                name='equipment_ergonomics_metric_country_year_indicator_unique',
            ),
        ]
        indexes = [
            models.Index(fields=['country_code', 'year']),
            models.Index(fields=['equipment_class', 'year']),
        ]


class EquipmentCategory(models.Model):
    """Категория техники: оружие, машины, электроинструмент и т.д."""

    name = models.CharField('Название', max_length=255)
    code = models.SlugField('Код', max_length=64, unique=True)
    order = models.IntegerField('Порядок', default=0)

    class Meta:
        app_label = 'equipment_ergonomics'
        verbose_name = 'Категория техники'
        verbose_name_plural = 'Категории техники'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Equipment(models.Model):
    """Единица техники в справочнике."""

    EQUIPMENT_TYPE_MANUAL = 'manual'
    EQUIPMENT_TYPE_MECHANICAL = 'mechanical'
    EQUIPMENT_TYPE_ELECTRICAL = 'electrical'
    EQUIPMENT_TYPE_CHOICES = [
        (EQUIPMENT_TYPE_MANUAL, 'Ручная'),
        (EQUIPMENT_TYPE_MECHANICAL, 'Механическая'),
        (EQUIPMENT_TYPE_ELECTRICAL, 'Электрическая'),
    ]

    name = models.CharField('Название', max_length=255)
    category = models.ForeignKey(
        EquipmentCategory,
        on_delete=models.PROTECT,
        related_name='equipment_list',
        verbose_name='Категория',
        null=True,
        blank=True,
    )
    equipment_type = models.CharField(
        'Тип техники',
        max_length=32,
        choices=EQUIPMENT_TYPE_CHOICES,
    )
    description = models.TextField('Описание', blank=True)
    electrical_class = models.ForeignKey(
        ElectricalEquipmentClass,
        on_delete=models.PROTECT,
        related_name='equipment_list',
        verbose_name='Класс электротехники',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        app_label = 'equipment_ergonomics'
        verbose_name = 'Техника'
        verbose_name_plural = 'Техника'
        ordering = ['name']

    def __str__(self):
        return self.name


class EquipmentErgonomicsRecord(models.Model):
    """Запись датасета: метрики эргономики по одной единице техники."""

    CRITERIA_MAX = 100.0

    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.CASCADE,
        related_name='ergonomics_records',
        verbose_name='Техника',
    )
    safety = models.FloatField('Безопасность', default=0)
    comfort = models.FloatField('Комфорт', default=0)
    functionality = models.FloatField('Функциональность', default=0)
    controllability = models.FloatField('Управляемость', default=0)
    learnability = models.FloatField('Освояемость', default=0)
    total_score = models.FloatField('Итоговая оценка', null=True, blank=True)
    source_notes = models.TextField('Примечания к источнику', blank=True)
    recorded_at = models.DateTimeField('Дата фиксации', null=True, blank=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)

    class Meta:
        app_label = 'equipment_ergonomics'
        verbose_name = 'Запись эргономики'
        verbose_name_plural = 'Записи эргономики'
        ordering = ['-recorded_at', '-created_at']

    def save(self, *args, **kwargs):
        criteria_values = [
            self.safety,
            self.comfort,
            self.functionality,
            self.controllability,
            self.learnability,
        ]
        valid = [v for v in criteria_values if v is not None]
        self.total_score = sum(valid) / len(valid) if valid else None
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.equipment.name} — {self.total_score or "-"}'
