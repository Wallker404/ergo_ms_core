<template>
  <div class="container-fluid py-3">
    <!-- Заголовок с кнопками действий -->
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h4 class="mb-0">Критерии эргономичности</h4>
      <div class="d-flex gap-2">
        <button class="btn btn-outline-primary" @click="showAddForm = !showAddForm">
          {{ showAddForm ? 'Отменить' : 'Добавить критерий' }}
        </button>
        <button 
          class="btn btn-success" 
          @click="saveCriteria"
          :disabled="isLoading"
        >
          <span v-if="isLoading" class="spinner-border spinner-border-sm me-2" role="status"></span>
          {{ isLoading ? 'Сохранение...' : 'Сохранить изменения' }}
        </button>
      </div>
    </div>

    <!-- Форма добавления -->
    <div v-if="showAddForm" class="card mb-4 border-primary">
      <div class="card-body">
        <h6 class="card-subtitle mb-3 text-muted">Новый критерий</h6>
        <div class="row g-3 align-items-end">
          <div class="col-md-3">
            <label class="form-label small">Название</label>
            <input 
              type="text" 
              class="form-control" 
              v-model.trim="newCriterion.name" 
              placeholder="Введите название"
              @keyup.enter="addCriterion"
            />
          </div>
          <div class="col-md-2">
            <label class="form-label small">Имя переменной</label>
            <input 
              type="text" 
              class="form-control" 
              v-model.trim="newCriterion.var_name" 
              placeholder="Напр. C1"
              maxlength="15"
            />
          </div>
          <div class="col-md-2">
            <label class="form-label small">Вес (0–1)</label>
            <input 
              type="number" 
              class="form-control" 
              v-model.number="newCriterion.weight"
              min="0" max="1" step="0.01"
            />
          </div>
          <div class="col-md-3">
            <label class="form-label small">Способ вычисления</label>
            <div class="d-flex align-items-center gap-2 mt-1">
              <span class="small" :class="!newCriterion.is_counting_by_system_equastion ? 'fw-bold text-primary' : 'text-muted'">
                Анкетирование
              </span>
              <div class="form-check form-switch m-0">
                <input 
                  class="form-check-input" 
                  type="checkbox" 
                  role="switch"
                  id="newCountingType"
                  v-model="newCriterion.is_counting_by_system_equastion"
                />
              </div>
              <span class="small" :class="newCriterion.is_counting_by_system_equastion ? 'fw-bold text-primary' : 'text-muted'">
                Система уравнений
              </span>
            </div>
          </div>
          <div class="col-md-2">
            <button 
              class="btn btn-success w-100" 
              @click="addCriterion" 
              :disabled="!canCreate || addLoading"
            >
              <span v-if="addLoading" class="spinner-border spinner-border-sm me-1" role="status"></span>
              {{ addLoading ? '...' : 'Создать' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Сообщение об ошибке валидации -->
    <div v-if="validationError" class="alert alert-danger d-flex align-items-center" role="alert">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-exclamation-triangle-fill me-2 flex-shrink-0" viewBox="0 0 16 16">
        <path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767L8.982 1.566zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5zm.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2z"/>
      </svg>
      {{ validationError }}
    </div>

    <!-- Индикатор загрузки -->
    <div v-if="isLoading && !validationError" class="text-center py-5 text-muted">
      <span class="spinner-border spinner-border-sm me-2" role="status"></span>
      Загрузка критериев...
    </div>

    <!-- Сетка карточек -->
    <div v-else class="row g-4">
      <div 
        v-for="criterion in criteria" 
        :key="criterion.id" 
        class="col-md-6 col-lg-4"
      >
        <div class="card h-100 shadow-sm">
          <!-- Цветная шапка карточки -->
          <div 
            class="card-header d-flex justify-content-between align-items-center py-2"
            :style="{ backgroundColor: criterion.color || '#6c757d' }"
          >
            <h6 class="card-title mb-0 text-white fw-medium">{{ criterion.name }}</h6>
            <div class="dropdown">
              <button 
                class="btn btn-sm btn-light dropdown-toggle p-1" 
                type="button" 
                data-bs-toggle="dropdown"
                title="Изменить цвет"
              >
                <Palette size="16" />
              </button>
              <ul class="dropdown-menu dropdown-menu-end p-2" style="min-width: 180px;">
                <li class="mb-1 small text-muted px-2">Выберите цвет</li>
                <li>
                  <div class="d-flex flex-wrap gap-1">
                    <button 
                      v-for="color in colorPalette" 
                      :key="color"
                      class="btn btn-sm border-0 p-0"
                      :style="{ 
                        backgroundColor: color, 
                        width: '20px', 
                        height: '20px', 
                        borderRadius: '4px',
                        border: criterion.color === color ? '2px solid #000' : '1px solid rgba(0,0,0,0.1)'
                      }"
                      @click="updateColor(criterion.id, color)"
                      :title="color"
                    ></button>
                  </div>
                </li>
              </ul>
            </div>
          </div>
          
          <div class="card-body">
            <!-- Мета-информация -->
            <div class="small text-muted mb-3">
              <div class="d-flex justify-content-between">
                <span>Создан:</span>
                <span>{{ formatDate(criterion.createdAt) }}</span>
              </div>
              <div class="d-flex justify-content-between mt-1">
                <span>Статус:</span>
                <span :class="criterion.active ? 'text-success' : 'text-danger'">
                  {{ criterion.active ? 'Активен' : 'Неактивен' }}
                </span>
              </div>
            </div>

            <!-- 🔥 Имя переменной -->
            <div class="mb-3">
              <label class="form-label small d-flex justify-content-between">
                <span>Имя переменной</span>
                <span class="text-muted small">используется в формулах</span>
              </label>
              <input 
                type="text" 
                class="form-control form-control-sm"
                :class="{ 'is-invalid': !criterion.varName?.trim() }"
                :value="criterion.varName"
                @input="updateVarName(criterion.id, $event.target.value)"
                maxlength="15"
                placeholder="Напр. C1"
              />
              <div class="invalid-feedback">Имя переменной не может быть пустым</div>
            </div>

            <!-- 🔥 Способ вычисления (read-only) -->
            <div class="mb-3">
              <label class="form-label small">Способ вычисления</label>
              <div class="d-flex align-items-center gap-2 p-2 rounded" 
                   :style="{ backgroundColor: criterion.isCountingBySystemEquastion ? '#e7f1ff' : '#f8f9fa' }">
                <span 
                  class="badge" 
                  :class="criterion.isCountingBySystemEquastion ? 'bg-info' : 'bg-secondary'"
                >
                  {{ criterion.isCountingBySystemEquastion ? 'Система уравнений' : 'Анкетирование' }}
                </span>
                <small class="text-muted">
                  {{ criterion.isCountingBySystemEquastion 
                     ? 'Расчитывается на основе других критериев' 
                     : 'Вычисляется на основе данных анкеты' }}
                </small>
              </div>
              <small class="text-muted d-block mt-1">
                Тип расчёта задаётся при создании и не может быть изменён
              </small>
            </div>

            <!-- Переключатель активности -->
            <div class="form-check form-switch mb-3">
              <input 
                class="form-check-input" 
                type="checkbox" 
                :id="'active-' + criterion.id"
                :checked="criterion.active"
                @change="toggleActive(criterion.id)"
              />
              <label class="form-check-label small" :for="'active-' + criterion.id">
                Использовать в расчёте модели
              </label>
            </div>

            <!-- Вес критерия -->
            <div class="mb-3">
              <label class="form-label small d-flex justify-content-between">
                <span>Вес критерия</span>
                <span class="fw-bold">{{ criterion.weight?.toFixed(2) }}</span>
              </label>
              <div class="d-flex align-items-center gap-2">
                <input 
                  type="range" 
                  class="form-range flex-grow-1" 
                  min="0" max="1" step="0.01"
                  :value="criterion.weight"
                  @input="updateWeight(criterion.id, $event.target.value)"
                />
                <input 
                  type="number" 
                  class="form-control" 
                  style="max-width: 80px;"
                  :value="criterion.weight"
                  @change="updateWeight(criterion.id, $event.target.value)"
                  min="0" max="1" step="0.01"
                />
              </div>
              <div class="d-flex justify-content-between small text-muted mt-1">
                <span>0</span>
                <span>1</span>
              </div>
            </div>

            <!-- Шкала оценки -->
            <div>
              <label class="form-label small mb-2">Шкала оценки (0–10)</label>
              <div class="table-responsive">
                <table class="table table-sm table-borderless mb-0 small">
                  <thead>
                    <tr class="text-muted">
                      <th>Категория</th>
                      <th>Верхняя граница</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td class="align-middle">Ужасно</td>
                      <td>
                        <input 
                          type="number" 
                          class="form-control form-control-sm" 
                          :value="criterion.borders.terrible"
                          @change="updateBorder(criterion.id, 'terrible', $event.target.value)"
                          min="0.1" max="9.9" step="0.1"
                        />
                      </td>
                    </tr>
                    <tr>
                      <td class="align-middle">Плохо</td>
                      <td>
                        <input 
                          type="number" 
                          class="form-control form-control-sm" 
                          :value="criterion.borders.bad"
                          @change="updateBorder(criterion.id, 'bad', $event.target.value)"
                          :min="criterion.borders.terrible + 0.1"
                          :max="9.9" step="0.1"
                        />
                      </td>
                    </tr>
                    <tr>
                      <td class="align-middle">Нормально</td>
                      <td>
                        <input 
                          type="number" 
                          class="form-control form-control-sm" 
                          :value="criterion.borders.normal"
                          @change="updateBorder(criterion.id, 'normal', $event.target.value)"
                          :min="criterion.borders.bad + 0.1"
                          :max="9.9" step="0.1"
                        />
                      </td>
                    </tr>
                    <tr>
                      <td class="align-middle">Хорошо</td>
                      <td>
                        <input 
                          type="number" 
                          class="form-control form-control-sm" 
                          :value="criterion.borders.good"
                          @change="updateBorder(criterion.id, 'good', $event.target.value)"
                          :min="criterion.borders.normal + 0.1"
                          :max="9.9" step="0.1"
                        />
                      </td>
                    </tr>
                    <tr>
                      <td class="align-middle">Отлично</td>
                      <td class="text-muted">10 (фикс.)</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div class="small text-muted mt-1">
                Границы должны возрастать: 0 &lt; Ужасно &lt; Плохо &lt; Нормально &lt; Хорошо &lt; 10
              </div>
            </div>
          </div>
          
          <div class="card-footer bg-white border-top-0 pt-0">
            <div class="btn-group w-100" role="group">
              <button 
                class="btn btn-outline-secondary btn-sm" 
                @click="openMathModel(criterion.id)"
                title="Перейти к настройке математической модели"
              >
                <Settings size="14" class="me-1" /> Настроить мат. модель
              </button>
              <button 
                class="btn btn-outline-danger btn-sm" 
                @click="deleteCriterion(criterion.id)"
              >
                <Trash2 size="14" class="me-1" /> Удалить
              </button>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Пустое состояние -->
      <div v-if="criteria.length === 0 && !isLoading" class="col-12">
        <div class="card text-center py-5">
          <div class="card-body">
            <Palette size="48" class="text-muted mb-3" />
            <h6 class="text-muted">Список критериев пуст</h6>
            <p class="text-muted small mb-3">Добавьте первый критерий для начала работы</p>
            <button class="btn btn-primary btn-sm" @click="showAddForm = true">
              Добавить критерий
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Settings, Trash2, Palette } from 'lucide-vue-next'
import { apiClient } from '../../../../core/client/src/js/api/manager'
import { roomAnalyticsEndpoints } from '../js/endpoints'

