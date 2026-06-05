from typing import List, Dict, Any
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from .models import *
import math
from enum import Enum

class ElementType(Enum):
    ROOM = "room"
    FURNITURE = "furniture"
    CONSTRUCT_ELEMENT = "construct_element"
    FLOORPLAN = "floorplan"


@dataclass
class SpecialMethodResult:
    """Результат вычисления специального метода"""
    parameter_name: str
    result: float
    recommendations: List[Dict[str, Any]] = field(default_factory=list)


class BaseSpecialMethod(ABC):
    """Абстрактный базовый класс для специальных методов"""
    
    @abstractmethod
    def get_name(self) -> str:
        """Возвращает название вычисляемого параметра"""
        pass
    
    @abstractmethod
    def get(self, floorplan_id: int) -> SpecialMethodResult:
        """
        Вычисляет параметр и возвращает результат с рекомендациями
        
        Args:
            floorplan_id: ID плана этажа
            
        Returns:
            SpecialMethodResult с оценкой и рекомендациями
        """
        pass


class GetAislewidth(BaseSpecialMethod):
    # Константы
    DOOR_TYPE_IDS = [2, 4]  # ID типов дверей
    BATHROOM_ROOM_TYPE_IDS = [4, 5]  # ID типов комнат (туалет, ванная)
    
    MIN_WIDTH_BATHROOM = 0.6  # Минимальная ширина для санузлов
    MIN_WIDTH_STANDARD = 0.8  # Минимальная ширина для обычных дверей
    OPTIMAL_WIDTH = 1.2  # Оптимальная ширина
    
    def get_name(self) -> str:
        return "Минимальная ширина прохода (дверных проемов)"
    
    def get(self, floorplan_id: int) -> SpecialMethodResult:
        # 1. Получаем план с дверями и комнатами
        floorplan = Floorplan.objects.prefetch_related(
            "constructelement_set",
            "room_set__room_type_id"
        ).get(id=floorplan_id)
        
        # 2. Получаем все двери
        doors = floorplan.constructelement_set.filter(
            construct_element_type_id__in=self.DOOR_TYPE_IDS
        )
        
        # 3. Получаем все комнаты
        rooms = list(floorplan.room_set.all())
        
        total_score = 0.0
        door_count = 0
        recommendations = []
        
        # Для теста: информация о пересечениях
        intersection_info = []
        
        # 4. Анализируем каждую дверь
        for door in doors:
            # Вычисляем ширину проема в метрах
            width_px = max(
                abs(door.max_x - door.min_x),
                abs(door.max_y - door.min_y)
            )
            width_meters = width_px * math.sqrt(floorplan.pixel_to_m_in_square)
            width_meters = round(width_meters, 3)
            
            # Проверяем пересечение bbox двери с комнатами
            intersecting_rooms = self._find_intersecting_rooms(door, rooms)
        
            
            # Определяем тип комнаты и требуемую ширину
            bathroom_rooms = [r for r in intersecting_rooms if r.room_type_id_id in self.BATHROOM_ROOM_TYPE_IDS]
            
            if bathroom_rooms:
                min_required = self.MIN_WIDTH_BATHROOM
                room_type_name = "санузла (ванной или туалета)"
            else:
                min_required = self.MIN_WIDTH_STANDARD
                room_type_name = "комнаты"
            
            # Вычисляем балл
            score = self._calculate_score(width_meters, min_required)
            
            total_score += score
            door_count += 1
            
            # 🔹 ДОБАВЛЕНО: добавляем ВСЕ двери в рекомендации (для теста)
            if width_meters < min_required:
                recommendations.append({
                    "element_type": ElementType.CONSTRUCT_ELEMENT.value, 
                    "element_id": door.id,
                    "recommendation": (
                        f"Ширина проема {width_meters}м не соответствует требованию "
                        f">= {min_required}м для {room_type_name}"
                    )
                })
        
        # 5. Вычисляем среднюю оценку
        if door_count > 0:
            final_score = round(total_score / door_count, 2)
        else:
            final_score = 0.0
        
        return SpecialMethodResult(
            parameter_name=self.get_name(),
            result=final_score,
            recommendations=recommendations,
        )
    
    def _find_intersecting_rooms(self, door, rooms: List[Room]) -> List[Room]:
        intersecting = []
        
        for room in rooms:
            if (door.min_x < room.max_x and door.max_x > room.min_x and
                door.min_y < room.max_y and door.max_y > room.min_y):
                intersecting.append(room)
        
        return intersecting
    
    def _calculate_score(self, width: float, min_required: float) -> float:
        if width < min_required:
            return 0.0
        elif width >= self.OPTIMAL_WIDTH:
            return 10.0
        else:
            # Линейная интерполяция от 5 до 10 между минимумом и оптимумом
            # score = 5 + (width - min) / (optimal - min) * 5
            score = 5.0 + (width - min_required) / (self.OPTIMAL_WIDTH - min_required) * 5.0
            return round(score, 2)


