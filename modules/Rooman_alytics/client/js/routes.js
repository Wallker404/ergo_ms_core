export default {
  "AnalyticsModule": {
    "path": "/room-analytics",
    "redirect": { "name": "AnalyzePage" },
    "meta": {
      "title": "Модуль анализа помещения",
      "requiresAuth": true
    }
  },
  "AnalyzePage": {
    "path": "/room-analytics/analyze",
    "component": "@/modules/Rooman_alytics/client/AnalyticsModule/AnalizePage.vue",
    "meta": {
      "title": "Анализ помещения",
      "requiresAuth": true
    }
  },
  "LoadPlan": {
    "path": "/room-analytics/load-plan",
    "component": "@/modules/Rooman_alytics/client/AnalyticsModule/LoadPlan.vue",
    "meta": {
      "title": "Загрузить план",
      "requiresAuth": true
    }
  },
  "SurveyStart": {
    "path": "/room-analytics/survey-start",
    "component": "@/modules/Rooman_alytics/client/AnalyticsModule/SurveyStart.vue",
    "meta": {
      "title": "Пройти анкетирование",
      "requiresAuth": true
    }
  },
  "DataUpload": {
    "path": "/room-analytics/data-upload",
    "component": "@/modules/Rooman_alytics/client/AnalyticsInsruments/DataUpload.vue",
    "meta": {
      "title": "Загрузка данных",
      "requiresAuth": true
    }
  },
  "ModelEditor": {
    "path": "/room-analytics/model-editor",
    "component": "@/modules/Rooman_alytics/client/AnalyticsInsruments/ModelEditor.vue",
    "meta": {
      "title": "Редактирование мат. модели",
      "requiresAuth": true
    }
  },
  "RegressionAnalysis": {
    "path": "/room-analytics/regression-analysis",
    "component": "@/modules/Rooman_alytics/client/AnalyticsInsruments/RegressionAnalysis.vue",
    "meta": {
      "title": "Регрессионный анализ",
      "requiresAuth": true
    }
  },
  "ClassificationAnalysis": {
    "path": "/room-analytics/classification-analysis",
    "component": "@/modules/Rooman_alytics/client/AnalyticsInsruments/ClassificationAnalysis.vue",
    "meta": {
      "title": "Классификация",
      "requiresAuth": true
    }
  },
  "ClusteringAnalysis": {
    "path": "/room-analytics/clustering-analysis",
    "component": "@/modules/Rooman_alytics/client/AnalyticsInsruments/ClusteringAnalysis.vue",
    "meta": {
      "title": "Кластеризационный анализ",
      "requiresAuth": true
    }
  },
  "BayesianAnalysis": {
    "path": "/room-analytics/bayesian-analysis",
    "component": "@/modules/Rooman_alytics/client/AnalyticsInsruments/BayesianAnalysis.vue",
    "meta": {
      "title": "Байсовый анализ",
      "requiresAuth": true
    }
  },
  "FunctionsAndFormPage":{
    "name":"FunctionsAnsFormsPage",
    "path": "/room-analytics/formandfunctions/:criterionId",
    "component":"@/modules/Rooman_alytics/client/AnalyticsInsruments/FunctionsAndFormPage.vue",
    "meta":{
      "title":"Функции и анкета",
      "requiresAuth": true
    }

  },
"FormCustomPage": {
  "name": "FormCustomPage",
  "path": "/room-analytics/formcustom/:criterionId",
  "component": "@/modules/Rooman_alytics/client/AnalyticsInsruments/FormCustomPage.vue",
  "meta": {
    "title": "Настройка анкеты",
    "requiresAuth": true
  }
},
"FormulaCustomPage": {
  "name": "FormulaCustomPage",
  "path": "/room-analytics/formulacustom/:criterionId",
  "component": "@/modules/Rooman_alytics/client/AnalyticsInsruments/Formularedact.vue",
  "meta": {
    "title": "Настройка анкеты",
    "requiresAuth": true
  }
}
}
