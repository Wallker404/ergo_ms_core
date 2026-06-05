export const roomAnalyticsEndpoints = {
  roomAnalytics: {
    test: 'Rooman_alytics/test/',
    dbscan: 'Rooman_alytics/cluster/dbscan/',
    kmeans: 'Rooman_alytics/cluster/kmeans/',
    elbow: 'Rooman_alytics/cluster/elbow/',
    silhouette: 'Rooman_alytics/cluster/silhouette/',
    modelList: 'Rooman_alytics/models/',
    modelUpload: 'Rooman_alytics/models/upload/',
    modelDetail: (pk) => `Rooman_alytics/models/${pk}/`,
    modelToggle: (pk) => `Rooman_alytics/models/${pk}/toggle/`,
    CriteriesGet:'Rooman_alytics/criteries/',
    CriteriesAdd:'Rooman_alytics/critery/post',
    CriteriesUpdate:'Rooman_alytics/criteriy/update/',
    Criteriesdelete: (pk) => `Rooman_alytics/criteries/${pk}/delete/`,
    CruteriesSurvey: (pk)=> `Rooman_alytics/criteries/${pk}/survey-stats/`,
    RoomTypesList: 'Rooman_alytics/room-types/',
    QuestionsUpdate: 'Rooman_alytics/questions/batch/',
    QuestionAdd: 'Rooman_alytics/questions/add/',
    QuestionDelete:(pk)=>`Rooman_alytics/questions/${pk}/delete`,
    CriteriesQuestions: (cid) => `Rooman_alytics/criteries/${cid}/questions/`,
    FurnitureTypesList: 'Rooman_alytics/furniture-types/',
    ConstrucElementTypesList: 'Rooman_alytics/cunstruct-element-types/',
    FloorplanSave: 'Rooman_alytics/floorplans/save/',
    FloorplanList: 'Rooman_alytics/floorplans/',
    FloorplanDetail: (id) => `Rooman_alytics/floorplans/${id}/`,
    SpecialMethodList: 'Rooman_alytics/special-methods/',
    ParamsList:'Rooman_alytics/parameters/',
    ParamDetail: (id) => `Rooman_alytics/parameters/${id}/`,

    LimitParamsList: 'Rooman_alytics/limit-params/',
    LimitParamDetail: (id) => `Rooman_alytics/limit-params/${id}/`,

    FormulasList: 'Rooman_alytics/formulas/',
    FormulaDetail: (id) => `Rooman_alytics/formulas/${id}/`,
    GetCriteryQuestionsAndParams: 'Rooman_alytics/criteries/questionsandparams/',
    AutoCountingMethodsList: 'Rooman_alytics/auto-counting-methods/',
    CriterionMethods: (criterionId) =>
      `Rooman_alytics/criteries/${criterionId}/methods/`,
    CriterionSystemEquation: (criterionId) =>
      `Rooman_alytics/criteries/${criterionId}/system-equation/`,
    
    // Глобальные параметры
    GlobalParametersList: 'Rooman_alytics/global-parameters/',
    
    // Все критерии
    AllCriteriaList: 'Rooman_alytics/all-criteria/',
  },
}
