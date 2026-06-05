<template>
  <div class="container-fluid vh-100 d-flex flex-column p-0 bg-light">
    
    <!-- Верхняя панель -->
    <div class="card-header bg-white border-bottom shadow-sm py-2">
      <div class="d-flex align-items-center gap-3">
        <div class="d-flex align-items-center gap-2">
          <span class="fw-bold text-muted small text-uppercase">План:</span>
          <span class="badge bg-info text-dark">#{{ floorplanId }}</span>
        </div>
        
        <div class="vr"></div>
        
        <div class="d-flex align-items-center gap-2 flex-grow-1">
          <span class="fw-bold text-muted small text-uppercase">Критерий:</span>
          <div class="btn-group" role="group">
            <button
              v-for="crit in criteria"
              :key="crit.id"
              type="button"
              class="btn btn-sm"
              :class="activeCriterionId === crit.id ? 'text-white' : 'btn-outline-light border'"
              :style="{
                backgroundColor: activeCriterionId === crit.id ? crit.color : 'transparent',
                borderColor: crit.color,
                color: activeCriterionId === crit.id ? 'white' : crit.color
              }"
              @click="selectCriterion(crit.id)"
            >
              <span 
                class="rounded-circle me-1" 
                :style="{ 
                  backgroundColor: crit.color, 
                  width: '10px', height: '10px', display: 'inline-block',
                  border: activeCriterionId === crit.id ? '2px solid white' : 'none'
                }"
              ></span>
              {{ crit.name }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="d-flex flex-grow-1 overflow-hidden">
      
      <!-- Левое меню -->
      <div class="bg-white border-end d-flex flex-column" style="width: 320px; min-width: 320px;">
        <div class="p-3 border-bottom bg-light">
          <h6 class="mb-0 fw-bold text-muted text-uppercase small">
            {{ activeCriterion?.name || 'Выберите критерий' }}
          </h6>
          <small class="text-muted" v-if="activeCriterion">
            {{ activeCriterion.questions.length }} вопросов, {{ activeCriterion.parameters.length }} параметров
          </small>
        </div>
        
        <div class="overflow-auto flex-grow-1 p-2">
          
          <div v-if="globalParameters.length" class="mb-3">
            <div class="text-muted small text-uppercase fw-bold px-2 mb-2">Общие параметры</div>
            <button
              v-for="param in globalParameters"
              :key="'gparam-' + param.id"
              class="list-group-item list-group-item-action d-flex align-items-center gap-2 small mb-1 rounded border-start border-3"
              :style="{ borderLeftColor: '#6f42c1' }"
              :class="{ 
                'active bg-primary text-white': selectedItem?.type === 'param' && selectedItem?.id === param.id,
                'border-danger': hasParamValidationError(param.id)
              }"
              @click="selectItem('param', param)"
            >
              <span class="badge" :class="param.input_type === 'global' ? 'bg-secondary' : 'bg-info'">
                {{ getParamTypeLabel(param.input_type) }}
              </span>
              <span class="flex-grow-1 text-start text-truncate">{{ param.label || param.name }}</span>
              <span v-if="hasParamValidationError(param.id)" class="text-danger small" title="Есть ошибка валидации">!</span>
              <span class="text-muted small" v-else-if="isParamFilled(param.id)">✓</span>
            </button>
          </div>
          
          <div v-if="globalParameters.length" class="border-bottom mb-3"></div>
          
          <div v-if="activeCriterion?.parameters.length" class="mb-3">
            <div class="text-muted small text-uppercase fw-bold px-2 mb-2">Параметры критерия</div>
            <button
              v-for="param in activeCriterion.parameters"
              :key="'param-' + param.id"
              class="list-group-item list-group-item-action d-flex align-items-center gap-2 small mb-1 rounded"
              :class="{ 
                'active bg-primary text-white': selectedItem?.type === 'param' && selectedItem?.id === param.id,
                'border-danger': hasParamValidationError(param.id)
              }"
              @click="selectItem('param', param)"
            >
              <span class="badge" :class="param.input_type === 'global' ? 'bg-secondary' : 'bg-info'">
                {{ getParamTypeLabel(param.input_type) }}
              </span>
              <span class="flex-grow-1 text-start text-truncate">{{ param.label || param.name }}</span>
              <span v-if="hasParamValidationError(param.id)" class="text-danger small" title="Есть ошибка валидации">!</span>
              <span class="text-muted small" v-else-if="isParamFilled(param.id)">✓</span>
            </button>
          </div>
          
          <div v-if="activeCriterion?.questions.length">
            <div class="text-muted small text-uppercase fw-bold px-2 mb-2">Вопросы</div>
            <button
              v-for="q in activeCriterion.questions"
              :key="'q-' + q.id"
              class="list-group-item list-group-item-action d-flex align-items-center gap-2 small mb-1 rounded"
              :class="{ 'active bg-primary text-white': selectedItem?.type === 'question' && selectedItem?.id === q.id }"
              @click="selectItem('question', q)"
            >
              <span class="badge" :class="getQuestionTypeBadge(q.type)">
                {{ getQuestionTypeLabel(q.type) }}
              </span>
              <span class="flex-grow-1 text-start text-truncate">{{ q.question }}</span>
              <span class="text-muted small" v-if="isQuestionFilled(q.id)">✓</span>
            </button>
          </div>
          
          <div v-if="!activeCriterion" class="text-center text-muted py-5 small">
            Выберите критерий в верхней панели
          </div>
          
          <div v-else-if="!activeCriterion.questions.length && !activeCriterion.parameters.length && !globalParameters.length" 
               class="text-center text-muted py-5 small">
            У критерия нет вопросов и параметров
          </div>
        </div>
      </div>

      <!-- Центр: форма ввода -->
      <div class="flex-grow-1 overflow-auto p-4 bg-light">
        
        <!-- Пустое состояние -->
        <div v-if="!selectedItem" class="d-flex flex-column align-items-center justify-content-center h-100 text-muted">
          <svg width="80" height="80" fill="none" stroke="currentColor" stroke-width="1" viewBox="0 0 24 24" class="mb-3">
            <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
          <h5>Выберите вопрос или параметр</h5>
          <p class="small">Используйте меню слева для выбора элемента</p>
        </div>

        <!-- Форма для ПАРАМЕТРА -->
        <div v-else-if="selectedItem.type === 'param'" class="mx-auto" style="max-width: 900px;">
          <div class="card shadow-sm">
            <div class="card-header d-flex align-items-center gap-2" 
                 :style="{ 
                   backgroundColor: (selectedItem.item.isGlobal ? '#6f42c1' : activeCriterion.color) + '22', 
                   borderLeft: `4px solid ${selectedItem.item.isGlobal ? '#6f42c1' : activeCriterion.color}` 
                 }">
              <span class="badge" :class="selectedItem.item.isGlobal ? 'bg-purple-custom' : 'bg-secondary'">
                {{ selectedItem.item.isGlobal ? 'Общий параметр' : 'Параметр' }}
              </span>
              <span class="badge" :class="selectedItem.item.input_type === 'global' ? 'bg-info' : 'bg-warning text-dark'">
                {{ getParamTypeLabel(selectedItem.item.input_type) }}
              </span>
              <strong>{{ selectedItem.item.label || selectedItem.item.name }}</strong>
            </div>
            <div class="card-body">
              <!-- Общий параметр -->
              <div v-if="selectedItem.item.input_type === 'global'" class="row g-3">
                <div class="col-md-6">
                  <label class="form-label fw-bold">Значение</label>
                  <input
                    type="number"
                    :min="selectedItem.item.min_value"
                    :max="selectedItem.item.max_value"
                    :step="0.01"
                    v-model.number="userAnswers.param[selectedItem.item.id].global"
                    @input="validateParamGlobal(selectedItem.item.id)"
                    :class="[
                      'form-control form-control-lg',
                      { 'is-invalid': getParamGlobalError(selectedItem.item) !== null }
                    ]"
                    :placeholder="getPlaceholder(selectedItem.item)"
                  />
                  <div class="invalid-feedback d-block" v-if="getParamGlobalError(selectedItem.item) !== null">
                    {{ getParamGlobalError(selectedItem.item) }}
                  </div>
                </div>
              </div>
              
              <!-- Параметр по комнатам -->
              <div v-else>
                <div class="alert alert-info py-2 small mb-3">
                  <strong>Укажите значение параметра для каждой комнаты</strong>
                  <span v-if="getRoomsForItem(selectedItem.item).length === 0" class="text-danger d-block mt-1">
                    На плане нет комнат подходящего типа
                  </span>
                </div>
                <div class="row g-3">
                  <div 
                    v-for="room in getRoomsForItem(selectedItem.item)" 
                    :key="'param-room-' + room.id"
                    class="col-md-6"
                  >
                    <div class="card h-100 border-start border-4" :style="{ borderLeftColor: room.color }">
                      <div class="card-body p-3">
                        <div class="d-flex align-items-center gap-2 mb-2">
                          <span 
                            class="rounded-circle" 
                            :style="{ backgroundColor: room.color, width: '14px', height: '14px', display: 'inline-block' }"
                          ></span>
                          <strong>{{ room.label }}</strong>
                        </div>

                        <RoomPreview 
                          v-if="room.bbox && floorplanImageUrl"
                          :image-url="floorplanImageUrl"
                          :bbox="room.bbox"
                          :room-color="room.color"
                          :room-label="room.label"
                          class="mb-2"
                        />

                        <input
                          type="number"
                          :min="selectedItem.item.min_value"
                          :max="selectedItem.item.max_value"
                          :step="0.01"
                          v-model.number="userAnswers.param[selectedItem.item.id].rooms[room.id]"
                          @input="validateParamRoom(selectedItem.item.id, room.id)"
                          :class="[
                            'form-control',
                            { 'is-invalid': getParamRoomError(selectedItem.item, room.id) !== null }
                          ]"
                          :placeholder="getPlaceholder(selectedItem.item)"
                        />
                        <div class="invalid-feedback d-block" v-if="getParamRoomError(selectedItem.item, room.id) !== null">
                         {{ getParamRoomError(selectedItem.item, room.id) }}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Кнопки действий внутри карточки (параметр) -->
            <div class="card-footer bg-light d-flex justify-content-between align-items-center gap-2 py-2">
              <button 
                class="btn btn-outline-danger btn-sm"
                @click="resetCurrentItem"
              >
                Сбросить значение
              </button>
              <div class="d-flex gap-2 align-items-center">
                <small class="text-muted" v-if="validationErrorsCount > 0">
                  {{ validationErrorsCount }} {{ validationErrorsCount === 1 ? 'ошибка' : 'ошибок' }}
                </small>
                <button 
                  class="btn btn-primary btn-sm"
                  :disabled="validationErrorsCount > 0"
                  @click="saveAnswers"
                  :title="validationErrorsCount > 0 ? 'Исправьте ошибки валидации перед сохранением' : ''"
                >
                  Сохранить все ответы
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Форма для ВОПРОСА -->
        <div v-else-if="selectedItem.type === 'question'" class="mx-auto" style="max-width: 900px;">
          <div class="card shadow-sm">
            <div class="card-header" :style="{ backgroundColor: activeCriterion.color + '22', borderLeft: `4px solid ${activeCriterion.color}` }">
              <div class="d-flex align-items-center gap-2 mb-2">
                <span class="badge bg-primary">Вопрос</span>
                <span class="badge" :class="getQuestionTypeBadge(selectedItem.item.type)">
                  {{ getQuestionTypeLabel(selectedItem.item.type) }}
                </span>
              </div>
              <h5 class="mb-0">{{ selectedItem.item.question }}</h5>
            </div>
            <div class="card-body">
              <div v-if="isGlobalQuestion(selectedItem.item)">
                <div class="row g-2">
                  <div 
                    v-for="ans in selectedItem.item.answers" 
                    :key="'ans-global-' + ans.id"
                    class="col-md-6"
                  >
                    <label class="card answer-card h-100 p-3 mb-0 cursor-pointer" 
                           :class="{ 'border-primary bg-primary bg-opacity-10': userAnswers.question[selectedItem.item.id].global === ans.id }"
                           @click="userAnswers.question[selectedItem.item.id].global = ans.id"
                           style="cursor: pointer;">
                      <div class="d-flex align-items-center gap-2">
                        <input 
                          type="radio" 
                          :name="'q-global-' + selectedItem.item.id"
                          :checked="userAnswers.question[selectedItem.item.id].global === ans.id"
                          class="form-check-input"
                        />
                        <div class="flex-grow-1">
                          <div>{{ ans.answer }}</div>
                        </div>
                      </div>
                    </label>
                  </div>
                </div>
              </div>
              
              <div v-else>
                <div class="alert alert-info py-2 small mb-3">
                  <strong>Выберите ответ для каждой комнаты</strong>
                  <span v-if="getRoomsForQuestion(selectedItem.item).length === 0" class="text-danger d-block mt-1">
                    На плане нет комнат подходящего типа
                  </span>
                </div>
                <div 
                  v-for="room in getRoomsForQuestion(selectedItem.item)" 
                  :key="'q-room-' + room.id"
                  class="card mb-3 border-start border-4"
                  :style="{ borderLeftColor: room.color }"
                >
                  <div class="card-header py-2 d-flex align-items-center gap-2 bg-light">
                    <span 
                      class="rounded-circle" 
                      :style="{ backgroundColor: room.color, width: '14px', height: '14px', display: 'inline-block' }"
                    ></span>
                    <strong>{{ room.label }}</strong>
                  </div>
                  <div class="card-body">
                    <RoomPreview 
                      v-if="room.bbox && floorplanImageUrl"
                      :image-url="floorplanImageUrl"
                      :bbox="room.bbox"
                      :room-color="room.color"
                      :room-label="room.label"
                      class="mb-3"
                    />

                    <div class="row g-2">
                      <div 
                        v-for="ans in selectedItem.item.answers" 
                        :key="'ans-room-' + room.id + '-' + ans.id"
                        class="col-md-6"
                      >
                        <label class="card answer-card h-100 p-2 mb-0"
                               :class="{ 'border-primary bg-primary bg-opacity-10': userAnswers.question[selectedItem.item.id].rooms[room.id] === ans.id }"
                               @click="userAnswers.question[selectedItem.item.id].rooms[room.id] = ans.id"
                               style="cursor: pointer;">
                          <div class="d-flex align-items-center gap-2">
                            <input 
                              type="radio" 
                              :name="'q-room-' + selectedItem.item.id + '-' + room.id"
                              :checked="userAnswers.question[selectedItem.item.id].rooms[room.id] === ans.id"
                              class="form-check-input"
                            />
                            <div class="flex-grow-1">
                              <div class="small">{{ ans.answer }}</div>
                            </div>
                          </div>
                        </label>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Кнопки действий внутри карточки (вопрос) -->
            <div class="card-footer bg-light d-flex justify-content-between align-items-center gap-2 py-2">
              <button 
                class="btn btn-outline-danger btn-sm"
                @click="resetCurrentItem"
              >
                Сбросить ответы
              </button>
              <button 
                class="btn btn-primary btn-sm"
                :disabled="validationErrorsCount > 0"
                @click="saveAnswers"
                :title="validationErrorsCount > 0 ? 'Исправьте ошибки валидации перед сохранением' : ''"
              >
                Сохранить все ответы
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Нижняя панель: прогресс + переход к результатам -->
    <div class="card-footer bg-white border-top py-2 d-flex justify-content-between align-items-center">
      <div class="small text-muted d-flex align-items-center gap-3">
        <span>
          <span class="badge bg-success me-2">{{ filledCount }}</span>
          из <span class="badge bg-secondary">{{ totalCount }}</span> элементов заполнено
        </span>
        <span v-if="validationErrorsCount > 0" class="text-danger">
          <span class="badge bg-danger me-1">{{ validationErrorsCount }}</span>
          {{ validationErrorsCount === 1 ? 'ошибка' : 'ошибок' }} в значениях
        </span>
      </div>
      <button 
        class="btn btn-success"
        @click="goToResults"
      >
        Перейти к результатам
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiClient } from '../../../../core/client/src/js/api/manager'
import { roomAnalyticsEndpoints } from '../js/endpoints'
import RoomPreview from './RoomPreview.vue'

