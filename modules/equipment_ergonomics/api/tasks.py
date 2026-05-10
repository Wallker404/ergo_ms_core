"""
Celery autodiscovery entrypoint for equipment_ergonomics.
Celery ищет модуль `tasks` внутри INSTALLED_APPS.
"""

from .tasks.analytics import run_classification_analysis  # noqa: F401
from .tasks.csv_import import import_dataset_csv_task  # noqa: F401

