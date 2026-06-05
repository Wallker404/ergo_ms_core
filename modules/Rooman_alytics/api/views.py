from django.http import response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from django.db import connection
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from sklearn.cluster import KMeans, DBSCAN
from sklearn.metrics import silhouette_score
import json
import numpy as np
import pandas as pd
from src.core.utils.base.base_views import BaseAPIView, BaseAPIViewAuthMixin
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .models import *
import os
import json
from django.db.models import Count, Q 
import math
import uuid
import base64
from drf_yasg import openapi
from . import acp_methods, special_methods
import dataclasses
import math
from simpleeval import simple_eval
CLUSTER_COLORS = [
    'rgb(54, 162, 235)',   # blue
    'rgb(255, 99, 132)',   # red
    'rgb(75, 192, 192)',   # teal
    'rgb(255, 206, 86)',   # yellow
    'rgb(153, 102, 255)',  # purple
    'rgb(255, 159, 64)',   # orange
    'rgb(199, 199, 199)',  # gray
    'rgb(83, 102, 255)',   # indigo
    'rgb(0, 188, 149)',    # green
    'rgb(244, 67, 54)',    # red-dark
]


def _load_numeric_data(file_obj):
    """Читает CSV/JSON, возвращает numpy array + список имён признаков."""
    if file_obj.name.lower().endswith('.csv'):
        df = pd.read_csv(file_obj)
    elif file_obj.name.lower().endswith('.json'):
        df = pd.read_json(file_obj)
    else:
        raise ValueError("Поддерживаются только .csv и .json")

    df_num = df.select_dtypes(include=[np.number, np.bool_]).dropna()

    # 🔹 Удаляем колонки-артефакты индекса (Unnamed: 0, 0, index и т.п.)
    mask_unnamed = ~df_num.columns.astype(str).str.lower().str.contains(r'^(unnamed|index)', na=False)
    mask_digits  = ~df_num.columns.astype(str).str.match(r'^\d+$', na=False)
    df_num = df_num.loc[:, mask_unnamed & mask_digits]

    if df_num.shape[1] < 2:
        raise ValueError("Необходимо минимум 2 валидных числовых признака")

    features = list(df_num.columns)
    return df_num.values, features

class ElbowAPIView(BaseAPIView):
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_summary="Метод локтя (расчёт Inertia)",
        manual_parameters=[
            openapi.Parameter('file', openapi.IN_FORM, type=openapi.TYPE_FILE, required=True),
            openapi.Parameter('k_start', openapi.IN_FORM, type=openapi.TYPE_INTEGER, default=2),
            openapi.Parameter('k_end', openapi.IN_FORM, type=openapi.TYPE_INTEGER, default=10),
        ],
        responses={200: "Успех", 400: "Ошибка"}
    )
    def post(self, request):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "Файл не загружен"}, status=400)

        try:
            X, _ = _load_numeric_data(file_obj)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)

        k_start = int(request.data.get('k_start', 2))
        k_end = int(request.data.get('k_end', 10))
        if k_start < 2 or k_end <= k_start:
            return Response({"error": "k_start должен быть >= 2, k_end > k_start"}, status=400)

        inertias = []
        # 🔹 ИСПРАВЛЕНО: диапазон должен быть [k_start, k_end] включительно
        for k in range(k_start, k_end + 1):
            km = KMeans(n_clusters=k, random_state=42)
            km.fit(X)  # 🔹 Данные не масштабируются, как ты и просил
            inertias.append(km.inertia_)

        return Response({
            "status": "success",
            "type": "elbow",
            "k_values": list(range(k_start, k_end + 1)),  # 🔹 Теперь совпадает с расчётом
            "inertia": inertias
        })

class SilhouetteAPIView(BaseAPIView):
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_summary="Метод силуэта (Silhouette Score)",
        manual_parameters=[
            openapi.Parameter('file', openapi.IN_FORM, type=openapi.TYPE_FILE, required=True),
            openapi.Parameter('k_start', openapi.IN_FORM, type=openapi.TYPE_INTEGER, default=2),
            openapi.Parameter('k_end', openapi.IN_FORM, type=openapi.TYPE_INTEGER, default=10),
        ],
        responses={200: "Успех", 400: "Ошибка"}
    )
    def post(self, request):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "Файл не загружен"}, status=400)

        try:
            X, _ = _load_numeric_data(file_obj)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)

        k_start = int(request.data.get('k_start', 2))
        k_end = int(request.data.get('k_end', 10))
        if k_start < 2 or k_end <= k_start:
            return Response({"error": "k_start должен быть >= 2, k_end > k_start"}, status=400)

        silhouettes = []
        for k in range(k_start, k_end + 1):
            km = KMeans(n_clusters=k, random_state=42)
            labels = km.fit_predict(X)
            silhouettes.append(float(silhouette_score(X, labels)))

        return Response({
            "status": "success",
            "type": "silhouette",
            "k_values": list(range(k_start, k_end + 1)),
            "silhouette": silhouettes
        })

def _prepare_chart_data(X, labels, features, x_idx, y_idx, algorithm):
    """Подготовка данных для Chart.js scatter plot"""
    datasets = []
    
    if algorithm == 'kmeans':
        # K-Means: все кластеры известные (0, 1, 2, ...)
        unique_labels = sorted(set(labels))
        for cluster_id in unique_labels:
            mask = labels == cluster_id
            points = X[mask]
            datasets.append({
                'label': f'Кластер {cluster_id}',
                'data': [{'x': float(p[x_idx]), 'y': float(p[y_idx])} for p in points],
                'backgroundColor': CLUSTER_COLORS[cluster_id % len(CLUSTER_COLORS)] + '0.6)',
                'borderColor': CLUSTER_COLORS[cluster_id % len(CLUSTER_COLORS)],
                'pointRadius': 5,
                'pointHoverRadius': 7,
                'showLine': False
            })
    
    elif algorithm == 'dbscan':
        # DBSCAN: разделяем шум (-1) и кластеры
        # Сначала кластеры
        cluster_ids = sorted([l for l in set(labels) if l >= 0])
        for cluster_id in cluster_ids:
            mask = labels == cluster_id
            points = X[mask]
            datasets.append({
                'label': f'Кластер {cluster_id}',
                'data': [{'x': float(p[x_idx]), 'y': float(p[y_idx])} for p in points],
                'backgroundColor': CLUSTER_COLORS[cluster_id % len(CLUSTER_COLORS)] + '0.6)',
                'borderColor': CLUSTER_COLORS[cluster_id % len(CLUSTER_COLORS)],
                'pointRadius': 5,
                'pointHoverRadius': 7,
                'showLine': False
            })
        
        # Затем шум (серым цветом)
        if -1 in labels:
            mask = labels == -1
            points = X[mask]
            datasets.append({
                'label': 'Шум',
                'data': [{'x': float(p[x_idx]), 'y': float(p[y_idx])} for p in points],
                'backgroundColor': 'rgba(128, 128, 128, 0.4)',
                'borderColor': 'rgba(128, 128, 128, 1)',
                'pointRadius': 4,
                'pointHoverRadius': 6,
                'showLine': False
            })
    
    return {
        'datasets': datasets,
        'xAxi   sLabel': features[x_idx],
        'yAxisLabel': features[y_idx]
    }

def _compute_cluster_stats(X, labels, features):    
    stats = {}
    unique_labels = sorted(set(labels))
    
    for cluster_id in unique_labels:
        mask = labels == cluster_id
        cluster_data = X[mask]
        
        if len(cluster_data) == 0:
            continue
            
        cluster_stats = {}
        for i, feat_name in enumerate(features):
            values = cluster_data[:, i]
            cluster_stats[feat_name] = {
                'mean': float(np.mean(values)),
                'min': float(np.min(values)),
                'max': float(np.max(values)),
                'count': int(len(values))
            }
        
        label_key = 'noise' if cluster_id == -1 else f'cluster_{cluster_id}'
        stats[label_key] = {
            'size': int(len(cluster_data)),
            'features': cluster_stats
        }
    
    return stats


class KMeansAPIView(BaseAPIView):
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_summary="Кластеризация K-Means",
        manual_parameters=[
            openapi.Parameter('file', openapi.IN_FORM, type=openapi.TYPE_FILE, required=True),
            openapi.Parameter('k', openapi.IN_FORM, type=openapi.TYPE_INTEGER, required=True, minimum=2),
            openapi.Parameter('x_axis', openapi.IN_FORM, type=openapi.TYPE_INTEGER, description="Индекс признака для оси X (0-based)", required=False),
            openapi.Parameter('y_axis', openapi.IN_FORM, type=openapi.TYPE_INTEGER, description="Индекс признака для оси Y (0-based)", required=False),
        ],
        responses={200: "Успех", 400: "Ошибка"}
    )
    def post(self, request):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "Файл не загружен"}, status=400)

        try:
            X, features = _load_numeric_data(file_obj)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)

        try:
            k = int(request.data.get('k'))
            if k < 2: 
                raise ValueError("k должно быть >= 2")
        except Exception as e:
            return Response({"error": f"Параметр k обязателен и должен быть >= 2. Ошибка: {e}"}, status=400)

        x_idx = int(request.data.get('x_axis', 0))
        y_idx = int(request.data.get('y_axis', 1))
        if x_idx < 0 or x_idx >= len(features) or y_idx < 0 or y_idx >= len(features):
            return Response({"error": f"Неверные индексы осей. Доступно признаков: {len(features)}"}, status=400)

        model = KMeans(n_clusters=k, random_state=42)
        labels = model.fit_predict(X)
        chart_data = _prepare_chart_data(X, labels, features, x_idx, y_idx, 'kmeans')
        clusted_data = _compute_cluster_stats(X,labels,features)
        return Response({
            "status": "success",
            "algorithm": "kmeans",
            "n_clusters": k,
            "features": features,
            "chart_data": chart_data,  # 🔹 Данные для Chart.js
            "plot_info": {
                "x_axis": features[x_idx],
                "y_axis": features[y_idx]
            },
            "cluster_stats": clusted_data,
        })

class DBSCANAPIView(BaseAPIView):
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_summary="Кластеризация DBSCAN",
        manual_parameters=[
            openapi.Parameter('file', openapi.IN_FORM, type=openapi.TYPE_FILE, required=True),
            openapi.Parameter('eps', openapi.IN_FORM, type=openapi.TYPE_NUMBER, default=0.5),
            openapi.Parameter('min_samples', openapi.IN_FORM, type=openapi.TYPE_INTEGER, default=5),
            openapi.Parameter('x_axis', openapi.IN_FORM, type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter('y_axis', openapi.IN_FORM, type=openapi.TYPE_INTEGER, required=False),
        ],
        responses={200: "Успех", 400: "Ошибка"}
    )
    def post(self, request):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "Файл не загружен"}, status=400)

        try:
            X, features = _load_numeric_data(file_obj)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)

        try:
            eps = float(request.data.get('eps', 0.5))
            min_samples = int(request.data.get('min_samples', 5))
        except Exception as e:
            return Response({"error": f"Неверные параметры: {e}"}, status=400)

        x_idx = int(request.data.get('x_axis', 0))
        y_idx = int(request.data.get('y_axis', 1))
        if x_idx < 0 or x_idx >= len(features) or y_idx < 0 or y_idx >= len(features):
            return Response({"error": f"Неверные индексы осей. Доступно признаков: {len(features)}"}, status=400)

        model = DBSCAN(eps=eps, min_samples=min_samples)
        labels = model.fit_predict(X)
        n_noise = int(np.sum(labels == -1))
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        
        # Подготовка данных для Chart.js
        chart_data = _prepare_chart_data(X, labels, features, x_idx, y_idx, 'dbscan')
        
        return Response({
            "status": "success",
            "algorithm": "dbscan",
            "n_clusters": n_clusters,
            "n_noise": n_noise,
            "features": features,
            "chart_data": chart_data,  # 🔹 Данные для Chart.js
            "plot_info": {
                "x_axis": features[x_idx],
                "y_axis": features[y_idx]
            },
            "params": {"eps": eps, "min_samples": min_samples}
        })

def read_labels_file(file_obj):
    if not file_obj:
        return []

    # 1. Читаем байты безопасно
    if hasattr(file_obj, 'read'):
        raw = file_obj.read()
        if hasattr(file_obj, 'seek'):
            file_obj.seek(0)  # Сбрасываем курсор для Django
    else:
        raw = str(file_obj).encode('utf-8')

    # 2. Декодируем (utf-8-sig убирает BOM из Windows)
    try:
        text = raw.decode('utf-8-sig').strip()
    except Exception:
        text = raw.decode('utf-8', errors='ignore').strip()

    if not text:
        return []

    # 3. Определяем формат
    is_json = False
    if hasattr(file_obj, 'name'):
        is_json = file_obj.name.lower().endswith('.json')
    elif text.startswith(('{', '[')):
        is_json = True  # Эвристика, если имя потерялось

    if is_json:
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return [str(x).strip() for x in data if str(x).strip()]
            if isinstance(data, dict):
                return [str(v).strip() for v in data.values() if str(v).strip()]
        except json.JSONDecodeError:
            pass
        return []

    # 4. TXT: поддержка переносов строк и запятых
    return [
        lbl.strip()
        for line in text.splitlines()
        for lbl in line.split(',')
        if lbl.strip()
    ]

class ModelUploadView(BaseAPIView):
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_summary="Загрузка ONNX модели",
        manual_parameters=[
            openapi.Parameter('category', openapi.IN_FORM, type=openapi.TYPE_STRING, required=True, enum=[c.value for c in ModelCategory]),
            openapi.Parameter('onnx_file', openapi.IN_FORM, type=openapi.TYPE_FILE, required=True),
            openapi.Parameter('classes', openapi.IN_FORM, type=openapi.TYPE_FILE, required=False),
        ],
        responses={201: "Успех", 400: "Ошибка валидации", 409: "Дубликат"}
    )
    def post(self, request):
        category = request.data.get('category')
        onnx_file = request.FILES.get('onnx_file')
        classes_file = request.FILES.get('classes') or request.FILES.get('classes_file')
        if not category or category not in dict(ModelCategory.choices):
            return Response({"error": "Неверная категория"}, status=400)
        if not onnx_file:
            return Response({"error": "Файл .onnx не загружен"}, status=400)

        try:
            classes = read_labels_file(classes_file)
        except Exception:
            return Response({'error': "не удается прочитать файл классов"},status=400 )

        if OnnxModel.objects.filter(name=onnx_file.name, category=category).exists():
            return Response({"error": "Модель с таким именем уже существует в этой категории"}, status=409)

        try:
            model = OnnxModel.objects.create(
                name=onnx_file.name, category=category, onnx_file=onnx_file, classes=classes, is_active=False
            )
        except Exception as e:
            return Response({"error": f"Ошибка сохранения: {str(e)}"}, status=500)

        return Response({
            "status": "success",
            "id": model.pk, "name": model.name, "category": model.category,
            "onnx_file": model.onnx_file.url, "install_date": model.install_date.isoformat(),
            "is_active": model.is_active, "classes": model.classes
        }, status=201)


class ModelListView(BaseAPIView):
    @swagger_auto_schema(
        operation_summary="Список моделей",
        manual_parameters=[
            openapi.Parameter('category', openapi.IN_QUERY, type=openapi.TYPE_STRING, enum=[c.value for c in ModelCategory]),
            openapi.Parameter('active_only', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN, default=False),
        ],
        responses={200: "Успех", 400: "Ошибка"}
    )
    def get(self, request):
        category = request.query_params.get('category')
        active_only = request.query_params.get('active_only', 'false').lower() == 'true'

        if category and category not in dict(ModelCategory.choices):
            return Response({"error": "Неверная категория"}, status=400)

        qs = OnnxModel.objects.all()
        if category: qs = qs.filter(category=category)
        if active_only: qs = qs.filter(is_active=True)

        return Response({
            "status": "success",
            "count": qs.count(),
            "models": [
                {"id": m.pk, "name": m.name, "category": m.category, "onnx_file": m.onnx_file.url,
                 "install_date": m.install_date.isoformat(), "is_active": m.is_active, "classes": m.classes}
                for m in qs
            ]
        })


class ModelDetailView(BaseAPIView):
    @swagger_auto_schema(operation_summary="Информация о модели", responses={200: "Успех", 404: "Не найдена"})
    def get(self, request, pk):
        try: model = OnnxModel.objects.get(pk=pk)
        except OnnxModel.DoesNotExist: return Response({"error": "Модель не найдена"}, status=404)

        return Response({
            "status": "success", "id": model.pk, "name": model.name, "category": model.category,
            "onnx_file": model.onnx_file.url, "install_date": model.install_date.isoformat(),
            "is_active": model.is_active, "classes": model.classes
        })

    @swagger_auto_schema(operation_summary="Удалить модель", responses={200: "Удалено", 404: "Не найдена"})
    def delete(self, request, pk):
        try: model = OnnxModel.objects.get(pk=pk)
        except OnnxModel.DoesNotExist: return Response({"error": "Модель не найдена"}, status=404)

        file_path = model.onnx_file.path
        model.delete()
        if os.path.exists(file_path):
            try: os.remove(file_path)
            except OSError: pass

        return Response({"status": "success", "message": "Модель удалена"})


class ModelToggleActiveView(BaseAPIView):
    @swagger_auto_schema(operation_summary="Переключить активность (1 на категорию)", responses={200: "Успех", 404: "Не найдена"})
    def post(self, request, pk):
        try: model = OnnxModel.objects.select_for_update().get(pk=pk)
        except OnnxModel.DoesNotExist: return Response({"error": "Модель не найдена"}, status=404)

        new_status = not model.is_active
        if new_status:
            OnnxModel.objects.filter(category=model.category, is_active=True).exclude(pk=pk).update(is_active=False)

        model.is_active = new_status
        model.save(update_fields=['is_active'])

        return Response({
            "status": "success",
            "message": f"Модель {'активирована' if new_status else 'деактивирована'}",
            "is_active": model.is_active
        })


class ModelActiveByCategoryView(BaseAPIView):
    @swagger_auto_schema(operation_summary="Активные модели по категориям", responses={200: "Успех"})
    def get(self, request):
        result = {}
        for key, _ in ModelCategory.choices:
            model = OnnxModel.objects.filter(category=key, is_active=True).first()
            if model:
                result[key] = {"id": model.pk, "name": model.name, "onnx_file": model.onnx_file.url}
        return Response({"status": "success", "active_models": result})

