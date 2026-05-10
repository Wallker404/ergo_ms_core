# Data migration: подклассы энергетики для разбивки показателей OWID

from django.db import migrations


def seed_energy_subclasses(apps, schema_editor):
    ElectricalEquipmentClass = apps.get_model('equipment_ergonomics', 'ElectricalEquipmentClass')
    subclasses = [
        {'name': 'Уголь', 'code': 'energy_coal', 'is_non_eco': False, 'non_eco_reason': '', 'order': 4,
         'description': 'Потребление и производство угля, доля угля в энергобалансе (OWID).'},
        {'name': 'Газ', 'code': 'energy_gas', 'is_non_eco': False, 'non_eco_reason': '', 'order': 6,
         'description': 'Потребление и производство газа (OWID).'},
        {'name': 'Нефть', 'code': 'energy_oil', 'is_non_eco': False, 'non_eco_reason': '', 'order': 7,
         'description': 'Потребление и производство нефти (OWID).'},
        {'name': 'Ядерная энергия', 'code': 'energy_nuclear', 'is_non_eco': False, 'non_eco_reason': '', 'order': 8,
         'description': 'Потребление ядерной энергии, доля в энергобалансе (OWID).'},
        {'name': 'ВИЭ', 'code': 'energy_renewables', 'is_non_eco': False, 'non_eco_reason': '', 'order': 9,
         'description': 'Гидро, солнце, ветер, биотопливо, прочие ВИЭ (OWID).'},
        {'name': 'Ископаемое топливо', 'code': 'energy_fossil', 'is_non_eco': False, 'non_eco_reason': '', 'order': 10,
         'description': 'Совокупное потребление ископаемого топлива (OWID).'},
        {'name': 'Низкоуглеродная энергия', 'code': 'energy_low_carbon', 'is_non_eco': False, 'non_eco_reason': '', 'order': 11,
         'description': 'Низкоуглеродное потребление (ядерная + ВИЭ) (OWID).'},
        {'name': 'Электроэнергия', 'code': 'energy_electricity', 'is_non_eco': False, 'non_eco_reason': '', 'order': 12,
         'description': 'Спрос и выработка электроэнергии, импорт/экспорт (OWID).'},
        {'name': 'Выбросы и углеродоёмкость', 'code': 'energy_emissions', 'is_non_eco': False, 'non_eco_reason': '', 'order': 13,
         'description': 'Выбросы ПГ, углеродоёмкость электроэнергии (OWID).'},
    ]
    for c in subclasses:
        ElectricalEquipmentClass.objects.get_or_create(code=c['code'], defaults=c)


def reverse_seed(apps, schema_editor):
    ElectricalEquipmentClass = apps.get_model('equipment_ergonomics', 'ElectricalEquipmentClass')
    codes = [
        'energy_coal', 'energy_gas', 'energy_oil', 'energy_nuclear',
        'energy_renewables', 'energy_fossil', 'energy_low_carbon',
        'energy_electricity', 'energy_emissions',
    ]
    ElectricalEquipmentClass.objects.filter(code__in=codes).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('equipment_ergonomics', '0003_metric_unique_and_energy_class'),
    ]

    operations = [
        migrations.RunPython(seed_energy_subclasses, reverse_seed),
    ]
