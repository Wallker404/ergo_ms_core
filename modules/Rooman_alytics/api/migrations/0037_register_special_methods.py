from django.db import migrations


def register_special_methods(apps, schema_editor):
    AutoCountingMethod = apps.get_model('rooman_alytics', 'AutoCountingMethod')
    
    methods = [
        {
            'name': 'GetRoomCount',
            'label': 'Количество комнат типа',
            'inputType': 'rooms',
        },
        {
            'name': 'GetFreeSpacePercentage',
            'label': 'Доля свободного пространства',
            'inputType': 'rooms',
        },

    ]
    
    for method_data in methods:
            # ✅ Используем get_or_create вместо update_or_create
            obj, created = AutoCountingMethod.objects.get_or_create(
                name=method_data['name'],
                defaults={
                    'label': method_data['label'],
                    'inputType': method_data['inputType'],
                }
            )
            # ✅ Если запись уже существовала — обновляем поля
            if not created:
                obj.label = method_data['label']
                obj.inputType = method_data['inputType']
                obj.save()


def reverse_register(apps, schema_editor):
    AutoCountingMethod = apps.get_model('rooman_alytics', 'AutoCountingMethod')
    AutoCountingMethod.objects.filter(
        name__in=[
            'GetMinAislewidth',
            'CheckRequiredFurniture',
            'GetRoomCount',
            'GetFreeSpacePercentage',
            'GetFurnitureCount',
            'GetCountOfFurnitureInRoom',
        ]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('rooman_alytics', '0036_commonformula_name_systemequastion_name'),  # замените на актуальную
    ]

    operations = [
        migrations.RunPython(
            register_special_methods,
            reverse_register,
        ),
    ]