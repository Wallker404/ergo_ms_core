# Unique constraint on (country_code, year, indicator_name) and seed energy_aggregate class

from django.db import migrations, models


def remove_duplicate_metrics(apps, schema_editor):
    """Оставляем по одной записи на (country_code, year, indicator_name)."""
    EquipmentMetricByCountry = apps.get_model('equipment_ergonomics', 'EquipmentMetricByCountry')
    from django.db.models import Min
    # Оставляем запись с минимальным id для каждой тройки
    keep_ids = (
        EquipmentMetricByCountry.objects.values('country_code', 'year', 'indicator_name')
        .annotate(min_id=Min('id'))
        .values_list('min_id', flat=True)
    )
    deleted = EquipmentMetricByCountry.objects.exclude(id__in=keep_ids).delete()[0]
    if deleted:
        print(f'  Removed {deleted} duplicate metric(s).')


def seed_energy_class(apps, schema_editor):
    ElectricalEquipmentClass = apps.get_model('equipment_ergonomics', 'ElectricalEquipmentClass')
    ElectricalEquipmentClass.objects.get_or_create(
        code='energy_aggregate',
        defaults={
            'name': 'Энергетика (агрегированные показатели)',
            'is_non_eco': False,
            'non_eco_reason': '',
            'order': 5,
            'description': 'Потребление электроэнергии, первичной энергии и др. по странам (OWID).',
        },
    )


def reverse_energy_class(apps, schema_editor):
    ElectricalEquipmentClass = apps.get_model('equipment_ergonomics', 'ElectricalEquipmentClass')
    ElectricalEquipmentClass.objects.filter(code='energy_aggregate').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('equipment_ergonomics', '0002_seed_electrical_classes'),
    ]

    operations = [
        migrations.RunPython(remove_duplicate_metrics, migrations.RunPython.noop),
        migrations.RunPython(seed_energy_class, reverse_energy_class),
        migrations.AddConstraint(
            model_name='equipmentmetricbycountry',
            constraint=models.UniqueConstraint(
                fields=('country_code', 'year', 'indicator_name'),
                name='equipment_ergonomics_metric_country_year_indicator_unique',
            ),
        ),
    ]
