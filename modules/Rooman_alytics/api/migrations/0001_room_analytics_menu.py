"""
Миграция данных: итоговое меню room analytics после переноса в modules.
"""

from django.db import migrations


def add_room_analytics_menu(apps, schema_editor):
    from src.core.cms.adp.menu.migration_utils import MenuMigrationHelper

    MenuItem = apps.get_model('cms_adp', 'MenuItem')
    MenuItem.objects.filter(module_source='core/room_analytics').delete()
    MenuItem.objects.filter(module_source='modules/Rooman_alytics').delete()

    sc = MenuMigrationHelper(apps, 'modules/Rooman_alytics')

    module_menu = sc.create_group(
        'Модуль анализа помещения',
        'AnalyticsModule',
        icon='Armchair',
        order=40,
    )

    analysis_section = sc.create_group(
        'Анализ помещения',
        parent=module_menu,
        route_name='AnalyzePage',
    )
    sc.create_routes_batch([
        ('Анализ помещения', 'AnalyzePage'),
        ('Разметить план помещения', 'LoadPlan'),
        ('Пройти анкетирование', 'SurveyStart'),
    ], parent=analysis_section)

    admin_tools_section = sc.create_group(
        'Аналитические инструменты',
        parent=module_menu,
        is_admin_only=True,
        route_name='ModelEditor',
    )
    sc.create_route(
        name='Кластеризационный анализ',
        route_name='ClusteringAnalysis',
        parent=admin_tools_section,
        is_admin_only=True,
    )
    sc.create_route(
        name='Загрузка моделей',
        route_name='DataUpload',
        parent=admin_tools_section,
        is_admin_only=True,
    )
    sc.create_route(
        name='Редактировать мат. модель',
        route_name='ModelEditor',
        parent=admin_tools_section,
        is_admin_only=True,
    )


def reverse_room_analytics_menu(apps, schema_editor):
    MenuItem = apps.get_model('cms_adp', 'MenuItem')
    MenuItem.objects.filter(module_source='core/room_analytics').delete()
    MenuItem.objects.filter(module_source='modules/Rooman_alytics').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('cms_adp', '0016_alter_menuitem_item_type'),
    ]

    operations = [
        migrations.RunPython(
            add_room_analytics_menu,
            reverse_room_analytics_menu,
        ),
    ]
