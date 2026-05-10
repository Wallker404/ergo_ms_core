# Generated for equipment_ergonomics: categories, equipment, ergonomics records

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='ElectricalEquipmentClass',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Название')),
                ('code', models.SlugField(max_length=64, unique=True, verbose_name='Код')),
                ('is_non_eco', models.BooleanField(default=False, verbose_name='Неэкологичная (вред здоровью/среде)')),
                ('non_eco_reason', models.CharField(blank=True, choices=[('cooling', 'Охлаждающее оборудование (хладагенты)'), ('mercury_containing', 'Ртутьсодержащее оборудование'), ('heavy_metals_batteries', 'Оборудование с тяжёлыми металлами и батареями'), ('halogenated_pfas', 'Оборудование с галогенированными веществами / ПФАС'), ('e_waste_hazardous', 'Электроника с опасными веществами при утилизации')], max_length=32, verbose_name='Причина неэкологичности')),
                ('description', models.TextField(blank=True, verbose_name='Описание')),
                ('order', models.IntegerField(default=0, verbose_name='Порядок')),
            ],
            options={
                'verbose_name': 'Класс электротехники',
                'verbose_name_plural': 'Классы электротехники',
                'ordering': ['order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='EquipmentCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Название')),
                ('code', models.SlugField(max_length=64, unique=True, verbose_name='Код')),
                ('order', models.IntegerField(default=0, verbose_name='Порядок')),
            ],
            options={
                'verbose_name': 'Категория техники',
                'verbose_name_plural': 'Категории техники',
                'ordering': ['order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='ExternalDataFetch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_name', models.CharField(max_length=128, verbose_name='Источник')),
                ('request_url', models.TextField(blank=True, verbose_name='URL или идентификатор запроса')),
                ('fetched_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата запроса')),
                ('response_body', models.TextField(blank=True, verbose_name='Тело ответа (JSON/текст)')),
                ('status_code', models.IntegerField(blank=True, null=True, verbose_name='HTTP-код ответа')),
                ('error_message', models.TextField(blank=True, verbose_name='Сообщение об ошибке')),
            ],
            options={
                'verbose_name': 'Запрос к внешнему API',
                'verbose_name_plural': 'Запросы к внешним API',
                'ordering': ['-fetched_at'],
            },
        ),
        migrations.CreateModel(
            name='Equipment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Название')),
                ('equipment_type', models.CharField(choices=[('manual', 'Ручная'), ('mechanical', 'Механическая'), ('electrical', 'Электрическая')], max_length=32, verbose_name='Тип техники')),
                ('description', models.TextField(blank=True, verbose_name='Описание')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Дата обновления')),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='equipment_list', to='equipment_ergonomics.equipmentcategory', verbose_name='Категория')),
                ('electrical_class', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='equipment_list', to='equipment_ergonomics.electricalequipmentclass', verbose_name='Класс электротехники')),
            ],
            options={
                'verbose_name': 'Техника',
                'verbose_name_plural': 'Техника',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='EquipmentMetricByCountry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('country_code', models.CharField(db_index=True, max_length=8, verbose_name='Код страны (ISO)')),
                ('year', models.IntegerField(blank=True, db_index=True, null=True, verbose_name='Год')),
                ('indicator_name', models.CharField(db_index=True, max_length=255, verbose_name='Наименование показателя')),
                ('value', models.FloatField(blank=True, null=True, verbose_name='Значение')),
                ('unit', models.CharField(blank=True, max_length=64, verbose_name='Единица измерения')),
                ('source_notes', models.CharField(blank=True, max_length=512, verbose_name='Примечание к источнику')),
                ('equipment_class', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='metric_records', to='equipment_ergonomics.electricalequipmentclass', verbose_name='Класс техники')),
                ('source_fetch', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='metric_records', to='equipment_ergonomics.externaldatafetch', verbose_name='Источник (запрос к API)')),
            ],
            options={
                'verbose_name': 'Показатель по стране',
                'verbose_name_plural': 'Показатели по странам',
                'ordering': ['country_code', 'year', 'indicator_name'],
            },
        ),
        migrations.CreateModel(
            name='EquipmentErgonomicsRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('safety', models.FloatField(default=0, verbose_name='Безопасность')),
                ('comfort', models.FloatField(default=0, verbose_name='Комфорт')),
                ('functionality', models.FloatField(default=0, verbose_name='Функциональность')),
                ('controllability', models.FloatField(default=0, verbose_name='Управляемость')),
                ('learnability', models.FloatField(default=0, verbose_name='Освояемость')),
                ('total_score', models.FloatField(blank=True, null=True, verbose_name='Итоговая оценка')),
                ('source_notes', models.TextField(blank=True, verbose_name='Примечания к источнику')),
                ('recorded_at', models.DateTimeField(blank=True, null=True, verbose_name='Дата фиксации')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('equipment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ergonomics_records', to='equipment_ergonomics.equipment', verbose_name='Техника')),
            ],
            options={
                'verbose_name': 'Запись эргономики',
                'verbose_name_plural': 'Записи эргономики',
                'ordering': ['-recorded_at', '-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='equipmentmetricbycountry',
            index=models.Index(fields=['country_code', 'year'], name='equipment_er_country_8b0f0d_idx'),
        ),
        migrations.AddIndex(
            model_name='equipmentmetricbycountry',
            index=models.Index(fields=['equipment_class', 'year'], name='equipment_er_equipme_2a8c2a_idx'),
        ),
    ]