class CriteryPost(BaseAPIView):
    @swagger_auto_schema(
        operation_summary="Добавление нового критерия эргономичности",
        responses={
            200: "Критерий успешно добавлен",
            400: "Ошибка добавления критерия",
        },
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['name', 'weight', 'var_name'],
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='Имя критерия'),
                'weight': openapi.Schema(type=openapi.TYPE_NUMBER, description='Вес критерия'),
                'var_name': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Имя переменной (латиница/кириллица, до 15 символов)'
                ),
                'is_counting_by_system_equastion': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description='Способ вычисления: false — обычный, true — через систему уравнений',
                    default=False
                ),
            }
        )
    )
    def post(self, request):
        name = request.data.get('name', '').strip()
        weight = request.data.get('weight')
        var_name = request.data.get('var_name', '').strip()
        is_counting_by_system_equastion = bool(request.data.get('is_counting_by_system_equastion', False))

        # Валидация обязательных полей
        if not name:
            return Response({'error': 'Поле "name" обязательно'}, status=400)
        if not var_name:
            return Response({'error': 'Поле "var_name" (имя переменной) обязательно'}, status=400)
        if len(var_name) > 15:
            return Response({'error': 'Имя переменной не должно превышать 15 символов'}, status=400)

        # Проверка уникальности имени критерия
        if Criterion_of_ergonomy.objects.filter(name=name).exists():
            return Response({'error': 'Критерий с таким названием уже существует'}, status=400)

        # Проверка уникальности имени переменной
        if Criterion_of_ergonomy.objects.filter(var_name=var_name).exists():
            return Response({'error': f'Переменная с именем "{var_name}" уже существует'}, status=400)

        try:
            new_criteria = Criterion_of_ergonomy.objects.create(
                name=name,
                weight=weight if weight is not None else 0,
                var_name=var_name,
                is_counting_by_system_equastion=is_counting_by_system_equastion,
            )
        except Exception as e:
            return Response({'error': f'Ошибка создания: {str(e)}'}, status=400)

        criteria_data = {
            'id': new_criteria.id,
            'name': new_criteria.name,
            'date_of_creation': new_criteria.date_of_creation.isoformat(),
            'is_active': new_criteria.is_active,
            'weight': new_criteria.weight,
            'color': new_criteria.color,
            'terrible_mark_border': new_criteria.terrible_mark_border,
            'bad_mark_border': new_criteria.bad_mark_border,
            'normal_mark_border': new_criteria.normal_mark_border,
            'good_mark_border': new_criteria.good_mark_border,
            'var_name': new_criteria.var_name,
            'is_counting_by_system_equastion': new_criteria.is_counting_by_system_equastion,
        }

        return Response({'message': 'Критерий успешно добавлен', 'object': criteria_data}, status=200)



class CriterionListView(BaseAPIView):
    @swagger_auto_schema(
        operation_summary="Получение всех критериев эргономичности",
        responses={200: "Список критериев"}
    )
    def get(self, request):
        criteria = Criterion_of_ergonomy.objects.all().order_by('id')
        data = []
        for c in criteria:
            data.append({
                "id": c.id,
                "name": c.name,
                "date_of_creation": c.date_of_creation.isoformat() if c.date_of_creation else None,
                "is_active": c.is_active,
                "weight": c.weight,
                "color": c.color,
                'terrible_mark_border': c.terrible_mark_border,
                'bad_mark_border': c.bad_mark_border,
                'normal_mark_border': c.normal_mark_border,
                'good_mark_border': c.good_mark_border,
                'var_name': c.var_name,
                'is_counting_by_system_equastion': c.is_counting_by_system_equastion,
            })
        return Response(data, status=200)

class CriterionBatchUpdateView(BaseAPIView):
    @swagger_auto_schema(
        operation_summary="Обновление списка критериев эргономичности",
        request_body=openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Items(
                type=openapi.TYPE_OBJECT,
                required=['id'],
                properties={
                    'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID критерия (обязательно)'),
                    'name': openapi.Schema(type=openapi.TYPE_STRING),
                    'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'weight': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'color': openapi.Schema(type=openapi.TYPE_STRING),
                    'terrible_mark_border': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'bad_mark_border': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'normal_mark_border': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'good_mark_border': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'var_name': openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description='Имя переменной (до 15 символов). Изменять с осторожностью.'
                    ),
                    # is_counting_by_system_equastion НЕ включён — его менять нельзя
                }
            )
        ),
        responses={200: "Успешное обновление", 400: "Ошибка валидации"}
    )
    def put(self, request):
        data = request.data
        if not isinstance(data, list) or len(data) == 0:
            return Response({"error": "Ожидается непустой список объектов"}, status=400)

        requested_ids = [item.get('id') for item in data if 'id' in item]
        if not requested_ids:
            return Response({"error": "В каждом объекте должно быть поле 'id'"}, status=400)

        existing_qs = Criterion_of_ergonomy.objects.filter(id__in=requested_ids)
        existing_map = {obj.id: obj for obj in existing_qs}

        if len(existing_map) != len(set(requested_ids)):
            missing = set(requested_ids) - set(existing_map.keys())
            return Response({"error": f"Критерии с ID {list(missing)} не найдены в БД"}, status=404)

        # Проверка уникальности var_name (с учётом того, что свой же var_name не считается дубликатом)
        new_var_names = [item.get('var_name') for item in data if item.get('var_name')]
        if new_var_names:
            duplicates_in_request = set([v for v in new_var_names if new_var_names.count(v) > 1])
            if duplicates_in_request:
                return Response(
                    {"error": f"В запросе есть повторяющиеся имена переменных: {list(duplicates_in_request)}"},
                    status=400
                )

            existing_vars = {
                c.var_name: c.id
                for c in Criterion_of_ergonomy.objects.filter(var_name__in=new_var_names)
            }
            for item in data:
                new_var = item.get('var_name')
                if new_var and new_var in existing_vars and existing_vars[new_var] != item['id']:
                    return Response(
                        {"error": f"Имя переменной '{new_var}' уже используется другим критерием (ID {existing_vars[new_var]})"},
                        status=400
                    )

        # Проверка границ
        for item in data:
            cid = item['id']
            obj = existing_map[cid]

            t_border = item.get('terrible_mark_border', obj.terrible_mark_border)
            b_border = item.get('bad_mark_border', obj.bad_mark_border)
            n_border = item.get('normal_mark_border', obj.normal_mark_border)
            g_border = item.get('good_mark_border', obj.good_mark_border)

            if t_border <= 0:
                return Response({"error": f"terrible_mark_border для ID {cid} должен быть > 0"}, status=400)

            if not (t_border < b_border < n_border < g_border):
                return Response({
                    "error": f"Нарушен порядок границ для ID {cid}.",
                    "received": {
                        "terrible_mark_border": t_border,
                        "bad_mark_border": b_border,
                        "normal_mark_border": n_border,
                        "good_mark_border": g_border,
                    }
                }, status=400)

        # Проверка суммы весов
        active_weight_sum = sum(
            item.get('weight', existing_map[item['id']].weight)
            for item in data
            if item.get('is_active', existing_map[item['id']].is_active) is True
        )

        if not math.isclose(active_weight_sum, 1.0, abs_tol=1e-6):
            return Response({
                "error": f"Сумма весов активных критериев должна быть равна 1.0. Текущая сумма: {active_weight_sum:.4f}"
            }, status=400)

        # ⚠️ ВАЖНО: is_counting_by_system_equastion НЕ входит в список обновляемых полей
        updatable_fields = [
            'name', 'is_active', 'weight', 'color',
            'terrible_mark_border', 'bad_mark_border',
            'normal_mark_border', 'good_mark_border',
            'var_name',  # имя переменной можно менять
        ]

        updated_count = 0
        for item in data:
            obj = existing_map[item['id']]
            changed = False

            for field in updatable_fields:
                new_val = item.get(field)
                if new_val is not None and getattr(obj, field) != new_val:
                    setattr(obj, field, new_val)
                    changed = True

            if changed:
                obj.save()
                updated_count += 1

        return Response({
            "message": f"Успешно обработано. Обновлено записей: {updated_count}",
            "active_weight_sum": round(active_weight_sum, 4)
        }, status=200)


class CriterionDeleteView(BaseAPIView):
    @swagger_auto_schema(
        operation_summary="Удаление критерия по ID",
        manual_parameters=[
            openapi.Parameter(
                'id', openapi.IN_PATH,
                type=openapi.TYPE_INTEGER, required=True,
                description='ID критерия для удаления'
            )
        ],
        responses={
            204: 'Критерий успешно удалён',
            404: 'Критерий не найден',
        }
    )
    def delete(self, request, pk):
        try:
            criterion = Criterion_of_ergonomy.objects.get(id=pk)
        except Criterion_of_ergonomy.DoesNotExist:
            return Response({'error': f'Критерий с ID {pk} не найден'}, status=404)
        
        try:
            # Собираем информацию о том, что будет удалено (для логирования)
            related_info = {
                'form_questions': criterion.form_question_set.count(),
                'formula_params': criterion.formulaparam_set.count(),
                'system_equations': criterion.systemequastion_set.count(),
                'common_formulas': criterion.commonformula_set.count(),
                'system_equations_for_criterion': criterion.systemequastionforcriterion_set.count(),
                'criterion_using_for_formulas': criterion.cilterionusingforformula_set.count(),
                'auto_counting_methods': criterion.autocountingmethod_criterion_set.count(),
            }
            
            # Удаляем критерий (Django автоматически удалит всё каскадно благодаря on_delete=CASCADE)
            deleted_count, deleted_details = criterion.delete()
            
            # Логируем результат
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"✅ Критерий #{pk} '{criterion.name}' удалён. Всего удалено объектов: {deleted_count}")
            logger.debug(f"Детали удаления: {deleted_details}")
            
            return Response({
                'message': f'Критерий "{criterion.name}" успешно удалён',
                'deleted_count': deleted_count,
                'deleted_details': related_info
            }, status=200)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"❌ Ошибка при удалении критерия #{pk}: {str(e)}", exc_info=True)
            return Response({
                'error': f'Ошибка при удалении критерия: {str(e)}'
            }, status=500)

class CriterionSurveyStatsView(BaseAPIView):    
    @swagger_auto_schema(
        operation_summary="Статистика вопросов и формул критерия",
        operation_description="""
        Возвращает:
        - Количество вопросов по типам (общие, по помещениям, и т.д.)
        - Заглушку для статистики формул (обычные, системы, для комнат, для помещений)
        Примечание: Статистика формул пока возвращается как mock-данные.
        """,
        manual_parameters=[
            openapi.Parameter(
                'criterion_id',
                openapi.IN_PATH,
                type=openapi.TYPE_INTEGER,
                required=True,
                description='ID критерия эргономичности'
            )
        ],
        responses={
            200: openapi.Response(
                description='Успешный ответ',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'name':openapi.Schema(type= openapi.TYPE_STRING),
                        'questions': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'general': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'room_total': openapi.Schema(type=openapi.TYPE_INTEGER),
                            }
                        ),
                        'formulas': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'ordinary': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'system': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'forPremises': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'perRoom': openapi.Schema(type=openapi.TYPE_INTEGER),
                            }
                        )
                    }
                ),
                examples={
                    'application/json': {
                        'questions': {
                            'general': 6,
                            'room_total': 16
                        },
                        'formulas': {
                            'ordinary': 5,
                            'system': 2,
                            'forPremises': 4,
                            'perRoom': 3
                        }
                    }
                }
            ),
            404: 'Критерий не найден',
            400: 'Некорректный ID'
        }
    )
    def get(self, request, criterion_id):
        try:
            criterion_id = int(criterion_id)
        except (ValueError, TypeError):
            return Response({'error': 'Некорректный ID'}, status=400)

        try:
            criterion = Criterion_of_ergonomy.objects.get(id=criterion_id)
        except Criterion_of_ergonomy.DoesNotExist:
            return Response({'error': 'Критерий не найден'}, status=404)

        is_system = criterion.is_counting_by_system_equastion
        criterion_color = criterion.color

        # Общая статистика по анкете (вопросам)
        question_stats = Form_question.objects.filter(
            criterion_id=criterion_id, is_active=True
        ).aggregate(
            general=Count('id', filter=Q(type='for_floorplan')),
            room_total=Count('id', filter=Q(type='for_every_room')),
        )

        # Разная статистика для формул в зависимости от режима
        if not is_system:
            # ─ Обычный режим (анкетирование + формулы) ──
            fp_ids = FormulaParam.objects.filter(
                cryteria_id=criterion_id, is_active=True
            ).values_list('id', flat=True)

            formulas_data = {
                'formulas_count': CommonFormula.objects.filter(criterion_id=criterion_id, is_active=True).count(),
                'systems_count': SystemEquastionForCriterion.objects.filter(criterion_id=criterion_id).count(),
                'limit_params_count': LimitParam.objects.filter(formula_param_id__in=fp_ids).count(),
                'parameters_count': UserInputParam.objects.filter(formula_param_id__in=fp_ids).count(),
                'auto_params_count': AutoCountingParam.objects.filter(formula_param_id__in=fp_ids).count(),
            }
        else:
            # ── Режим системы уравнений ──
            sys_eq_ids = SystemEquastionForCriterion.objects.filter(
                criterion_id=criterion_id
            ).values_list('id', flat=True)

            formulas_data = {
                'equations_count': EquastionOfCriterionSystemEquastion.objects.filter(
                    criterion_system_equastion_id__in=sys_eq_ids
                ).count(),
                'variables_count': SystemEquastionForCriterion_UIP.objects.filter(
                    system_equation_for_criteria_id__in=sys_eq_ids
                ).values('user_input_param_id').distinct().count(),
                'other_criteria_count': CilterionUsingForFormula.objects.filter(
                    system_equation_for_criteria_id__in=sys_eq_ids
                ).values('criterion_id').distinct().count(),
            }

        return Response({
            'name': criterion.name,
            'color': criterion_color,
            'is_counting_by_system_equastion': is_system,
            'questions': {
                'general': question_stats.get('general') or 0,
                'room_total': question_stats.get('room_total') or 0,
            },
            'formulas': formulas_data
        }, status=200)

class RoomTypeListView(BaseAPIView):
    @swagger_auto_schema(
        operation_summary="Получение всех типов комнат",
        responses={
            200: openapi.Response(
                description='Список типов комнат',
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'type_name': openapi.Schema(type=openapi.TYPE_STRING),
                            'label': openapi.Schema(type=openapi.TYPE_STRING),
                            'color': openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    )
                )
            )
        }
    )
    def get(self, request):
        room_types = RoomType.objects.all().order_by('id')
        data = [
            {
                'id': rt.id,
                'type_name': rt.type_name,
                'label': rt.label or '',
                'color': rt.color,
            }
            for rt in room_types
        ]
        
        return Response(data, status=200)

class QuestionCreateView(BaseAPIView):
    @swagger_auto_schema(
        operation_summary="Добавление нового вопроса",
        operation_description="Создаёт вопрос с рекомендацией, пороговым баллом и вариантами ответов",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['text', 'recommendation', 'score_for_recommendation', 'type', 'criterion_id'],
            properties={
                'text': openapi.Schema(type=openapi.TYPE_STRING, description='Текст вопроса'),
                'recommendation': openapi.Schema(type=openapi.TYPE_STRING, description='Рекомендация по улучшению (обязательно)'),
                'score_for_recommendation': openapi.Schema(
                    type=openapi.TYPE_NUMBER, 
                    format='float',
                    default=6,
                    description='Пороговый балл: рекомендация показывается, если набрано меньше этого значения'
                ),
                'criterion_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID критерия'),
                'type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=[c[0] for c in QuestionType.choices],
                    description='Тип вопроса'
                ),
                'room_type_ids': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_INTEGER),
                    description='ID типов комнат (для for_selected_rooms / for_unselected_rooms)'
                ),
                'answers': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'text': openapi.Schema(type=openapi.TYPE_STRING, description='Текст ответа'),
                            'score': openapi.Schema(type=openapi.TYPE_NUMBER, format='float', description='Баллы (0-10)')
                        },
                        required=['text', 'score']
                    ),
                    description='Список вариантов ответов'
                ),
            }
        ),
        responses={
            201: openapi.Response(
                description='Вопрос создан',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'question': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'text': openapi.Schema(type=openapi.TYPE_STRING),
                                'recommendation': openapi.Schema(type=openapi.TYPE_STRING),
                                'score_for_recommendation': openapi.Schema(type=openapi.TYPE_NUMBER),
                                'type': openapi.Schema(type=openapi.TYPE_STRING),
                                'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'room_type_ids': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Items(type=openapi.TYPE_INTEGER)
                                ),
                                'answers': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Items(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                            'text': openapi.Schema(type=openapi.TYPE_STRING),
                                            'score': openapi.Schema(type=openapi.TYPE_NUMBER)
                                        }
                                    )
                                )
                            }
                        )
                    }
                )
            ),
            400: 'Ошибка валидации',
            404: 'Критерий не найден'
        }
    )
    def post(self, request):
        criterion_id = request.data.get('criterion_id')
        if not Criterion_of_ergonomy.objects.filter(id=criterion_id).exists():
            return Response({'error': f'Критерий с ID {criterion_id} не найден'}, status=404)
        
        text = request.data.get('text', '').strip()
        recommendation = request.data.get('recommendation', '').strip()  # ← исправлено имя
        score_for_rec = request.data.get('score_for_recommendation', 6)  # ← новое поле, default=6
        q_type = request.data.get('type')
        room_type_ids = request.data.get('room_type_ids', [])
        answers_data = request.data.get('answers', [])
        
        # 🔹 Валидация
        if not text:
            return Response({'error': 'Поле "text" обязательно'}, status=400)
        if not recommendation:
            return Response({'error': 'Поле "recommendation" обязательно'}, status=400)
        
        # Валидация порогового балла (0-10)
        try:
            score_for_rec = float(score_for_rec)
            if not (0 <= score_for_rec <= 10):
                return Response({'error': 'score_for_recommendation должен быть от 0 до 10'}, status=400)
        except (TypeError, ValueError):
            return Response({'error': 'Некорректное значение score_for_recommendation'}, status=400)
            
        if not q_type or q_type not in dict(QuestionType.choices):
            return Response({'error': f'Некорректный тип'}, status=400)
            
        if q_type in ['for_selected_rooms', 'for_unselected_rooms']:
            if not room_type_ids:
                return Response({'error': f'Для типа "{q_type}" обязательны room_type_ids'}, status=400)
            existing_rt = set(RoomType.objects.filter(id__in=room_type_ids).values_list('id', flat=True))
            if set(room_type_ids) - existing_rt:
                return Response({'error': 'Не все room_type_ids существуют'}, status=400)
        
        # 🔹 Валидация ответов (минимум 2)
        valid_answers = [a for a in answers_data if isinstance(a, dict) and a.get('text', '').strip()]
        if len(valid_answers) < 2:
            return Response({'error': 'Минимум 2 варианта ответа обязательны'}, status=400)
        
        # 🔹 Создание вопроса (используем исправленные имена полей!)
        question = Form_question.objects.create(
            criterion_id_id=criterion_id,
            question=text,  # ← было quesion
            recommendation=recommendation,  # ← было recomendation
            score_for_recommendation=score_for_rec,  # ← новое поле
            type=q_type,
            is_active=False
        )
        
        # 🔹 Привязка типов комнат
        if q_type in ['for_selected_rooms', 'for_unselected_rooms'] and room_type_ids:
            Form_Question_RoomType.objects.bulk_create([
                Form_Question_RoomType(
                    qusion_id=question,
                    room_type_id_id=room_id
                )
                for room_id in room_type_ids
            ])
        
       # 🔹 Создание ответов (РАБОЧИЙ ВАРИАНТ под текущую модель)
        created_answers = []
        for ans in valid_answers:
            ans_text = ans.get('text', '').strip()
            ans_score = ans.get('score', 0)
            
            try:
                ans_score = float(ans_score) if ans_score is not None else 0
                if not (0 <= ans_score <= 10):
                    continue
            except (TypeError, ValueError):
                continue
                
            created_answers.append(FormAnswer(
                question_id=question,    # ← передаём объект (поле уже называется qusion_id)
                answer=ans_text,       # ← как есть
                score=ans_score        # ← заглавная буква, как в модели!
            ))

        if created_answers:
            FormAnswer.objects.bulk_create(created_answers)
        
        # 🔹 Формируем ответ для фронтенда
        answers_payload = [
            {'id': a.id, 'text': a.answer, 'score': a.score}
            for a in FormAnswer.objects.filter(question_id=question)
        ]
        
        return Response({
            'message': 'Вопрос успешно создан',
            'question': {
                'id': question.id,
                'text': question.question,  # ← исправлено
                'recommendation': question.recommendation,  # ← исправлено
                'score_for_recommendation': question.score_for_recommendation,  # ← новое поле
                'type': question.type,
                'is_active': question.is_active,
                'room_type_ids': room_type_ids if q_type in ['for_selected_rooms', 'for_unselected_rooms'] else [],
                'answers': answers_payload
            }
        }, status=201)