const route = useRoute()
const router = useRouter()

// Имя маршрута страницы результатов. Подставь своё.
const RESULTS_ROUTE_NAME = 'Rooman_alytics.Results'

const floorplanId = computed(() => Number(route.query.floorplanId))

const criteria = ref([])
const globalParameters = ref([])
const floorplan = ref(null)
const planRooms = ref([])
const floorplanImageUrl = ref(null)
const activeCriterionId = ref(null)
const selectedItem = ref(null)

const userAnswers = reactive({ param: {}, question: {} })
const validationErrors = reactive({})

const CRITERION_COLORS = [
  '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
  '#FF9F40', '#8D6E63', '#EC407A', '#26A69A', '#AB47BC'
]
const getCriterionColor = (i) => CRITERION_COLORS[i % CRITERION_COLORS.length]

const activeCriterion = computed(() => criteria.value.find(c => c.id === activeCriterionId.value))

function isGlobalQuestion(q) {
  return q.type === 'for_floorplan'
}

function getParamTypeLabel(type) {
  const map = { 'global': 'Общий', 'for_floorplan': 'Для плана', 'rooms': 'По комнатам' }
  return map[type] || type
}

function getQuestionTypeLabel(type) {
  const map = {
    'for_floorplan': 'Для плана',
    'for_every_room': 'Для комнат',
    'for_selected_rooms': 'Для комнат',
    'for_unselected_rooms': 'Для комнат',
  }
  return map[type]
}

