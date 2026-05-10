/**
 * Маршруты модуля для Vue Router (формат объекта — см. core/client/src/core/cms/js/routes.js).
 * Имя ключа = name маршрута; оно же используется в админке меню (route_name).
 */
export default {
  EquipmentErgonomics: {
    path: '/equipment-ergonomics',
    component:
      '@/modules/equipment_ergonomics/client/src/components/EquipmentErgonomics.vue',
    meta: {
      title: 'Эргономика техники',
      requiresAuth: true
    }
  },
  EquipmentErgonomicsAnalysis: {
    path: '/equipment-ergonomics/analysis',
    component:
      '@/modules/equipment_ergonomics/client/src/components/DataAnalysis.vue',
    meta: {
      title: 'Анализ данных',
      requiresAuth: true
    }
  }
}
