from email.policy import default
from pyexpat import model
from random import choices
from tkinter import CASCADE
from django.db import models
from django.core.validators import FileExtensionValidator 

class ModelCategory(models.TextChoices):
    DETECTION = 'detection', 'Детекция комнат и стен'
    CLASSIFICATION = 'classification', 'Классификация комнат'
    FURNITURE = 'furniture', 'Детекция и классификация мебели'

class QuestionType(models.TextChoices):
    for_every_room = 'for_every_room', 'Для каждой комнаты'
    for_floorplan = 'for_floorplan', 'Для каждого помещения'
    for_selected_rooms ='for_selected_rooms','для выбранных комнат'
    for_unselected_rooms ='for_unselected_rooms','для невыбранных комнат'


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


class RoomAnalyticsPluginState(models.Model):
    plugin_key = models.SlugField('Ключ плагина', max_length=64, unique=True, default='rooman_alytics')
    is_enabled = models.BooleanField('Включен', default=False)
    disabled_at = models.DateTimeField('Дата выключения', null=True, blank=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Состояние плагина room analytics'
        verbose_name_plural = 'Состояние плагина room analytics'

    def __str__(self):
        return f'{self.plugin_key}: {"enabled" if self.is_enabled else "disabled"}'

class Criterion_of_ergonomy(models.Model):
    name = models.CharField(max_length=255  )
    date_of_creation = models.DateTimeField('Дата создания', auto_now=True)
    is_active = models.BooleanField('Активен', default=False)
    weight = models.FloatField('Вес', default=0)
    color = models.CharField("Цвет", max_length=7,default="#0d6efd")
    terrible_mark_border = models.FloatField(default=3)
    bad_mark_border = models.FloatField(default=5)
    normal_mark_border = models.FloatField(default=7)
    good_mark_border = models.FloatField(default=9)

class Form_question(models.Model):
    criterion_id= models.ForeignKey(Criterion_of_ergonomy, on_delete=models.CASCADE)
    question = models.TextField()
    recommendation = models.TextField(default='')
    score_for_recommendation = models.FloatField(default=6)
    is_active = models.BooleanField('Активен', default=False)
    type = models.CharField(
        max_length=50,
        choices=QuestionType.choices,
        db_index=True,
        help_text="Категория модели"
    )
class RoomType(models.Model):
    type_name= models.CharField(max_length = 50)
    label = models.CharField(max_length = 50, default='')
    color = models.CharField("Цвет", max_length=7,default="#0d6efd")

class FormAnswer(models.Model):
    question_id = models.ForeignKey(Form_question, on_delete= models.CASCADE)
    answer = models.TextField()
    score = models.FloatField(default = 5)
    
class Form_Question_RoomType(models.Model):
    qusion_id = models.ForeignKey(Form_question, on_delete= models.CASCADE)
    room_type_id = models.ForeignKey(RoomType, on_delete= models.CASCADE)
    class Meta:
        unique_together = ['qusion_id', 'room_type_id']

class FurnitureType(models.Model):
    type_name= models.CharField(max_length = 50)
    color = models.CharField("Цвет", max_length=7,default="#0d6efd")
    label = models.CharField(max_length = 50, default='')


class ConstructElementType(models.Model):
    type_name= models.CharField(max_length = 50)
    color = models.CharField("Цвет", max_length=7,default="#0d6efd")
    label = models.CharField(max_length = 50, default='')

class Floorplan(models.Model):
    img = models.FileField(
        upload_to= "floorplans" ,
        validators=[FileExtensionValidator(allowed_extensions=['.png','jpg'])],
        help_text="план изображений"
    )
    width = models.FloatField(default=0)
    height = models.FloatField(default=0)
    upload_at = models.DateTimeField('Загружен', auto_now=True)
    pixel_to_m_in_square = models.FloatField(default=0)
    square_of_habitation = models.FloatField(default=0)

class Room(models.Model):
    min_x =models.FloatField(default=0)
    max_x = models.FloatField(default=0)
    min_y =models.FloatField(default=0)
    max_y = models.FloatField(default=0)
    square = models.FloatField(default=0)
    floorplan_id = models.ForeignKey(Floorplan, on_delete=models.CASCADE)
    room_type_id = models.ForeignKey(RoomType, on_delete=models.CASCADE)

class ConstructElement(models.Model):
    min_x =models.FloatField(default=0)
    max_x = models.FloatField(default=0)
    min_y =models.FloatField(default=0)
    max_y = models.FloatField(default=0)
    floorplan_id = models.ForeignKey(Floorplan, on_delete=models.CASCADE)
    construct_element_type_id = models.ForeignKey(ConstructElementType, on_delete=models.CASCADE)

class Furniture(models.Model):
    min_x =models.FloatField(default=0)
    max_x = models.FloatField(default=0)
    min_y =models.FloatField(default=0)
    max_y = models.FloatField(default=0)
    furniture_type_id = models.ForeignKey(FurnitureType, on_delete=models.CASCADE)
    room_id = models.ForeignKey(Room, on_delete=models.CASCADE)


class FormulaParam(models.Model):
    name = models.CharField(max_length=255)
    label = models.CharField(max_length=255, blank=True, null=True)
    cryteria_id = models.ForeignKey(Criterion_of_ergonomy, on_delete=models.CASCADE,   null=True,)

class SpecialMethods(models.Model):
    """Специальные методы"""
    INPUT_TYPE_CHOICES = [
        ('nothing', 'Nothing'),
        ('rooms', 'Rooms'),
        ('furniture', 'Furniture'),
        ('roomsfurniture', 'Rooms Furniture'),
    ]
    name = models.CharField(max_length=255)
    inputType = models.CharField(
        max_length=50,
        choices=INPUT_TYPE_CHOICES,
        default='nothing'
    )

class LimitParam(models.Model):
    formula_param = models.ForeignKey(
        FormulaParam,
        on_delete=models.CASCADE,
        db_column='FormulaParamId'
    )

class UniversalLimitParam(models.Model):
    """Универсальные параметры ограничений"""
    limit_param = models.ForeignKey(
        LimitParam,
        on_delete=models.CASCADE,
        db_column='LimitParamId'
    )
    value = models.FloatField()

class RoomsLimitParam(models.Model):
    limit_param = models.ForeignKey(
        LimitParam,
        on_delete=models.CASCADE,
    )
    room_type = models.ForeignKey(
        RoomType,
        on_delete=models.CASCADE,
    )
    value = models.FloatField()

class AutoCountingParam(models.Model):
    """Параметры автоматического подсчета"""
    formula_param = models.ForeignKey(
        FormulaParam,
        on_delete=models.CASCADE,
    )
    special_methods = models.ForeignKey(
        SpecialMethods,
        on_delete=models.CASCADE
    )


class ACPUsings(models.Model):
    """Использование автоматического подсчета"""
    acp = models.ForeignKey(
        AutoCountingParam,
        on_delete=models.CASCADE,
    )
    room_type = models.ForeignKey(
        RoomType,
        on_delete=models.CASCADE,
        null=True
    )
    furniture_type = models.ForeignKey(
        FurnitureType,
        on_delete=models.CASCADE,
        null=True
    )

class UserInputParam(models.Model):
    TYPE_CHOICES = [
    ('global', 'Global'),
    ('rooms', 'Rooms'),
    ]
    formula_param = models.ForeignKey(
        FormulaParam,
        on_delete=models.CASCADE,
    )
    min_value = models.FloatField(blank=True, null=True)
    max_value = models.FloatField(blank=True, null=True)
    type = models.CharField(max_length=50,
        choices=TYPE_CHOICES,
        default='global')

class UserInputParamRoomType(models.Model):
    user_input_param = models.ForeignKey(
        UserInputParam,
        on_delete=models.CASCADE,
    )
    room_type = models.ForeignKey(
        RoomType,
        on_delete=models.CASCADE,
    )

class Formula(models.Model):
    equation = models.TextField(default ='')
    
class SystemEquastion(models.Model):
    """Системные уравнения"""
    TYPE_CHOICES =  [
    ('house', 'House'),
    ('rooms', 'Rooms'),
    ]
    type = models.CharField(max_length = 50, choices = TYPE_CHOICES, default='house')
    criterion = models.ForeignKey(Criterion_of_ergonomy, on_delete=models.CASCADE, null=True)
    
    
class SystemEquastionUserInputParam(models.Model):
    sys_equ = models.ForeignKey(SystemEquastion, on_delete=models.CASCADE)
    useR_input_param = models.ForeignKey(UserInputParam, on_delete=models.CASCADE)

class SystemEquastionUserACP(models.Model):
    sys_equ = models.ForeignKey(SystemEquastion, on_delete=models.CASCADE)
    acp = models.ForeignKey(AutoCountingParam, on_delete=models.CASCADE)

class EquastionOfSystemEquastion(models.Model):
    """Универсальные системные уравнения"""
    system_equastion = models.ForeignKey(
        SystemEquastion,
        on_delete=models.CASCADE,
    )
    formula = models.ForeignKey(
        Formula,
        on_delete=models.CASCADE,
    )
    limit_equastion = models.TextField()
    recommendation = models.TextField(blank=True)

class SystemEquastionUniversalLimitParam(models.Model):
    universal_limit_param = models.ForeignKey(
        UniversalLimitParam,
        on_delete=models.CASCADE,
    )
    sys_equastion = models.ForeignKey(
        SystemEquastion,
        on_delete=models.CASCADE,
    )

class SystemEquastionRoomsLimitParam(models.Model):
    rooms_limit_param = models.ForeignKey(
        RoomsLimitParam,
        on_delete=models.CASCADE,
        null=True
    )
    system_equastion = models.ForeignKey(
        SystemEquastion,
        on_delete=models.CASCADE,
    )

class SysEquastRoomType(models.Model):
    """Связь системных уравнений с типами комнат"""
    system_equastion = models.ForeignKey(
        SystemEquastion,
        on_delete=models.CASCADE,
    )
    room_type = models.ForeignKey(
        RoomType,
        on_delete=models.CASCADE,
    )

class CommonFormula(models.Model):
    """Общие формулы"""
    TYPE_CHOICES = [
    ('global', 'Global'),
    ('rooms', 'Rooms'),
    ]
    formula = models.ForeignKey(
        Formula,
        on_delete=models.CASCADE,
    )
    type = models.CharField(max_length=50,
        choices=TYPE_CHOICES,
        default='global')
    criterion = models.ForeignKey(Criterion_of_ergonomy, on_delete=models.CASCADE, null=True)
    recommendation = models.TextField(blank=True)
    value_recomm = models.FloatField(blank=True)

class CommonFormulaRoomTypes(models.Model):
    commonformula = models.ForeignKey(CommonFormula, on_delete=models.CASCADE)
    roomtype = models.ForeignKey(RoomType, on_delete=models.CASCADE)


class CommonFormulaAcp(models.Model):
    """Связь формул с автоподсчетом"""
    acp = models.ForeignKey(
        AutoCountingParam,
        on_delete=models.CASCADE,
    )
    commonformula = models.ForeignKey(CommonFormula, on_delete=models.CASCADE)

class CommonFormulaInputParam(models.Model):
    """Связь формул с параметрами пользовательского ввода"""
    
    user_input_param = models.ForeignKey(
        UserInputParam,
        on_delete=models.CASCADE,
    )
    commonformula = models.ForeignKey(CommonFormula, on_delete=models.CASCADE)