class QuestionDeleteView(BaseAPIView):
    @swagger_auto_schema(
        operation_summary="Удаление вопроса",
        operation_description="Удаляет вопрос и все связанные ответы (каскадно).",
        manual_parameters=[
            openapi.Parameter(
                'question_id',
                openapi.IN_PATH,
                type=openapi.TYPE_INTEGER,
                required=True,
                description='ID вопроса'
            )
        ],
        responses={
            204: 'Вопрос успешно удалён',
            404: 'Вопрос не найден'
        }
    )
    def delete(self, request, question_id):
        try:
            question = Form_question.objects.get(id=question_id)
        except Form_question.DoesNotExist:
            return Response({'error': f'Вопрос с ID {question_id} не найден'}, status=404)
        question.delete()
        
        return Response(status=204)

class QuestionBatchSaveView(BaseAPIView):
    @swagger_auto_schema(
        operation_summary="Полная синхронизация вопросов критерия",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['questions'],
            properties={
                'criterion_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID критерия'),
                'questions': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(
                        type=openapi.TYPE_OBJECT,
                        required=['text', 'recommendation', 'score_for_recommendation', 'type'],
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'text': openapi.Schema(type=openapi.TYPE_STRING),
                            'recommendation': openapi.Schema(type=openapi.TYPE_STRING),
                            'score_for_recommendation': openapi.Schema(type=openapi.TYPE_NUMBER, format='float', default=6),
                            'type': openapi.Schema(type=openapi.TYPE_STRING, enum=[c[0] for c in QuestionType.choices]),
                            'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            'answers': openapi.Schema(
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Items(type=openapi.TYPE_OBJECT, properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'text': openapi.Schema(type=openapi.TYPE_STRING),
                                    'score': openapi.Schema(type=openapi.TYPE_NUMBER),
                                })
                            ),
                            'room_type_ids': openapi.Schema(
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Items(type=openapi.TYPE_INTEGER)
                            ),
                        }
                    )
                ),
            }
        ),
        responses={
            200: openapi.Response(
                description='Синхронизация завершена',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'updated': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'deleted': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'errors': openapi.Schema(
                            type=openapi.TYPE_ARRAY, 
                            items=openapi.Items(type=openapi.TYPE_OBJECT),
                            nullable=True
                        ),
                    }
                )
            ),
            400: 'Ошибка валидации',
            404: 'Критерий не найден'
        }
    )
    def put(self, request):
        questions_data = request.data.get('questions', [])
        payload_criterion_id = request.data.get('criterion_id')
        
        if not isinstance(questions_data, list):
            return Response({'error': '"questions" должен быть массивом'}, status=400)
        
        # 🔍 1. Определяем target_criterion_id
        target_criterion_id = payload_criterion_id
        if not target_criterion_id:
            for q in questions_data:
                q_id = q.get('id')
                if q_id:
                    try:
                        target_criterion_id = Form_question.objects.get(id=q_id).criterion_id_id
                        break
                    except Form_question.DoesNotExist:
                        continue
                        
        if not target_criterion_id:
            return Response({
                'error': 'Не указан criterion_id и не найден среди существующих вопросов в payload'
            }, status=400)
            
        if not Criterion_of_ergonomy.objects.filter(id=target_criterion_id).exists():
            return Response({'error': f'Критерий с ID {target_criterion_id} не найден'}, status=404)
        
        errors = []
        updated_count = 0
        processed_question_ids = []
        
        # 🔹 2. Создание/Обновление вопросов и ответов
        for idx, q_data in enumerate(questions_data):
            q_id = q_data.get('id')
            text = q_data.get('text', '').strip()
            recommendation = q_data.get('recommendation', '').strip()
            score_for_rec = q_data.get('score_for_recommendation', 6)
            q_type = q_data.get('type')
            answers_data = q_data.get('answers') or []
            is_active = q_data.get('is_active', True)
            room_type_ids = q_data.get('room_type_ids') or []
            
            # 🔹 Базовая валидация
            if not text:
                errors.append({'index': idx, 'error': 'Пустой текст вопроса'})
                continue
            if not recommendation:
                errors.append({'index': idx, 'error': 'Поле "recommendation" обязательно'})
                continue
            
            # Валидация порогового балла
            try:
                score_for_rec = float(score_for_rec)
                if not (0 <= score_for_rec <= 10):
                    errors.append({'index': idx, 'error': 'score_for_recommendation должен быть от 0 до 10'})
                    continue
            except (TypeError, ValueError):
                errors.append({'index': idx, 'error': 'Некорректное значение score_for_recommendation'})
                continue
                
            if not q_type or q_type not in dict(QuestionType.choices):
                errors.append({'index': idx, 'error': f'Некорректный тип: {q_type}'})
                continue
            
            # 🔹 Валидация ответов для активных вопросов
            valid_answers = [a for a in answers_data if isinstance(a, dict) and a.get('text', '').strip()]
            if is_active and len(valid_answers) < 2:
                errors.append({'index': idx, 'error': 'Минимум 2 варианта ответа обязательны для активных вопросов'})
                continue
                
            if is_active and valid_answers:
                scores = []
                for a in valid_answers:
                    try:
                        s = float(a.get('score', 0))
                        if 0 <= s <= 10:
                            scores.append(s)
                    except (TypeError, ValueError):
                        continue
                if 10 not in scores:
                    errors.append({'text': text, 'error': 'Активный вопрос требует хотя бы один ответ с 10 баллами'})
                    continue
            
            # 🔹 Валидация room_type_ids
            if q_type in ['for_selected_rooms', 'for_unselected_rooms']:
                if not room_type_ids:
                    errors.append({'text': text, 'error': f'Для типа "{q_type}" обязательны room_type_ids'})
                    continue
                existing_rt = set(RoomType.objects.filter(id__in=room_type_ids).values_list('id', flat=True))
                missing_rt = set(room_type_ids) - existing_rt
                if missing_rt:
                    errors.append({'text': text, 'error': f'Не найдены типы комнат: {list(missing_rt)}'})
                    continue
                    
            try:
                # 🔹 Получение или создание вопроса
                if q_id:
                    try:
                        question = Form_question.objects.get(id=q_id)
                        if question.criterion_id_id != target_criterion_id:
                            errors.append({'id': q_id, 'error': 'Вопрос принадлежит другому критерию'})
                            continue
                    except Form_question.DoesNotExist:
                        errors.append({'id': q_id, 'error': 'Вопрос не найден в БД'})
                        continue
                else:
                    # Создаём новый вопрос с временными значениями
                    question = Form_question.objects.create(
                        criterion_id_id=target_criterion_id,
                        question='',  # временное значение, обновим ниже
                        recommendation='',
                        score_for_recommendation=6,
                        type=q_type,
                        is_active=False
                    )
                
                # 🔹 Обновление полей вопроса (ПРАВИЛЬНЫЕ ИМЕНА ПОЛЕЙ)
                question.question = text  # ✅ было quesion → стало question
                question.recommendation = recommendation  # ✅ было recomendation → стало recommendation
                question.score_for_recommendation = score_for_rec  # ✅ новое поле
                question.type = q_type
                question.is_active = is_active if valid_answers else False
                question.save()
                
                if not q_id:  # если создали новый — добавляем ID в обработанные
                    processed_question_ids.append(question.id)
                elif question.id not in processed_question_ids:  # избегаем дубликатов
                    processed_question_ids.append(question.id)
                    
                updated_count += 1

                # 🔹 Синхронизация ответов (ПРАВИЛЬНЫЕ ИМЕНА ПОЛЕЙ FormAnswer)
                answer_ids_to_keep = []
                for ans_data in valid_answers:
                    ans_id = ans_data.get('id')
                    ans_text = ans_data.get('text', '').strip()
                    ans_score = ans_data.get('score', 0)
                    
                    try:
                        ans_score = float(ans_score) if ans_score is not None else 0
                        if not (0 <= ans_score <= 10):
                            continue
                    except (TypeError, ValueError):
                        continue
                        
                    if ans_id:
                        # ✅ update_or_create с правильными именами полей:
                        # question_id (FK), answer, score (lowercase!)
                        FormAnswer.objects.update_or_create(
                            id=ans_id,
                            question_id=question,  # ✅ было qusion_id → стало question_id
                            defaults={
                                'answer': ans_text,
                                'score': ans_score  # ✅ было Score → стало score (lowercase)
                            }
                        )
                        answer_ids_to_keep.append(ans_id)
                    else:
                        # ✅ create с правильными именами полей
                        new_ans = FormAnswer.objects.create(
                            question_id=question,  # ✅ было qusion_id → стало question_id
                            answer=ans_text,
                            score=ans_score  # ✅ было Score → стало score (lowercase)
                        )
                        answer_ids_to_keep.append(new_ans.id)
                
                # Удаляем ответы, которых нет в payload
                FormAnswer.objects.filter(question_id=question).exclude(id__in=answer_ids_to_keep).delete()
                
                # 🔹 Синхронизация привязки к комнатам
                # ⚠️ Form_Question_RoomType всё ещё использует qusion_id (опечатка в модели)
                Form_Question_RoomType.objects.filter(qusion_id=question).delete()
                if q_type in ['for_selected_rooms', 'for_unselected_rooms'] and room_type_ids:
                    Form_Question_RoomType.objects.bulk_create([
                        Form_Question_RoomType(
                            qusion_id=question,        # ⚠️ опечатка сохраняется в этой модели
                            room_type_id_id=rt_id      # ✅ room_type_id_id = передача числа
                        ) 
                        for rt_id in room_type_ids
                    ])
                    
            except Exception as e:
                errors.append({'text': text or f'Индекс {idx}', 'error': str(e)})
                continue
        
        # 🔹 3. Удаление отсутствующих вопросов
        to_delete = Form_question.objects.filter(
            criterion_id_id=target_criterion_id
        ).exclude(id__in=processed_question_ids)
        deleted_count = to_delete.count()
        to_delete.delete()  # CASCADE удалит ответы и связи с комнатами
        
        # 🔹 4. Формирование ответа
        return Response({
            'message': f'Синхронизация завершена: обновлено={updated_count}, удалено={deleted_count}',
            'updated': updated_count,
            'deleted': deleted_count,
            'errors': errors if errors else None
        }, status=207 if errors else 200)   

class CriterionQuestionsListView(BaseAPIView):
    @swagger_auto_schema(
        operation_summary="Получение списка вопросов критерия",
        operation_description="Возвращает вопросы с рекомендациями, пороговыми баллами, ответами и привязкой к комнатам",
        manual_parameters=[
            openapi.Parameter('criterion_id', openapi.IN_PATH, type=openapi.TYPE_INTEGER, required=True, 
                            description='ID критерия эргономики')
        ],
        responses={
            200: openapi.Response(
                description='Список вопросов',
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'text': openapi.Schema(type=openapi.TYPE_STRING),
                            'recommendation': openapi.Schema(type=openapi.TYPE_STRING),
                            'score_for_recommendation': openapi.Schema(type=openapi.TYPE_NUMBER, format='float'),
                            'type': openapi.Schema(type=openapi.TYPE_STRING),
                            'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            'room_type_ids': openapi.Schema(
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Items(type=openapi.TYPE_INTEGER)
                            ),
                            'answers': openapi.Schema(
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Items(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                        'text': openapi.Schema(type=openapi.TYPE_STRING),
                                        'score': openapi.Schema(type=openapi.TYPE_NUMBER)
                                    }
                                )
                            )
                        }
                    )
                )
            ),
            404: 'Критерий не найден'
        }
    )
    def get(self, request, criterion_id):
        # 🔹 Проверка существования критерия
        if not Criterion_of_ergonomy.objects.filter(id=criterion_id).exists():
            return Response({'error': f'Критерий с ID {criterion_id} не найден'}, status=404)
        
        # 🔹 Получаем вопросы (используем исправленное имя поля question)
        questions = Form_question.objects.filter(
            criterion_id_id=criterion_id
        ).order_by('id')
        
        data = []
        for q in questions:
            # 🔹 Ответы: загрузка через reverse-связь
            answers = []
            for ans in q.formanswer_set.all():  # default related_name
                answers.append({
                    'id': ans.id,
                    'text': ans.answer,
                    'score': ans.score  # поле с заглавной буквы в модели
                })
            
            # 🔹 Типы комнат: загрузка через промежуточную модель
            room_ids = []
            for link in q.form_question_roomtype_set.all():  # default related_name
                room_ids.append(link.room_type_id_id)  # получаем числовой ID
            
            # 🔹 Формируем объект вопроса с исправленными именами полей
            data.append({
                'id': q.id,
                'text': q.question,  # ← было q.quesion (опечатка)
                'recommendation': q.recommendation,  # ← было q.recomendation (опечатка)
                'score_for_recommendation': q.score_for_recommendation,  # ← новое поле
                'type': q.type,
                'is_active': q.is_active,
                'room_type_ids': room_ids,
                'answers': answers
            })
        
        return Response(data, status=200)

class FurnitureTypeListView(BaseAPIView):
    @swagger_auto_schema(
        operation_summary="Получение всех типов мебели",
        responses={
            200: openapi.Response(
                description='Список типов мебели',
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'type_name': openapi.Schema(type=openapi.TYPE_STRING),
                            'label': openapi.Schema(type=openapi.TYPE_STRING),
                            'color': openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    )
                )
            )
        }
    )
    def get(self, request):
        f_types = FurnitureType.objects.all().order_by('id')
        data = [
            {
                'id': ft.id,
                'type_name': ft.type_name,
                'label': ft.label or '',
                'color': ft.color,
            }
            for ft in f_types
        ]
        
        return Response(data, status=200)

class ConstructElementTypeListView(BaseAPIView):
    @swagger_auto_schema(
        operation_summary="Получение всех типов мебели",
        responses={
            200: openapi.Response(
                description='Список типов мебели',
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'type_name': openapi.Schema(type=openapi.TYPE_STRING),
                            'label': openapi.Schema(type=openapi.TYPE_STRING),
                            'color': openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    )
                )
            )
        }
    )
    def get(self, request):
        ce_types = ConstructElementType.objects.all().order_by('id')
        data = [
            {
                'id': cet.id,
                'type_name': cet.type_name,
                'label': cet.label or '',
                'color': cet.color,
            }
            for cet in ce_types
        ]
        
        return Response(data, status=200)

class FloorplanSaveView(BaseAPIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def post(self, request):
        try:
            image_file = request.FILES.get('image')
            if not image_file:
                return Response({'error': 'Файл изображения обязателен'}, status=400)

            _, ext = os.path.splitext(image_file.name)
            image_file.name = f"{uuid.uuid4().hex}{ext.lower()}"

            floorplan_name = request.data.get('name', 'floorplan')
            width = float(request.data.get('width', 0))
            height = float(request.data.get('height', 0))
            pixel_to_m = float(request.data.get('pixel_to_m_in_square', 0))
            square_habitation = float(request.data.get('square_of_habitation', 0))

            floorplan = Floorplan.objects.create(
                img=image_file,
                width=width,
                height=height,
                pixel_to_m_in_square=pixel_to_m,
                square_of_habitation=square_habitation
            )

            annotations_json = request.data.get('data')
            if isinstance(annotations_json, str):
                annotations = json.loads(annotations_json)
            else:
                annotations = annotations_json or {}

            rooms_data = annotations.get('rooms', [])
            walls_data = annotations.get('walls', [])
            furniture_data = annotations.get('furniture', [])

            # === СОХРАНЯЕМ КОМНАТЫ ===
            # Маппинг frontend_id -> backend_id
            room_id_map = {}

            for room_data in rooms_data:
                room_type = RoomType.objects.filter(id=room_data.get('type')).first()
                if not room_type:
                    continue

                bbox = room_data.get('bbox', [0, 0, 0, 0])
                room = Room.objects.create(
                    floorplan_id=floorplan,
                    room_type_id=room_type,
                    min_x=float(bbox[0]),
                    max_x=float(bbox[1]),
                    min_y=float(bbox[2]),
                    max_y=float(bbox[3]),
                    square=float(room_data.get('realArea', 0))
                )
                # Сохраняем маппинг frontend_id -> backend_id
                room_id_map[room_data['id']] = room.id

            # === СОХРАНЯЕМ СТЕНЫ ===
            for wall_data in walls_data:
                construct_type = ConstructElementType.objects.filter(id=wall_data.get('type')).first()
                if not construct_type:
                    continue

                bbox = wall_data.get('bbox', [0, 0, 0, 0])
                ConstructElement.objects.create(
                    floorplan_id=floorplan,
                    construct_element_type_id=construct_type,
                    min_x=float(bbox[0]),
                    max_x=float(bbox[1]),
                    min_y=float(bbox[2]),
                    max_y=float(bbox[3]),
                )

            # === СОХРАНЯЕМ МЕБЕЛЬ ===
            for furn_data in furniture_data:
                furniture_type = FurnitureType.objects.filter(id=furn_data.get('type')).first()
                if not furniture_type:
                    continue

                # ✅ Определяем комнату по room_id (frontend_id), а не по label
                room = None
                frontend_room_id = furn_data.get('room_id')

                if frontend_room_id is not None and frontend_room_id in room_id_map:
                    backend_room_id = room_id_map[frontend_room_id]
                    room = Room.objects.filter(id=backend_room_id).first()
                else:
                    # Fallback: если room_id не передан, ищем комнату по позиции центра мебели
                    bbox = furn_data.get('bbox', [0, 0, 0, 0])
                    center_x = (float(bbox[0]) + float(bbox[1])) / 2
                    center_y = (float(bbox[2]) + float(bbox[3])) / 2

                    for r in Room.objects.filter(floorplan_id=floorplan):
                        if (r.min_x <= center_x <= r.max_x and
                            r.min_y <= center_y <= r.max_y):
                            room = r
                            break

                bbox = furn_data.get('bbox', [0, 0, 0, 0])
                Furniture.objects.create(
                    furniture_type_id=furniture_type,
                    room_id=room,
                    min_x=float(bbox[0]),
                    max_x=float(bbox[1]),
                    min_y=float(bbox[2]),
                    max_y=float(bbox[3])
                )

            return Response({
                'message': 'План успешно сохранён',
                'floorplan_id': floorplan.id,
                'rooms_count': len(room_id_map),
                'walls_count': len(walls_data),
                'furniture_count': len(furniture_data)
            }, status=201)

        except json.JSONDecodeError as e:
            return Response({'error': f'Ошибка JSON: {str(e)}'}, status=400)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=500)