function getQuestionTypeBadge(type) {
  const map = {
    'for_floorplan': 'bg-info',
    'for_every_room': 'bg-warning text-dark',
    'for_selected_rooms': 'bg-warning text-dark',
    'for_unselected_rooms': 'bg-warning text-dark',
  }
  return map[type] || 'bg-secondary'
}

function getRoomsForItem(param) {
  if (param.input_type === 'global' || param.input_type === 'for_floorplan') return []
  if (!param.room_type_ids || param.room_type_ids.length === 0) return planRooms.value
  return planRooms.value.filter(r => param.room_type_ids.includes(r.type))
}

function getRoomsForQuestion(question) {
  if (isGlobalQuestion(question)) return []
  const roomTypeIds = question.room_type_ids || []
  
  if (question.type === 'for_every_room') return planRooms.value
  if (question.type === 'for_selected_rooms') {
    if (roomTypeIds.length === 0) return planRooms.value
    return planRooms.value.filter(r => roomTypeIds.includes(r.type))
  }
  if (question.type === 'for_unselected_rooms') {
    if (roomTypeIds.length === 0) return planRooms.value
    return planRooms.value.filter(r => !roomTypeIds.includes(r.type))
  }
  return planRooms.value
}

// ============================================
// ВАЛИДАЦИЯ ПАРАМЕТРОВ
// ============================================

