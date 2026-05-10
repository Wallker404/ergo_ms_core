from django.urls import (
    path,
    include
)
from modules.Rooman_alytics.api.views import *
urlpatterns = [
    path('test/', TestView.as_view(), name='test'),
    path('cluster/dbscan/', DBSCANAPIView.as_view(), name='dbscan'),
    path('cluster/elbow/', ElbowAPIView.as_view(), name='elbow'),
    path('cluster/silhouette/', SilhouetteAPIView.as_view(), name='silhouette'),
    path('cluster/kmeans/', KMeansAPIView.as_view(), name='kmeans'),

    
    path('models/upload/', ModelUploadView.as_view(), name='model-upload'),
    path('models/', ModelListView.as_view(), name='model-list'),
    path('models/<int:pk>/', ModelDetailView.as_view(), name='model-detail'),
    path('models/<int:pk>/toggle/', ModelToggleActiveView.as_view(), name='model-toggle'),
    path('models/active/', ModelActiveByCategoryView.as_view(), name='model-active'),
]