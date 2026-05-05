# Data migration: seed electrical equipment classes (including non-eco)

from django.db import migrations


def seed_electrical_classes(apps, schema_editor):
    ElectricalEquipmentClass = apps.get_model('equipment_ergonomics', 'ElectricalEquipmentClass')
    classes = [
        # Неэкологичные классы (is_non_eco=True)
        {'name': 'Охлаждающее оборудование (хладагенты)', 'code': 'cooling', 'is_non_eco': True, 'non_eco_reason': 'cooling', 'order': 10,
         'description': 'Кондиционеры, холодильники, морозильники, чиллеры. Вред: хладагенты (HFC, HCFC и др.) — токсичность, воздействие на здоровье человека.'},
        {'name': 'Ртутьсодержащее оборудование', 'code': 'mercury_containing', 'is_non_eco': True, 'non_eco_reason': 'mercury_containing', 'order': 20,
         'description': 'Ртутные лампы, старые дисплеи. Вред: ртуть при повреждении или утилизации.'},
        {'name': 'Оборудование с тяжёлыми металлами и батареями', 'code': 'heavy_metals_batteries', 'is_non_eco': True, 'non_eco_reason': 'heavy_metals_batteries', 'order': 30,
         'description': 'Аккумуляторы, часть электроники. Вред: свинец, кадмий, кобальт при утилизации и производстве.'},
        {'name': 'Оборудование с галогенированными веществами / ПФАС', 'code': 'halogenated_pfas', 'is_non_eco': True, 'non_eco_reason': 'halogenated_pfas', 'order': 40,
         'description': 'Изоляция, антипригарные покрытия в электроприборах, часть хладагентов. Вред: ПФАС и продукты разложения.'},
        {'name': 'Электроника с опасными веществами при утилизации', 'code': 'e_waste_hazardous', 'is_non_eco': True, 'non_eco_reason': 'e_waste_hazardous', 'order': 50,
         'description': 'Устройства с бромированными антипиренами, тяжёлыми металлами в платах. Вред при неправильной утилизации.'},
        # Нейтральные классы (для сравнения и полноты)
        {'name': 'Бытовая техника (без хладагентов)', 'code': 'household_other', 'is_non_eco': False, 'non_eco_reason': '', 'order': 60, 'description': 'Стиральные машины, посудомойки, плиты, мелкая техника.'},
        {'name': 'Осветительное оборудование', 'code': 'lighting', 'is_non_eco': False, 'non_eco_reason': '', 'order': 70, 'description': 'Светильники, LED (без ртути).'},
        {'name': 'ИКТ и бытовая электроника', 'code': 'ict_consumer', 'is_non_eco': False, 'non_eco_reason': '', 'order': 80, 'description': 'ТВ, ПК, мобильные устройства (общий класс).'},
        {'name': 'Электроприготовление пищи', 'code': 'e_cooking', 'is_non_eco': False, 'non_eco_reason': '', 'order': 90, 'description': 'Электроплиты, e-cooking приборы.'},
    ]
    for c in classes:
        ElectricalEquipmentClass.objects.get_or_create(code=c['code'], defaults=c)


def reverse_seed(apps, schema_editor):
    ElectricalEquipmentClass = apps.get_model('equipment_ergonomics', 'ElectricalEquipmentClass')
    codes = [c['code'] for c in (
        {'code': 'cooling'}, {'code': 'mercury_containing'}, {'code': 'heavy_metals_batteries'},
        {'code': 'halogenated_pfas'}, {'code': 'e_waste_hazardous'}, {'code': 'household_other'},
        {'code': 'lighting'}, {'code': 'ict_consumer'}, {'code': 'e_cooking'},
    )]
    ElectricalEquipmentClass.objects.filter(code__in=codes).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('equipment_ergonomics', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_electrical_classes, reverse_seed),
    ]