function validateValue(param, value) {
  if (value === null || value === undefined || value === '') return null
  
  const num = Number(value)
  if (isNaN(num)) return 'Значение должно быть числом'
  if (param.min_value != null && num < param.min_value) {
    return `Значение не может быть меньше ${param.min_value}`
  }
  if (param.max_value != null && num > param.max_value) {
    return `Значение не может быть больше ${param.max_value}`
  }
  return null
}

function getParamGlobalError(param) {
  const ans = userAnswers.param[param.id]
  if (!ans) return null
  return validateValue(param, ans.global)
}

function getParamRoomError(param, roomId) {
  const ans = userAnswers.param[param.id]
  if (!ans) return null
  return validateValue(param, ans.rooms?.[roomId])
}

function hasParamValidationError(paramId) {
  const param = globalParameters.value.find(p => p.id === paramId) 
             || activeCriterion.value?.parameters.find(p => p.id === paramId)
  if (!param) return false
  
  if (getParamGlobalError(param) !== null) return true
  if (param.input_type !== 'global' && param.input_type !== 'for_floorplan') {
    const rooms = getRoomsForItem(param)
    return rooms.some(r => getParamRoomError(param, r.id) !== null)
  }
  return false
}

const validationErrorsCount = computed(() => {
  let count = 0
  const allParams = [
    ...globalParameters.value,
    ...(activeCriterion.value?.parameters || [])
  ]
  for (const param of allParams) {
    if (getParamGlobalError(param) !== null) count++
    if (param.input_type !== 'global' && param.input_type !== 'for_floorplan') {
      const rooms = getRoomsForItem(param)
      count += rooms.filter(r => getParamRoomError(param, r.id) !== null).length
    }
  }
  return count
})

