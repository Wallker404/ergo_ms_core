from django.apps import AppConfig


class EquipmentErgonomicsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.equipment_ergonomics.api'
    label = 'equipment_ergonomics'
    verbose_name = 'Эргономика техники'

    def ready(self):
        pass
