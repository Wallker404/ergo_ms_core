from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from django.db import connection, transaction
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import random
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import (Group, Permission, User)
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans, DBSCAN
from sklearn.metrics import silhouette_score
import json
import numpy as np
import pandas as pd
from src.core.utils.base.base_views import BaseAPIView, BaseAPIViewAuthMixin
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import base64
from io import BytesIO
from .models import OnnxModel, ModelCategory
import os
class TestView(BaseAPIView):
    @swagger_auto_schema(
        operation_description="Тестовое API",
        responses={
            200: "Тестовое API",
        },
        manual_parameters=[
            openapi.Parameter(
                'test',
                openapi.IN_QUERY,
                description='Тестовое API',
                type=openapi.TYPE_STRING,
                required=False,
            )
        ],
    )
    def get(self, request, *args, **kwargs):
        points = [
            {'x': i, 'y': round(random.uniform(0, 100), 2)}
            for i in range(1, 21)  # 20 точек
        ]
                
        return Response({'points': points})


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

def _fig_to_base64(fig, dpi=120):
    """Конвертирует matplotlib Figure в base64-строку data:image/png;base64,..."""
    buf = BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=dpi)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return f"data:image/png;base64,{b64}"


def _generate_scatter_plot(X, labels, features, x_idx=0, y_idx=1, title_extra=""):
    """
    Генерирует ОДИН scatter plot для выбранных осей.
    Возвращает base64-строку изображения.
    """
    fig, ax = plt.subplots(figsize=(8, 6), dpi=120)
    
    unique_labels = np.unique(labels)
    # Цвета: до 10 кластеров — tab10, иначе — tab20
    cmap = plt.cm.get_cmap('tab10' if len(unique_labels) <= 10 else 'tab20')
    colors = cmap(np.linspace(0, 1, len(unique_labels)))
    
    for lbl, color in zip(unique_labels, colors):
        mask = labels == lbl
        name = 'Noise' if lbl == -1 else f'Cluster {lbl}'
        ax.scatter(
            X[mask, x_idx], X[mask, y_idx],
            c=[color], s=30, alpha=0.8, label=name,
            edgecolors='white', linewidths=0.5
        )
    
    ax.set_xlabel(features[x_idx], fontsize=11, fontweight='bold')
    ax.set_ylabel(features[y_idx], fontsize=11, fontweight='bold')
    algo_info = f" | {title_extra}" if title_extra else ""
    ax.set_title(f"Кластеризация: {features[x_idx]} vs {features[y_idx]}{algo_info}", 
                 fontsize=13, fontweight='bold', pad=15)
    ax.legend(loc='best', fontsize=9, markerscale=1.5)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    return _fig_to_base64(fig)


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
            if k < 2: raise ValueError("k должно быть >= 2")
        except Exception as e:
            return Response({"error": f"Параметр k обязателен и должен быть >= 2. Ошибка: {e}"}, status=400)

        # Опционально: выбор осей для графика (по умолчанию первые два признака)
        x_idx = int(request.data.get('x_axis', 0))
        y_idx = int(request.data.get('y_axis', 1))
        if x_idx < 0 or x_idx >= len(features) or y_idx < 0 or y_idx >= len(features):
            return Response({"error": f"Неверные индексы осей. Доступно признаков: {len(features)}"}, status=400)

        model = KMeans(n_clusters=k, random_state=42)
        labels = model.fit_predict(X)
        
        # Генерируем график
        plot_base64 = _generate_scatter_plot(X, labels, features, x_idx, y_idx, f"k={k}")
        
        return Response({
            "status": "success",
            "algorithm": "kmeans",
            "n_clusters": k,
            "features": features,
            "plot": plot_base64,  # 🔹 Base64-изображение
            "plot_info": {
                "x_axis": features[x_idx],
                "y_axis": features[y_idx]
            }
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
        
        plot_base64 = _generate_scatter_plot(X, labels, features, x_idx, y_idx, f"eps={eps}, min_samples={min_samples}")
        
        return Response({
            "status": "success",
            "algorithm": "dbscan",
            "n_clusters": n_clusters,
            "n_noise": n_noise,
            "features": features,
            "plot": plot_base64,
            "plot_info": {
                "x_axis": features[x_idx],
                "y_axis": features[y_idx]
            },
            "params": {"eps": eps, "min_samples": min_samples}
        })


import json

def read_labels_file(file_obj):
    print(file_obj)
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
        classes_file = request.FILES.get('classes_file') 
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
    @transaction.atomic
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