const router = useRouter()

const colorPalette = [
  '#0d6efd', '#6610f2', '#6f42c1', '#d63384', '#dc3545',
  '#fd7e14', '#ffc107', '#198754', '#20c997', '#0dcaf0',
  '#343a40', '#6c757d', '#adb5bd', '#e83e8c', '#007bff',
  '#28a745', '#17a2b8'
]

const criteria = ref([])
const isLoading = ref(true)

const addLoading = ref(false)
const showAddForm = ref(false)
const validationError = ref('')

const newCriterion = ref({
  name: '',
  weight: 0.5,
  var_name: '',
  is_counting_by_system_equastion: false,
})

// Валидация формы создания
const canCreate = computed(() => {
  const n = newCriterion.value
  return n.name?.trim() 
      && n.var_name?.trim() 
      && n.var_name.length <= 15
})

// 🔁 Трансформер: Бэкенд → Фронтенд
function backendToFrontend(c) {
  return {
    id: c.id,
    name: c.name,
    createdAt: c.date_of_creation,
    active: c.is_active,
    weight: c.weight,
    color: c.color,
    varName: c.var_name || '',
    isCountingBySystemEquastion: !!c.is_counting_by_system_equastion,
    borders: {
      terrible: c.terrible_mark_border ?? 3,
      bad: c.bad_mark_border ?? 5,
      normal: c.normal_mark_border ?? 7,
      good: c.good_mark_border ?? 9
    }
  }
}

