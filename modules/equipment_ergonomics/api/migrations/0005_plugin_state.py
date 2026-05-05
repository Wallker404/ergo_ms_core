from django.db import migrations, models


def create_default_state(apps, schema_editor):
    State = apps.get_model('equipment_ergonomics', 'EquipmentErgonomicsPluginState')
    State.objects.get_or_create(
        plugin_key='equipment_ergonomics',
        defaults={'is_enabled': False},
    )


class Migration(migrations.Migration):
    dependencies = [
        ('equipment_ergonomics', '0004_seed_energy_subclasses'),
    ]

    operations = [
        migrations.CreateModel(
            name='EquipmentErgonomicsPluginState',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('plugin_key', models.SlugField(default='equipment_ergonomics', max_length=64, unique=True, verbose_name='Ключ плагина')),
                ('is_enabled', models.BooleanField(default=False, verbose_name='Включен')),
                ('disabled_at', models.DateTimeField(blank=True, null=True, verbose_name='Дата выключения')),
                ('last_archive_path', models.TextField(blank=True, verbose_name='Путь последнего архива')),
                ('last_archive_meta', models.JSONField(blank=True, null=True, verbose_name='Метаданные последнего архива')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
            ],
            options={
                'verbose_name': 'Состояние плагина ergonomics',
                'verbose_name_plural': 'Состояние плагина ergonomics',
            },
        ),
        migrations.RunPython(create_default_state, reverse_code=migrations.RunPython.noop),
    ]