class FloorplanListView(BaseAPIView):
    def get(self, request):
        floorplans = Floorplan.objects.all().order_by('-upload_at')
        data = []
        for fp in floorplans:
            # Читаем файл и кодируем в base64
            img_base64 = None
            if fp.img and os.path.isfile(fp.img.path):
                with open(fp.img.path, 'rb') as f:
                    img_data = f.read()
                    img_base64 = base64.b64encode(img_data).decode('utf-8')
                    # Определяем MIME type
                    ext = os.path.splitext(fp.img.name)[1].lower()
                    mime_type = {
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.png': 'image/png',
                        '.webp': 'image/webp'
                    }.get(ext, 'image/jpeg')
            
            data.append({
                'id': fp.id,
                'img': f'data:{mime_type};base64,{img_base64}',
                'width': fp.width,
                'height': fp.height,
                'upload_at': fp.upload_at.isoformat() if fp.upload_at else None,
                'square_of_habitation': fp.square_of_habitation,
            })
        return Response({'results': data, 'count': len(data)}, status=200)


class FloorplanDetailView(BaseAPIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get(self, request, pk):
        try:
            floorplan = Floorplan.objects.prefetch_related(
                'room_set__room_type_id',
                'room_set__furniture_set__furniture_type_id',
                'constructelement_set__construct_element_type_id'
            ).get(id=pk)

            img_url = None
            if floorplan.img and os.path.isfile(floorplan.img.path):
                with open(floorplan.img.path, 'rb') as f:
                    img_data = f.read()
                    img_base64 = base64.b64encode(img_data).decode('utf-8')
                    ext = os.path.splitext(floorplan.img.name)[1].lower()
                    mime_type = {
                        '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                        '.png': 'image/png', '.webp': 'image/webp'
                    }.get(ext, 'image/jpeg')
                    img_url = f'data:{mime_type};base64,{img_base64}'

            rooms = []
            furniture = []
            for room in floorplan.room_set.all():
                rooms.append({
                    'id': room.id,
                    'type': room.room_type_id.id if room.room_type_id else None,
                    'label': room.room_type_id.label if room.room_type_id else '',
                    'color': room.room_type_id.color if room.room_type_id else '#0d6efd',
                    'bbox': [float(room.min_x), float(room.max_x), float(room.min_y), float(room.max_y)],
                    'square': float(room.square) if room.square else 0
                })

                for furn in room.furniture_set.all():
                    furniture.append({
                        'id': furn.id,
                        'type': furn.furniture_type_id.id if furn.furniture_type_id else None,
                        'label': furn.furniture_type_id.label if furn.furniture_type_id else '',
                        'color': furn.furniture_type_id.color if furn.furniture_type_id else '#0d6efd',
                        'bbox': [float(furn.min_x), float(furn.max_x), float(furn.min_y), float(furn.max_y)],
                        'room': room.room_type_id.label if room.room_type_id else None,
                        'room_id': room.id,  # ✅ ДОБАВЛЕНО: ID комнаты
                    })

            walls = []
            for wall in floorplan.constructelement_set.all():
                walls.append({
                    'id': wall.id,
                    'type': wall.construct_element_type_id.id if wall.construct_element_type_id else None,
                    'label': wall.construct_element_type_id.label if wall.construct_element_type_id else '',
                    'color': wall.construct_element_type_id.color if wall.construct_element_type_id else '#0d6efd',
                    'bbox': [float(wall.min_x), float(wall.max_x), float(wall.min_y), float(wall.max_y)]
                })

            return Response({
                'id': floorplan.id,
                'img': img_url,
                'width': float(floorplan.width) if floorplan.width else 0,
                'height': float(floorplan.height) if floorplan.height else 0,
                'upload_at': floorplan.upload_at.isoformat() if floorplan.upload_at else None,
                'pixel_to_m_in_square': float(floorplan.pixel_to_m_in_square) if floorplan.pixel_to_m_in_square else 0,
                'square_of_habitation': float(floorplan.square_of_habitation) if floorplan.square_of_habitation else 0,
                'rooms': rooms,
                'walls': walls,
                'furniture': furniture
            }, status=200)

        except Floorplan.DoesNotExist:
            return Response({'error': 'План не найден'}, status=404)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=500)
    def put(self, request, pk):
        try:
            floorplan = Floorplan.objects.get(id=pk)
            
            # Обновляем метаданные плана
            if 'name' in request.data:
                floorplan.name = request.data['name']
            if 'width' in request.data:
                floorplan.width = float(request.data['width'])
            if 'height' in request.data:
                floorplan.height = float(request.data['height'])
            if 'pixel_to_m_in_square' in request.data:
                floorplan.pixel_to_m_in_square = float(request.data['pixel_to_m_in_square'])
            if 'square_of_habitation' in request.data:
                floorplan.square_of_habitation = float(request.data['square_of_habitation'])
            
            # Опционально: замена изображения
            new_image = request.FILES.get('image')
            if new_image:
                if floorplan.img and os.path.isfile(floorplan.img.path):
                    os.remove(floorplan.img.path)
                _, ext = os.path.splitext(new_image.name)
                new_image.name = f"{uuid.uuid4().hex}{ext.lower()}"
                floorplan.img = new_image
            
            floorplan.save()
            
            # Обрабатываем аннотации
            annotations_json = request.data.get('data')
            if annotations_json:
                annotations = json.loads(annotations_json) if isinstance(annotations_json, str) else annotations_json
                
                # === КОМНАТЫ ===
                existing_rooms = {r.id: r for r in Room.objects.filter(floorplan_id=floorplan)}
                received_room_ids = set()
                frontend_to_backend_room_id = {}  # маппинг frontend_id -> backend_id
                
                for room_data in annotations.get('rooms', []):
                    room_type = RoomType.objects.filter(id=room_data.get('type')).first()
                    if not room_type:
                        continue
                    
                    bbox = room_data.get('bbox', [0]*4)
                    frontend_id = room_data.get('id')
                    
                    if frontend_id and frontend_id in existing_rooms:
                        # Обновляем существующую комнату
                        room = existing_rooms[frontend_id]
                        room.room_type_id = room_type
                        room.min_x = float(bbox[0])
                        room.max_x = float(bbox[1])
                        room.min_y = float(bbox[2])
                        room.max_y = float(bbox[3])
                        room.square = float(room_data.get('realArea', 0))
                        room.save()
                        received_room_ids.add(frontend_id)
                        frontend_to_backend_room_id[frontend_id] = room.id
                    else:
                        # Создаём новую комнату
                        room = Room.objects.create(
                            floorplan_id=floorplan,
                            room_type_id=room_type,
                            min_x=float(bbox[0]),
                            max_x=float(bbox[1]),
                            min_y=float(bbox[2]),
                            max_y=float(bbox[3]),
                            square=float(room_data.get('realArea', 0))
                        )
                        if frontend_id:
                            frontend_to_backend_room_id[frontend_id] = room.id
                
                # Удаляем комнаты, которых нет в переданном списке
                rooms_to_delete = [rid for rid in existing_rooms.keys() if rid not in received_room_ids]
                if rooms_to_delete:
                    Furniture.objects.filter(room_id__in=rooms_to_delete).delete()
                    Room.objects.filter(id__in=rooms_to_delete).delete()
                
                # === СТЕНЫ ===
                existing_walls = {w.id: w for w in ConstructElement.objects.filter(floorplan_id=floorplan)}
                received_wall_ids = set()
                
                for wall_data in annotations.get('walls', []):
                    ct = ConstructElementType.objects.filter(id=wall_data.get('type')).first()
                    if not ct:
                        continue
                    
                    bbox = wall_data.get('bbox', [0]*4)
                    frontend_id = wall_data.get('id')
                    
                    if frontend_id and frontend_id in existing_walls:
                        wall = existing_walls[frontend_id]
                        wall.construct_element_type_id = ct
                        wall.min_x = float(bbox[0])
                        wall.max_x = float(bbox[1])
                        wall.min_y = float(bbox[2])
                        wall.max_y = float(bbox[3])
                        wall.save()
                        received_wall_ids.add(frontend_id)
                    else:
                        ConstructElement.objects.create(
                            floorplan_id=floorplan,
                            construct_element_type_id=ct,
                            min_x=float(bbox[0]),
                            max_x=float(bbox[1]),
                            min_y=float(bbox[2]),
                            max_y=float(bbox[3])
                        )
                
                walls_to_delete = [wid for wid in existing_walls.keys() if wid not in received_wall_ids]
                if walls_to_delete:
                    ConstructElement.objects.filter(id__in=walls_to_delete).delete()
                
                # === МЕБЕЛЬ ===
                all_rooms = {r.id: r for r in Room.objects.filter(floorplan_id=floorplan)}
                existing_furniture = {f.id: f for f in Furniture.objects.filter(room_id__in=all_rooms.keys())}
                received_furniture_ids = set()
                
                for furn_data in annotations.get('furniture', []):
                    ft = FurnitureType.objects.filter(id=furn_data.get('type')).first()
                    if not ft:
                        continue
                    
                    bbox = furn_data.get('bbox', [0]*4)
                    frontend_id = furn_data.get('id')
                    
                    # Определяем комнату для мебели по room_id
                    room = None
                    frontend_room_id = furn_data.get('room_id')
                    if frontend_room_id and frontend_room_id in frontend_to_backend_room_id:
                        backend_room_id = frontend_to_backend_room_id[frontend_room_id]
                        room = all_rooms.get(backend_room_id)
                    
                    if frontend_id and frontend_id in existing_furniture:
                        # Обновляем существующую мебель
                        furn = existing_furniture[frontend_id]
                        furn.furniture_type_id = ft
                        furn.room_id = room
                        furn.min_x = float(bbox[0])
                        furn.max_x = float(bbox[1])
                        furn.min_y = float(bbox[2])
                        furn.max_y = float(bbox[3])
                        furn.save()
                        received_furniture_ids.add(frontend_id)
                    else:
                        # Создаём новую мебель
                        Furniture.objects.create(
                            furniture_type_id=ft,
                            room_id=room,
                            min_x=float(bbox[0]),
                            max_x=float(bbox[1]),
                            min_y=float(bbox[2]),
                            max_y=float(bbox[3])
                        )
                
                furniture_to_delete = [fid for fid in existing_furniture.keys() if fid not in received_furniture_ids]
                if furniture_to_delete:
                    Furniture.objects.filter(id__in=furniture_to_delete).delete()
            
            return Response({
                'message': 'План обновлён',
                'floorplan_id': floorplan.id
            }, status=200)
            
        except Floorplan.DoesNotExist:
            return Response({'error': 'План не найден'}, status=404)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=500)
    
    # 🔸 DELETE — удалить план + все связанные данные + файл изображения
    def delete(self, request, pk):
        try:
                floorplan = Floorplan.objects.get(id=pk)
                rooms = Room.objects.filter(floorplan_id=floorplan)
                for room in rooms:
                    Furniture.objects.filter(room_id=room).delete()
                rooms.delete()
                ConstructElement.objects.filter(floorplan_id=floorplan).delete()
                
                if floorplan.img and os.path.isfile(floorplan.img.path):
                    os.remove(floorplan.img.path)
                floorplan.delete()
                
                return Response({'message': 'План успешно удалён'}, status=200)
                
        except Floorplan.DoesNotExist:
            return Response({'error': 'План не найден'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

class GetScecialMethods(BaseAPIView):
    @swagger_auto_schema(
    operation_summary="Получение специальных методов",
    operation_description="Возвращает список доступных специальных методов",
    responses={
            200: openapi.Response(
                description="Список методов",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(  # ← вместо auto_Schema
                        type=openapi.TYPE_OBJECT,  # ← убран лишний openapi.openapi
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),  # ← добавлена запятая
                            'name': openapi.Schema(type=openapi.TYPE_STRING),
                            'inputType': openapi.Schema(type=openapi.TYPE_STRING)
                        }
                    )
                )
            )
        }
    )
    def get(self, request):
        try:
            methods = SpecialMethods.objects.all().order_by('id')
            data =[]
            for m in methods:
                data.append(
                    {
                        "id":m.id,
                        'name':m.name,
                        'inputType':m.inputType
                    }
                )
            return Response(data, status=200)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

PARAMETER_ITEM_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
        'varName': openapi.Schema(type=openapi.TYPE_STRING),
        'label': openapi.Schema(type=openapi.TYPE_STRING),
        'cryteria_id': openapi.Schema(type=openapi.TYPE_INTEGER),
        'inputType': openapi.Schema(type=openapi.TYPE_STRING),
        'type': openapi.Schema(type=openapi.TYPE_STRING),
        'paramType': openapi.Schema(type=openapi.TYPE_STRING),
        'roomTypeIds': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_INTEGER)),
        'minVal': openapi.Schema(type=openapi.TYPE_NUMBER, format='float'),
        'maxVal': openapi.Schema(type=openapi.TYPE_NUMBER, format='float'),
        'methodId': openapi.Schema(type=openapi.TYPE_INTEGER),
        'methodName': openapi.Schema(type=openapi.TYPE_STRING),
        'methodType': openapi.Schema(type=openapi.TYPE_STRING),
        'room_type_id': openapi.Schema(type=openapi.TYPE_INTEGER),
        'furniture_type_id': openapi.Schema(type=openapi.TYPE_INTEGER),
    }
)

PARAMETER_REQUEST_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['varName', 'inputType'],
    properties={
        'varName': openapi.Schema(type=openapi.TYPE_STRING),
        'label': openapi.Schema(type=openapi.TYPE_STRING),
        'cryteria_id': openapi.Schema(type=openapi.TYPE_INTEGER),
        'inputType': openapi.Schema(type=openapi.TYPE_STRING),
        'paramType': openapi.Schema(type=openapi.TYPE_STRING),
        'room_type_ids': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_INTEGER)),
        'minVal': openapi.Schema(type=openapi.TYPE_NUMBER, format='float'),
        'maxVal': openapi.Schema(type=openapi.TYPE_NUMBER, format='float'),
        'methodId': openapi.Schema(type=openapi.TYPE_INTEGER),
        'room_type_id': openapi.Schema(type=openapi.TYPE_INTEGER),
        'furniture_type_id': openapi.Schema(type=openapi.TYPE_INTEGER),
        'methodName': openapi.Schema(type=openapi.TYPE_STRING),
        'methodType': openapi.Schema(type=openapi.TYPE_STRING),
    }
)

def _serialize_param_dict(param, p_type):
    """Единая сериализация параметра в dict"""
    fp = param.formula_param
    base = {
        'id': param.id,
        'varName': fp.name,
        'label': fp.label or '',
        'cryteria_id': fp.cryteria_id_id,
        'inputType': 'manual' if p_type == 'user' else 'auto',
        'type': 'UserInputParam' if p_type == 'user' else 'AutoCountingParam',
        'isActive': fp.is_active, 
    }
    if p_type == 'user':
        room_ids = list(param.userinputparamroomtype_set.values_list('room_type_id', flat=True))
        base.update({
            'paramType': param.type,
            'roomTypeIds': room_ids,
            'minVal': float(param.min_value) if param.min_value is not None else None,
            'maxVal': float(param.max_value) if param.max_value is not None else None,
            'methodId': None, 'methodName': None, 'methodType': None,
            'room_type_id': None, 'furniture_type_id': None,
        })
    else:
        # 🔍 Безопасное извлечение связанных объектов
        sm = param.special_methods
        acp = param.acpusings_set.first()
        print('==============================')
        print(sm.name)
        print('==============================')
        # Если sm == None, значит в БД special_methods_id действительно NULL
        # или связь не была подгружена запросом
        if sm is None:
            # Для отладки: раскомментируйте, чтобы увидеть ID проблемной записи
            # print(f"⚠️ AutoCountingParam {param.id} имеет special_methods_id={param.special_methods_id}")
            pass

        base.update({
            'paramType': None,
            'roomTypeIds': [],
            'minVal': None, 'maxVal': None,
            'methodId': sm.id if sm else None,
            'methodName': sm.name if sm else None,  # ✅ Вернёт None, если sm отсутствует
            'methodType': sm.inputType if sm else None,
            'room_type_id': acp.room_type_id if acp else None,
            'furniture_type_id': acp.furniture_type_id if acp else None,
        })
    return base

