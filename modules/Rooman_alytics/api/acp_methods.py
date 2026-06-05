from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Any
from .models import *
import math
@dataclass
class VoidMethodResult:
    result: float                     
    rooms: List[Any]                 
    furnitures: List[Any]            
    construct_elements: List[Any]   

@dataclass
class RoomsMethodResult:
    result: float                     
    rooms: List[Any]                 
@dataclass
class FurnituresMethodResult:
    result: float                     
    furnitures: List[Any]        

@dataclass
class RoomsFurnituresMethodResult:
    result: float                     
    rooms: List[Any]    
    furnitures: List[Any] 

class BaseVoidMethod(ABC):
    @abstractmethod
    def get(self, floorplan_id)-> VoidMethodResult:
        pass

class BaseFurnitureMethod(ABC):
    @abstractmethod
    def get(self, floorplan_id, furniture_type_id)->FurnituresMethodResult:
            pass

class BaseRoomMethod(ABC):
    @abstractmethod
    def get(self, floorplan_id, room_type_id) ->RoomsMethodResult:
            pass


class BaseRoomFurnitureMethod(ABC):
    @abstractmethod
    def get(self, floorplan_id,  room_type_id, furniture_type_id) ->RoomsFurnituresMethodResult:
            pass


class GetFurnitureCount(BaseFurnitureMethod):
    """
    Возвращает количество мебели определённого типа на плане.
    inputType: furniture
    """
    def get(self, floorplan_id: int, furniture_type_id: int) -> FurnituresMethodResult:
        # Получаем все комнаты плана
        rooms = Room.objects.filter(floorplan_id=floorplan_id)
        room_ids = list(rooms.values_list('id', flat=True))
        
        # Считаем мебель заданного типа во всех комнатах плана
        furniture_qs = Furniture.objects.filter(
            room_id__in=room_ids,
            furniture_type_id=furniture_type_id
        )
        
        count = furniture_qs.count()
        furniture_ids = list(furniture_qs.values_list('id', flat=True))
        
        return FurnituresMethodResult(
            result=float(count),
            furnitures=furniture_ids
        )


class GetRoomCount(BaseRoomMethod):
    """
    Возвращает количество комнат определённого типа на плане.
    inputType: rooms
    """
    def get(self, floorplan_id: int, room_type_id: int) -> RoomsMethodResult:
        rooms_qs = Room.objects.filter(
            floorplan_id=floorplan_id,
            room_type_id=room_type_id
        )
        
        count = rooms_qs.count()
        room_ids = list(rooms_qs.values_list('id', flat=True))
        
        return RoomsMethodResult(
            result=float(count),
            rooms=room_ids
        )


class GetCountOfFurnitureInRoom(BaseRoomFurnitureMethod):
    """
    Возвращает количество мебели определённого типа в комнатах определённого типа на плане.
    inputType: roomsfurniture
    """
    def get(self, floorplan_id: int, room_type_id: int, furniture_type_id: int) -> RoomsFurnituresMethodResult:
        # Находим комнаты заданного типа на плане
        rooms_qs = Room.objects.filter(
            floorplan_id=floorplan_id,
            room_type_id=room_type_id
        )
        room_ids = list(rooms_qs.values_list('id', flat=True))
        
        # Считаем мебель заданного типа в этих комнатах
        furniture_qs = Furniture.objects.filter(
            room_id__in=room_ids,
            furniture_type_id=furniture_type_id
        )
        
        count = furniture_qs.count()
        furniture_ids = list(furniture_qs.values_list('id', flat=True))
        
        return RoomsFurnituresMethodResult(
            result=float(count),
            rooms=room_ids,
            furnitures=furniture_ids
        )