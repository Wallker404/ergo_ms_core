from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ElectricalEquipmentClassViewSet,
    EquipmentMetricByCountryViewSet,
    EquipmentErgonomicsPluginStatusViewSet,
    AnalysisCoefficientViewSet,
    AnalysisMetricViewSet,
    CustomDatasetViewSet,
    AnalysisRunViewSet,
    AnalysisDashboardViewSet,
)

router = DefaultRouter()
router.register(r'electrical-classes', ElectricalEquipmentClassViewSet, basename='electrical-class')
router.register(r'dataset', EquipmentMetricByCountryViewSet, basename='equipment-metric-by-country')
router.register(r'plugin-status', EquipmentErgonomicsPluginStatusViewSet, basename='equipment-ergonomics-plugin-status')
router.register(r'analysis/coefficients', AnalysisCoefficientViewSet, basename='equipment-analysis-coefficients')
router.register(r'analysis/metrics', AnalysisMetricViewSet, basename='equipment-analysis-metrics')
router.register(r'analysis/custom-datasets', CustomDatasetViewSet, basename='equipment-analysis-custom-datasets')
router.register(r'analysis/runs', AnalysisRunViewSet, basename='equipment-analysis-runs')
router.register(r'analysis/dashboard', AnalysisDashboardViewSet, basename='equipment-analysis-dashboard')

urlpatterns = [
    path('', include(router.urls)),
]
