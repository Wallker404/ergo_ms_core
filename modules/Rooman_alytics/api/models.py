from django.db import models
from django.core.validators import FileExtensionValidator 
from pathlib import Path
class ModelCategory(models.TextChoices):
    DETECTION = 'detection', 'Детекция комнат и стен'
    CLASSIFICATION = 'classification', 'Классификация комнат'
    FURNITURE = 'furniture', 'Детекция и классификация мебели'

class OnnxModel(models.Model):
    name = models.CharField(max_length=255, help_text="Имя файла модели")
    category = models.CharField(
        max_length=50,
        choices=ModelCategory.choices,
        db_index=True,
        help_text="Категория модели"
    )
    
    # Файлы
    onnx_file = models.FileField(
        upload_to= "rooman_alytics/models" ,
        validators=[FileExtensionValidator(allowed_extensions=['onnx'])],
        help_text="ONNX файл модели"
    )
    # Метаданные
    classes = models.JSONField(
        default=list,
        help_text="Список обнаруживаемых классов: ['sofa', 'table', ...]"
    )
    install_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(
        default=False, # type: ignore[reportArgumentType]
        db_index=True,
        help_text="Используется ли модель на сервере прямо сейчас"
    )
    
    class Meta:
        ordering = ['-install_date']
        indexes = [
            models.Index(fields=['category', 'is_active']),
        ]
        constraints = [
            # Гарантируем, что имя уникально в рамках категории
            models.UniqueConstraint(
                fields=['name', 'category'],
                name='unique_name_per_category'
            )
        ]
    
    def __str__(self):
        return f"{self.name}"