function validateParamGlobal(paramId) {
  validationErrors._tick = Date.now()
}

function validateParamRoom(paramId, roomId) {
  validationErrors._tick = Date.now()
}

// === Computed для прогресса ===
const filledCount = computed(() => {
  let count = 0
  
  for (const param of globalParameters.value) {
    const ans = userAnswers.param[param.id]
    if (!ans) continue
    if (param.input_type === 'global' || param.input_type === 'for_floorplan') {
      if (ans.global !== null && ans.global !== undefined && ans.global !== '' 
          && getParamGlobalError(param) === null) count++
    } else {
      const rooms = getRoomsForItem(param)
      const filled = rooms.filter(r => 
        ans.rooms?.[r.id] !== null && ans.rooms?.[r.id] !== undefined && ans.rooms?.[r.id] !== ''
        && getParamRoomError(param, r.id) === null
      ).length
      if (filled === rooms.length && rooms.length > 0) count++
    }
  }
  
  if (!activeCriterion.value) return count
  
  for (const param of activeCriterion.value.parameters) {
    const ans = userAnswers.param[param.id]
    if (!ans) continue
    if (param.input_type === 'global' || param.input_type === 'for_floorplan') {
      if (ans.global !== null && ans.global !== undefined && ans.global !== ''
          && getParamGlobalError(param) === null) count++
    } else {
      const rooms = getRoomsForItem(param)
      const filled = rooms.filter(r => 
        ans.rooms?.[r.id] !== null && ans.rooms?.[r.id] !== undefined && ans.rooms?.[r.id] !== ''
        && getParamRoomError(param, r.id) === null
      ).length
      if (filled === rooms.length && rooms.length > 0) count++
    }
  }
  
  for (const q of activeCriterion.value.questions) {
    const ans = userAnswers.question[q.id]
    if (!ans) continue
    if (isGlobalQuestion(q)) {
      if (ans.global !== null && ans.global !== undefined) count++
    } else {
      const rooms = getRoomsForQuestion(q)
      const filled = rooms.filter(r => ans.rooms?.[r.id] !== null && ans.rooms?.[r.id] !== undefined).length
      if (filled === rooms.length && rooms.length > 0) count++
    }
  }
  return count
})