// 🔁 Трансформер: Фронтенд → Бэкенд
function frontendToBackend(c) {
  const b = c.borders || {}
  return {
    id: c.id,
    name: c.name,
    is_active: c.active,
    weight: c.weight,
    color: c.color,
    var_name: c.varName || '',
    // ⚠️ is_counting_by_system_equastion НЕ отправляем — его менять нельзя
    terrible_mark_border: b.terrible ?? 3,
    bad_mark_border: b.bad ?? 5,
    normal_mark_border: b.normal ?? 7,
    good_mark_border: b.good ?? 9
  }
}

async function fetchCriteria() {
  isLoading.value = true
  validationError.value = ''
  
  try {
    const response = await apiClient.get(roomAnalyticsEndpoints.roomAnalytics.CriteriesGet)
    criteria.value = (Array.isArray(response.data) ? response.data : response).map(backendToFrontend)
  } catch (error) {
    console.error('Ошибка загрузки критериев:', error)
    validationError.value = 'Не удалось загрузить критерии: ' + (error.message || 'Ошибка сети')
    criteria.value = []
  } finally {
    isLoading.value = false
  }
}

function formatDate(dateString) {
  if (!dateString) return '—'
  const date = new Date(dateString)
  return date.toLocaleDateString('ru-RU', { day: '2-digit', month: 'short', year: 'numeric' })
}

