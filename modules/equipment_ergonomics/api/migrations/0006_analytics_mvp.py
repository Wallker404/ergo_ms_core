from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ('equipment_ergonomics', '0005_plugin_state'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='AnalysisCoefficient',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.SlugField(max_length=64, unique=True, verbose_name='Ключ')),
                ('name', models.CharField(max_length=255, verbose_name='Название')),
                ('value', models.FloatField(default=1.0, verbose_name='Значение')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активен')),
                ('version', models.IntegerField(default=1, verbose_name='Версия')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
            ],
            options={
                'verbose_name': 'Коэффициент анализа',
                'verbose_name_plural': 'Коэффициенты анализа',
                'ordering': ['key'],
            },
        ),
        migrations.CreateModel(
            name='AnalysisMetric',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.SlugField(max_length=64, unique=True, verbose_name='Ключ')),
                ('name', models.CharField(max_length=255, verbose_name='Название')),
                ('description', models.TextField(blank=True, verbose_name='Описание')),
                ('metric_type', models.CharField(choices=[('source', 'Источник'), ('proxy', 'Proxy/расчет'), ('custom', 'Пользовательский')], default='source', max_length=16, verbose_name='Тип')),
                ('formula_json', models.JSONField(blank=True, null=True, verbose_name='Формула/настройки')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активен')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
            ],
            options={
                'verbose_name': 'Показатель анализа',
                'verbose_name_plural': 'Показатели анализа',
                'ordering': ['key'],
            },
        ),
        migrations.CreateModel(
            name='CustomDataset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Название')),
                ('schema_json', models.JSONField(blank=True, null=True, verbose_name='Схема')),
                ('content_csv', models.TextField(verbose_name='CSV содержимое')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='equipment_custom_datasets', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Кастомный датасет',
                'verbose_name_plural': 'Кастомные датасеты',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AnalysisRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('run_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='Run ID')),
                ('status', models.CharField(choices=[('queued', 'В очереди'), ('running', 'Выполняется'), ('done', 'Готово'), ('error', 'Ошибка')], default='queued', max_length=16, verbose_name='Статус')),
                ('task_id', models.CharField(blank=True, max_length=128, verbose_name='Celery task id')),
                ('method', models.SlugField(max_length=64, verbose_name='Метод')),
                ('config_json', models.JSONField(blank=True, null=True, verbose_name='Конфигурация')),
                ('config_hash', models.CharField(blank=True, db_index=True, max_length=64, verbose_name='Хэш конфигурации')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                ('started_at', models.DateTimeField(blank=True, null=True, verbose_name='Старт')),
                ('finished_at', models.DateTimeField(blank=True, null=True, verbose_name='Финиш')),
                ('error_message', models.TextField(blank=True, verbose_name='Ошибка')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='equipment_analysis_runs', to=settings.AUTH_USER_MODEL)),
                ('dataset_ref', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='analysis_runs', to='equipment_ergonomics.customdataset')),
                ('reused_from', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reused_runs', to='equipment_ergonomics.analysisrun')),
            ],
            options={
                'verbose_name': 'Запуск анализа',
                'verbose_name_plural': 'Запуски анализа',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AnalysisResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('metrics_json', models.JSONField(blank=True, null=True, verbose_name='Метрики качества')),
                ('charts_json', models.JSONField(blank=True, null=True, verbose_name='Данные графиков')),
                ('explanation_json', models.JSONField(blank=True, null=True, verbose_name='Вывод 1/2/3')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                ('run', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='result', to='equipment_ergonomics.analysisrun')),
            ],
            options={
                'verbose_name': 'Результат анализа',
                'verbose_name_plural': 'Результаты анализа',
            },
        ),
    ]