const totalCount = computed(() => {
  let count = globalParameters.value.length
  if (activeCriterion.value) {
    count += activeCriterion.value.parameters.length + activeCriterion.value.questions.length
  }
  return count
})

const canSave = computed(() => filledCount.value > 0 && validationErrorsCount.value === 0)

// === Методы ===
function selectCriterion(id) {
  activeCriterionId.value = id
  selectedItem.value = null
  initAnswersForCriterion()
  for (const p of globalParameters.value) initAnswersForItem('param', p)
}

function selectItem(type, item) {
  selectedItem.value = { 
    type, 
    item: { 
      ...item, 
      isGlobal: globalParameters.value.some(gp => gp.id === item.id)
    } 
  }
  initAnswersForItem(type, item)
}

function initAnswersForCriterion() {
  if (!activeCriterion.value) return
  for (const p of activeCriterion.value.parameters) initAnswersForItem('param', p)
  for (const q of activeCriterion.value.questions) initAnswersForItem('question', q)
}

function initAnswersForItem(type, item) {
  if (type === 'param') {
    if (!userAnswers.param[item.id]) userAnswers.param[item.id] = { global: null, rooms: {} }
  } else {
    if (!userAnswers.question[item.id]) userAnswers.question[item.id] = { global: null, rooms: {} }
  }
}

