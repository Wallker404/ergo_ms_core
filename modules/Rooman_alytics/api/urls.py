from django.urls import (
    path,
    include
)
from modules.Rooman_alytics.api.views import *
urlpatterns = [
    path('cluster/dbscan/', DBSCANAPIView.as_view(), name='dbscan'),
    path('cluster/elbow/', ElbowAPIView.as_view(), name='elbow'),
    path('cluster/silhouette/', SilhouetteAPIView.as_view(), name='silhouette'),
    path('cluster/kmeans/', KMeansAPIView.as_view(), name='kmeans'),

    
    path('models/upload/', ModelUploadView.as_view(), name='model-upload'),
    path('models/', ModelListView.as_view(), name='model-list'),
    path('models/<int:pk>/', ModelDetailView.as_view(), name='model-detail'),
    path('models/<int:pk>/toggle/', ModelToggleActiveView.as_view(), name='model-toggle'),
    path('models/active/', ModelActiveByCategoryView.as_view(), name='model-active'),
    path('critery/post', CriteryPost.as_view(), name='critery add'),
    path('criteries/', CriterionListView.as_view(), name='criteria-list'),
    path('criteriy/update/', CriterionBatchUpdateView.as_view(), name='criteria-update'),
    path('criteries/<int:pk>/delete/', CriterionDeleteView.as_view(), name='criteria-delete'),
    path('criteries/<int:criterion_id>/survey-stats/', CriterionSurveyStatsView.as_view(), name='criterion-survey-stats'),

    path('room-types/', RoomTypeListView.as_view(), name='room-types-list'),
    path('questions/batch/', QuestionBatchSaveView.as_view(), name='question-batch-save'),
    path('questions/add/', QuestionCreateView.as_view(), name='question-create'),
    path('questions/<int:question_id>/delete', QuestionDeleteView.as_view(), name='question-delete'),
    path('criteries/<int:criterion_id>/questions/', CriterionQuestionsListView.as_view()),
    path('furniture-types/', FurnitureTypeListView.as_view(), name='furniture type list'),
    path('cunstruct-element-types/', ConstructElementTypeListView.as_view(), name='construct element type list'),
    path('floorplans/save/', FloorplanSaveView.as_view(), name='floorplan-save'),
    path('floorplans/', FloorplanListView.as_view(), name='floorplan-list'),
    path('floorplans/<int:pk>/', FloorplanDetailView.as_view(), name='floorplan-detail'),
    
    path('special-methods/', GetScecialMethods.as_view(), name='special_methods'),
    path('parameters/', ParameterListView.as_view(), name='parameter_list'),
    path('parameters/<int:pk>/', ParameterDetailView.as_view(), name='parameter_detail'),
    path('limit-params/', LimitParamListView.as_view(), name='limit_params_list'),
    path('limit-params/<int:pk>/', LimitParamDetailView.as_view(), name='limit_params_detail'),

    path('formulas/', FormulaListView.as_view(), name="formulas list"),
    path('formulas/<int:pk>/', FormulaDetailView.as_view(), name="formulas detail"),
    path('criteries/questionsandparams/', ActiveCriterionListView.as_view(), name='Questions and params'),
    path(
        'special-methods/<int:id>/<int:floorplan_id>/', 
        TestView.as_view(), 
        name='special-method-test'
    ),
    path('auto-counting-methods/',
         AutoCountingMethodListView.as_view(),
         name='auto-counting-methods'),
    path('criteries/<int:criterion_id>/methods/',
         CriterionMethodsView.as_view(),
         name='criterion-methods'),

        path('criteries/<int:criterion_id>/system-equation/',
         CriterionSystemEquationView.as_view(),
         name='criterion-system-equation'),
    
    # Глобальные параметры
    path('global-parameters/',
         GlobalParametersListView.as_view(),
         name='global-parameters'),
    
    # Все критерии
    path('all-criteria/',
         AllCriteriaListView.as_view(),
         name='all-criteria'),


     path('reports/', ReportCreateView.as_view(), name='report-create'),
    path('reports/<int:pk>/', ReportDetailView.as_view(), name='report-detail'),
]