class ParameterListView(BaseAPIView):
    @swagger_auto_schema(
        operation_summary="Получение списка параметров",
        operation_description="Возвращает объединенный список параметров",
        responses={200: openapi.Response(description='Список', schema=openapi.Schema(type=openapi.TYPE_ARRAY, items=PARAMETER_ITEM_SCHEMA))}
    )
    def get(self, request):
        try:
            criteria_id = request.query_params.get('criteria_id')
            q_filter = Q(formula_param__cryteria_id_id=criteria_id) | \
                       Q(formula_param__cryteria_id__isnull=True)

            user_params = UserInputParam.objects.select_related('formula_param') \
                .prefetch_related('userinputparamroomtype_set').filter(q_filter)
                
            auto_params = AutoCountingParam.objects.select_related('formula_param', 'special_methods') \
                .prefetch_related('acpusings_set').filter(q_filter)

            data = [_serialize_param_dict(p, 'user') for p in user_params]
            data += [_serialize_param_dict(p, 'auto') for p in auto_params]

            return Response(data, status=200)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

    @swagger_auto_schema(
        operation_summary="Создание нового параметра",
        request_body=PARAMETER_REQUEST_SCHEMA,
        responses={201: openapi.Response(description='Создано', schema=PARAMETER_ITEM_SCHEMA)}
    )
    def post(self, request):
        try:
            data = request.data
            if not data.get('varName'):
                return Response({'error': 'Поле varName обязательно'}, status=400)

            input_type = data.get('inputType')
            if input_type not in ('manual', 'auto'):
                return Response({'error': 'Неверный inputType'}, status=400)

            cryteria_id = data.get('cryteria_id')
            if cryteria_id == 0: 
                cryteria_id = None

            fp = FormulaParam.objects.create(
                name=data.get('varName'),
                label=data.get('label', ''),
                cryteria_id_id=cryteria_id,
                is_active=data.get('isActive', False)
            )

            if input_type == 'manual':
                param_type = data.get('paramType', 'global')
                if param_type == 'rooms' and not data.get('room_type_ids'):
                    return Response({'error': 'Для типа rooms укажите room_type_ids'}, status=400)

                param = UserInputParam.objects.create(
                    formula_param=fp,
                    min_value=data.get('minVal'),
                    max_value=data.get('maxVal'),
                    type=param_type
                )

                if param_type == 'rooms':
                    room_ids = data.get('room_type_ids', []) or []
                    UserInputParamRoomType.objects.bulk_create([
                        UserInputParamRoomType(user_input_param=param, room_type_id=rid) for rid in room_ids
                    ])
                p_type = 'user'
            else:
                method_id = data.get('methodId')
                if not method_id:
                    return Response({'error': 'Для auto укажите methodId'}, status=400)

                param = AutoCountingParam.objects.create(
                    formula_param=fp,
                    special_methods_id=method_id
                )
                p_type = 'auto'

                # ✅ ИСПРАВЛЕНО: передаем ID напрямую (можно None)
                room_id = data.get('room_type_id')
                furn_id = data.get('furniture_type_id')
                
                ACPUsings.objects.create(
                    acp=param,
                    room_type_id=room_id,
                    furniture_type_id=furn_id
                )

            return Response(_serialize_param_dict(param, p_type), status=201)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

class ParameterDetailView(BaseAPIView):
    def _get_param(self, pk):
        try:
            p = UserInputParam.objects.select_related('formula_param') \
                .prefetch_related('userinputparamroomtype_set').get(id=pk)
            return p, 'user'
        except UserInputParam.DoesNotExist:
            pass
        try:
            p = AutoCountingParam.objects.select_related('formula_param', 'special_methods') \
                .prefetch_related('acpusings_set').get(id=pk)
            return p, 'auto'
        except AutoCountingParam.DoesNotExist:
            return None, None

    @swagger_auto_schema(
        operation_summary="Получение параметра по ID",
        responses={200: openapi.Response(description='Параметр', schema=PARAMETER_ITEM_SCHEMA), 404: openapi.Response(description='Не найден')}
    )
    def get(self, request, pk):
        try:
            param, p_type = self._get_param(pk)
            if not param:
                return Response({'error': 'Параметр не найден'}, status=404)
            return Response(_serialize_param_dict(param, p_type), status=200)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

    @swagger_auto_schema(
        operation_summary="Обновление параметра",
        request_body=PARAMETER_REQUEST_SCHEMA,
        responses={200: openapi.Response(description='Обновлено', schema=PARAMETER_ITEM_SCHEMA), 400: openapi.Response(description='Ошибка'), 404: openapi.Response(description='Не найден')}
    )
    def put(self, request, pk):
            try:
                param, current_type = self._get_param(pk)
                if not param:
                    return Response({'error': 'Параметр не найден'}, status=404)

                data = request.data
                input_type = data.get('inputType') or ('manual' if current_type == 'user' else 'auto')
                fp = param.formula_param
                fp.name = data.get('varName', fp.name)
                fp.label = data.get('label', fp.label)
                fp.cryteria_id_id = data.get('cryteria_id', fp.cryteria_id_id)
                fp.is_active = data.get('isActive', fp.is_active)
                fp.save()

                type_changed = (current_type == 'user' and input_type == 'auto') or \
                                (current_type == 'auto' and input_type == 'manual')

                if type_changed:
                    if current_type == 'user':
                        param.userinputparamroomtype_set.all().delete()
                    elif current_type == 'auto':
                        param.acpusings_set.all().delete()
                    param.delete()

                    if input_type == 'manual':
                        param_type = data.get('paramType', 'global')
                        if param_type == 'rooms' and not data.get('room_type_ids'):
                            return Response({'error': 'Укажите комнаты'}, status=400)

                        new_param = UserInputParam.objects.create(
                            formula_param=fp,
                            min_value=data.get('minVal'),
                            max_value=data.get('maxVal'),
                            type=param_type
                        )
                        if param_type == 'rooms':
                            room_ids = data.get('room_type_ids', []) or []
                            UserInputParamRoomType.objects.bulk_create([
                                UserInputParamRoomType(user_input_param=new_param, room_type_id=rid) for rid in room_ids
                            ])
                        new_type = 'user'
                    else:
                        method_id = data.get('methodId')
                        if not method_id: return Response({'error': 'Укажите methodId'}, status=400)
                        
                        new_param = AutoCountingParam.objects.create(
                            formula_param=fp, special_methods_id=method_id
                        )
                        new_type = 'auto'
                        
                        r_id = data.get('room_type_id')
                        f_id = data.get('furniture_type_id')
                        
                        ACPUsings.objects.create(
                            acp=new_param,
                            room_type_id=r_id,
                            furniture_type_id=f_id
                        )

                    return Response(_serialize_param_dict(new_param, new_type), status=200)

                else:
                    if input_type == 'manual':
                        param.min_value = data.get('minVal', param.min_value)
                        param.max_value = data.get('maxVal', param.max_value)
                        new_ptype = data.get('paramType', param.type)
                        param.type = new_ptype
                        param.save()

                        if new_ptype == 'rooms':
                            new_ids = set(data.get('room_type_ids', []) or [])
                            current_ids = set(param.userinputparamroomtype_set.values_list('room_type_id', flat=True))
                            to_del = current_ids - new_ids
                            to_add = new_ids - current_ids

                            if to_del: param.userinputparamroomtype_set.filter(room_type_id__in=to_del).delete()
                            if to_add:
                                UserInputParamRoomType.objects.bulk_create([
                                    UserInputParamRoomType(user_input_param=param, room_type_id=rid) for rid in to_add
                                ])
                        else:
                            param.userinputparamroomtype_set.all().delete()

                    else: # auto
                        if data.get('methodId') is not None:
                            param.special_methods_id = data['methodId']
                        param.save()

                        acp = param.acpusings_set.first()
                        r_id = data.get('room_type_id')
                        f_id = data.get('furniture_type_id')

                        if acp:
                            acp.room_type_id = r_id
                            acp.furniture_type_id = f_id
                            acp.save()
                        elif r_id or f_id:
                            ACPUsings.objects.create(
                                acp=param,
                                room_type_id=r_id,
                                furniture_type_id=f_id
                            )

                return Response(_serialize_param_dict(param, current_type), status=200)
            except Exception as e:
                return Response({'error': str(e)}, status=500)

    @swagger_auto_schema(
        operation_summary="Удаление параметра",
        responses={204: openapi.Response(description='Успешно удалено'), 404: openapi.Response(description='Не найден')}
    )
    def delete(self, request, pk):
        try:
            param, p_type = self._get_param(pk)
            if not param:
                return Response({'error': 'Параметр не найден'}, status=404)

            if p_type == 'user':
                param.userinputparamroomtype_set.all().delete()
            elif p_type == 'auto':
                param.acpusings_set.all().delete()

            fp_id = param.formula_param_id
            param.delete()
            FormulaParam.objects.filter(id=fp_id).delete()

            return Response(status=204)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

LIMIT_ITEM_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
        'symbol': openapi.Schema(type=openapi.TYPE_STRING),
        'label': openapi.Schema(type=openapi.TYPE_STRING),
        'type': openapi.Schema(type=openapi.TYPE_STRING),
        'cryteria_id': openapi.Schema(type=openapi.TYPE_INTEGER),
        'universalValue': openapi.Schema(type=openapi.TYPE_NUMBER, format='float'),
        'roomValues': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'roomId': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'value': openapi.Schema(type=openapi.TYPE_NUMBER, format='float')
                }
            )
        )
    }
)

LIMIT_REQUEST_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'symbol': openapi.Schema(type=openapi.TYPE_STRING),
        'label': openapi.Schema(type=openapi.TYPE_STRING),
        'cryteria_id': openapi.Schema(type=openapi.TYPE_INTEGER),
        'type': openapi.Schema(type=openapi.TYPE_STRING),
        'universalValue': openapi.Schema(type=openapi.TYPE_NUMBER),
        'roomValues': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'roomId': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'value': openapi.Schema(type=openapi.TYPE_NUMBER)
                }
            )
        )
    }
)

def _serialize_limit(limit_param):
    fp = limit_param.formula_param

    ulp = limit_param.universallimitparam_set.first()
    is_universal = ulp is not None

    base = {
        'id': limit_param.id,
        'symbol': fp.name,
        'label': fp.label or '',
        'type': 'universal' if is_universal else 'byRoom',
        'universalValue': float(ulp.value) if is_universal else None,
        'cryteria_id':fp.cryteria_id_id,
        'isActive': fp.is_active,
        'roomValues': []
    }

    for rlp in limit_param.roomslimitparam_set.select_related('room_type').all():
        base['roomValues'].append({
            'roomId': rlp.room_type_id,
            'value': float(rlp.value)
        })

    return base

class LimitParamListView(BaseAPIView):
    @swagger_auto_schema(
        operation_summary="Список ограничений",
        responses={200: openapi.Response(description='Список', schema=openapi.Schema(type=openapi.TYPE_ARRAY, items=LIMIT_ITEM_SCHEMA))}
    )
    def get(self, request):
        try:
            criteria_id = request.query_params.get('criteria_id')
            q_filter = Q(formula_param__cryteria_id_id=criteria_id) | \
                           Q(formula_param__cryteria_id__isnull=True)

            limits = LimitParam.objects.select_related('formula_param') \
                .prefetch_related('roomslimitparam_set__room_type') \
                .filter(q_filter)

            data = [_serialize_limit(lp) for lp in limits]
            return Response(data, status=200)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

    @swagger_auto_schema(
        operation_summary="Создание ограничения",
        request_body=LIMIT_REQUEST_SCHEMA,
        responses={201: LIMIT_ITEM_SCHEMA}
    )
    def post(self, request):
        try:
            data = request.data
            if not data.get('symbol'):
                return Response({'error': 'Поле symbol обязательно'}, status=400)

            limit_type = data.get('type', 'universal')
            cryteria_id = data.get('cryteria_id')
            
            # 1. Создаем FormulaParam (symbol -> name)
            fp = FormulaParam.objects.create(
                name=data['symbol'],
                label=data.get('label', ''),
                cryteria_id_id=cryteria_id if cryteria_id != 0 else None,
                is_active=data.get('isActive', False)
            )

            # 2. Создаем LimitParam
            lp = LimitParam.objects.create(formula_param=fp)

            # 3. Создаем значения
            if limit_type == 'universal':
                val = data.get('universalValue')
                if val is None: 
                    return Response({'error': 'Укажите universalValue'}, status=400)
                UniversalLimitParam.objects.create(limit_param=lp, value=float(val))
            else:
                room_vals = data.get('roomValues', [])
                if not room_vals: 
                    return Response({'error': 'Укажите roomValues'}, status=400)
                RoomsLimitParam.objects.bulk_create([
                    RoomsLimitParam(limit_param=lp, room_type_id=rv['roomId'], value=float(rv['value']))
                    for rv in room_vals
                ])

            return Response(_serialize_limit(lp), status=201)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

class LimitParamDetailView(BaseAPIView):
    def _get_limit(self, pk):
        try:
            return LimitParam.objects.select_related('formula_param') \
                .prefetch_related('roomslimitparam_set__room_type').get(id=pk)
        except LimitParam.DoesNotExist:
            return None

    @swagger_auto_schema(
        operation_summary="Получение ограничения",
        responses={200: LIMIT_ITEM_SCHEMA, 404: 'Не найдено'}
    )
    def get(self, request, pk):
        try:
            lp = self._get_limit(pk)
            if not lp: 
                return Response({'error': 'Не найдено'}, status=404)
            return Response(_serialize_limit(lp), status=200)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

    @swagger_auto_schema(
        operation_summary="Обновление ограничения",
        request_body=LIMIT_REQUEST_SCHEMA,
        responses={200: LIMIT_ITEM_SCHEMA, 400: 'Ошибка'}
    )
    def put(self, request, pk):
        try:
            lp = self._get_limit(pk)
            if not lp: 
                return Response({'error': 'Не найдено'}, status=404)

            data = request.data
            limit_type = data.get('type') or ('universal' if hasattr(lp, 'universallimitparam') else 'byRoom')
            
            fp = lp.formula_param
            fp.name = data.get('symbol', fp.name)
            fp.label = data.get('label', fp.label)
            fp.cryteria_id_id = data.get('cryteria_id', fp.cryteria_id_id)
            fp.is_active = data.get('isActive', fp.is_active)
            fp.save()
            lp.universallimitparam_set.all().delete()
            lp.roomslimitparam_set.all().delete()
            
            if limit_type == 'universal':
                UniversalLimitParam.objects.create(limit_param=lp, value=float(data['universalValue']))
            else:
                RoomsLimitParam.objects.bulk_create([
                    RoomsLimitParam(limit_param=lp, room_type_id=rv['roomId'], value=float(rv['value']))
                    for rv in data.get('roomValues', [])
                ])

            return Response(_serialize_limit(lp), status=200)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

    def delete(self, request, pk):
        try:
            lp = self._get_limit(pk)
            if not lp: 
                return Response({'error': 'Не найдено'}, status=404)

            fp_id = lp.formula_param_id
            lp.delete()
            FormulaParam.objects.filter(id=fp_id).delete()
            
            return Response(status=204)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

FORMULA_ITEM_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
        'objType': openapi.Schema(type=openapi.TYPE_STRING, enum=['single', 'system']),
        'criterion_id': openapi.Schema(type=openapi.TYPE_INTEGER),  
        'type': openapi.Schema(type=openapi.TYPE_STRING, enum=['global', 'rooms']),  # ✅ Единое поле для обоих типов
        # --- Для objType: single ---
        'equation': openapi.Schema(type=openapi.TYPE_STRING),
        'recommendation': openapi.Schema(type=openapi.TYPE_STRING),
        'value_recomm': openapi.Schema(type=openapi.TYPE_NUMBER, format='float'),
        # --- Для objType: system ---
        'equations': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'limit_equastion': openapi.Schema(type=openapi.TYPE_STRING),
                    'equastion': openapi.Schema(type=openapi.TYPE_STRING),
                    'recommendation': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )
        ),
        # --- Общие ссылки ---
        'for_room_types_ids': openapi.Schema(
            type=openapi.TYPE_ARRAY, 
            items=openapi.Schema(type=openapi.TYPE_INTEGER)
        ),
        'used_input_ids': openapi.Schema(
            type=openapi.TYPE_ARRAY, 
            items=openapi.Schema(type=openapi.TYPE_INTEGER)
        ),
        'used_acp_ids': openapi.Schema(
            type=openapi.TYPE_ARRAY, 
            items=openapi.Schema(type=openapi.TYPE_INTEGER)
        ),
        'used_limit_ids': openapi.Schema(
            type=openapi.TYPE_ARRAY, 
            items=openapi.Schema(type=openapi.TYPE_INTEGER)
        ),
    }
)

FORMULA_REQUEST_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['objType'],
    properties={
        'objType': openapi.Schema(type=openapi.TYPE_STRING, enum=['single', 'system']),
        'criterion_id': openapi.Schema(type=openapi.TYPE_INTEGER),
        'equation': openapi.Schema(type=openapi.TYPE_STRING),
        'type': openapi.Schema(type=openapi.TYPE_STRING, enum=['global', 'rooms']),
        'recommendation': openapi.Schema(type=openapi.TYPE_STRING),
        'value_recomm': openapi.Schema(type=openapi.TYPE_NUMBER),
        'equations': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                required=['limit_equastion', 'equastion'],
                properties={
                    'limit_equastion': openapi.Schema(type=openapi.TYPE_STRING),
                    'equastion': openapi.Schema(type=openapi.TYPE_STRING),
                    'recommendation': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )
        ),
        'for_room_types_ids': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_INTEGER)),
        'used_input_ids': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_INTEGER)),
        'used_acp_ids': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_INTEGER)),
        'used_limit_ids': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_INTEGER)),
    }
)

def _serialize_common_formula(cf):
    return {
        'id': cf.id,
        'objType': 'single',
        'name': cf.name or '',  
        'isActive': cf.is_active, 
        'criterion_id': cf.criterion_id,
        'equation': cf.formula.equation,
        'type': cf.type,
        'recommendation': cf.recommendation,
        'value_recomm': cf.value_recomm,
        'for_room_types_ids': list(cf.commonformularoomtypes_set.values_list('roomtype_id', flat=True)),
        'used_input_ids': list(cf.commonformulainputparam_set.values_list('user_input_param_id', flat=True)),
        'used_acp_ids': list(cf.commonformulaacp_set.values_list('acp_id', flat=True))
    }

