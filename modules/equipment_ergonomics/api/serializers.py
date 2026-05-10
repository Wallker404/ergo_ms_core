from rest_framework import serializers

CSV_MAX_BYTES = 64 * 1024 * 1024

from .models import (
    ElectricalEquipmentClass,
    EquipmentMetricByCountry,
    AnalysisCoefficient,
    AnalysisMetric,
    CustomDataset,
    AnalysisRun,
    AnalysisResult,
)


INDICATOR_LABELS = {
    'electricity_demand': 'Потребление электроэнергии (TWh)',
    'electricity_demand_per_capita': 'Потребление электроэнергии на душу (кВт·ч)',
    'electricity_generation': 'Выработка электроэнергии (TWh)',
    'energy_per_capita': 'Потребление первичной энергии на душу (кВт·ч)',
    'primary_energy_consumption': 'Потребление первичной энергии (TWh)',
    'coal_consumption': 'Потребление угля (TWh)',
    'gas_consumption': 'Потребление газа (TWh)',
    'oil_consumption': 'Потребление нефти (TWh)',
    'nuclear_consumption': 'Потребление ядерной энергии (TWh)',
    'hydro_consumption': 'Потребление ГЭС (TWh)',
    'solar_consumption': 'Потребление солнечной энергии (TWh)',
    'wind_consumption': 'Потребление ветровой энергии (TWh)',
    'renewable_consumption': 'Потребление ВИЭ (TWh)',
    'low_carbon_consumption': 'Низкоуглеродное потребление (TWh)',
    'fossil_fuel_consumption': 'Потребление ископаемого топлива (TWh)',
    'carbon_intensity_elec': 'Углеродоёмкость электроэнергии (г CO₂/кВт·ч)',
    'greenhouse_gas_emissions': 'Выбросы ПГ от электроэнергии (Mt CO₂)',
    # World Bank (префикс wb_)
    'wb_eg_use_elec_kh_pc': 'Потребление электроэнергии на душу (World Bank), кВт·ч',
    'wb_eg_use_pcap_kg_oe': 'Потребление энергии на душу (World Bank), кг нефтяного экв.',
    'wb_eg_elc_accs_zs': 'Доступ к электроэнергии, % населения (World Bank)',
    'wb_eg_fec_rnew_zs': 'Доля ВИЭ в потреблении (World Bank), %',
    'wb_eg_imp_cons_zs': 'Импорт энергоносителей, % потребления (World Bank)',
    'wb_en_atm_co2e_pc': 'Выбросы CO₂ на душу (World Bank), т CO₂',
}

# Единицы измерения для отображения на фронте (если в БД пусто)
INDICATOR_UNITS = {
    'electricity_demand': 'TWh',
    'electricity_demand_per_capita': 'kWh',
    'electricity_generation': 'TWh',
    'energy_per_capita': 'kWh',
    'primary_energy_consumption': 'TWh',
    'coal_consumption': 'TWh',
    'gas_consumption': 'TWh',
    'oil_consumption': 'TWh',
    'nuclear_consumption': 'TWh',
    'hydro_consumption': 'TWh',
    'solar_consumption': 'TWh',
    'wind_consumption': 'TWh',
    'renewable_consumption': 'TWh',
    'renewables_consumption': 'TWh',
    'low_carbon_consumption': 'TWh',
    'fossil_fuel_consumption': 'TWh',
    'carbon_intensity_elec': 'g CO₂/kWh',
    'greenhouse_gas_emissions': 'Mt CO₂',
    'energy_cons_change_pct': '%',
    'energy_cons_change_twh': 'TWh',
    'wb_eg_use_elec_kh_pc': 'kWh',
    'wb_eg_use_pcap_kg_oe': 'kg oil eq',
    'wb_eg_elc_accs_zs': '%',
    'wb_eg_fec_rnew_zs': '%',
    'wb_eg_imp_cons_zs': '%',
    'wb_en_atm_co2e_pc': 't CO2',
}


def _unit_from_indicator_name(name: str) -> str:
    """Вывод единицы по имени показателя для старых записей без unit."""
    if not name:
        return ''
    n = name.lower()
    if '_change_pct' in n or '_share_' in n or n.endswith('_pct'):
        return '%'
    if '_change_twh' in n:
        return 'TWh'
    if '_per_capita' in n or '_elec_per_capita' in n or n == 'per_capita_electricity':
        return 'kWh'
    if '_consumption' in n or '_electricity' in n or '_production' in n or 'net_elec_imports' in n:
        return 'TWh'
    if 'carbon_intensity' in n:
        return 'g CO₂/kWh'
    if 'greenhouse_gas' in n:
        return 'Mt CO₂'
    if 'share' in n:
        return '%'
    return ''


class ElectricalEquipmentClassSerializer(serializers.ModelSerializer):
    """Класс электротехники для списков и фильтров."""

    class Meta:
        model = ElectricalEquipmentClass
        fields = ('id', 'name', 'code', 'is_non_eco', 'non_eco_reason', 'description', 'order')


class EquipmentMetricByCountrySerializer(serializers.ModelSerializer):
    """Показатель по стране — с человекочитаемыми полями для фронта."""

    indicator_label = serializers.SerializerMethodField()
    equipment_class_code = serializers.SerializerMethodField()
    equipment_class_name = serializers.SerializerMethodField()

    class Meta:
        model = EquipmentMetricByCountry
        fields = (
            'id',
            'country_code',
            'year',
            'indicator_name',
            'indicator_label',
            'value',
            'unit',
            'equipment_class_code',
            'equipment_class_name',
            'source_notes',
        )

    def get_indicator_label(self, obj):
        return INDICATOR_LABELS.get(obj.indicator_name) or obj.indicator_name.replace('_', ' ').title()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not data.get('unit') and instance.indicator_name:
            data['unit'] = (
                INDICATOR_UNITS.get(instance.indicator_name)
                or _unit_from_indicator_name(instance.indicator_name)
                or ''
            )
        return data

    def get_equipment_class_code(self, obj):
        return obj.equipment_class.code if obj.equipment_class_id else None

    def get_equipment_class_name(self, obj):
        return obj.equipment_class.name if obj.equipment_class_id else None


class AnalysisCoefficientSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisCoefficient
        fields = ('id', 'key', 'name', 'value', 'is_active', 'version', 'updated_at')


class AnalysisMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisMetric
        fields = ('id', 'key', 'name', 'description', 'metric_type', 'formula_json', 'is_active', 'updated_at')


class CustomDatasetCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomDataset
        fields = ('id', 'name', 'schema_json', 'content_csv', 'created_at')
        read_only_fields = ('id', 'created_at')

    def validate_content_csv(self, value: str) -> str:
        if value and len(value.encode('utf-8')) > CSV_MAX_BYTES:
            raise serializers.ValidationError(f'CSV слишком большой (лимит {CSV_MAX_BYTES // (1024 * 1024)} MB).')
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            raise serializers.ValidationError('Требуется авторизация.')
        return CustomDataset.objects.create(created_by=request.user, **validated_data)


class CustomDatasetListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomDataset
        fields = ('id', 'name', 'schema_json', 'created_at')


class AnalysisRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisRun
        fields = (
            'run_id',
            'status',
            'task_id',
            'method',
            'config_json',
            'config_hash',
            'dataset_ref',
            'reused_from',
            'created_at',
            'started_at',
            'finished_at',
            'error_message',
        )


class AnalysisResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisResult
        fields = ('metrics_json', 'charts_json', 'explanation_json', 'created_at')

