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
        operation_summary="добавление нового критерия эргономичности",
        responses={200: "Критерий успешно добавлен", 400: "Ошибка добавления критерия", 
        409: "Критерий с таким названием уже существует"},
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'name': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Имя критерия'
                ),
                'weight': openapi.Schema(
                    type=openapi.TYPE_NUMBER,
                    description='вес критерия'
                )
            }
        )
    )
    def post(self, request):
        name = request.data['name']
        weight = request.data['weight']

            # Проверка на дубликат
        if Criterion_of_ergonomy.objects.filter(name=name).exists():
            return Response({'error': 'Критерий с таким названием уже существует'}, status=400)


        new_criteria = Criterion_of_ergonomy.objects.create(name = name, weight = weight)

                # Преобразование модели в JSON-совместимый словарь
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
        }


        return Response({'message':'Критерий успешно добавлен', "object":criteria_data}, status=200 )


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
                }
            )
        ),
        responses={200: "Успешное обновление", 400: "Ошибка валидации"}
    )
    def put(self, request):
        data = request.data
        if not isinstance(data, list) or len(data) == 0:
            return Response({"error": "Ожидается непустой список объектов"}, status=400)

        # 1. Проверка наличия всех ID и загрузка из БД
        requested_ids = [item.get('id') for item in data if 'id' in item]
        if not requested_ids:
            return Response({"error": "В каждом объекте должно быть поле 'id'"}, status=400)

        existing_qs = Criterion_of_ergonomy.objects.filter(id__in=requested_ids)
        existing_map = {obj.id: obj for obj in existing_qs}

        if len(existing_map) != len(set(requested_ids)):
            missing = set(requested_ids) - set(existing_map.keys())
            return Response({"error": f"Критерии с ID {list(missing)} не найдены в БД"}, status=404)

        for item in data:
            cid = item['id']
            obj = existing_map[cid]

            t_border = item.get('terrible_mark_border', obj.terrible_mark_border)
            b_border  = item.get('bad_mark_border', obj.bad_mark_border)
            n_border = item.get('normal_mark_border', obj.normal_mark_border)
            g_border  = item.get('good_mark_border', obj.good_mark_border)

            if t_border <= 0:
                return Response({"error": f"terrible_mark_border для ID {cid} должен быть > 0"}, status=400)

            if not (t_border < b_border < n_border < g_border):
                return Response({
                    "error": f"Нарушен порядок границ для ID {cid}. "
                             "Верхняя граница каждого уровня должна быть строго меньше нижней границы следующего.",
                    "received": {"terrible_mark_border": t_border, "bad_mark_border": b_border, "normal_mark_border": n_border,
                                 "good_mark_border": g_border, }
                }, status=400)

        active_weight_sum = sum(
            item.get('weight', existing_map[item['id']].weight)
            for item in data
            if item.get('is_active', existing_map[item['id']].is_active) is True
        )

        if not math.isclose(active_weight_sum, 1.0, abs_tol=1e-6):
            return Response({
                "error": f"Сумма весов активных критериев должна быть равна 1.0. Текущая сумма: {active_weight_sum:.4f}"
            }, status=400)
        updatable_fields = [
            'name', 'is_active', 'weight', 'color',
            'terrible_mark_border',
            'bad_mark_border',
            'normal_mark_border',
            'good_mark_border'
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
                'id',
                openapi.IN_PATH,
                type=openapi.TYPE_INTEGER,
                required=True,
                description='ID критерия для удаления'
            )
        ],
        responses={
            204: 'Критерий успешно удалён (без тела ответа)',
            404: 'Критерий не найден',
            400: 'Критерий используется и не может быть удалён'
        }
    )
    def delete(self, request, pk):
        try:
            criterion = Criterion_of_ergonomy.objects.get(id=pk)
        except Criterion_of_ergonomy.DoesNotExist:
            return Response({'error': f'Критерий с ID {pk} не найден'}, status=404)
        criterion.delete()
        return Response(status=204)

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
        # 🔹 1. Валидация ID
        try:
            criterion_id = int(criterion_id)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Некорректный формат ID критерия'}, 
                status=400
            )
        if not Criterion_of_ergonomy.objects.filter(id=criterion_id).exists():
            return Response(
                {'error': f'Критерий с ID {criterion_id} не найден'}, 
                status=404
            )
        
        # 🔹 3. Агрегируем статистику вопросов по типам
        # Замените 'general' / 'room' на реальные значения из QuestionType.choices
        critery =Criterion_of_ergonomy.objects.get(id=criterion_id)
        question_stats = Form_question.objects.filter(
            criterion_id=criterion_id
        ).aggregate(
            general_count=Count('id', filter=Q(type='for_floorplan')),
            room_total_count=Count('id', filter=Q(type='for_every_room')),
        )
        formula_stats = {
            'ordinary': 0,      # Обычные уравнения
            'system': 0,        # Системы уравнений
            'forPremises': 0,   # Для помещения в целом
            'perRoom': 0,       # По комнатам
        }
        response_data = {
            'name':critery.name,
            'questions': {
                'general': question_stats.get('general_count') or 0,
                'room_total': question_stats.get('room_total_count') or 0,
            },
            'formulas': formula_stats
        }
        return Response(response_data, status=200)

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
            # 🔹 1. Получаем файл изображения
            image_file = request.FILES.get('image')
            if not image_file:
                return Response({'error': 'Файл изображения обязателен'}, 
                              status=400)
            
            _, ext = os.path.splitext(image_file.name)
            unique_filename = f"{uuid.uuid4().hex}{ext.lower()}"
            image_file.name = unique_filename 

            # 🔹 2. Получаем остальные данные
            floorplan_name = request.data.get('name', 'floorplan')
            width = float(request.data.get('width', 0))
            height = float(request.data.get('height', 0))
            pixel_to_m = float(request.data.get('pixel_to_m_in_square', 0))
            square_habitation = float(request.data.get('square_of_habitation', 0))
            
            # 🔹 3. Создаём Floorplan с файлом
            floorplan = Floorplan.objects.create(
                img=image_file,  # ← файл напрямую
                width=width,
                height=height,
                pixel_to_m_in_square=pixel_to_m,
                square_of_habitation=square_habitation
            )
            
            # 🔹 4. Получаем JSON с аннотациями
            # Если данные пришли как JSON строка в поле 'data'
            annotations_json = request.data.get('data')
            if isinstance(annotations_json, str):
                annotations = json.loads(annotations_json)
            else:
                annotations = annotations_json or {}
            
            rooms_data = annotations.get('rooms', [])
            walls_data = annotations.get('walls', [])
            furniture_data = annotations.get('furniture', [])
            
            # 🔹 5. Сохраняем комнаты
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
                    max_y=float(bbox[3])
                )
                room_id_map[room_data['id']] = room.id
            
            # 🔹 6. Сохраняем стены
            for wall_data in walls_data:
                construct_type = ConstructElementType.objects.filter(
                    id=wall_data.get('type')
                ).first()
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
            
            # 🔹 7. Сохраняем мебель
            for furn_data in furniture_data:
                furniture_type = FurnitureType.objects.filter(
                    id=furn_data.get('type')
                ).first()
                if not furniture_type:
                    continue
                
                # Находим комнату
                room = None
                furn_room_label = furn_data.get('room')
                
                if furn_room_label:
                    for room_id, backend_id in room_id_map.items():
                        room_obj = Room.objects.get(id=backend_id)
                        if (room_obj.room_type_id.label == furn_room_label or 
                            room_obj.room_type_id.type_name == furn_room_label):
                            room = room_obj
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
            return Response({'error': f'Ошибка JSON: {str(e)}'}, 
                          status=400)
        except Exception as e:
            return Response({'error': str(e)}, 
                          status=500)

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
            
            # 🔹 Читаем файл и кодируем в base64
            img_base64 = None
            if floorplan.img and os.path.isfile(floorplan.img.path):
                with open(floorplan.img.path, 'rb') as f:
                    img_data = f.read()
                    img_base64 = base64.b64encode(img_data).decode('utf-8')
                    ext = os.path.splitext(floorplan.img.name)[1].lower()
                    mime_type = {
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.png': 'image/png',
                        '.webp': 'image/webp'
                    }.get(ext, 'image/jpeg')
                    img_url = f'data:{mime_type};base64,{img_base64}'
            else:
                img_url = None
            
            # 🔹 Формируем комнаты + мебель
            rooms = []
            furniture = []
            
            for room in floorplan.room_set.all():
                rooms.append({
                    'id': room.id,
                    'type': room.room_type_id.id if room.room_type_id else None,
                    'label': room.room_type_id.label if room.room_type_id else '',
                    'color': room.room_type_id.color if room.room_type_id else '#0d6efd',
                    'bbox': [
                        float(room.min_x),
                        float(room.max_x),
                        float(room.min_y),
                        float(room.max_y)
                    ],
                    'square': float(room.square) if room.square else 0
                })
                
                for furn in room.furniture_set.all():
                    furniture.append({
                        'id': furn.id,
                        'type': furn.furniture_type_id.id if furn.furniture_type_id else None,
                        'label': furn.furniture_type_id.label if furn.furniture_type_id else '',
                        'color': furn.furniture_type_id.color if furn.furniture_type_id else '#0d6efd',
                        'bbox': [
                            float(furn.min_x),
                            float(furn.max_x),
                            float(furn.min_y),
                            float(furn.max_y)
                        ],
                        'room': room.room_type_id.label if room.room_type_id else None
                    })
            
            walls = []
            for wall in floorplan.constructelement_set.all():
                walls.append({
                    'id': wall.id,
                    'type': wall.construct_element_type_id.id if wall.construct_element_type_id else None,
                    'label': wall.construct_element_type_id.label if wall.construct_element_type_id else '',
                    'color': wall.construct_element_type_id.color if wall.construct_element_type_id else '#0d6efd',
                    'bbox': [
                        float(wall.min_x),
                        float(wall.max_x),
                        float(wall.min_y),
                        float(wall.max_y)
                    ]
                })
            
            return Response({
                'id': floorplan.id,
                'img': img_url,  # ← Base64 вместо URL
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
    
    # 🔸 PUT — обновить план (метаданные + опционально файл + аннотации)
    def put(self, request, pk):
        try:
            floorplan = Floorplan.objects.get(id=pk)
            
            # 🔹 Обновляем метаданные
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
            
            # 🔹 Опционально: замена изображения
            new_image = request.FILES.get('image')
            if new_image:
                if floorplan.img and os.path.isfile(floorplan.img.path):
                    os.remove(floorplan.img.path)
                _, ext = os.path.splitext(new_image.name)
                new_image.name = f"{uuid.uuid4().hex}{ext.lower()}"
                floorplan.img = new_image
            
            floorplan.save()
            
            # 🔹 Опционально: полная замена аннотаций
            annotations_json = request.data.get('data')
            if annotations_json:
                annotations = json.loads(annotations_json) if isinstance(annotations_json, str) else annotations_json
                
                # 🔸 Получаем все комнаты плана для удаления мебели
                rooms_to_delete = Room.objects.filter(floorplan_id=floorplan)
                room_ids_to_delete = [room.id for room in rooms_to_delete]
                
                # 🔸 Удаляем мебель, которая принадлежит комнатам этого плана
                Furniture.objects.filter(room_id__in=room_ids_to_delete).delete()
                
                # 🔸 Удаляем комнаты и стены
                Room.objects.filter(floorplan_id=floorplan).delete()
                ConstructElement.objects.filter(floorplan_id=floorplan).delete()
                
                # 🔸 Сохраняем новые аннотации
                room_id_map = {}
                
                # Комнаты
                for room_data in annotations.get('rooms', []):
                    room_type = RoomType.objects.filter(id=room_data.get('type')).first()
                    if not room_type: continue
                    
                    bbox = room_data.get('bbox', [0]*4)
                    
                    room = Room.objects.create(
                        floorplan_id=floorplan,
                        room_type_id=room_type,
                        min_x=float(bbox[0]),
                        max_x=float(bbox[1]),
                        min_y=float(bbox[2]),
                        max_y=float(bbox[3]),
                        square=float(room_data.get('square', 0))
                    )
                    room_id_map[room_data['id']] = room.id
                
                # Стены
                for wall_data in annotations.get('walls', []):
                    ct = ConstructElementType.objects.filter(id=wall_data.get('type')).first()
                    if not ct: continue
                    bbox = wall_data.get('bbox', [0]*4)
                    ConstructElement.objects.create(
                        floorplan_id=floorplan,
                        construct_element_type_id=ct,
                        min_x=float(bbox[0]), max_x=float(bbox[1]),
                        min_y=float(bbox[2]), max_y=float(bbox[3])
                    )
                
                # Мебель
                for furn_data in annotations.get('furniture', []):
                    ft = FurnitureType.objects.filter(id=furn_data.get('type')).first()
                    if not ft: continue
                    
                    room = None
                    if furn_data.get('room'):
                        for rid, bid in room_id_map.items():
                            r = Room.objects.get(id=bid)
                            if r.room_type_id.label == furn_data['room']:
                                room = r
                                break
                    
                    bbox = furn_data.get('bbox', [0]*4)
                    Furniture.objects.create(
                        furniture_type_id=ft,
                        room_id=room,
                        min_x=float(bbox[0]), max_x=float(bbox[1]),
                        min_y=float(bbox[2]), max_y=float(bbox[3])
                    )
            
            return Response({
                'message': 'План обновлён',
                'floorplan_id': floorplan.id
            }, status=200)
            
        except Floorplan.DoesNotExist:
            return Response({'error': 'План не найден'}, status=404)
        except Exception as e:
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
    }
    print('==============================')
    print(p_type)
    print('==============================')
    if p_type == 'user':
        # ✅ Используем values_list для производительности
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
                cryteria_id_id=cryteria_id
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


# 🔹 Схемы для ограничений
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

# ✅ ИСПРАВЛЕНО: добавлен items= для roomValues
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
                cryteria_id_id=cryteria_id if cryteria_id != 0 else None
            )

            # 2. Создаем LimitParam
            lp = LimitParam.objects.create(formula_param=fp)

            # 3. Создаем значения
            if limit_type == 'universal':
                val = data.get('universal_value')
                if val is None: 
                    return Response({'error': 'Укажите universal_value'}, status=400)
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



