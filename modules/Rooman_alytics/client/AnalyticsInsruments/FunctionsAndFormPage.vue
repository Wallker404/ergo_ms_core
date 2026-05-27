<template>
  <div class="container-fluid py-3">
    <nav class="mb-3">
      <ol class="breadcrumb mb-0">
        <li class="breadcrumb-item"><a href="#" @click.prevent="goBack">Критерии</a></li>
        <li class="breadcrumb-item active">{{ criterionName }}</li>
      </ol>
    </nav>

    <h4 class="mb-4">Обзор модели</h4>

    <div v-if="isLoading" class="text-center py-5">Загрузка...</div>

    <div v-else class="row g-4">
      <!-- Формулы -->
      <div class="col-md-6">
        <div class="card h-100 d-flex flex-column">
          <div class="card-header text-white py-3" :style="{ backgroundColor: color }">
            <h5 class="mb-0">Формулы</h5>
          </div>
          <div class="card-body d-flex flex-column flex-grow-1 p-3">
            <div class="d-flex flex-column gap-3">
              <div class="d-flex align-items-center justify-content-between p-3 bg-light rounded">
                <div class="d-flex align-items-center gap-3">
                  <div class="d-flex justify-content-center align-items-center bg-primary bg-opacity-10 rounded-circle" style="width: 40px; height: 40px;">
                    <Calculator :size="20" class="text-primary" />
                  </div>
                  <span class="text-muted">Обычные уравнения</span>
                </div>
                <span class="fw-bold fs-5">{{ formulaStats.ordinary }}</span>
              </div>
              <div class="d-flex align-items-center justify-content-between p-3 bg-light rounded">
                <div class="d-flex align-items-center gap-3">
                  <div class="d-flex justify-content-center align-items-center bg-success bg-opacity-10 rounded-circle" style="width: 40px; height: 40px;">
                    <GitBranch :size="20" class="text-success" />
                  </div>
                  <span class="text-muted">Системы уравнений</span>
                </div>
                <span class="fw-bold fs-5">{{ formulaStats.system }}</span>
              </div>
              <div class="d-flex align-items-center justify-content-between p-3 bg-light rounded">
                <div class="d-flex align-items-center gap-3">
                  <div class="d-flex justify-content-center align-items-center bg-info bg-opacity-10 rounded-circle" style="width: 40px; height: 40px;">
                    <Building :size="20" class="text-info" />
                  </div>
                  <span class="text-muted">Для помещений</span>
                </div>
                <span class="fw-bold fs-5">{{ formulaStats.forPremises }}</span>
              </div>
              <div class="d-flex align-items-center justify-content-between p-3 bg-light rounded">
                <div class="d-flex align-items-center gap-3">
                  <div class="d-flex justify-content-center align-items-center bg-warning bg-opacity-10 rounded-circle" style="width: 40px; height: 40px;">
                    <LayoutGrid :size="20" class="text-warning" />
                  </div>
                  <span class="text-muted">По комнатам</span>
                </div>
                <span class="fw-bold fs-5">{{ formulaStats.perRoom }}</span>
              </div>
            </div>
            <button class="btn btn-outline-primary w-100 mt-auto" @click="goToFormulas">Настроить формулы</button>
          </div>
        </div>
      </div>

      <!-- Анкета -->
      <div class="col-md-6">
        <div class="card h-100 d-flex flex-column">
          <div class="card-header text-white py-3" :style="{ backgroundColor: color }">
            <h5 class="mb-0">Анкета</h5>
          </div>
          <div class="card-body d-flex flex-column flex-grow-1 p-3">
            <div class="d-flex flex-column gap-3">
              <div class="d-flex align-items-center justify-content-between p-3 bg-light rounded">
                <div class="d-flex align-items-center gap-3">
                  <div class="d-flex justify-content-center align-items-center bg-primary bg-opacity-10 rounded-circle" style="width: 40px; height: 40px;">
                    <MessageSquare :size="20" class="text-primary" />
                  </div>
                  <span class="text-muted">Общие вопросы</span>
                </div>
                <span class="fw-bold fs-5">{{ surveyStats.general }}</span>
              </div>
              <div class="d-flex align-items-center justify-content-between p-3 bg-light rounded">
                <div class="d-flex align-items-center gap-3">
                  <div class="d-flex justify-content-center align-items-center bg-success bg-opacity-10 rounded-circle" style="width: 40px; height: 40px;">
                    <Home :size="20" class="text-success" />
                  </div>
                  <span class="text-muted">По помещениям (всего)</span>
                </div>
                <span class="fw-bold fs-5">{{ surveyStats.room_total }}</span>
              </div>
            </div>
            <button class="btn btn-outline-primary w-100 mt-auto" @click="goToSurvey">Настроить анкету</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Calculator, GitBranch, Building, LayoutGrid, MessageSquare, Home } from 'lucide-vue-next'
import { apiClient } from '../../../../core/client/src/js/api/manager'
import { roomAnalyticsEndpoints } from '../js/endpoints'
const router = useRouter()
const route = useRoute()

const criterionName = ref('Безопасность')
const color = ref('#dc3545')
const isLoading = ref(true)
const formulaStats = ref()

const surveyStats = ref(null)

onMounted(async () => {
  const criterionId = route.params.criterionId
  const response = await apiClient.get(roomAnalyticsEndpoints.roomAnalytics.CruteriesSurvey(criterionId));
  criterionName.value = response.data['name']
  surveyStats.value = response.data['questions'];
  formulaStats.value = response.data['formulas']
  isLoading.value = false;
})

function goBack() {
  router.back()
}

function goToFormulas() {
  const id = route.params.criterionId
  router.push({ name: "FormulaCustomPage", params: { criterionId: id } })
}

function goToSurvey() {
  
  const id = route.params.criterionId
  router.push({ name: "FormCustomPage", params: { criterionId: id } })
}
</script>