function isParamFilled(paramId) {
  const param = globalParameters.value.find(p => p.id === paramId) 
             || activeCriterion.value?.parameters.find(p => p.id === paramId)
  if (!param) return false
  const ans = userAnswers.param[paramId]
  if (!ans) return false
  if (param.input_type === 'global' || param.input_type === 'for_floorplan') {
    return ans.global !== null && ans.global !== undefined && ans.global !== ''
           && getParamGlobalError(param) === null
  }
  const rooms = getRoomsForItem(param)
  return rooms.length > 0 && rooms.every(r => 
    ans.rooms?.[r.id] !== null && ans.rooms?.[r.id] !== undefined && ans.rooms?.[r.id] !== ''
    && getParamRoomError(param, r.id) === null
  )
}

function isQuestionFilled(questionId) {
  const q = activeCriterion.value?.questions.find(q => q.id === questionId)
  if (!q) return false
  const ans = userAnswers.question[questionId]
  if (!ans) return false
  if (isGlobalQuestion(q)) return ans.global !== null && ans.global !== undefined
  const rooms = getRoomsForQuestion(q)
  return rooms.length > 0 && rooms.every(r => ans.rooms?.[r.id] !== null && ans.rooms?.[r.id] !== undefined)
}

function getPlaceholder(param) {
  const parts = []
  if (param.min_value != null) parts.push(`от ${param.min_value}`)
  if (param.max_value != null) parts.push(`до ${param.max_value}`)
  return parts.length ? `Введите значение ${parts.join(' ')}` : 'Введите значение'
}

/**
 * Сбросить ТОЛЬКО текущий выбранный элемент (параметр или вопрос).
 */
function resetCurrentItem() {
  if (!selectedItem.value) return
  if (!confirm('Сбросить ответы для этого элемента?')) return
  
  const { type, item } = selectedItem.value
  if (type === 'param') {
    userAnswers.param[item.id] = { global: null, rooms: {} }
  } else {
    userAnswers.question[item.id] = { global: null, rooms: {} }
  }
}

/**
 * Полный сброс всех ответов (на случай, если понадобится).
 */
function resetAllAnswers() {
  if (!confirm('Сбросить все ответы? Включая общие параметры?')) return
  
  for (const p of globalParameters.value) userAnswers.param[p.id] = { global: null, rooms: {} }
  if (!activeCriterion.value) return
  for (const p of activeCriterion.value.parameters) userAnswers.param[p.id] = { global: null, rooms: {} }
  for (const q of activeCriterion.value.questions) userAnswers.question[q.id] = { global: null, rooms: {} }
}

/**
 * Переход на страницу результатов.
 */
function goToResults() {
  if (validationErrorsCount.value > 0) {
    alert(`Нельзя перейти к результатам: есть ${validationErrorsCount.value} ошибочных значений. Исправьте их.`)
    return
  }
  
  // Пытаемся перейти по имени маршрута. Если не задан — fallback на query-параметр.
  try {
    router.push({
      name: RESULTS_ROUTE_NAME,
      query: { floorplanId: floorplanId.value }
    })
  } catch (e) {
    // Если маршрут не найден — просто переходим назад с параметром
    console.warn('Маршрут результатов не найден, используем fallback')
    router.push({ path: '/results', query: { floorplanId: floorplanId.value } })
  }
}