class GetFreeSpacePercentage(BaseSpecialMethod):
    """
    Анализирует долю свободного пространства в комнате.
    Вычисляет процент незанятой площади мебелью.
    При подсчёте площади мебели исключается та, которая стоит на другой мебели
    (например, телевизор на столе не учитывается).
    
    Нормы свободного пространства зависят от типа комнаты:
    - Туалеты, ванные, гардеробные: 40%
    - Остальные комнаты: 50%
    """
    
    # Нормы свободного пространства по типам комнат
    MIN_FREE_SPACE_PERCENT_DEFAULT = 50.0
    MIN_FREE_SPACE_PERCENT_COMPACT = 40.0
    
    # ID типов комнат с компактной нормой (туалеты, ванные, гардеробные)
    COMPACT_ROOM_TYPE_IDS = [4, 5, 9]  # Toilet, Bathroom, dressing_room
    
    def get_name(self) -> str:
        return "Доля свободного пространства в комнате"
    
    def _get_min_free_percent(self, room_type_id: int) -> float:
        """Возвращает минимальный процент свободного пространства для типа комнаты"""
        if room_type_id in self.COMPACT_ROOM_TYPE_IDS:
            return self.MIN_FREE_SPACE_PERCENT_COMPACT
        return self.MIN_FREE_SPACE_PERCENT_DEFAULT
    
    def _get_base_furniture(self, furniture_list):
        """
        Возвращает список "базовой" мебели — той, которая не стоит на другой мебели.
        
        Мебель A считается стоящей на мебели B, если:
        - Центр A находится внутри bbox B
        - Площадь B >= площади A (B — это "база", A — то, что на ней стоит)
        """
        base_furniture = []
        
        for furn in furniture_list:
            # Центр текущей мебели
            cx = (furn.min_x + furn.max_x) / 2
            cy = (furn.min_y + furn.max_y) / 2
            furn_area = (furn.max_x - furn.min_x) * (furn.max_y - furn.min_y)
            
            is_on_other = False
            for other in furniture_list:
                if other.id == furn.id:
                    continue
                
                other_area = (other.max_x - other.min_x) * (other.max_y - other.min_y)
                
                # Центр furn внутри bbox other И other не меньше по площади
                if (other.min_x <= cx <= other.max_x and
                    other.min_y <= cy <= other.max_y and
                    other_area >= furn_area):
                    is_on_other = True
                    break
            
            if not is_on_other:
                base_furniture.append(furn)
        
        return base_furniture
    
    def get(self, floorplan_id: int) -> SpecialMethodResult:
        # Получаем план с комнатами и мебелью
        floorplan = Floorplan.objects.prefetch_related(
            "room_set__furniture_set__furniture_type_id",
            "room_set__room_type_id"
        ).get(id=floorplan_id)
        
        rooms = floorplan.room_set.all()
        
        recommendations = []
        total_score = 0.0
        room_count = 0
        
        for room in rooms:
            # Определяем норму свободного пространства для типа комнаты
            room_type_id = room.room_type_id_id if room.room_type_id else None
            min_free_percent = self._get_min_free_percent(room_type_id)
            room_type_name = room.room_type_id.type_name if room.room_type_id else "комната"
            
            # Вычисляем площадь комнаты
            room_width = abs(room.max_x - room.min_x)
            room_height = abs(room.max_y - room.min_y)
            room_area_px = room_width * room_height
            
            # Получаем всю мебель в комнате
            all_furniture = list(room.furniture_set.all())
            
            # Фильтруем: оставляем только "базовую" мебель
            base_furniture = self._get_base_furniture(all_furniture)
            
            # Вычисляем общую площадь базовой мебели
            furniture_area_px = 0.0
            for furniture in base_furniture:
                furn_width = abs(furniture.max_x - furniture.min_x)
                furn_height = abs(furniture.max_y - furniture.min_y)
                furniture_area_px += furn_width * furn_height
            
            # Вычисляем процент занятой площади
            if room_area_px > 0:
                occupied_percent = (furniture_area_px / room_area_px) * 100
                free_percent = 100 - occupied_percent
            else:
                free_percent = 100.0
            
            free_percent = round(free_percent, 2)
            
            # Вычисляем балл (0-10) с учётом нормы для типа комнаты
            if free_percent >= min_free_percent:
                score = 10.0
            elif free_percent >= min_free_percent / 2:
                # Линейная интерполяция от 5 до 10
                score = 5.0 + (free_percent - min_free_percent / 2) / (min_free_percent / 2) * 5.0
            else:
                score = 0.0
            
            score = round(score, 2)
            total_score += score
            room_count += 1
            
            # Формируем рекомендацию
            if free_percent < min_free_percent:
                recommendations.append({
                    "element_type": ElementType.ROOM.value, 
                    "element_id": room.id,
                    "passed": False,
                    "recommendation": (
                        f"❌ В комнате слишком много мебели (только {free_percent}% свободно). "
                        f"Тип: {room_type_name}. Норма свободного пространства для данного типа — {min_free_percent}%. "
                        f"Рекомендуется провести перепланировку или заменить мебель на мебель-трансформер."
                    )
                })
        
        # Вычисляем среднюю оценку
        if room_count > 0:
            final_score = round(total_score / room_count, 2)
        else:
            final_score = 0.0
        
        return SpecialMethodResult(
            parameter_name=self.get_name(),
            result=final_score,
            recommendations=recommendations
        )