async function addCriterion() {
  if (!canCreate.value || addLoading.value) return
  
  addLoading.value = true
  validationError.value = ''
  
  try {
    const response = await apiClient.post(
      roomAnalyticsEndpoints.roomAnalytics.CriteriesAdd,
      {
        name: newCriterion.value.name.trim(),
        weight: newCriterion.value.weight,
        var_name: newCriterion.value.var_name.trim(),
        is_counting_by_system_equastion: newCriterion.value.is_counting_by_system_equastion,
      }
    )
    
    const newBackendObj = response.data?.object || response.data
    if (newBackendObj) {
      criteria.value.unshift(backendToFrontend(newBackendObj))
    } else {
      await fetchCriteria()
    }
    
    newCriterion.value = {
      name: '',
      weight: 0.5,
      var_name: '',
      is_counting_by_system_equastion: false,
    }
    showAddForm.value = false
    
  } catch (error) {
    console.error('Ошибка добавления:', error)
    validationError.value = error.response?.data?.error || error.message || 'Ошибка при добавлении'
  } finally {
    addLoading.value = false
  }
}

async function deleteCriterion(id) {
  if (!confirm('Удалить этот критерий? Это действие нельзя отменить.')) return
  try {
    await apiClient.delete(roomAnalyticsEndpoints.roomAnalytics.Criteriesdelete(id))
    criteria.value = criteria.value.filter(c => c.id !== id)
    console.log(`Критерий #${id} удалён`)
  } catch (error) {
    console.error(`Ошибка удаления критерия #${id}:`, error)
    const errorMsg = error.response?.data?.error || error.message || 'Не удалось удалить критерий'
    alert('Ошибка: ' + errorMsg)
  }
}

function updateColor(id, color) {
  const c = criteria.value.find(c => c.id === id)
  if (c) c.color = color
}

function toggleActive(id) {
  const c = criteria.value.find(c => c.id === id)
  if (c) c.active = !c.active
}

function updateWeight(id, value) {
  const c = criteria.value.find(c => c.id === id)
  if (c) {
    const numValue = parseFloat(value)
    c.weight = Math.max(0, Math.min(1, isNaN(numValue) ? 0 : numValue))
  }
}

function updateVarName(id, value) {
  const c = criteria.value.find(c => c.id === id)
  if (c) {
    // Обрезаем до 15 символов
    c.varName = (value || '').slice(0, 15)
  }
}