def _serialize_system(sys_obj):
    """Сериализация системы уравнений"""
    
    # Собираем все лимиты (и universal, и rooms)
    limit_ids = []
    
    # Universal-лимиты
    universal_links = SystemEquastionUniversalLimitParam.objects.filter(
        sys_equastion=sys_obj
    ).values_list('universal_limit_param__limit_param_id', flat=True)
    limit_ids.extend(list(universal_links))
    
    # Rooms-лимиты
    rooms_links = SystemEquastionRoomsLimitParam.objects.filter(
        system_equastion=sys_obj
    ).values_list('rooms_limit_param__limit_param_id', flat=True)
    limit_ids.extend(list(rooms_links))
    
    # Убираем дубликаты
    limit_ids = list(set(limit_ids))
    
    # Собираем уравнения
    equations = []
    for eq_link in EquastionOfSystemEquastion.objects.filter(system_equastion=sys_obj).select_related('formula'):
        equations.append({
            'limit_equastion': eq_link.limit_equastion,
            'equastion': eq_link.formula.equation,
            'recommendation': eq_link.recommendation
        })
    
    # Собираем комнаты
    room_type_ids = list(
        SysEquastRoomType.objects.filter(system_equastion=sys_obj)
        .values_list('room_type_id', flat=True)
    )
    
    # ✅ ИСПРАВЛЕНО: правильные related_name и имена полей
    # Модель: SystemEquastionUserInputParam, поле: useR_input_param
    input_ids = list(
        sys_obj.systemequastionuserinputparam_set.values_list('useR_input_param_id', flat=True)
    )
    
    # Модель: SystemEquastionUserACP, поле: acp
    acp_ids = list(
        sys_obj.systemequastionuseracp_set.values_list('acp_id', flat=True)
    )
    
    return {
        'id': sys_obj.id,
        'objType': 'system',
        'name': sys_obj.name or '',
        'isActive': sys_obj.is_active, 
        'type': sys_obj.type,
        'criterion_id': sys_obj.criterion_id,
        'equations': equations,
        'for_room_types_ids': room_type_ids,
        'used_input_ids': input_ids,
        'used_acp_ids': acp_ids,
        'used_limit_ids': limit_ids,
    }


def _create_param_links(target, input_ids, acp_ids, is_system=False):
    if is_system:
        SystemEquastionUserInputParam.objects.bulk_create([
            SystemEquastionUserInputParam(sys_equ=target, useR_input_param_id=iid) for iid in input_ids
        ])
        SystemEquastionUserACP.objects.bulk_create([
            SystemEquastionUserACP(sys_equ=target, acp_id=aid) for aid in acp_ids
        ])
    else:
        CommonFormulaInputParam.objects.bulk_create([
            CommonFormulaInputParam(commonformula=target, user_input_param_id=iid) for iid in input_ids
        ])
        CommonFormulaAcp.objects.bulk_create([
            CommonFormulaAcp(commonformula=target, acp_id=aid) for aid in acp_ids
        ])

def _delete_param_links(target, is_system=False):
    if is_system:
        SystemEquastionUserInputParam.objects.filter(sys_equ=target).delete()
        SystemEquastionUserACP.objects.filter(sys_equ=target).delete()
    else:
        CommonFormulaInputParam.objects.filter(commonformula=target).delete()
        CommonFormulaAcp.objects.filter(commonformula=target).delete()


class FormulaListView(BaseAPIView):
    @swagger_auto_schema(operation_summary="Список формул и систем", 
                         manual_parameters=[openapi.Parameter('criterion_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER)],
                         responses={200: FORMULA_ITEM_SCHEMA})
    def get(self, request):
        try:
            # ✅ Получаем criterion_id из любого формата отправки
            criterion_id = (
                request.query_params.get('criterion_id') or 
                request.query_params.get('params[criterion_id]')
            )
            
            singles_qs = CommonFormula.objects.select_related('formula').prefetch_related('commonformularoomtypes_set')
            systems_qs = SystemEquastion.objects.prefetch_related(
                'equastionofsystemequastion_set__formula',
                'systemequastionroomslimitparam_set',
                'systemequastionuniversallimitparam_set',
                'sysequastroomtype_set' 
            )
            
            # ✅ Фильтрация только если criterion_id передан и валиден
            if criterion_id:
                try:
                    criterion_id = int(criterion_id)  # Конвертируем строку в число
                    critery = Criterion_of_ergonomy.objects.get(id=criterion_id)
                    singles_qs = singles_qs.filter(criterion=critery)
                    systems_qs = systems_qs.filter(criterion=critery)
                except ValueError:
                    return Response({'error': 'Неверный формат criterion_id'}, status=400)
                except Criterion_of_ergonomy.DoesNotExist:
                    return Response({'error': 'Критерий не найден'}, status=404)
                    
            data = [_serialize_common_formula(s) for s in singles_qs] + [_serialize_system(s) for s in systems_qs]
            return Response(data, status=200)
            
        except Exception as e:
            import logging, traceback
            logging.error(f"❌ FormulaListView GET error: {str(e)}\n{traceback.format_exc()}")
            return Response({'error': str(e)}, status=500)


    @swagger_auto_schema(operation_summary="Создание формулы или системы", request_body=FORMULA_REQUEST_SCHEMA, responses={201: FORMULA_ITEM_SCHEMA})
    def post(self, request):
        try:
            data = request.data
            criterion_id = data.get('criterion_id')
            if not criterion_id:
                return Response({'error': 'criterion_id обязателен'}, status=400)
                
            obj_type = data.get('objType', 'single')
            f_type = data.get('type', 'global')
            input_ids = data.get('used_input_ids', []) or []
            acp_ids = data.get('used_acp_ids', []) or []

            if obj_type == 'single':
                if not data.get('equation'): 
                    return Response({'error': 'Укажите equation'}, status=400)
                fp = Formula.objects.create(equation=data['equation'])
                cf = CommonFormula.objects.create(
                    formula=fp, type=f_type, criterion_id=criterion_id,
                    recommendation=data.get('recommendation'), 
                    value_recomm=data.get('value_recomm'),
                    name=data.get('name', ''),
                    is_active=data.get('isActive', False),
                )
                if f_type == 'rooms' and data.get('for_room_types_ids'):
                    CommonFormulaRoomTypes.objects.bulk_create([
                        CommonFormulaRoomTypes(commonformula=cf, roomtype_id=rid) 
                        for rid in data['for_room_types_ids']
                    ])
                _create_param_links(cf, input_ids, acp_ids, is_system=False)
                return Response(_serialize_common_formula(cf), status=201)

            else:  # system
                equations = data.get('equations', [])
                if not equations: 
                    return Response({'error': 'Добавьте хотя бы одно уравнение'}, status=400)
                
                sys_type = data.get('type', 'house')
                sys_obj = SystemEquastion.objects.create(type=sys_type, 
                criterion_id=criterion_id,
                name=data.get('name', ''),
                is_active=data.get('isActive', False))
                _create_param_links(sys_obj, input_ids, acp_ids, is_system=True)

                for eq in equations:
                    # ✅ ИСПРАВЛЕНО: в Formula.equation попадает только правая часть (equastion)
                    formula = Formula.objects.create(equation=eq.get('equastion', ''))
                    EquastionOfSystemEquastion.objects.create(
                        system_equastion=sys_obj,
                        formula=formula,
                        limit_equastion=eq.get('limit_equastion', ''),
                        recommendation=eq.get('recommendation', '')
                    )

                limit_ids = data.get('used_limit_ids', []) or []
                room_type_ids = data.get('for_room_types_ids', []) or []

                # ✅ БЕЗОПАСНЫЙ МАППИНГ ЛИМИТОВ: избегаем IntegrityError
                if limit_ids:
                    if sys_type == 'rooms':
                    # Ищем RoomsLimitParam по limit_param_id
                        room_limits = RoomsLimitParam.objects.filter(limit_param_id__in=limit_ids).select_related('limit_param')
                        
                        # Проверка: все ли переданные лимиты найдены?
                        found_ids = {rl.limit_param_id for rl in room_limits}
                        missing = set(limit_ids) - found_ids
                        if missing:
                            return Response({
                                'error': f'Не найдены ограничения по комнатам для ID: {list(missing)}'
                            }, status=400)
                        
                        # Создаём связи, используя найденные RoomsLimitParam
                        SystemEquastionRoomsLimitParam.objects.bulk_create([
                            SystemEquastionRoomsLimitParam(system_equastion=sys_obj, rooms_limit_param=rl) 
                            for rl in room_limits
                        ])
                    
                    else:  # house
                        universal_limits = UniversalLimitParam.objects.filter(limit_param_id__in=limit_ids).select_related('limit_param')
                        
                        found_ids = {ul.limit_param_id for ul in universal_limits}
                        missing = set(limit_ids) - found_ids
                        if missing:
                            return Response({
                                'error': f'Не найдены универсальные ограничения для ID: {list(missing)}'
                            }, status=400)
                        
                        SystemEquastionUniversalLimitParam.objects.bulk_create([
                            SystemEquastionUniversalLimitParam(sys_equastion=sys_obj, universal_limit_param=ul) 
                            for ul in universal_limits
                        ])

                if sys_type == 'rooms' and room_type_ids:
                    SysEquastRoomType.objects.bulk_create([
                        SysEquastRoomType(system_equastion=sys_obj, room_type_id=rid) 
                        for rid in room_type_ids
                    ])

                return Response(_serialize_system(sys_obj), status=201)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

class FormulaDetailView(BaseAPIView):
    def _get_obj(self, pk, obj_type):
        try:
            return CommonFormula.objects.select_related('formula').get(id=pk) if obj_type == 'single' else SystemEquastion.objects.get(id=pk)
        except: return None

    @swagger_auto_schema(responses={200: FORMULA_ITEM_SCHEMA, 404: 'Не найдено'})
    def get(self, request, pk):
        obj = self._get_obj(pk, 'single')
        if obj: return Response(_serialize_common_formula(obj), status=200)
        obj = self._get_obj(pk, 'system')
        if obj: return Response(_serialize_system(obj), status=200)
        return Response({'error': 'Не найдено'}, status=404)

    @swagger_auto_schema(responses={200: FORMULA_ITEM_SCHEMA, 400: 'Ошибка'})
    def put(self, request, pk):
        try:
            data = request.data
            criterion_id = data.get('criterion_id')
            if not criterion_id:
                return Response({'error': 'criterion_id обязателен'}, status=400)

            obj_type = data.get('objType', 'single')
            f_type = data.get('type', 'global')
            input_ids = data.get('used_input_ids', []) or []
            acp_ids = data.get('used_acp_ids', []) or []

            # ✅ Валидация для rooms
            if f_type == 'rooms' and not data.get('for_room_types_ids'):
                return Response({'error': 'for_room_types_ids обязателен при type=rooms'}, status=400)

            if obj_type == 'single':
                cf = self._get_obj(pk, 'single')
                if not cf: 
                    return Response({'error': 'Не найдено'}, status=404)
                
                # ✅ Полная очистка старых связей
                cf.commonformularoomtypes_set.all().delete()
                _delete_param_links(cf, is_system=False)
                
                # 📝 Обновление формулы
                cf.formula.equation = data.get('equation', cf.formula.equation)
                cf.formula.save()
                
                cf.type = f_type
                cf.criterion_id = criterion_id
                cf.recommendation = data.get('recommendation', cf.recommendation)
                cf.value_recomm = data.get('value_recomm', cf.value_recomm)
                cf.name = data.get('name', cf.name)             
                cf.is_active = data.get('isActive', cf.is_active)
                cf.save()

                # 🔗 Создание новых связей только если type == 'rooms'
                if f_type == 'rooms' and data.get('for_room_types_ids'):
                    CommonFormulaRoomTypes.objects.bulk_create([
                        CommonFormulaRoomTypes(commonformula=cf, roomtype_id=rid) 
                        for rid in data['for_room_types_ids']
                    ])
                
                _create_param_links(cf, input_ids, acp_ids, is_system=False)
                return Response(_serialize_common_formula(cf), status=200)

            else:  # system
                sys_obj = self._get_obj(pk, 'system')
                if not sys_obj: 
                    return Response({'error': 'Не найдено'}, status=404)
                
                sys_type = data.get('type', sys_obj.type)
                
                # ✅ Полная очистка ВСЕХ старых связей
                EquastionOfSystemEquastion.objects.filter(system_equastion=sys_obj).delete()
                SystemEquastionRoomsLimitParam.objects.filter(system_equastion=sys_obj).delete()
                SystemEquastionUniversalLimitParam.objects.filter(sys_equastion=sys_obj).delete()
                SysEquastRoomType.objects.filter(system_equastion=sys_obj).delete()
                _delete_param_links(sys_obj, is_system=True)
                
                # 📝 Обновление системы
                sys_obj.type = sys_type
                sys_obj.criterion_id = criterion_id
                sys_obj.name = data.get('name', sys_obj.name)         
                sys_obj.is_active = data.get('isActive', sys_obj.is_active)
                sys_obj.save()

                # 📝 Создание новых уравнений
                equations = data.get('equations', [])
                if not equations:
                    return Response({'error': 'equations не может быть пустым для system'}, status=400)
                
                for eq in equations:
                    formula = Formula.objects.create(equation=eq.get('equastion', ''))
                    EquastionOfSystemEquastion.objects.create(
                        system_equastion=sys_obj,
                        formula=formula,
                        limit_equastion=eq.get('limit_equastion', ''),
                        recommendation=eq.get('recommendation', '')
                    )

                # ✅ ДОБАВЛЕНО: Создание связей input/acp параметров
                _create_param_links(sys_obj, input_ids, acp_ids, is_system=True)

                # 🔗 Обработка лимитов
                                # 🔗 Обработка лимитов — СТРОГО по типу системы
                limit_ids = data.get('used_limit_ids', []) or []
                room_type_ids = data.get('for_room_types_ids', []) or []

                if limit_ids:
                    if sys_type == 'rooms':
                        # ✅ Для rooms: сохраняем ТОЛЬКО rooms-лимиты
                        rooms_valid_ids = list(
                            RoomsLimitParam.objects
                            .filter(limit_param_id__in=limit_ids)
                            .values_list('id', flat=True)
                        )
                        if rooms_valid_ids:
                            SystemEquastionRoomsLimitParam.objects.bulk_create([
                                SystemEquastionRoomsLimitParam(
                                    system_equastion=sys_obj, 
                                    rooms_limit_param_id=rid
                                ) 
                                for rid in rooms_valid_ids
                            ])
                        # Universal-лимиты НЕ сохраняем для rooms
                            
                    else:  # global — ТОЛЬКО universal
                        universal_valid_ids = list(
                            UniversalLimitParam.objects
                            .filter(limit_param_id__in=limit_ids)
                            .values_list('id', flat=True)
                        )
                        if universal_valid_ids:
                            SystemEquastionUniversalLimitParam.objects.bulk_create([
                                SystemEquastionUniversalLimitParam(
                                    sys_equastion=sys_obj, 
                                    universal_limit_param_id=uid
                                ) 
                                for uid in universal_valid_ids
                            ])

                # 🔗 Комнатные связи только для rooms
                if sys_type == 'rooms' and room_type_ids:
                    SysEquastRoomType.objects.bulk_create([
                        SysEquastRoomType(system_equastion=sys_obj, room_type_id=rid) 
                        for rid in room_type_ids
                    ])
                                                    
                return Response(_serialize_system(sys_obj), status=200)
                
        except Exception as e:
            return Response({'error': str(e)}, status=500)
    def delete(self, request, pk):
        """
        Корректное удаление формулы или системы уравнений с очисткой ВСЕХ связанных записей.
        Порядок важен: сначала дочерние связи, потом родительские объекты.
        """
        try:
            # ==================== УДАЛЕНИЕ ОДИНОЧНОЙ ФОРМУЛЫ ====================
            obj = self._get_obj(pk, 'single')
            if obj:
                # obj — это экземпляр CommonFormula
                
                # 1. Удаляем связи с параметрами (через вспомогательную функцию)
                _delete_param_links(obj, is_system=False)
                
                # 2. Удаляем связи с типами комнат
                CommonFormulaRoomTypes.objects.filter(commonformula=obj).delete()
                
                # 3. Сохраняем ID формулы для удаления после удаления объекта
                formula_id = obj.formula_id
                
                # 4. Удаляем саму запись CommonFormula
                obj.delete()
                
                # 5. Удаляем базовую формулу, если она больше не используется
                #    (проверяем, нет ли других ссылок на неё)
                if formula_id and not Formula.objects.filter(
                    id=formula_id
                ).exclude(  # Исключаем текущую, если она ещё не удалена
                    commonformula__isnull=False,
                    equastionofsystemequastion__isnull=False
                ).exists():
                    Formula.objects.filter(id=formula_id).delete()
                
                return Response(status=204)
            
            obj = self._get_obj(pk, 'system')
            if obj:
                # obj — это экземпляр SystemEquastion
                
                # 1. Удаляем уравнения системы и их формулы
                #    Сначала удаляем формулы, привязанные к уравнениям
                equation_ids = list(EquastionOfSystemEquastion.objects.filter(
                    system_equastion=obj
                ).values_list('formula_id', flat=True))
                
                # Удаляем связи уравнений с системой
                EquastionOfSystemEquastion.objects.filter(system_equastion=obj).delete()
                
                # Удаляем сами формулы, если они не используются в других местах
                for fid in equation_ids:
                    if fid and not Formula.objects.filter(
                        id=fid
                    ).exclude(
                        commonformula__isnull=False,
                        equastionofsystemequastion__isnull=False
                    ).exists():
                        Formula.objects.filter(id=fid).delete()
                
                # 2. Удаляем связи с параметрами пользовательского ввода
                SystemEquastionUserInputParam.objects.filter(sys_equ=obj).delete()
                
                # 3. Удаляем связи с параметрами автоподсчёта
                SystemEquastionUserACP.objects.filter(sys_equ=obj).delete()
                
                # 4. Удаляем связи с универсальными ограничениями ⭐ ИСПРАВЛЕНО
                SystemEquastionUniversalLimitParam.objects.filter(sys_equastion=obj).delete()
                
                # 5. Удаляем связи с ограничениями по комнатам ⭐ ИСПРАВЛЕНО
                SystemEquastionRoomsLimitParam.objects.filter(system_equastion=obj).delete()
                
                # 6. Удаляем связи с типами комнат
                SysEquastRoomType.objects.filter(system_equastion=obj).delete()
                
                # 7. Удаляем саму систему уравнений
                obj.delete()
                
                return Response(status=204)
            
            # Если объект не найден ни в одном из типов
            return Response({'error': 'Формула или система не найдена'}, status=404)
            
        except Exception as e:
            import logging
            logging.error(f'❌ Ошибка при удалении формулы {pk}: {str(e)}', exc_info=True)
            return Response({'error': f'Внутренняя ошибка сервера: {str(e)}'}, status=500)

CRITERION_ITEM_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
        'name': openapi.Schema(type=openapi.TYPE_STRING),
        'color':openapi.Schema(type=openapi.TYPE_STRING),
        'parameters': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'name': openapi.Schema(type=openapi.TYPE_STRING),
                    'label': openapi.Schema(type=openapi.TYPE_STRING),
                    'input_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['global', 'rooms']),
                    'min_value': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'max_value': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'room_type_ids': openapi.Schema(
                        type=openapi.TYPE_ARRAY, 
                        items=openapi.Schema(type=openapi.TYPE_INTEGER),
                        description='Заполняется только если input_type == rooms'
                    ),
                }
            )
        ),
        'questions': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'question': openapi.Schema(type=openapi.TYPE_STRING),
                    'recommendation': openapi.Schema(type=openapi.TYPE_STRING),
                    'score_for_recommendation': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'type': openapi.Schema(type=openapi.TYPE_STRING),
                    'room_type_ids': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_INTEGER),
                        description='ID типов комнат (если вопрос привязан к конкретным комнатам)'
                    ),
                    'answers': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'answer': openapi.Schema(type=openapi.TYPE_STRING),
                                'score': openapi.Schema(type=openapi.TYPE_NUMBER),
                            }
                        )
                    )
                }
            )
        ),
    }
)