class CheckRequiredFurniture(BaseSpecialMethod):
    """
    Определяет наличие необходимой мебели для каждого типа комнат.
    Проверяет все комнаты на плане и возвращает рекомендации о недостающей мебели.
    
    Формат REQUIRED_FURNITURE:
    - Число: обязательный предмет (логическое И)
    - Список чисел: один из предметов (логическое ИЛИ)
    
    Пример:
    - [3, [4, 5]] означает: нужен предмет 3 И (предмет 4 ИЛИ предмет 5)
    - [[19, 18], 11, 5] означает: (плита ИЛИ раковина) И холодильник И столешница
    """
    
    # Словарь необходимой мебели для каждого типа комнаты
    # Ключ: ID типа комнаты, Значение: список требований
    REQUIRED_FURNITURE = {
        1: [19, 18, 11, [4,5]],
        2: [7, 17],
        3: [[2,21], [3,4,12], 20],
        4: [22],
        5: [23, 24],
        9: [20],
    }
    
    # Названия типов мебели для рекомендаций
    FURNITURE_NAMES = {
        1: "Стул", 2: "Кровать", 3: "Тумбочка", 4: "Стол", 5: "Столешница",
        6: "Кресло", 7: "Диван", 8: "Телевизор", 9: "Лампа", 10: "Стиральная машина",
        11: "Холодильник", 12: "Рабочий стол", 13: "Книжная полка", 14: "Тренажер",
        15: "Растения", 16: "Книжный шкаф", 17: "Журнальный столик", 18: "Кухонная раковина",
        19: "Газовая плита", 20: "Шкаф для одежды", 21: "Двуспальная кровать",
        22: "Туалет", 23: "Ванна", 24: "Раковина в ванной"
    }
    
    def get_name(self) -> str:
        return "Наличие необходимой мебели для типа комнаты"
    
    def _get_furniture_name(self, fid: int) -> str:
        """Возвращает название мебели по ID"""
        return self.FURNITURE_NAMES.get(fid, f"ID:{fid}")
    
    def _check_requirement(self, requirement, present_furniture_ids: set) -> tuple:
        """
        Проверяет одно требование.
        
        Args:
            requirement: число (обязательный предмет) или список (один из предметов)
            present_furniture_ids: множество ID мебели, присутствующей в комнате
            
        Returns:
            (is_satisfied: bool, missing_description: str)
        """
        if isinstance(requirement, list):
            # Логическое ИЛИ: достаточно одного из элементов
            for fid in requirement:
                if fid in present_furniture_ids:
                    return True, ""
            
            # Ни один не найден
            names = [self._get_furniture_name(fid) for fid in requirement]
            description = f"один из: {', '.join(names)}"
            return False, description
        else:
            # Логическое И: предмет обязателен
            if requirement in present_furniture_ids:
                return True, ""
            
            name = self._get_furniture_name(requirement)
            return False, name
    
    def get(self, floorplan_id: int) -> SpecialMethodResult:
        # Получаем план с комнатами и мебелью
        floorplan = Floorplan.objects.prefetch_related(
            "room_set__furniture_set__furniture_type_id",
            "room_set__room_type_id"
        ).get(id=floorplan_id)
        
        recommendations = []
        total_score = 0.0
        room_count = 0
        
        for room in floorplan.room_set.all():
            room_type_id = room.room_type_id_id
            
            # Получаем список требований для этого типа комнаты
            requirements = self.REQUIRED_FURNITURE.get(room_type_id, [])
            
            if not requirements:
                # Для этого типа комнаты нет требований
                continue
            
            # Получаем ID мебели, которая есть в комнате
            present_furniture_ids = set(
                room.furniture_set.values_list('furniture_type_id_id', flat=True)
            )
            
            # Проверяем каждое требование
            satisfied_count = 0
            missing_descriptions = []
            
            for requirement in requirements:
                is_satisfied, missing_desc = self._check_requirement(
                    requirement, present_furniture_ids
                )
                
                if is_satisfied:
                    satisfied_count += 1
                else:
                    missing_descriptions.append(missing_desc)
            
            # Вычисляем балл
            total_requirements = len(requirements)
            if satisfied_count == total_requirements:
                score = 10.0
            else:
                # Процент выполненности требований
                fulfillment_percent = (satisfied_count / total_requirements) * 100
                score = round(fulfillment_percent / 10, 1)  # От 0 до 10
            
            total_score += score
            room_count += 1
            
            # Формируем рекомендацию
            if missing_descriptions:
                missing_list = ", ".join(missing_descriptions)
                
                recommendations.append({
                    "element_type": ElementType.ROOM.value, 
                    "element_id": room.id,
                    "passed": False,
                    "recommendation": (
                        f"❌ В комнате отсутствует необходимая мебель: {missing_list}. "
                        f"Рекомендуется добавить для полноценного использования помещения."
                    )
                })

        # Вычисляем среднюю оценку
        if room_count > 0:
            final_score = round(total_score / room_count, 2)
        else:
            final_score = 0.0
        
        return SpecialMethodResult(
            parameter_name=self.get_name(),
            result=final_score,
            recommendations=recommendations
        )