function updateBorder(criterionId, borderName, value) {
  const c = criteria.value.find(c => c.id === criterionId)
  if (!c || !c.borders) return
  
  const numValue = parseFloat(value)
  if (isNaN(numValue)) return
  
  const clamped = Math.max(0.1, Math.min(9.9, numValue))
  c.borders[borderName] = clamped
  
  const order = ['terrible', 'bad', 'normal', 'good']
  const idx = order.indexOf(borderName)
  
  if (idx > 0) {
    const prevBorder = order[idx - 1]
    if (c.borders[borderName] <= c.borders[prevBorder] + 0.01) {
      c.borders[prevBorder] = Math.max(0.1, c.borders[borderName] - 0.1)
    }
  }
  if (idx < order.length - 1) {
    const nextBorder = order[idx + 1]
    if (c.borders[borderName] >= c.borders[nextBorder] - 0.01) {
      c.borders[nextBorder] = Math.min(9.9, c.borders[borderName] + 0.1)
    }
  }
}

function openMathModel(id) {
  router.push({ name: 'FunctionsAndFormPage', params: { criterionId: id } })
}

// Валидация весов
function validateWeights() {
  const activeCriteria = criteria.value.filter(c => c.active)
  const totalWeight = activeCriteria.reduce((sum, c) => sum + (c.weight || 0), 0)
  const diff = Math.abs(totalWeight - 1)
  
  if (diff > 0.001) {
    return `Сумма весов активных критериев должна быть равна 1. Сейчас: ${totalWeight.toFixed(2)}`
  }
  return null
}

// Валидация границ
function validateBorders() {
  for (const c of criteria.value) {
    const b = c.borders
    if (!b) continue
    
    if (b.terrible <= 0) {
      return `Критерий "${c.name}": граница "Ужасно" должна быть > 0`
    }
    
    const borders = [0, b.terrible, b.bad, b.normal, b.good, 10]
    for (let i = 0; i < borders.length - 1; i++) {
      if (borders[i] >= borders[i + 1] - 0.001) {
        const labels = ['0', 'Ужасно', 'Плохо', 'Нормально', 'Хорошо', '10']
        return `Критерий "${c.name}": границы должны строго возрастать (${labels[i]} < ${labels[i+1]})`
      }
    }
  }
  return null
}

// Валидация имён переменных
function validateVarNames() {
  const names = criteria.value.map(c => c.varName?.trim()).filter(Boolean)
  
  // Проверка на пустые
  const empty = criteria.value.find(c => !c.varName?.trim())
  if (empty) {
    return `Критерий "${empty.name}": имя переменной не может быть пустым`
  }
  
  // Проверка длины
  const tooLong = criteria.value.find(c => (c.varName || '').length > 15)
  if (tooLong) {
    return `Критерий "${tooLong.name}": имя переменной не должно превышать 15 символов`
  }
  
  // Проверка уникальности
  const unique = new Set(names)
  if (unique.size !== names.length) {
    return 'Имена переменных должны быть уникальными'
  }
  
  return null
}

async function saveCriteria() {
  validationError.value = ''
  
  const weightError = validateWeights()
  if (weightError) { validationError.value = weightError; return }
  
  const borderError = validateBorders()
  if (borderError) { validationError.value = borderError; return }
  
  const varNameError = validateVarNames()
  if (varNameError) { validationError.value = varNameError; return }
  
  isLoading.value = true
  
  try {
    const backendPayload = criteria.value.map(frontendToBackend)
    
    const response = await apiClient.put(
      roomAnalyticsEndpoints.roomAnalytics.CriteriesUpdate,
      backendPayload
    )
    
    console.log('Критерии сохранены:', response.data)
    
    if (response.data?.objects && Array.isArray(response.data.objects)) {
      criteria.value = response.data.objects.map(backendToFrontend)
    }
    
    alert('Критерии успешно сохранены!')
    
  } catch (error) {
    console.error('Ошибка сохранения:', error)
    validationError.value = 'Ошибка при сохранении: ' + (error.response?.data?.error || error.message || 'Ошибка сети')
  } finally {
    isLoading.value = false
  }
}

onMounted(fetchCriteria)
</script>

<style scoped>
.dropdown-menu { box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15); }
.card-header .dropdown-toggle::after { display: none; }
input[type="number"]::-webkit-inner-spin-button,
input[type="number"]::-webkit-outer-spin-button { opacity: 1; }
.table td { vertical-align: middle; }
</style>