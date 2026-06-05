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
      
      <!-- ═══════════════════════════════════════════════════════════════
           РЕЖИМ 1: Обычные формулы + анкета (is_counting_by_system_equastion = false)
      ═══════════════════════════════════════════════════════════════ -->
      <div v-if="!isSystemMode" class="col-md-6">
        <div class="card h-100 d-flex flex-column">
          <div class="card-header text-white py-3" :style="{ backgroundColor: criterionColor }">
            <h5 class="mb-0">Формулы и параметры</h5>
          </div>
          <div class="card-body d-flex flex-column flex-grow-1 p-3">
            <div class="d-flex flex-column gap-3">
              
              <div class="d-flex align-items-center justify-content-between p-3 bg-light rounded">
                <div class="d-flex align-items-center gap-3">
                  <div class="d-flex justify-content-center align-items-center rounded-circle" 
                       :style="{ backgroundColor: criterionColor + '22', color: criterionColor }"
                       style="width: 40px; height: 40px;">
                    <Calculator :size="20" />
                  </div>
                  <span class="text-muted">Обычные уравнения</span>
                </div>
                <span class="fw-bold fs-5">{{ formulaStats.formulas_count }}</span>
              </div>

              <div class="d-flex align-items-center justify-content-between p-3 bg-light rounded">
                <div class="d-flex align-items-center gap-3">
                  <div class="d-flex justify-content-center align-items-center rounded-circle" 
                       :style="{ backgroundColor: criterionColor + '22', color: criterionColor }"
                       style="width: 40px; height: 40px;">
                    <GitBranch :size="20" />
                  </div>
                  <span class="text-muted">Системы уравнений</span>
                </div>
                <span class="fw-bold fs-5">{{ formulaStats.systems_count }}</span>
              </div>

              <div class="d-flex align-items-center justify-content-between p-3 bg-light rounded">
                <div class="d-flex align-items-center gap-3">
                  <div class="d-flex justify-content-center align-items-center rounded-circle" 
                       :style="{ backgroundColor: criterionColor + '22', color: criterionColor }"
                       style="width: 40px; height: 40px;">
                    <SlidersHorizontal :size="20" />
                  </div>
                  <span class="text-muted">Параметры ввода</span>
                </div>
                <span class="fw-bold fs-5">{{ formulaStats.parameters_count }}</span>
              </div>

              <div class="d-flex align-items-center justify-content-between p-3 bg-light rounded">
                <div class="d-flex align-items-center gap-3">
                  <div class="d-flex justify-content-center align-items-center rounded-circle" 
                       :style="{ backgroundColor: criterionColor + '22', color: criterionColor }"
                       style="width: 40px; height: 40px;">
                    <Lock :size="20" />
                  </div>
                  <span class="text-muted">Параметры ограничений</span>
                </div>
                <span class="fw-bold fs-5">{{ formulaStats.limit_params_count }}</span>
              </div>

              <div class="d-flex align-items-center justify-content-between p-3 bg-light rounded">
                <div class="d-flex align-items-center gap-3">
                  <div class="d-flex justify-content-center align-items-center rounded-circle" 
                       :style="{ backgroundColor: criterionColor + '22', color: criterionColor }"
                       style="width: 40px; height: 40px;">
                    <Cog :size="20" />
                  </div>
                  <span class="text-muted">Авторасчитываемые параметры</span>
                </div>
                <span class="fw-bold fs-5">{{ formulaStats.auto_params_count }}</span>
              </div>

            </div>
            <button class="btn btn-outline-primary w-100 mt-auto" @click="goToFormulas">Настроить формулы</button>
          </div>
        </div>
      </div>

      <!-- Анкета (показывается только в обычном режиме) -->
      <div v-if="!isSystemMode" class="col-md-6">
        <div class="card h-100 d-flex flex-column">
          <div class="card-header text-white py-3" :style="{ backgroundColor: criterionColor }">
            <h5 class="mb-0">Анкета</h5>
          </div>
          <div class="card-body d-flex flex-column flex-grow-1 p-3">
            <div class="d-flex flex-column gap-3">
              <div class="d-flex align-items-center justify-content-between p-3 bg-light rounded">
                <div class="d-flex align-items-center gap-3">
                  <div class="d-flex justify-content-center align-items-center rounded-circle" 
                       :style="{ backgroundColor: criterionColor + '22', color: criterionColor }"
                       style="width: 40px; height: 40px;">
                    <MessageSquare :size="20" />
                  </div>
                  <span class="text-muted">Общие вопросы</span>
                </div>
                <span class="fw-bold fs-5">{{ surveyStats.general }}</span>
              </div>
              <div class="d-flex align-items-center justify-content-between p-3 bg-light rounded">
                <div class="d-flex align-items-center gap-3">
                  <div class="d-flex justify-content-center align-items-center rounded-circle" 
                       :style="{ backgroundColor: criterionColor + '22', color: criterionColor }"
                       style="width: 40px; height: 40px;">
                    <Home :size="20" />
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

      <!-- ═══════════════════════════════════════════════════════════════
           РЕЖИМ 2: Система уравнений (is_counting_by_system_equastion = true)
      ═══════════════════════════════════════════════════════════════ -->
      <div v-else class="col-12">
        <div class="card">
          <div class="card-header text-white py-3" :style="{ backgroundColor: criterionColor }">
            <h5 class="mb-0">Система уравнений</h5>
            <small class="d-block mt-1 opacity-75">Расчёт показателя через систему уравнений</small>
          </div>
          <div class="card-body p-3">
            <div class="row g-3">
              
              <div class="col-md-4">
                <div class="d-flex align-items-center justify-content-between p-3 bg-light rounded h-100">
                  <div class="d-flex align-items-center gap-3">
                    <div class="d-flex justify-content-center align-items-center rounded-circle" 
                         :style="{ backgroundColor: criterionColor + '22', color: criterionColor }"
                         style="width: 40px; height: 40px;">
                      <Sigma :size="20" />
                    </div>
                    <span class="text-muted">Уравнений в системе</span>
                  </div>
                  <span class="fw-bold fs-5">{{ formulaStats.equations_count }}</span>
                </div>
              </div>

              <div class="col-md-4">
                <div class="d-flex align-items-center justify-content-between p-3 bg-light rounded h-100">
                  <div class="d-flex align-items-center gap-3">
                    <div class="d-flex justify-content-center align-items-center rounded-circle" 
                         :style="{ backgroundColor: criterionColor + '22', color: criterionColor }"
                         style="width: 40px; height: 40px;">
                      <SlidersHorizontal :size="20" />
                    </div>
                    <span class="text-muted">Используемых переменных</span>
                  </div>
                  <span class="fw-bold fs-5">{{ formulaStats.variables_count }}</span>
                </div>
              </div>

              <div class="col-md-4">
                <div class="d-flex align-items-center justify-content-between p-3 bg-light rounded h-100">
                  <div class="d-flex align-items-center gap-3">
                    <div class="d-flex justify-content-center align-items-center rounded-circle" 
                         :style="{ backgroundColor: criterionColor + '22', color: criterionColor }"
                         style="width: 40px; height: 40px;">
                      <GitBranch :size="20" />
                    </div>
                    <span class="text-muted">Других критериев</span>
                  </div>
                  <span class="fw-bold fs-5">{{ formulaStats.other_criteria_count }}</span>
                </div>
              </div>

            </div>
            <button class="btn btn-outline-primary w-100 mt-4" @click="goToSystemEquation">
              Редактировать систему уравнений
            </button>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Calculator, GitBranch, MessageSquare, Home, 
  SlidersHorizontal, Lock, Cog, Sigma
} from 'lucide-vue-next'
import { apiClient } from '../../../../core/client/src/js/api/manager'
import { roomAnalyticsEndpoints } from '../js/endpoints'