# ==========================================
#  SCHEMAS
# ==========================================
FORMULA_ITEM_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
        'objType': openapi.Schema(type=openapi.TYPE_STRING, enum=['single', 'system']),
        'criterion_id': openapi.Schema(type=openapi.TYPE_INTEGER),  
        # --- Для objType: single ---
        'equation': openapi.Schema(type=openapi.TYPE_STRING),
        'type': openapi.Schema(type=openapi.TYPE_STRING, enum=['global', 'rooms']),
        'recommendation': openapi.Schema(type=openapi.TYPE_STRING),
        'value_recomm': openapi.Schema(type=openapi.TYPE_NUMBER, format='float'),
        # --- Для objType: system ---
        'systemType': openapi.Schema(type=openapi.TYPE_STRING, enum=['house', 'rooms']),
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
        'for_room_types_ids': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_INTEGER)),
        'used_input_ids': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_INTEGER)),
        'used_acp_ids': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_INTEGER)),
        'used_limit_ids': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_INTEGER)),
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
        'systemType': openapi.Schema(type=openapi.TYPE_STRING, enum=['house', 'rooms']),
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
    # Параметры системы
    input_ids = list(SystemEquastionUserInputParam.objects.filter(sys_equ=sys_obj).values_list('useR_input_param_id', flat=True))
    acp_ids = list(SystemEquastionUserACP.objects.filter(sys_equ=sys_obj).values_list('acp_id', flat=True))
    lim_ids=[]
    room_type_ids=[]
    if(sys_obj.type == 'rooms'):
        lim_ids = list(SystemEquastionRoomsLimitParam.objects.filter(system_equastion=sys_obj).values_list('rooms_limit_param_id', flat=True))
        room_type_ids = list(SysEquastRoomType.objects.filter(system_equastion=sys_obj).values_list('room_type_id',flat=True))
    else:
        lim_ids = list(SystemEquastionUniversalLimitParam.objects.filter(system_equastion=sys_obj).values_list('universal_limit_param_id', flat=True))
    equastions = []
    # Универсальные уравнения
    for ueq in EquastionOfSystemEquastion.objects.filter(system_equastion=sys_obj):
        equastions.append({
            'limit_equastion': ueq.limit_equastion,
            'equastion': ueq.formula.equation.strip(),
            'recommendation': ueq.recommendation,
        })

    return {
        'id': sys_obj.id,
        'objType': 'system',
        'systemType':sys_obj.type,
        'equations': equastions,
        'criterion_id': sys_obj.criterion_id,
        'used_input_ids': input_ids,
        'used_acp_ids': acp_ids,
        'used_limit_ids':lim_ids,
        'for_room_types_ids':room_type_ids
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
                'syueqastroomtype_set'  # ⚠️ Проверьте, что это имя related_name верное!
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
                if not data.get('equation'): return Response({'error': 'Укажите equation'}, status=400)
                fp = Formula.objects.create(equation=data['equation'])
                cf = CommonFormula.objects.create(
                    formula=fp, type=f_type, criterion_id=criterion_id,
                    recommendation=data.get('recommendation'), value_recomm=data.get('value_recomm')
                )
                if f_type == 'rooms' and data.get('for_room_types_ids'):
                    CommonFormulaRoomTypes.objects.bulk_create([
                        CommonFormulaRoomTypes(commonformula=cf, roomtype_id=rid) 
                        for rid in data['for_room_types_ids']
                    ])
                _create_param_links(cf, input_ids, acp_ids, is_system=False)
                return Response(_serialize_common_formula(cf), status=201)

            else:
                equations = data.get('equations', [])
                if not equations: return Response({'error': 'Добавьте хотя бы одно уравнение'}, status=400)
                
                sys_type = data.get('systemType', 'house')
                sys_obj = SystemEquastion.objects.create(type=sys_type, criterion_id=criterion_id)
                _create_param_links(sys_obj, input_ids, acp_ids, is_system=True)

                for eq in equations:
                    eq_str = f"{eq.get('left', '')} = {eq.get('right', '')}".strip()
                    formula = Formula.objects.create(equation=eq_str)
                    EquastionOfSystemEquastion.objects.create(
                        system_equastion=sys_obj,
                        formula=formula,
                        limit_equastion=eq.get('left', ''),
                        recommendation=eq.get('recommendation', '')
                    )

                limit_ids = data.get('used_limit_ids', []) or []
                room_type_ids = data.get('for_room_types_ids', []) or []

                if sys_type == 'rooms':
                    if limit_ids:
                        SystemEquastionRoomsLimitParam.objects.bulk_create([
                            SystemEquastionRoomsLimitParam(system_equastion=sys_obj, rooms_limit_param_id=lim_id) 
                            for lim_id in limit_ids
                        ])
                    if room_type_ids:
                        SysEquastRoomType.objects.bulk_create([
                            SysEquastRoomType(system_equastion=sys_obj, room_type_id=rid) 
                            for rid in room_type_ids
                        ])
                else:
                    if limit_ids:
                        SystemEquastionUniversalLimitParam.objects.bulk_create([
                            SystemEquastionUniversalLimitParam(sys_equastion=sys_obj, universal_limit_param_id=lim_id) 
                            for lim_id in limit_ids
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

            if obj_type == 'single':
                cf = self._get_obj(pk, 'single')
                if not cf: return Response({'error': 'Не найдено'}, status=404)
                
                cf.formula.equation = data.get('equation', cf.formula.equation)
                cf.formula.save()
                cf.type = f_type
                cf.criterion_id = criterion_id
                cf.recommendation = data.get('recommendation', cf.recommendation)
                cf.value_recomm = data.get('value_recomm', cf.value_recomm)
                cf.save()

                cf.commonformularoomtypes_set.all().delete()
                if f_type == 'rooms' and data.get('for_room_types_ids'):
                    CommonFormulaRoomTypes.objects.bulk_create([
                        CommonFormulaRoomTypes(commonformula=cf, roomtype_id=rid) for rid in data['for_room_types_ids']
                    ])
                _delete_param_links(cf, is_system=False)
                _create_param_links(cf, input_ids, acp_ids, is_system=False)
                return Response(_serialize_common_formula(cf), status=200)

            else:
                sys_obj = self._get_obj(pk, 'system')
                if not sys_obj: return Response({'error': 'Не найдено'}, status=404)
                
                sys_type = data.get('systemType', sys_obj.type)
                sys_obj.type = sys_type
                sys_obj.criterion_id = criterion_id
                sys_obj.save()

                EquastionOfSystemEquastion.objects.filter(system_equastion=sys_obj).delete()
                SystemEquastionRoomsLimitParam.objects.filter(system_equastion=sys_obj).delete()
                SystemEquastionUniversalLimitParam.objects.filter(sys_equastion=sys_obj).delete()
                SysEquastRoomType.objects.filter(system_equastion=sys_obj).delete()
                _delete_param_links(sys_obj, is_system=True)
                
                _create_param_links(sys_obj, input_ids, acp_ids, is_system=True)
                equations = data.get('equations', [])

                for eq in equations:
                    eq_str = f"{eq.get('left', '')} = {eq.get('right', '')}".strip()
                    formula = Formula.objects.create(equation=eq_str)
                    EquastionOfSystemEquastion.objects.create(
                        system_equastion=sys_obj,
                        formula=formula,
                        limit_equastion=eq.get('left', ''),
                        recommendation=eq.get('recommendation', '')
                    )

                limit_ids = data.get('used_limit_ids', []) or []
                room_type_ids = data.get('for_room_types_ids', []) or []

                if sys_type == 'rooms':
                    if limit_ids:
                        SystemEquastionRoomsLimitParam.objects.bulk_create([
                            SystemEquastionRoomsLimitParam(system_equastion=sys_obj, rooms_limit_param_id=lim_id) 
                            for lim_id in limit_ids
                        ])
                    if room_type_ids:
                        SysEquastRoomType.objects.bulk_create([
                            SysEquastRoomType(system_equastion=sys_obj, room_type_id=rid) 
                            for rid in room_type_ids
                        ])
                else:
                    if limit_ids:
                        SystemEquastionUniversalLimitParam.objects.bulk_create([
                            SystemEquastionUniversalLimitParam(sys_equastion=sys_obj, universal_limit_param_id=lim_id) 
                            for lim_id in limit_ids
                        ])
                        
                return Response(_serialize_system(sys_obj), status=200)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
    def delete(self, request, pk):
        try:
            obj = self._get_obj(pk, 'single')
            if obj:
                _delete_param_links(obj, is_system=False)
                fid = obj.formula_id
                obj.commonformularoomtypes_set.all().delete()
                obj.delete()
                Formula.objects.filter(id=fid).delete()
                return Response(status=204)
            
            obj = self._get_obj(pk, 'system')
            if obj:
                # Удаление уравнений и связанных формул
                for ueq in EquastionOfSystemEquastion.objects.filter(system_equastion=obj).select_related('formula'):
                    ueq.formula.delete()
                EquastionOfSystemEquastion.objects.filter(system_equastion=obj).delete()
                
                # Очистка связей
                _delete_param_links(obj, is_system=True)
                SystemEquastionRoomsLimitParam.objects.filter(system_equastion=obj).delete()
                SystemEquastionUniversalLimitParam.objects.filter(system_equastion=obj).delete()
                SysEquastRoomType.objects.filter(system_equastion=obj).delete()
                
                obj.delete()
                return Response(status=204)
            return Response({'error': 'Не найдено'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)