class ActiveCriterionListView(BaseAPIView):
    @swagger_auto_schema(
        operation_summary="Список активных критериев с параметрами",
        responses={200: openapi.Response('Успех')}
    )
    def get(self, request):
        try:
            # ==========================================
            # 1. СБОР ОБЩИХ (ГЛОБАЛЬНЫХ) ПАРАМЕТРОВ
            # ==========================================
            # Ищем FormulaParam, которые НЕ привязаны ни к одному критерию (cryteria_id is NULL)
            global_fps = FormulaParam.objects.filter(
                cryteria_id__isnull=True
            ).prefetch_related(
                'userinputparam_set__userinputparamroomtype_set__room_type'
            )

            global_parameters = []
            for fp in global_fps:
                for uip in fp.userinputparam_set.all():
                    global_parameters.append({
                        'id': uip.id,
                        'name': fp.name,
                        'label': fp.label or fp.name,
                        'input_type': uip.type,
                        'min_value': uip.min_value,
                        'max_value': uip.max_value,
                        'room_type_ids': [
                            rel.room_type.id 
                            for rel in uip.userinputparamroomtype_set.all()
                        ],
                        'is_global': True  # 👈 Флаг для фронтенда, чтобы отличать их
                    })

            # ==========================================
            # 2. СБОР КРИТЕРИЕВ И ИХ ПАРАМЕТРОВ
            # ==========================================
            criteria = Criterion_of_ergonomy.objects.filter(
                is_active=True
            ).prefetch_related(
                'formulaparam_set__userinputparam_set__userinputparamroomtype_set__room_type',
                'form_question_set__formanswer_set',
                'form_question_set__form_question_roomtype_set__room_type_id'
            )

            criteria_result = []
            
            for crit in criteria:
                # --- СБОР ПАРАМЕТРОВ КОНКРЕТНОГО КРИТЕРИЯ ---
                parameters = []
                for fp in crit.formulaparam_set.all():
                    for uip in fp.userinputparam_set.all():
                        parameters.append({
                            'id': uip.id,
                            'name': fp.name,
                            'label': fp.label or fp.name,
                            'input_type': uip.type,
                            'min_value': uip.min_value,
                            'max_value': uip.max_value,
                            'room_type_ids': [
                                rel.room_type.id 
                                for rel in uip.userinputparamroomtype_set.all()
                            ],
                            'is_global': False # 👈 Явно указываем, что это параметр критерия
                        })

                # --- СБОР ВОПРОСОВ ---
                questions = []
                for q in crit.form_question_set.all():
                    if not q.is_active:
                        continue
                        
                    questions.append({
                        'id': q.id,
                        'question': q.question,
                        'recommendation': q.recommendation,
                        'score_for_recommendation': q.score_for_recommendation,
                        'type': q.type,
                        'room_type_ids': [
                            rel.room_type_id.id 
                            for rel in q.form_question_roomtype_set.all()
                        ],
                        'answers': [
                            {
                                'id': ans.id,
                                'answer': ans.answer,
                                'score': ans.score
                            }
                            for ans in q.formanswer_set.all()
                        ]
                    })

                criteria_result.append({
                    'id': crit.id,
                    'color': crit.color,
                    'name': crit.name,
                    'parameters': parameters,
                    'questions': questions,
                })

            # ==========================================
            # 3. ФОРМИРОВАНИЕ ИТОГОВОГО ОТВЕТА
            # ==========================================
            return Response({
                'global_parameters': global_parameters,
                'criteria': criteria_result
            }, status=200)

        except Exception as e:
            import logging, traceback
            logging.error(f"❌ ActiveCriterionListView GET error: {str(e)}\n{traceback.format_exc()}")
            return Response({'error': 'Внутренняя ошибка сервера', 'details': str(e)}, status=500)

class TestView(BaseAPIView):
    @swagger_auto_schema(
        operation_summary="Вызов специального метода по ID",
        manual_parameters=[
            openapi.Parameter('room_type_id', openapi.IN_QUERY, description="ID типа комнаты (если требуется методом)", type=openapi.TYPE_INTEGER),
            openapi.Parameter('furniture_type_id', openapi.IN_QUERY, description="ID типа мебели (если требуется методом)", type=openapi.TYPE_INTEGER),
        ],
        responses={
            200: openapi.Response('Успех'),
            404: openapi.Response('Метод или план не найдены'),
            500: openapi.Response('Ошибка выполнения')
        }
    )
    def get(self, request, id: int = None, floorplan_id: int = None):
        # ─ 0. Определяем, откуда брать метод: из БД (по id) или по имени напрямую ──
        method_name = None
        input_type = None

        if id is not None:
            # Режим 1: через запись в БД
            try:
                special_method = AutoCountingMethod.objects.get(id=id)
            except AutoCountingMethod.DoesNotExist:
                return Response(
                    {"error": f"SpecialMethod с id={id} не найден"},
                    status=404
                )
            method_name = special_method.name
            input_type = special_method.inputType
        # ── 1. Находим класс метода в модуле special_methods ──
        try:
            method_class = getattr(special_methods, method_name)
        except AttributeError:
            return Response(
                {"error": f"Класс '{method_name}' не найден в модуле special_methods"},
                status=404
            )

        # ── 2. Инстанциируем ──
        try:
            instance = method_class()
        except TypeError as e:
            return Response(
                {"error": f"Не удалось создать экземпляр '{method_name}': {str(e)}"},
                status=500
            )

        # ── 3. Вызываем get(...) с нужными аргументами ──
        try:
            if input_type == 'nothing':
                result = instance.get(floorplan_id=floorplan_id)

            elif input_type == 'rooms':
                room_type_id = request.query_params.get('room_type_id')
                if not room_type_id:
                    return Response(
                        {"error": "Для input_type='rooms' необходим параметр room_type_id"},
                        status=400
                    )
                result = instance.get(
                    floorplan_id=floorplan_id,
                    room_type_id=int(room_type_id)
                )

            elif input_type == 'furniture':
                furniture_type_id = request.query_params.get('furniture_type_id')
                if not furniture_type_id:
                    return Response(
                        {"error": "Для input_type='furniture' необходим параметр furniture_type_id"},
                        status=400
                    )
                result = instance.get(
                    floorplan_id=floorplan_id,
                    furniture_type_id=int(furniture_type_id)
                )

            elif input_type == 'roomsfurniture':
                room_type_id = request.query_params.get('room_type_id')
                furniture_type_id = request.query_params.get('furniture_type_id')
                if not room_type_id or not furniture_type_id:
                    return Response(
                        {"error": "Для input_type='roomsfurniture' нужны room_type_id и furniture_type_id"},
                        status=400
                    )
                result = instance.get(
                    floorplan_id=floorplan_id,
                    room_type_id=int(room_type_id),
                    furniture_type_id=int(furniture_type_id)
                )
            else:
                return Response(
                    {"error": f"Неизвестный input_type: {input_type}"},
                    status=400
                )

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {"error": f"Ошибка при выполнении метода '{method_name}': {str(e)}"},
                status=500
            )

        # ── 4. Сериализация результата ──
        # Поддерживаем оба формата: старый (VoidMethodResult) и новый (SpecialMethodResult)
        if hasattr(result, 'parameter_name'):
            # Новый формат: SpecialMethodResult
            result_dict = dataclasses.asdict(result)
            # Дополнительно добавим мета-информацию для удобства отладки
            result_dict['_meta'] = {
                'method_name': method_name,
                'input_type': input_type,
                'floorplan_id': floorplan_id,
                'recommendations_count': len(result_dict.get('recommendations', [])),
            }
        else:
            # Старый формат (VoidMethodResult, RoomsMethodResult и т.д.)
            result_dict = dataclasses.asdict(result)
            result_dict['_meta'] = {
                'method_name': method_name,
                'input_type': input_type,
                'floorplan_id': floorplan_id,
            }

        return Response(result_dict, status=200)


AUTO_COUNTING_METHOD_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
        'name': openapi.Schema(type=openapi.TYPE_STRING),
        'label': openapi.Schema(type=openapi.TYPE_STRING),
        'inputType': openapi.Schema(type=openapi.TYPE_STRING),
    }
)


class AutoCountingMethodListView(BaseAPIView):
    """Список всех методов автоподсчёта (справочник)."""
    @swagger_auto_schema(
        operation_summary="Список всех методов автоподсчёта",
        responses={200: openapi.Response(
            description='Список',
            schema=openapi.Schema(type=openapi.TYPE_ARRAY, items=AUTO_COUNTING_METHOD_SCHEMA)
        )}
    )
    def get(self, request):
        methods = AutoCountingMethod.objects.all().order_by('id')
        data = [
            {
                'id': m.id,
                'name': m.name,
                'label': m.label,
                'inputType': m.inputType,
            }
            for m in methods
        ]
        return Response(data, status=200)


class CriterionMethodsView(BaseAPIView):
    """Получение и назначение методов автоподсчёта для конкретного критерия."""

    @swagger_auto_schema(
        operation_summary="Методы автоподсчёта, назначенные критерию",
        manual_parameters=[
            openapi.Parameter('criterion_id', openapi.IN_PATH,
                              type=openapi.TYPE_INTEGER, required=True)
        ],
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(type=openapi.TYPE_INTEGER)
            ),
            404: 'Критерий не найден',
        }
    )
    def get(self, request, criterion_id):
        try:
            Criterion_of_ergonomy.objects.get(id=criterion_id)
        except Criterion_of_ergonomy.DoesNotExist:
            return Response({'error': 'Критерий не найден'}, status=404)

        method_ids = AutoCountingMethod_Criterion.objects.filter(
            criterion_id=criterion_id
        ).values_list('auto_counting_method_id', flat=True)

        return Response(list(method_ids), status=200)

    @swagger_auto_schema(
        operation_summary="Назначить методы автоподсчёта критерию",
        request_body=openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(type=openapi.TYPE_INTEGER),
            description='Список ID методов, которые должны быть привязаны к критерию'
        ),
        responses={200: 'Обновлено', 400: 'Ошибка'}
    )
    def put(self, request, criterion_id):
        try:
            criterion = Criterion_of_ergonomy.objects.get(id=criterion_id)
        except Criterion_of_ergonomy.DoesNotExist:
            return Response({'error': 'Критерий не найден'}, status=404)

        method_ids = request.data
        if not isinstance(method_ids, list):
            return Response({'error': 'Ожидается список ID методов'}, status=400)

        # Проверка, что все переданные методы существуют
        existing = set(
            AutoCountingMethod.objects
            .filter(id__in=method_ids)
            .values_list('id', flat=True)
        )
        missing = set(method_ids) - existing
        if missing:
            return Response(
                {'error': f'Методы с ID {list(missing)} не найдены'},
                status=400
            )

        # Полная замена связей
        AutoCountingMethod_Criterion.objects.filter(criterion_id=criterion_id).delete()

        if method_ids:
            links = [
                AutoCountingMethod_Criterion(
                    criterion=criterion,
                    auto_counting_method_id=mid
                )
                for mid in method_ids
            ]
            AutoCountingMethod_Criterion.objects.bulk_create(links)

        return Response(
            {'message': f'Назначено {len(method_ids)} методов'},
            status=200
        )





# views.py - добавить новые классы