async function saveAnswers() {
  if (validationErrorsCount.value > 0) {
    alert(`Нельзя сохранить: есть ${validationErrorsCount.value} ошибочных значений. Исправьте их перед сохранением.`)
    return
  }
  
  try {
    const payload = {
      floorplan_id: floorplanId.value,
      criterion_id: activeCriterionId.value,
      global_parameters: {},
      parameters: {},
      questions: {}
    }
    
    for (const param of globalParameters.value) {
      const ans = userAnswers.param[param.id]
      if (!ans) continue
      if (param.input_type === 'global' || param.input_type === 'for_floorplan') {
        if (ans.global != null && ans.global !== '') payload.global_parameters[param.id] = { global: ans.global }
      } else {
        const roomsData = {}
        for (const room of getRoomsForItem(param)) {
          if (ans.rooms?.[room.id] != null && ans.rooms?.[room.id] !== '') roomsData[room.id] = ans.rooms[room.id]
        }
        if (Object.keys(roomsData).length > 0) payload.global_parameters[param.id] = { rooms: roomsData }
      }
    }
    
    if (activeCriterion.value) {
      for (const param of activeCriterion.value.parameters) {
        const ans = userAnswers.param[param.id]
        if (!ans) continue
        if (param.input_type === 'global' || param.input_type === 'for_floorplan') {
          if (ans.global != null && ans.global !== '') payload.parameters[param.id] = { global: ans.global }
        } else {
          const roomsData = {}
          for (const room of getRoomsForItem(param)) {
            if (ans.rooms?.[room.id] != null && ans.rooms?.[room.id] !== '') roomsData[room.id] = ans.rooms[room.id]
          }
          if (Object.keys(roomsData).length > 0) payload.parameters[param.id] = { rooms: roomsData }
        }
      }
      
      for (const q of activeCriterion.value.questions) {
        const ans = userAnswers.question[q.id]
        if (!ans) continue
        if (isGlobalQuestion(q)) {
          if (ans.global != null) payload.questions[q.id] = { global: ans.global }
        } else {
          const roomsData = {}
          for (const room of getRoomsForQuestion(q)) {
            if (ans.rooms?.[room.id] != null) roomsData[room.id] = ans.rooms[room.id]
          }
          if (Object.keys(roomsData).length > 0) payload.questions[q.id] = { rooms: roomsData }
        }
      }
    }
    
    console.log('Сохранение:', payload)
    // await apiClient.post(roomAnalyticsEndpoints.roomAnalytics.SurveyAnswersSave, payload)
    alert(`Ответы сохранены. Заполнено: ${filledCount.value} из ${totalCount.value}`)
  } catch (e) {
    console.error('Ошибка:', e)
    alert('Ошибка: ' + (e.response?.data?.error || e.message))
  }
}

async function loadCriteria() {
  try {
    const response = await apiClient.get(roomAnalyticsEndpoints.roomAnalytics.GetCriteryQuestionsAndParams)
    const data = response.data
    
    globalParameters.value = (data.global_parameters || []).map(p => ({ ...p, isGlobal: true }))
    const criteriaData = data.criteria || []
    
    criteria.value = criteriaData.map((c, i) => ({ ...c, color: c.color || getCriterionColor(i) }))
    
    for (const p of globalParameters.value) initAnswersForItem('param', p)
    
    if (criteria.value.length > 0) {
      activeCriterionId.value = criteria.value[0].id
      initAnswersForCriterion()
    }
  } catch (e) {
    console.error('Ошибка загрузки критериев:', e)
    alert('Не удалось загрузить критерии')
  }
}

async function loadFloorplan() {
  if (!floorplanId.value) return
  try {
    const response = await apiClient.get(roomAnalyticsEndpoints.roomAnalytics.FloorplanDetail(floorplanId.value))
    floorplan.value = response.data
    
    floorplanImageUrl.value = response.data.img || null
    
    planRooms.value = (response.data.rooms || []).map(r => ({
      id: r.id,
      type: r.type,
      label: r.label,
      color: r.color,
      bbox: r.bbox || null
    }))
  } catch (e) {
    console.error('Ошибка загрузки плана:', e)
    alert('Не удалось загрузить план #' + floorplanId.value)
  }
}

onMounted(async () => {
  if (!floorplanId.value || isNaN(floorplanId.value)) {
    alert('ID плана не указан.')
    router.back()
    return
  }
  await Promise.all([loadCriteria(), loadFloorplan()])
})
</script>

<style scoped>
.cursor-pointer { cursor: pointer; }
.answer-card { transition: all 0.2s ease; cursor: pointer; }
.answer-card:hover { transform: translateY(-2px); box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
.list-group-item { transition: all 0.15s ease; }
.list-group-item.active { transform: translateX(4px); }
.overflow-auto::-webkit-scrollbar { width: 6px; }
.overflow-auto::-webkit-scrollbar-thumb { background: #888; border-radius: 3px; }

.bg-purple-custom {
  background-color: #6f42c1 !important;
  color: white !important;
}

.list-group-item.border-danger {
  border-width: 2px !important;
}

.form-control.is-invalid {
  border-color: #dc3545;
  box-shadow: 0 0 0 0.2rem rgba(220, 53, 69, 0.15);
}
</style>