from django.db import migrations


# Маршруты, которые нужно убрать из меню
ROUTES_TO_REMOVE = [
    'ClassificationAnalysis',
    'BayesianAnalysis',
]


def remove_unused_menu_items(apps, schema_editor):
    """Удаляет пункты меню по их route_name."""
    MenuItem = apps.get_model('cms_adp', 'MenuItem')

    deleted_count, _ = MenuItem.objects.filter(
        route_name__in=ROUTES_TO_REMOVE
    ).delete()

    print(f"\n[INFO] Удалено пунктов меню: {deleted_count}")


def restore_menu_items(apps, schema_editor):
    """
    Обратная операция.
    Точное восстановление невозможно без знания исходных parent/order,
    поэтому оставляем пустой. При необходимости — допишите вручную.
    """
    pass


class Migration(migrations.Migration):
    # ⚠️ Замените на имя последней миграции cms_adp в вашем проекте
    dependencies = [
        ('rooman_alytics', '0034_autocountingmethod_commonformula_is_active_and_more'),
    ]

    operations = [
        migrations.RunPython(
            remove_unused_menu_items,
            restore_menu_items,
        ),
    ]