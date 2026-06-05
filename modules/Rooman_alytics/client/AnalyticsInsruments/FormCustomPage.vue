<template>
  <div class="container-fluid py-3">
    <nav class="mb-3">
      <ol class="breadcrumb mb-0">
        <li class="breadcrumb-item"><a href="#" @click.prevent="goBack">Критерии</a></li>
        <li class="breadcrumb-item active">Настройка анкеты</li>
      </ol>
    </nav>

    <h4 class="mb-4">Вопросы анкеты</h4>

    <!-- 🔴 Ошибки валидации -->
    <div v-if="validationError" class="alert alert-danger d-flex align-items-center mb-3">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-exclamation-triangle-fill me-2" viewBox="0 0 16 16">
        <path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767L8.982 1.566zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5zm.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2z"/>
      </svg>
      {{ validationError }}
    </div>

    <!-- ✏️ Форма добавления нового вопроса -->
    <div class="card mb-4 border-primary">
      <div class="card-body">
        <h6 class="mb-3">Новый вопрос</h6>
        <div class="row g-3">
          
          <!-- Текст вопроса -->
          <div class="col-md-6">
            <label class="form-label small">Текст вопроса <span class="text-danger">*</span></label>
            <input type="text" class="form-control" v-model="newQuestion.text" placeholder="Введите текст вопроса" />
          </div>

          <!-- 🔥 Поле рекомендации (ОБЯЗАТЕЛЬНОЕ) -->
          <div class="col-md-6">
            <label class="form-label small">Рекомендация <span class="text-danger">*</span></label>
            <input class="form-control" v-model="newQuestion.recommendation" 
                      rows="2" placeholder="Рекомендация для улучшения эргономичности"></input>
          </div>

          <!-- 🔥 Пороговый балл (числовое поле!) -->
          <div class="col-md-3">
            <label class="form-label small">Пороговый балл <span class="text-danger">*</span></label>
            <input type="number" class="form-control" v-model.number="newQuestion.score_for_recommendation" 
                   min="0" max="10" step="0.5" placeholder="0-10" />
            <small class="text-muted">Рекомендация покажется, если балл ниже этого значения</small>
          </div>

          <!-- Тип вопроса -->
          <div class="col-md-3">
            <label class="form-label small">Тип</label>
            <select class="form-select" v-model="newQuestion.type" @change="onTypeChange">
              <option value="for_floorplan">Для помещения</option>
              <option value="for_every_room">Для каждой комнаты</option>
              <option value="for_selected_rooms">Для выбранных комнат</option>
              <option value="for_unselected_rooms">Для невыбранных комнат</option>
            </select>
          </div>
          
          <!-- 🔥 Чипсы для выбора типов комнат -->
          <div v-if="['for_selected_rooms', 'for_unselected_rooms'].includes(newQuestion.type)" class="col-md-5">
            <label class="form-label small">Типы комнат</label>
            <div class="d-flex flex-wrap gap-2">
              <button v-for="rt in roomTypes" :key="rt.id"
                      type="button"
                      class="btn btn-sm"
                      :class="newQuestion.room_type_ids.includes(rt.id) ? 'btn-primary' : 'btn-outline-secondary'"
                      @click="toggleNewRoom(rt.id)">
                {{ rt.label }}
              </button>
            </div>
            <small v-if="!roomTypes.length" class="text-muted">Список типов комнат пуст</small>
          </div>

          <div class="col-md-4 d-flex align-items-end">
            <button class="btn btn-success w-100" @click="addQuestion" :disabled="!canAdd || addLoading">
              <span v-if="addLoading" class="spinner-border spinner-border-sm me-1"></span>
              {{ addLoading ? '...' : 'Добавить вопрос' }}
            </button>
          </div>

          <!-- 🔥 Ответы для нового вопроса -->
          <div class="col-12">
            <div class="border-top pt-3 mt-2">
              <h6 class="small text-muted mb-2">Варианты ответа</h6>
              <div v-if="newQuestion.answers.length === 0" class="text-muted small mb-2">
                Нет ответов.
              </div>
              <div v-for="(a, idx) in newQuestion.answers" :key="'new-'+idx" class="row g-2 align-items-center mb-2">
                <div class="col-md-6">
                  <input type="text" class="form-control form-control-sm" v-model="a.text" placeholder="Текст ответа" />
                </div>
                <div class="col-md-3">
                  <input type="number" class="form-control form-control-sm" v-model.number="a.score" 
                         min="0" max="10" step="0.5" placeholder="Баллы (0-10)" />
                </div>
                <div class="col-md-3 d-flex justify-content-end">
                  <button class="btn btn-outline-danger btn-sm" @click="removeNewAnswer(idx)" title="Удалить">
                    <Trash2 size="14" />
                  </button>
                </div>
              </div>
              <button class="btn btn-link btn-sm p-0 mt-1" @click="addNewAnswer">+ Добавить вариант ответа</button>
            </div>
          </div>

        </div>
      </div>
    </div>

    <!-- Пустой список -->
    <div v-if="questions.length === 0 && !isLoading" class="text-center text-muted py-5">
      Список вопросов пуст. Добавьте первый вопрос выше.
    </div>

    <!-- Загрузка -->
    <div v-if="isLoading" class="text-center py-5 text-muted">
      <span class="spinner-border spinner-border-sm me-2"></span>Загрузка...
    </div>

    <!-- 🔥 Список существующих вопросов -->
    <div v-else class="d-flex flex-column gap-3">
      <div v-for="q in questions" :key="q.id" class="card">
        <div class="card-header d-flex justify-content-between align-items-center bg-light flex-wrap gap-2">
          <div class="d-flex align-items-center gap-2 flex-grow-1 flex-wrap">
            <input type="text" class="form-control form-control-sm fw-medium border-0 bg-transparent" 
                   v-model="q.text" style="max-width: 280px; min-width: 200px;" />
            
            <select class="form-select form-select-sm" style="width: 150px;" 
                    v-model="q.type" @change="onTypeChangeLocal(q)">
              <option value="for_floorplan">Для помещения</option>
              <option value="for_every_room">Для каждой комнаты</option>
              <option value="for_selected_rooms">Для выбранных комнат</option>
              <option value="for_unselected_rooms">Для невыбранных комнат</option>
            </select>
            
            <!-- Чипсы комнат -->
            <div v-if="['for_selected_rooms', 'for_unselected_rooms'].includes(q.type)" 
                 class="w-100 mt-2 pt-2 border-top">
              <small class="text-muted d-block mb-1">Типы комнат:</small>
              <div class="d-flex flex-wrap gap-2">
                <button v-for="rt in roomTypes" :key="rt.id"
                        type="button"
                        class="btn btn-sm"
                        :class="q.room_type_ids.includes(rt.id) ? 'btn-primary' : 'btn-outline-secondary'"
                        @click="toggleQuestionRoom(q.room_type_ids, rt.id)">
                  {{ rt.label }}
                </button>
              </div>
            </div>
          </div>
          
          <div class="d-flex align-items-center gap-2">
            <div class="form-check form-switch mb-0">
              <input class="form-check-input" type="checkbox" :id="'act-' + q.id" v-model="q.is_active" />
              <label class="form-check-label small" :for="'act-' + q.id">
                {{ q.is_active ? 'Активен' : 'Неактивен' }}
              </label>
            </div>
            <button class="btn btn-outline-danger btn-sm" @click="deleteQuestion(q.id)" title="Удалить">
              <Trash2 size="14" />
            </button>
          </div>
        </div>

        <div class="card-body">
          <!-- 🔥 Поле рекомендации -->
          <div class="mb-3">
            <label class="form-label small">Рекомендация <span class="text-danger">*</span></label>
            <input class="form-control form-control-sm" v-model="q.recommendation" 
                      rows="2" placeholder="Рекомендация по улучшению..."></input>
          </div>
          
          <!-- 🔥 Пороговый балл -->
          <div class="mb-3">
            <label class="form-label small">Пороговый балл <span class="text-danger">*</span></label>
            <input type="number" class="form-control form-control-sm" v-model.number="q.score_for_recommendation" 
                   min="0" max="10" step="0.5" placeholder="0-10" />
            <small class="text-muted">Рекомендация отобразится, если набрано меньше этого балла</small>
          </div>

          <h6 class="small text-muted mb-3">Варианты ответов</h6>
          <div v-if="q.answers.length === 0" class="text-muted small mb-3">
            Нет ответов. <button class="btn btn-link btn-sm p-0" @click="addAnswer(q.id)">Добавить</button>
          </div>
          <div v-for="(a, idx) in q.answers" :key="a.id || idx" class="row g-2 align-items-center mb-2">
            <div class="col-md-6">
              <input type="text" class="form-control form-control-sm" v-model="a.text" placeholder="Текст ответа" />
            </div>
            <div class="col-md-4">
              <input type="number" class="form-control form-control-sm" v-model.number="a.score" 
                     min="0" max="10" step="0.5" placeholder="Баллы" />
            </div>
            <div class="col-md-2 d-flex justify-content-end">
              <button class="btn btn-outline-danger btn-sm" @click="deleteAnswer(q.id, a.id)" title="Удалить">
                <Trash2 size="14" />
              </button>
            </div>
          </div>
          <button class="btn btn-link btn-sm p-0 mt-1" @click="addAnswer(q.id)">+ Добавить ответ</button>
        </div>
      </div>
    </div>

    <!-- Сохранение -->
    <div class="mt-4 text-end">
      <button class="btn btn-primary btn-lg" @click="saveQuestionnaire" :disabled="isSaving || isLoading">
        <span v-if="isSaving" class="spinner-border spinner-border-sm me-2" role="status"></span>
        {{ isSaving ? 'Сохранение изменений...' : 'Сохранить изменения' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Trash2 } from 'lucide-vue-next'
import { apiClient } from '../../../../core/client/src/js/api/manager'
import { roomAnalyticsEndpoints } from '../js/endpoints'

const router = useRouter()
const route = useRoute()

const questions = ref([])
const roomTypes = ref([])
const isLoading = ref(true)
const isSaving = ref(false)
const addLoading = ref(false)
const validationError = ref('')

// 🔥 Структура нового вопроса — ИМЕНА ПОЛЕЙ КАК В API (snake_case)
const newQuestion = ref({
  text: '',
  recommendation: '',                    // ← как в API
  score_for_recommendation: '',           // ← как в API (число!)
  type: 'for_floorplan',
  is_active: true,                       // ← как в API
  room_type_ids: [],                     // ← как в API
  answers: []                            // [{ text, score }]
})

const canAdd = computed(() => {
  if (!newQuestion.value.text?.trim()) return false
  if (!newQuestion.value.recommendation?.trim()) return false
  
  // Валидация порогового балла
  const score = newQuestion.value.score_for_recommendation
  if (score === undefined || score === null || isNaN(score) || score < 0 || score > 10) return false

  // Минимум 2 заполненных ответа
  const validAnswers = newQuestion.value.answers.filter(a => a.text?.trim())
  if (validAnswers.length < 2) return false
  
  // Комнаты для соответствующих типов
  if (['for_selected_rooms', 'for_unselected_rooms'].includes(newQuestion.value.type)) {
    return newQuestion.value.room_type_ids.length > 0
  }
  return true
})

// 🔹 Переключение комнат (работает с room_type_ids)
function toggleNewRoom(id) {
  const arr = newQuestion.value.room_type_ids
  const idx = arr.indexOf(id)
  idx > -1 ? arr.splice(idx, 1) : arr.push(id)
}

function toggleQuestionRoom(arr, id) {
  const idx = arr.indexOf(id)
  idx > -1 ? arr.splice(idx, 1) : arr.push(id)
}

function onTypeChange() {
  if (!['for_selected_rooms', 'for_unselected_rooms'].includes(newQuestion.value.type)) {
    newQuestion.value.room_type_ids = []
  }
}

function onTypeChangeLocal(q) {
  if (!['for_selected_rooms', 'for_unselected_rooms'].includes(q.type)) {
    q.room_type_ids = []
  }
}

// 🔹 Ответы для нового вопроса
function addNewAnswer() {
  newQuestion.value.answers.push({ text: '', score: 0 })
}

function removeNewAnswer(idx) {
  newQuestion.value.answers.splice(idx, 1)
}

// 🔹 Загрузка типов комнат
async function fetchRoomTypes() {
  try {
    const res = await apiClient.get(roomAnalyticsEndpoints.roomAnalytics.RoomTypesList)
    roomTypes.value = Array.isArray(res.data) ? res.data : []
    console.log(roomTypes.value)
  } catch (e) { console.error('RoomTypes error:', e) }
}

// 🔹 Загрузка вопросов — БЕЗ ТРАНСФОРМЕРОВ, прямое присваивание
async function fetchQuestions() {
  const cid = route.params.criterionId
  if (!cid) { isLoading.value = false; return }
  
  isLoading.value = true
  try {
    const res = await apiClient.get(roomAnalyticsEndpoints.roomAnalytics.CriteriesQuestions(cid))
    // API возвращает данные в нужном формате — просто копируем
    questions.value = Array.isArray(res.data) ? res.data : []
  } catch (e) {
    console.error('Questions load error:', e)
    questions.value = []
    validationError.value = 'Не удалось загрузить вопросы'
  } finally {
    isLoading.value = false
  }
}

// ➕ Добавление вопроса — ОТПРАВЛЯЕМ ДАННЫЕ «КАК ЕСТЬ»
async function addQuestion() {
  if (!canAdd.value || addLoading.value) return
  addLoading.value = true
  validationError.value = ''
  
  try {
    // Глубокая копия + фильтрация пустых ответов
    const payload = {
      criterion_id: route.params.criterionId,
      text: newQuestion.value.text?.trim() || '',
      recommendation: newQuestion.value.recommendation?.trim() || '',
      score_for_recommendation: Number(newQuestion.value.score_for_recommendation) ?? 6,
      type: newQuestion.value.type,
      is_active: false,  // новый вопрос создаётся неактивным
      room_type_ids: [...(newQuestion.value.room_type_ids || [])],
      answers: (newQuestion.value.answers || [])
        .filter(a => a.text?.trim())
        .map(a => ({ 
          text: a.text.trim(), 
          score: Number(a.score) || 0 
        }))
    }
    
    const res = await apiClient.post(roomAnalyticsEndpoints.roomAnalytics.QuestionAdd, payload)
    
    if (res.data?.question) {
      // API возвращает вопрос в том же формате — добавляем напрямую
      questions.value.unshift(res.data.question)
      resetNewQuestion()
    } else {
      await fetchQuestions()
      resetNewQuestion()
    }
  } catch (e) {
    console.log(e)
    validationError.value = e.response?.data?.error || 'Ошибка добавления'
  } finally {
    addLoading.value = false
  }
}

function resetNewQuestion() {
  newQuestion.value = { 
    text: '', 
    recommendation: '', 
    score_for_recommendation: 6, 
    type: 'for_floorplan', 
    is_active: true, 
    room_type_ids: [], 
    answers: [] 
  }
}

function deleteQuestion(id) {
  if (!confirm('Удалить вопрос из БД?')) return
  apiClient.delete(roomAnalyticsEndpoints.roomAnalytics.QuestionDelete(id))
    .then(() => {
      questions.value = questions.value.filter(q => q.id !== id)
    })
    .catch(e => {
      validationError.value = 'Ошибка удаления: ' + (e.response?.data?.error || '')
    })
}

function addAnswer(qid) {
  const q = questions.value.find(x => x.id === qid)
  if (q) q.answers.push({ id: null, text: '', score: 0 })
}

function deleteAnswer(qid, aid) {
  const q = questions.value.find(x => x.id === qid)
  if (q && aid) q.answers = q.answers.filter(a => a.id !== aid)
}

// ✅ Валидация — РАБОТАЕМ С ИМЕНАМИ ПОЛЕЙ КАК В API
function validate() {
  if (!questions.value.length) return 'Добавьте хотя бы один вопрос'
  
  for (const q of questions.value) {
    if (!q.text?.trim()) return 'Есть вопрос без текста'
    if (!q.recommendation?.trim()) return `Вопрос "${q.text}": рекомендация обязательна`
    
    // Валидация порогового балла
    const recScore = q.score_for_recommendation
    if (recScore === undefined || recScore === null || isNaN(recScore) || recScore < 0 || recScore > 10) {
      return `Вопрос "${q.text}": пороговый балл должен быть от 0 до 10`
    }

    // Проверка ответов
    const validAnswers = (q.answers || []).filter(a => a.text?.trim())
    if (q.is_active) {  // ← is_active, не isActive!
      if (validAnswers.length < 2) {
        return `Вопрос "${q.text}": необходимо минимум 2 варианта ответа`
      }
      if (!validAnswers.some(a => Number(a.score) === 10)) {
        return `Вопрос "${q.text}" активен, но нет ответа с 10 баллами`
      }
    }
    
    if (['for_selected_rooms', 'for_unselected_rooms'].includes(q.type) && !q.room_type_ids?.length) {
      return `Вопрос "${q.text}": выберите типы комнат`
    }
  }
  return null
}

// 💾 Сохранение — ОТПРАВЛЯЕМ ДАННЫЕ «КАК ЕСТЬ»
async function saveQuestionnaire() {
  validationError.value = ''
  const err = validate()
  if (err) { validationError.value = err; return }
  
  const cid = route.params.criterionId
  if (!cid) { validationError.value = 'Нет ID критерия'; return }
  
  isSaving.value = true
  try {
    // Отправляем вопросы напрямую — поля уже в нужном формате
    const payload = {
      criterion_id: Number(cid),
      questions: questions.value.map(q => ({
        id: q.id || null,
        text: q.text || '',
        recommendation: q.recommendation || '',
        score_for_recommendation: Number(q.score_for_recommendation) ?? 6,
        type: q.type,
        is_active: !!q.is_active,
        room_type_ids: Array.isArray(q.room_type_ids) ? [...q.room_type_ids] : [],
        answers: (q.answers || []).map(a => ({ 
          id: a.id || null, 
          text: a.text || '', 
          score: Number(a.score) || 0 
        }))
      }))
    }
    
    const res = await apiClient.put(roomAnalyticsEndpoints.roomAnalytics.QuestionsUpdate, payload)
    
    if (res.data?.errors?.length) {
      validationError.value = `Частичный успех: ${res.data.errors.map(e => e.error).join('; ')}`
    } else {
      alert('Изменения сохранены!')
    }
  } catch (e) {
    validationError.value = e.response?.data?.error || 'Ошибка сохранения'
  } finally {
    isSaving.value = false
    await fetchQuestions()
  }
}

function goBack() { router.back() }

onMounted(async () => {
  await Promise.all([fetchRoomTypes(), fetchQuestions()])
})
</script>

<style scoped>
.btn-sm { font-size: 0.75rem; padding: 0.25rem 0.5rem; white-space: nowrap; transition: all 0.15s; }
.btn-primary { border-color: #0d6efd; }
.btn-outline-secondary:hover { background-color: #f8f9fa; }
textarea { resize: vertical; min-height: 38px; }
input[type="number"]::-webkit-inner-spin-button,
input[type="number"]::-webkit-outer-spin-button {
  opacity: 1;
}
@media (max-width: 768px) {
  .card-header { flex-direction: column; align-items: stretch !important; }
  .card-header > div:first-child { margin-bottom: 0.5rem; }
}
</style>