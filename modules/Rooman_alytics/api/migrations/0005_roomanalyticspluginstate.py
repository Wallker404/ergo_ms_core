from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('rooman_alytics', '0004_alter_onnxmodel_onnx_file'),
    ]

    operations = [
        migrations.CreateModel(
            name='RoomAnalyticsPluginState',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('plugin_key', models.SlugField(default='rooman_alytics', max_length=64, unique=True, verbose_name='Ключ плагина')),
                ('is_enabled', models.BooleanField(default=False, verbose_name='Включен')),
                ('disabled_at', models.DateTimeField(blank=True, null=True, verbose_name='Дата выключения')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
            ],
            options={
                'verbose_name': 'Состояние плагина room analytics',
                'verbose_name_plural': 'Состояние плагина room analytics',
            },
        ),
    ]