const router = useRouter()
const route = useRoute()

const criterionName = ref('')
const criterionColor = ref('#dc3545') // Цвет по умолчанию
const isLoading = ref(true)
const isSystemMode = ref(false)

const formulaStats = ref({})
const surveyStats = ref({ general: 0, room_total: 0 })

onMounted(async () => {
  const criterionId = route.params.criterionId
  try {
    const response = await apiClient.get(
      roomAnalyticsEndpoints.roomAnalytics.CruteriesSurvey(criterionId)
    )
    const data = response.data
    criterionName.value = data.name
    criterionColor.value = data.color || '#dc3545'
    isSystemMode.value = !!data.is_counting_by_system_equastion
    
    surveyStats.value = data.questions || { general: 0, room_total: 0 }
    formulaStats.value = data.formulas || {}
    
  } catch (err) {
    console.error('Ошибка загрузки статистики:', err)
  } finally {
    isLoading.value = false
  }
})

function goBack() { router.back() }
function goToFormulas() {
  router.push({ name: 'FormulaCustomPage', params: { criterionId: route.params.criterionId } })
}
function goToSurvey() {
  router.push({ name: 'FormCustomPage', params: { criterionId: route.params.criterionId } })
}
function goToSystemEquation() {
  router.push({ 
    name: 'CriterionSystemEquationPage', 
    params: { criterionId: route.params.criterionId } 
  })
}
</script>