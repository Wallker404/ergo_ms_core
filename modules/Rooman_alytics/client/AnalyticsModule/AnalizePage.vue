<template>
    <div>
      <h1>Анализ помещения</h1>
    </div>
  </template>
  
  <script setup>
import { onMounted } from 'vue'
import { apiClient } from '@/js/api/manager'
import { roomAnalyticsEndpoints } from '../js/endpoints'
async function getRoomAnalytics() {
  const res = await apiClient.get(roomAnalyticsEndpoints.roomAnalytics.test)
  return res.data
}

onMounted(async () => {
  try {
    const data = await getRoomAnalytics()
    console.log(data)
  } catch (error) {
    console.error('Ошибка загрузки room analytics:', error)
  }
})
  </script>
  
  <style lang="scss" scoped>
  
  </style>