class CriterionSystemEquationView(BaseAPIView):
    """Работа с системой уравнений конкретного критерия"""
    
    @swagger_auto_schema(
        operation_summary="Получить систему уравнений критерия",
        responses={200: 'Система уравнений', 404: 'Не найдено'}
    )
    def get(self, request, criterion_id):
        try:
            criterion = Criterion_of_ergonomy.objects.get(id=criterion_id)
            
            # Получаем систему уравнений для этого критерия
            sys_eq = SystemEquastionForCriterion.objects.filter(criterion=criterion).first()
            
            if not sys_eq:
                return Response({
                    'id': None,
                    'equations': [],
                    'used_input_ids': [],
                    'used_criterion_ids': []
                }, status=200)
            
            # Собираем уравнения
            equations = []
            for eq_link in EquastionOfCriterionSystemEquastion.objects.filter(
                criterion_system_equastion=sys_eq
            ).select_related('formula'):
                equations.append({
                    'limit_equastion': eq_link.limit_equastion,
                    'equastion': eq_link.formula.equation,
                    'recommendation': eq_link.recommendation
                })
            
            # Собираем используемые параметры (только глобальные)
            used_input_ids = list(
                SystemEquastionForCriterion_UIP.objects.filter(
                    system_equation_for_criteria=sys_eq
                ).values_list('user_input_param_id', flat=True)
            )
            
            # Собираем используемые критерии
            used_criterion_ids = list(
                CilterionUsingForFormula.objects.filter(
                    system_equation_for_criteria=sys_eq
                ).values_list('criterion_id', flat=True)
            )
            
            return Response({
                'id': sys_eq.id,
                'equations': equations,
                'used_input_ids': used_input_ids,
                'used_criterion_ids': used_criterion_ids
            }, status=200)
            
        except Criterion_of_ergonomy.DoesNotExist:
            return Response({'error': 'Критерий не найден'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
    
    @swagger_auto_schema(
        operation_summary="Создать или обновить систему уравнений критерия",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['equations'],
            properties={
                'equations': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        required=['limit_equastion', 'equastion'],
                        properties={
                            'limit_equastion': openapi.Schema(type=openapi.TYPE_STRING),
                            'equastion': openapi.Schema(type=openapi.TYPE_STRING),
                            'recommendation': openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    )
                ),
                'used_input_ids': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_INTEGER)
                ),
                'used_criterion_ids': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_INTEGER)
                ),
            }
        ),
        responses={200: 'Система уравнений', 400: 'Ошибка'}
    )
    def post(self, request, criterion_id):
        try:
            criterion = Criterion_of_ergonomy.objects.get(id=criterion_id)
            
            data = request.data
            equations = data.get('equations', [])
            used_input_ids = data.get('used_input_ids', [])
            used_criterion_ids = data.get('used_criterion_ids', [])
            
            if not equations:
                return Response({'error': 'Добавьте хотя бы одно уравнение'}, status=400)
            
            # Получаем или создаем систему уравнений
            sys_eq, created = SystemEquastionForCriterion.objects.get_or_create(
                criterion=criterion
            )
            
            # Если не created, очищаем старые данные
            if not created:
                EquastionOfCriterionSystemEquastion.objects.filter(
                    criterion_system_equastion=sys_eq
                ).delete()
                SystemEquastionForCriterion_UIP.objects.filter(
                    system_equation_for_criteria=sys_eq
                ).delete()
                CilterionUsingForFormula.objects.filter(
                    system_equation_for_criteria=sys_eq
                ).delete()
            
            # Создаем уравнения
            for eq in equations:
                formula = Formula.objects.create(equation=eq.get('equastion', ''))
                EquastionOfCriterionSystemEquastion.objects.create(
                    criterion_system_equastion=sys_eq,
                    formula=formula,
                    limit_equastion=eq.get('limit_equastion', ''),
                    recommendation=eq.get('recommendation', '')
                )
            
            # Создаем связи с параметрами (глобальные + привязанные к текущему критерию)
            if used_input_ids:
                from django.db.models import Q
                
                # Принимаем параметры, которые:
                # 1. Глобальные (cryteria_id IS NULL)
                # 2. Привязаны к текущему критерию
                valid_params = UserInputParam.objects.filter(
                    Q(id__in=used_input_ids) & 
                    (Q(formula_param__cryteria_id__isnull=True) | 
                    Q(formula_param__cryteria_id=criterion))
                )
                
                if valid_params.count() != len(used_input_ids):
                    # Находим проблемные ID
                    valid_ids = set(valid_params.values_list('id', flat=True))
                    invalid_ids = set(used_input_ids) - valid_ids
                    return Response({
                        'error': f'Параметры с ID {list(invalid_ids)} не являются глобальными и не привязаны к текущему критерию'
                    }, status=400)
                
                SystemEquastionForCriterion_UIP.objects.bulk_create([
                    SystemEquastionForCriterion_UIP(
                        system_equation_for_criteria=sys_eq,
                        user_input_param_id=uid
                    ) for uid in used_input_ids
                ])
            
            # Создаем связи с другими критериями
            if used_criterion_ids:
                # Исключаем текущий критерий
                used_criterion_ids = [cid for cid in used_criterion_ids if cid != criterion_id]
                
                if used_criterion_ids:
                    CilterionUsingForFormula.objects.bulk_create([
                        CilterionUsingForFormula(
                            system_equation_for_criteria=sys_eq,
                            criterion_id=cid
                        ) for cid in used_criterion_ids
                    ])
            
            # Возвращаем обновленные данные
            return self.get(request, criterion_id)
            
        except Criterion_of_ergonomy.DoesNotExist:
            return Response({'error': 'Критерий не найден'}, status=404)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=500)
    
    @swagger_auto_schema(
        operation_summary="Удалить систему уравнений критерия",
        responses={204: 'Удалено', 404: 'Не найдено'}
    )
    def delete(self, request, criterion_id):
        try:
            criterion = Criterion_of_ergonomy.objects.get(id=criterion_id)
            sys_eq = SystemEquastionForCriterion.objects.filter(criterion=criterion).first()
            
            if not sys_eq:
                return Response({'error': 'Система уравнений не найдена'}, status=404)
            
            # Удаляем уравнения и их формулы
            for eq_link in EquastionOfCriterionSystemEquastion.objects.filter(
                criterion_system_equastion=sys_eq
            ):
                formula_id = eq_link.formula_id
                eq_link.delete()
                
                # Удаляем формулу, если она больше не используется
                if not Formula.objects.filter(id=formula_id).exclude(
                    equastionofcriterionsystemequastion__isnull=False,
                    commonformula__isnull=False,
                    equastionofsystemequastion__isnull=False
                ).exists():
                    Formula.objects.filter(id=formula_id).delete()
            
            # Удаляем связи
            SystemEquastionForCriterion_UIP.objects.filter(
                system_equation_for_criteria=sys_eq
            ).delete()
            CilterionUsingForFormula.objects.filter(
                system_equation_for_criteria=sys_eq
            ).delete()
            
            # Удаляем саму систему
            sys_eq.delete()
            
            return Response(status=204)
            
        except Criterion_of_ergonomy.DoesNotExist:
            return Response({'error': 'Критерий не найден'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class GlobalParametersListView(BaseAPIView):
    """Получение списка глобальных параметров (для использования в системе уравнений критерия)"""
    
    @swagger_auto_schema(
        operation_summary="Список глобальных параметров",
        responses={200: 'Список параметров'}
    )
    def get(self, request):
        try:
            # Получаем только параметры, у которых cryteria_id IS NULL
            global_fps = FormulaParam.objects.filter(
                cryteria_id__isnull=True,
                is_active=True
            ).prefetch_related(
                'userinputparam_set__userinputparamroomtype_set__room_type'
            )
            
            parameters = []
            for fp in global_fps:
                for uip in fp.userinputparam_set.all():
                    parameters.append({
                        'id': uip.id,
                        'varName': fp.name,
                        'label': fp.label or fp.name,
                        'inputType': 'manual',
                        'paramType': uip.type,
                        'minVal': uip.min_value,
                        'maxVal': uip.max_value,
                        'roomTypeIds': [
                            rel.room_type.id 
                            for rel in uip.userinputparamroomtype_set.all()
                        ],
                    })
            
            return Response(parameters, status=200)
            
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class AllCriteriaListView(BaseAPIView):
    """Получение списка всех критериев (для выбора других критериев)"""
    
    @swagger_auto_schema(
        operation_summary="Список всех критериев",
        responses={200: 'Список критериев'}
    )
    def get(self, request):
        try:
            criteria = Criterion_of_ergonomy.objects.filter(
                is_active=True
            ).values('id', 'name', 'var_name')
            
            return Response(list(criteria), status=200)
            
        except Exception as e:
            return Response({'error': str(e)}, status=500)  



class ReportCreateView(BaseAPIView):
    @swagger_auto_schema(
        operation_summary="Создание отчета",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['floorplan_id', 'criteria_data'],
            properties={
                'floorplan_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'criteria_data': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'criterion_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'answers': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                            'parameters': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                        }
                    )
                ),
                'global_parameters': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_OBJECT)
                ),
            }
        ),
        responses={201: 'Отчет создан', 400: 'Ошибка'}
    )
    def post(self, request):
        try:
            data = request.data
            floorplan_id = data.get('floorplan_id')
            criteria_data = data.get('criteria_data', [])
            global_parameters = data.get('global_parameters', [])
            
            if not floorplan_id:
                return Response({'error': 'floorplan_id обязателен'}, status=400)
            
            # Получаем план
            try:
                floorplan = Floorplan.objects.get(id=floorplan_id)
            except Floorplan.DoesNotExist:
                return Response({'error': 'План не найден'}, status=404)
            
            # 1. Создаем отчет
            report = Report.objects.create(
                date=timezone.now(),
                Mark_of_Ergonomy=0,
                Score_Of_Ergonomy=0
            )
            
            # 2. Создаем запись плана в отчете
            report_floorplan = Report_floorplan.objects.create(
                report=report,
                img=floorplan.img,
                floorpan_id=floorplan.id,
                width=floorplan.width,
                height=floorplan.height,
                pixel_to_m2=floorplan.pixel_to_m_in_square,
                square_of_habitation=floorplan.square_of_habitation
            )
            
            # Копируем комнаты, мебель и конструктивные элементы
            room_id_map = {}  # original_id -> report_room_id
            for room in floorplan.room_set.all():
                report_room = Report_Room.objects.create(
                    floorplan=report_floorplan,
                    min_x=room.min_x,
                    max_x=room.max_x,
                    min_y=room.min_y,
                    max_y=room.max_y,
                    room_type=room.room_type_id.type_name if room.room_type_id else '',
                    square_of_room=room.square
                )
                room_id_map[room.id] = report_room.id
                
                # Копируем мебель
                for furn in room.furniture_set.all():
                    Report_Furniture.objects.create(
                        room=report_room,
                        furniture_type=furn.furniture_type_id.type_name if furn.furniture_type_id else '',
                        min_x=furn.min_x,
                        max_x=furn.max_x,
                        min_y=furn.min_y,
                        max_y=furn.max_y
                    )
                
                # Копируем конструктивные элементы
                for ce in room.constructelement_set.all():
                    Report_Construct_eltment.objects.create(
                        room=report_room,
                        con_el_type=ce.construct_element_type_id.type_name if ce.construct_element_type_id else '',
                        min_x=ce.min_x,
                        max_x=ce.max_x,
                        min_y=ce.min_y,
                        max_y=ce.max_y
                    )
            
            # Копируем конструктивные элементы без комнаты (двери)
            for ce in floorplan.constructelement_set.filter(room_id__isnull=True):
                # Создаем виртуальную комнату для двери
                virtual_room = Report_Room.objects.create(
                    floorplan=report_floorplan,
                    min_x=ce.min_x,
                    max_x=ce.max_x,
                    min_y=ce.min_y,
                    max_y=ce.max_y,
                    room_type='corridor',
                    square_of_room=0
                )
                Report_Construct_eltment.objects.create(
                    room=virtual_room,
                    con_el_type=ce.construct_element_type_id.type_name if ce.construct_element_type_id else '',
                    min_x=ce.min_x,
                    max_x=ce.max_x,
                    min_y=ce.min_y,
                    max_y=ce.max_y
                )
            
            # 3. Обработка критериев
            total_score = 0
            total_weight = 0
            criterion_results = {}  # criterion_id -> {param_values, score}
            
            for crit_data in criteria_data:
                criterion_id = crit_data.get('criterion_id')
                answers = crit_data.get('answers', [])
                parameters = crit_data.get('parameters', [])
                
                try:
                    criterion = Criterion_of_ergonomy.objects.get(id=criterion_id)
                except Criterion_of_ergonomy.DoesNotExist:
                    continue
                
                # Создаем запись критерия в отчете
                cor = Critery_of_Ergonomy_Report.objects.create(
                    report=report,
                    weight=criterion.weight,
                    Name=criterion.name,
                    Score=0,
                    Mark=0
                )
                
                # 3.1. Вызов AutoCountingMethod
                auto_params = {}
                acm_links = AutoCountingMethod_Criterion.objects.filter(criterion=criterion)
                for acm_link in acm_links:
                    method = acm_link.auto_counting_method
                    try:
                        method_class = getattr(special_methods, method.name)
                        instance = method_class()
                        result = instance.get(floorplan_id=floorplan_id)
                        
                        # Сохраняем результат метода
                        SpecialMethodsResult.objects.create(
                            cor=cor,
                            name_of_method=method.name,
                            results=result.recommendations,
                            score=result.result
                        )
                        
                        # Сохраняем рекомендации для объектов
                        for rec in result.recommendations:
                            element_type = rec.get('element_type')
                            element_id = rec.get('element_id')
                            recommendation = rec.get('recommendation')
                            
                            if element_type == 'room' and element_id in room_id_map:
                                ReportRoomRecommendation.objects.create(
                                    room_id=room_id_map[element_id],
                                    recommendation=recommendation
                                )
                            elif element_type == 'furniture':
                                # Найти мебель в отчете
                                furn = Report_Furniture.objects.filter(
                                    room__floorplan=report_floorplan,
                                    id=element_id
                                ).first()
                                if furn:
                                    ReportFurnitureRecommendation.objects.create(
                                        furniture=furn,
                                        recommendation=recommendation
                                    )
                            elif element_type == 'construct_element':
                                ce = Report_Construct_eltment.objects.filter(
                                    room__floorplan=report_floorplan,
                                    id=element_id
                                ).first()
                                if ce:
                                    ReportConstructElementRecommendation.objects.create(
                                        construct_element=ce,
                                        recommendation=recommendation
                                    )
                        
                        auto_params[method.name] = result.result
                    except Exception as e:
                        print(f"Ошибка выполнения метода {method.name}: {e}")
                
                # 3.2. Обработка вопросов
                question_score = 0
                question_count = 0
                
                for answer_data in answers:
                    question_id = answer_data.get('question_id')
                    answer_text = answer_data.get('answer')
                    room_data = answer_data.get('room')  # Для вопросов по комнатам
                    
                    try:
                        question = Form_question.objects.get(id=question_id)
                    except Form_question.DoesNotExist:
                        continue
                    
                    # Находим ответ
                    form_answer = FormAnswer.objects.filter(
                        question_id=question,
                        answer=answer_text
                    ).first()
                    
                    score = form_answer.score if form_answer else 5
                    
                    if room_data:
                        # Вопрос по комнате - сохраняем для среднего балла
                        Report_Question_Answer.objects.create(
                            cor=cor,
                            question=question.question,
                            answer=answer_text,
                            score=score
                        )
                        question_score += score
                        question_count += 1
                    else:
                        # Общий вопрос
                        Report_Question_Answer.objects.create(
                            cor=cor,
                            question=question.question,
                            answer=answer_text,
                            score=score
                        )
                        question_score += score
                        question_count += 1
                
                # Средний балл по вопросам
                avg_question_score = question_score / question_count if question_count > 0 else 0
                
                # 3.3. Обработка параметров
                param_values = {}
                
                # Глобальные параметры
                for param_data in global_parameters:
                    param_id = param_data.get('id')
                    param_value = param_data.get('value')
                    try:
                        uip = UserInputParam.objects.get(id=param_id)
                        param_values[uip.formula_param.name] = param_value
                    except UserInputParam.DoesNotExist:
                        pass
                
                # Параметры критерия
                for param_data in parameters:
                    param_id = param_data.get('id')
                    param_value = param_data.get('value')
                    room_type_id = param_data.get('room_type_id')
                    
                    try:
                        uip = UserInputParam.objects.get(id=param_id)
                        param_name = uip.formula_param.name
                        
                        if room_type_id:
                            # Параметр по комнате - сохраняем для каждой комнаты
                            for orig_room_id, report_room_id in room_id_map.items():
                                report_room = Report_Room.objects.get(id=report_room_id)
                                if report_room.room_type == RoomType.objects.get(id=room_type_id).type_name:
                                    param_values[f"{param_name}_room_{report_room_id}"] = param_value
                        else:
                            param_values[param_name] = param_value
                    except UserInputParam.DoesNotExist:
                        pass
                
                # Добавляем автопараметры
                param_values.update(auto_params)
                
                criterion_results[criterion_id] = {
                    'cor': cor,
                    'param_values': param_values,
                    'question_score': avg_question_score
                }
            
            # 4. Обработка систем уравнений (в правильном порядке)
            # Сначала критерии без системы уравнений, потом с системой
            criteria_without_system = []
            criteria_with_system = []
            
            for crit_data in criteria_data:
                criterion_id = crit_data.get('criterion_id')
                try:
                    criterion = Criterion_of_ergonomy.objects.get(id=criterion_id)
                    if criterion.is_counting_by_system_equastion:
                        criteria_with_system.append(criterion_id)
                    else:
                        criteria_without_system.append(criterion_id)
                except:
                    pass
            
            # Обрабатываем сначала без системы
            for criterion_id in criteria_without_system:
                if criterion_id in criterion_results:
                    self._calculate_criterion_score(criterion_results[criterion_id])
            
            # Потом с системой (могут использовать результаты других критериев)
            for criterion_id in criteria_with_system:
                if criterion_id in criterion_results:
                    self._calculate_criterion_with_system(
                        criterion_results[criterion_id],
                        criterion_id,
                        criterion_results,
                        room_id_map,
                        report_floorplan
                    )
            
            # 5. Вычисляем итоговый балл
            for crit_data in criteria_data:
                criterion_id = crit_data.get('criterion_id')
                if criterion_id in criterion_results:
                    cr = criterion_results[criterion_id]
                    cor = cr['cor']
                    score = cr.get('final_score', cr['question_score'])
                    
                    cor.Score = score
                    cor.Mark = self._get_mark(score, criterion_id)
                    cor.save()
                    
                    total_score += score * cor.weight
                    total_weight += cor.weight
            
            report.Score_Of_Ergonomy = total_score / total_weight if total_weight > 0 else 0
            report.Mark_of_Ergonomy = self._get_mark(report.Score_Of_Ergonomy, None)
            report.save()
            
            return Response({
                'report_id': report.id,
                'score': report.Score_Of_Ergonomy,
                'mark': report.Mark_of_Ergonomy
            }, status=201)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=500)
    
    def _calculate_criterion_score(self, criterion_result):
        """Вычисление балла для критерия без системы уравнений"""
        # Пока просто используем средний балл вопросов
        criterion_result['final_score'] = criterion_result['question_score']
    
    def _calculate_criterion_with_system(self, criterion_result, criterion_id, all_results, room_id_map, report_floorplan):
        """Вычисление балла для критерия с системой уравнений"""
        try:
            sys_eq = SystemEquastionForCriterion.objects.get(criterion_id=criterion_id)
            equations = EquastionOfCriterionSystemEquastion.objects.filter(
                criterion_system_equastion=sys_eq
            ).select_related('formula')
            
            param_values = criterion_result['param_values']
            
            # Получаем лимитирующие параметры
            limit_params = {}
            for uip_link in SystemEquastionForCriterion_UIP.objects.filter(
                system_equation_for_criteria=sys_eq
            ):
                uip = uip_link.user_input_param
                param_name = uip.formula_param.name
                
                # Ищем значение в переданных параметрах
                if param_name in param_values:
                    limit_params[param_name] = param_values[param_name]
            
            # Получаем используемые критерии
            used_criteria = CilterionUsingForFormula.objects.filter(
                system_equation_for_criteria=sys_eq
            ).values_list('criterion_id', flat=True)
            
            for crit_id in used_criteria:
                if crit_id in all_results:
                    other_result = all_results[crit_id]
                    other_cor = other_result['cor']
                    # Добавляем балл другого критерия как параметр
                    crit = Criterion_of_ergonomy.objects.get(id=crit_id)
                    limit_params[crit.var_name] = other_cor.Score
            
            # Вычисляем по уравнениям
            total_score = 0
            equation_count = 0
            
            for eq_link in equations:
                formula = eq_link.formula.equation
                limit_condition = eq_link.limit_equastion
                
                # Проверяем условие
                if limit_condition:
                    try:
                        # Заменяем операторы
                        condition = limit_condition.replace('=>', '>=').replace('=<', '<=')
                        condition_met = simple_eval(condition, names=limit_params)
                        
                        if not condition_met:
                            continue
                    except:
                        continue
                
                # Вычисляем формулу
                try:
                    result = simple_eval(formula, names=limit_params)
                    total_score += result
                    equation_count += 1
                    
                    # Сохраняем результат вычисления
                    calculation_result.objects.create(
                        cor=criterion_result['cor'],
                        name_of_calculation=eq_link.limit_equastion,
                        formula=formula,
                        param_value=result,
                        score=result
                    )
                    
                    # Добавляем рекомендацию если есть
                    if eq_link.recommendation:
                        ReportFloorplanRecommendation.objects.create(
                            floorplan=report_floorplan,
                            recommendation=eq_link.recommendation
                        )
                except Exception as e:
                    print(f"Ошибка вычисления формулы: {e}")
            
            if equation_count > 0:
                criterion_result['final_score'] = total_score / equation_count
            else:
                criterion_result['final_score'] = criterion_result['question_score']
                
        except SystemEquastionForCriterion.DoesNotExist:
            criterion_result['final_score'] = criterion_result['question_score']
    
    def _get_mark(self, score, criterion_id):
        """Получение оценки по баллу"""
        if criterion_id:
            try:
                criterion = Criterion_of_ergonomy.objects.get(id=criterion_id)
                if score <= criterion.terrible_mark_border:
                    return 2
                elif score <= criterion.bad_mark_border:
                    return 3
                elif score <= criterion.normal_mark_border:
                    return 4
                else:
                    return 5
            except:
                pass
        
        # По умолчанию
        if score <= 3:
            return 2
        elif score <= 5:
            return 3
        elif score <= 7:
            return 4
        else:
            return 5


class ReportDetailView(BaseAPIView):
    @swagger_auto_schema(
        operation_summary="Получение отчета",
        responses={200: 'Отчет', 404: 'Не найден'}
    )
    def get(self, request, pk):
        try:
            report = Report.objects.prefetch_related(
                'criteries__calculation_results',
                'criteries__question_answers',
                'criteries__special_methods_results',
                'floorplans__rooms__furniture',
                'floorplans__rooms__construct_elements',
                'floorplans__recommendations',
                'floorplans__rooms__recommendations',
                'floorplans__rooms__furniture__recommendations',
                'floorplans__rooms__construct_elements__recommendations'
            ).get(id=pk)
            
            data = {
                'id': report.id,
                'date': report.date.isoformat(),
                'score': report.Score_Of_Ergonomy,
                'mark': report.Mark_of_Ergonomy,
                'criteries': []
            }
            
            for cor in report.criteries.all():
                criterion_data = {
                    'id': cor.id,
                    'name': cor.Name,
                    'weight': cor.weight,
                    'score': cor.Score,
                    'mark': cor.Mark,
                    'calculations': [],
                    'questions': [],
                    'special_methods': []
                }
                
                # Результаты вычислений
                for calc in cor.calculation_results.all():
                    criterion_data['calculations'].append({
                        'name': calc.name_of_calculation,
                        'formula': calc.formula,
                        'value': calc.param_value,
                        'score': calc.score
                    })
                
                # Ответы на вопросы
                for qa in cor.question_answers.all():
                    criterion_data['questions'].append({
                        'question': qa.question,
                        'answer': qa.answer,
                        'score': qa.score
                    })
                
                # Результаты специальных методов
                for sm in cor.special_methods_results.all():
                    criterion_data['special_methods'].append({
                        'name': sm.name_of_method,
                        'score': sm.score,
                        'results': sm.results
                    })
                
                data['criteries'].append(criterion_data)
            
            # Планы и рекомендации
            for fp in report.floorplans.all():
                fp_data = {
                    'id': fp.id,
                    'recommendations': [r.recommendation for r in fp.recommendations.all()],
                    'rooms': []
                }
                
                for room in fp.rooms.all():
                    room_data = {
                        'id': room.id,
                        'type': room.room_type,
                        'square': room.square_of_room,
                        'recommendations': [r.recommendation for r in room.recommendations.all()],
                        'furniture': [],
                        'construct_elements': []
                    }
                    
                    for furn in room.furniture.all():
                        furn_data = {
                            'type': furn.furniture_type,
                            'recommendations': [r.recommendation for r in furn.recommendations.all()]
                        }
                        room_data['furniture'].append(furn_data)
                    
                    for ce in room.construct_elements.all():
                        ce_data = {
                            'type': ce.con_el_type,
                            'recommendations': [r.recommendation for r in ce.recommendations.all()]
                        }
                        room_data['construct_elements'].append(ce_data)
                    
                    fp_data['rooms'].append(room_data)
                
                data['floorplans'] = [fp_data]
            
            return Response(data, status=200)
            
        except Report.DoesNotExist:
            return Response({'error': 'Отчет не найден'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)