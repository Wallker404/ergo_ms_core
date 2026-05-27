import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MEDIA_ROOT = BASE_DIR/ 'api/models'
DEBUG = True  # Обязательно True для dev

# 🔹 Полный вывод ошибок в консоль
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'DEBUG', 'propagate': False},
        'drf_yasg': {'handlers': ['console'], 'level': 'DEBUG', 'propagate': False},
    },
}

# 🔹 DRF: показывать полные ошибки в JSON вместо "Internal Server Error"
REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
}