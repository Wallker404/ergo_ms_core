<!-- CriterionSystemEquationPage.vue -->
<template>
    <div class="container-fluid py-4 bg-light min-vh-100">
      <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="mb-0">Система уравнений критерия: <span :style="{ color: criterionColor }">{{ criterionName }}</span></h2>
        <button class="btn btn-secondary" @click="goBack">← Назад</button>
      </div>
  
      <div v-if="isLoading" class="text-center py-5">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Загрузка...</span>
        </div>
      </div>
  
      <div v-else>
  
        <!-- ═══════════════════════════════════════════════════════════════
             КАРТОЧКА 1: Глобальные параметры
        ═══════════════════════════════════════════════════════════════ -->
        <div class="card shadow-sm mb-4">
          <div class="card-header text-white d-flex justify-content-between align-items-center"
               :style="{ backgroundColor: criterionColor }">
            <span class="fw-bold">Параметры</span>
            <button v-if="isEditingParam" class="btn btn-sm btn-light" @click="cancelEditParam">Отменить редактирование</button>
          </div>
          <div class="card-body">
            <p class="text-muted small mb-3">
              Параметры используются в системе уравнений данного критерия.
              Можно создать глобальный параметр (доступен всем критериям) или привязанный к текущему критерию.
              Поддерживается только ручной ввод без привязки к комнатам.
            </p>
  
            <!-- Форма создания/редактирования параметра -->
            <div class="row g-3 mb-3 p-3 bg-light rounded">
              <div class="col-md-2">
                <label class="form-label small fw-bold">Обозначение</label>
                <input v-model="paramForm.varName" type="text" class="form-control form-control-sm" placeholder="T_room" />
              </div>
              <div class="col-md-3">
                <label class="form-label small fw-bold">Название параметра</label>
                <input v-model="paramForm.label" type="text" class="form-control form-control-sm" placeholder="Температура в комнате" />
              </div>
              <div class="col-md-2">
                <label class="form-label small fw-bold">Область действия</label>
                <select v-model="paramForm.scope" class="form-select form-select-sm">
                  <option value="global">Для всех критериев</option>
                  <option value="current">Для текущего критерия</option>
                </select>
              </div>
              <div class="col-md-1">
                <label class="form-label small fw-bold">Мин.</label>
                <input v-model.number="paramForm.minVal" type="number" class="form-control form-control-sm" />
              </div>
              <div class="col-md-1">
                <label class="form-label small fw-bold">Макс.</label>
                <input v-model.number="paramForm.maxVal" type="number" class="form-control form-control-sm" />
              </div>
              <div class="col-md-2">
                <label class="form-label small fw-bold">Статус</label>
                <div class="form-check form-switch mt-2">
                  <input
                    class="form-check-input"
                    type="checkbox"
                    id="paramActiveSwitchGlobal"
                    v-model="paramForm.isActive"
                  />
                  <label class="form-check-label small" for="paramActiveSwitchGlobal">
                    {{ paramForm.isActive ? 'Активен' : 'Неактивен' }}
                  </label>
                </div>
              </div>
            </div>
  
            <div class="d-flex gap-2 mb-4">
              <button class="btn btn-primary btn-sm" @click="saveParam">
                {{ isEditingParam ? '💾 Обновить параметр' : '➕ Добавить параметр' }}
              </button>
              <button class="btn btn-secondary btn-sm" @click="resetParamForm">Очистить</button>
            </div>
  
            <!-- Таблица параметров -->
            <div class="table-responsive">
              <table class="table table-hover table-bordered align-middle table-sm">
                <thead class="table-light">
                  <tr>
                    <th>Переменная</th>
                    <th>Название</th>
                    <th style="width: 170px;">Область</th>
                    <th>Диапазон</th>
                    <th style="width: 100px;">Статус</th>
                    <th style="width: 120px;">Действия</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="p in globalParameters" :key="p.id" :class="{ 'inactive-row': !p.isActive }">
                    <td><code>{{ p.varName }}</code></td>
                    <td>{{ p.label }}</td>
                    <td>
                      <span class="badge" :class="p.cryteria_id ? 'bg-primary' : 'bg-secondary'">
                        {{ p.cryteria_id ? '🔒 Для критерия' : '🌐 Глобальный' }}
                      </span>
                    </td>
                    <td class="small">
                      [{{ p.minVal ?? '—' }}; {{ p.maxVal ?? '—' }}]
                    </td>
                    <td class="text-center">
                      <span class="badge" :class="p.isActive ? 'bg-success' : 'bg-secondary'">
                        {{ p.isActive ? 'Активен' : 'Выкл' }}
                      </span>
                    </td>
                    <td>
                      <button class="btn btn-sm btn-outline-warning me-1" @click="editParam(p)">Ред.</button>
                      <button class="btn btn-sm btn-outline-danger" @click="deleteParam(p.id)">X</button>
                    </td>
                  </tr>
                  <tr v-if="!globalParameters.length">
                    <td colspan="6" class="text-center text-muted">Параметры не добавлены</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
  
        <!-- ═══════════════════════════════════════════════════════════════
             КАРТОЧКА 2: Редактирование системы уравнений
        ═══════════════════════════════════════════════════════════════ -->
        <div class="card shadow-sm mb-4">
          <div class="card-header text-white d-flex justify-content-between align-items-center"
               :style="{ backgroundColor: criterionColor }">
            <span class="fw-bold">Редактирование системы уравнений</span>
            <button v-if="isEditing" class="btn btn-sm btn-light" @click="cancelEdit">Отменить</button>
          </div>
          <div class="card-body">
            <div class="row g-4">
              <!-- Левая колонка: Ввод выражений -->
              <div class="col-md-6">
                <div class="card h-100 border-0 shadow-sm">
                  <div class="card-header bg-light py-2 fw-bold small">Уравнения системы</div>
                  <div class="card-body p-3">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                      <span class="small fw-bold text-muted">Уравнения</span>
                      <button class="btn btn-xs btn-success" @click="addEquation">+ Добавить</button>
                    </div>
  
                    <div v-for="(eq, idx) in systemForm.equations" :key="idx" class="card mb-2 border-start border-3 border-info bg-white">
                      <div class="card-header py-1 px-2 d-flex justify-content-between align-items-center bg-transparent border-0">
                        <small class="fw-bold text-info">Уравнение #{{ idx + 1 }}</small>
                        <button class="btn btn-xs btn-outline-danger py-0 px-1" @click="removeEquation(idx)">🗑️</button>
                      </div>
                      <div class="card-body py-2 position-relative">
                        <div class="row g-1 mb-1">
                            <!-- Условие показываем только если уравнений больше одного -->
                            <div v-if="systemForm.equations.length > 1" class="col-5">
                                <div class="input-group input-group-sm">
                                <input v-model="eq.limit_equastion" type="text" class="form-control" placeholder="Условие" />
                                <button class="btn btn-outline-secondary btn-sm" @click="openMathHelperForEquation(idx, 'limit_equastion')">🧮</button>
                                </div>
                            </div>
                            
                            <!-- Если уравнение одно — оно занимает всю ширину -->
                            <div :class="systemForm.equations.length > 1 ? 'col-5' : 'col-10'">
                                <div class="input-group input-group-sm">
                                <input v-model="eq.equastion" type="text" class="form-control" placeholder="Уравнение" />
                                <button class="btn btn-outline-secondary btn-sm" @click="openMathHelperForEquation(idx, 'equastion')"></button>
                                </div>
                            </div>
                            
                            <div class="col-2 d-flex align-items-end justify-content-center">
                                <span class="text-muted small">=</span>
                            </div>
                            </div>
                        <textarea v-model="eq.recommendation" class="form-control form-control-sm" rows="1" placeholder="Рекомендация..."></textarea>
  
                        <div v-if="showMathHelper && mathTargetEquationIdx === idx" class="math-helper-box p-2 bg-white border rounded shadow-sm mt-2">
                          <div class="d-flex flex-wrap gap-1 align-items-center">
                            <button v-for="sym in mathSymbols" :key="sym" class="btn btn-xs btn-outline-dark" @click="insertMath(sym)">{{ sym }}</button>
                            <button class="btn btn-xs btn-danger ms-auto" @click="showMathHelper = false">✕</button>
                          </div>
                        </div>
                      </div>
                    </div>
  
                    <div v-if="!systemForm.equations.length" class="alert alert-warning py-2 small mb-0">
                      Добавьте хотя бы одно уравнение
                    </div>
                  </div>
                </div>
              </div>
  
              <!-- Правая колонка: Выбор параметров и критериев -->
              <div class="col-md-6">
                <div class="card h-100 border-0 shadow-sm">
                  <div class="card-header bg-light py-2 fw-bold small">Используемые параметры и критерии</div>
                  <div class="card-body p-3">
                    <ul class="nav nav-tabs mb-3">
                      <li class="nav-item">
                        <button class="nav-link" :class="{ active: paramFilter === 'global' }" @click="paramFilter = 'global'">
                          Параметры
                        </button>
                      </li>
                      <li class="nav-item">
                        <button class="nav-link" :class="{ active: paramFilter === 'criteria' }" @click="paramFilter = 'criteria'">
                          Другие критерии
                        </button>
                      </li>
                    </ul>
  
                    <!-- Параметры -->
                    <div v-if="paramFilter === 'global'" class="list-group" style="max-height: 320px; overflow-y: auto;">
                      <div v-for="p in globalParameters" :key="p.id" class="list-group-item list-group-item-action d-flex align-items-center py-2 px-2">
                        <div class="form-check flex-grow-1 m-0">
                          <input class="form-check-input mt-0" type="checkbox" :id="'gp-'+p.id" :checked="systemForm.used_input_ids.includes(p.id)" @change="toggleGlobalParam(p.id)">
                          <label class="form-check-label w-100 ps-2 small" :for="'gp-'+p.id">
                            <div class="d-flex justify-content-between align-items-center">
                              <span><code class="me-2">{{ p.varName }}</code> {{ p.label }}</span>
                              <span class="badge ms-1" :class="p.cryteria_id ? 'bg-primary' : 'bg-secondary'" style="font-size: 0.7rem;">
                                {{ p.cryteria_id ? '🔒 Критерий' : '🌐 Глобальный' }}
                              </span>
                            </div>
                          </label>
                        </div>
                      </div>
  
                      <div v-if="!globalParameters.length" class="text-center text-muted py-4 small">
                        Нет доступных параметров
                      </div>
                    </div>
  
                    <!-- Другие критерии -->
                    <div v-if="paramFilter === 'criteria'" class="list-group" style="max-height: 320px; overflow-y: auto;">
                      <div v-for="c in allCriteria" :key="c.id" class="list-group-item list-group-item-action d-flex align-items-center py-2 px-2">
                        <div class="form-check flex-grow-1 m-0">
                          <input class="form-check-input mt-0" type="checkbox" :id="'crit-'+c.id" :checked="systemForm.used_criterion_ids.includes(c.id)" @change="toggleCriterion(c.id)" :disabled="c.id === criterionId">
                          <label class="form-check-label w-100 ps-2 small" :for="'crit-'+c.id">
                            <div class="d-flex justify-content-between align-items-center">
                              <span>{{ c.name }}</span>
                              <code class="ms-1" style="font-size: 0.7rem;">{{ c.var_name }}</code>
                            </div>
                          </label>
                        </div>
                      </div>
  
                      <div v-if="!allCriteria.length" class="text-center text-muted py-4 small">
                        Нет доступных критериев
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
  
            <!-- Кнопки действий -->
            <div class="d-flex gap-2 mt-4">
              <button class="btn btn-primary" @click="saveSystem" :disabled="!systemForm.equations.length">
                {{ isEditing ? '💾 Обновить' : '➕ Создать' }}
              </button>
              <button class="btn btn-secondary" @click="resetForm">Очистить</button>
              <button v-if="systemData.id" class="btn btn-danger ms-auto" @click="deleteSystem">
                🗑️ Удалить систему
              </button>
            </div>
          </div>
        </div>
  
        <!-- Таблица текущей системы уравнений -->
        <div v-if="systemData.equations?.length" class="card shadow-sm">
          <div class="card-header text-white" :style="{ backgroundColor: criterionColor }">
            <span class="fw-bold">Текущая система уравнений</span>
          </div>
          <div class="card-body">
            <div class="table-responsive">
              <table class="table table-hover table-bordered align-middle table-sm">
                <thead class="table-light">
                  <tr>
                    <th style="width: 50px;">#</th>
                    <th>Условие</th>
                    <th>Уравнение</th>
                    <th style="width: 30%;">Рекомендация</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(eq, idx) in systemData.equations" :key="idx">
                    <td>{{ idx + 1 }}</td>
                    <td class="small"><span class="text-warning">{{ eq.limit_equastion || '—' }}</span></td>
                    <td class="small"><span class="text-info">{{ eq.equastion }}</span></td>
                    <td class="small text-muted">{{ eq.recommendation || '—' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
  
            <div v-if="systemData.used_input_ids?.length" class="mt-3">
              <h6 class="fw-bold">Используемые параметры:</h6>
              <div class="d-flex flex-wrap gap-2">
                <span v-for="pid in systemData.used_input_ids" :key="pid" class="badge bg-success">
                  {{ getGlobalParamName(pid) }}
                </span>
              </div>
            </div>
  
            <div v-if="systemData.used_criterion_ids?.length" class="mt-3">
              <h6 class="fw-bold">Используемые критерии:</h6>
              <div class="d-flex flex-wrap gap-2">
                <span v-for="cid in systemData.used_criterion_ids" :key="cid" class="badge bg-primary">
                  {{ getCriterionName(cid) }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </template>
  
  <script setup>
  import { ref, reactive, computed, onMounted } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { apiClient } from '../../../../core/client/src/js/api/manager'
  import { roomAnalyticsEndpoints } from '../js/endpoints'
  
  const route = useRoute()
  const router = useRouter()
  
  const criterionId = computed(() => Number(route.params.criterionId))
  const criterionName = ref('')
  const criterionColor = ref('#dc3545')
  const isLoading = ref(true)
  const isEditing = ref(false)
  
  const systemData = ref({})
  const globalParameters = ref([])
  const allCriteria = ref([])
  
  const systemForm = reactive({
    equations: [{ limit_equastion: '', equastion: '', recommendation: '' }],
    used_input_ids: [],
    used_criterion_ids: [],
  })
  
  // ==========================================
  // 🔹 ФОРМА ПАРАМЕТРОВ
  // ==========================================
  const paramForm = reactive({
    id: null,
    varName: '',
    label: '',
    scope: 'global',
    minVal: 0,
    maxVal: 100,
    isActive: false,
  })
  const isEditingParam = ref(false)
  
  // UI
  const showMathHelper = ref(false)
  const mathTargetEquationIdx = ref(null)
  const mathTarget = ref('')
  const mathSymbols = ['√', '^', 'sin', 'cos', 'tan', 'log', '(', ')', '+', '-', '*', '/', '>', '<', '=', 'π', 'e']
  const paramFilter = ref('global')
  
  // ==========================================
  // 🔹 НОРМАЛИЗАЦИЯ ДАННЫХ
  // ==========================================
  function normalizeInputParam(p) {
    return {
      id: p.id,
      varName: p.varName || p.name || '',
      label: p.label || '',
      inputType: p.inputType || 'manual',
      paramType: p.paramType || 'global',
      minVal: p.min_value ?? p.minVal ?? 0,
      maxVal: p.max_value ?? p.maxVal ?? 100,
      roomTypeIds: p.room_type_ids || p.roomTypeIds || [],
      cryteria_id: p.cryteria_id,
      isActive: p.isActive ?? false,
      methodId: p.methodId,
      methodName: p.methodName,
      methodType: p.methodType,
      room_type_id: p.room_type_id,
      furniture_type_id: p.furniture_type_id,
    }
  }
  
  // ==========================================
  // 🔹 ФУНКЦИИ РАБОТЫ С ПАРАМЕТРАМИ
  // ==========================================
  function resetParamForm() {
    Object.assign(paramForm, {
      id: null,
      varName: '',
      label: '',
      scope: 'global',
      minVal: 0,
      maxVal: 100,
      isActive: false,
    })
    isEditingParam.value = false
  }
  
  function cancelEditParam() {
    resetParamForm()
  }
  
  function editParam(p) {
    Object.assign(paramForm, {
      id: p.id,
      varName: p.varName || '',
      label: p.label || '',
      scope: p.cryteria_id ? 'current' : 'global',
      minVal: p.minVal ?? 0,
      maxVal: p.maxVal ?? 100,
      isActive: p.isActive ?? false,
    })
    isEditingParam.value = true
  }
  
  async function saveParam() {
    if (!paramForm.varName?.trim()) return alert('Укажите обозначение переменной')
    if (!paramForm.label?.trim()) return alert('Укажите название параметра')
  
    try {
      const payload = {
        varName: paramForm.varName.trim(),
        label: paramForm.label.trim(),
        cryteria_id: paramForm.scope === 'global' ? null : criterionId.value,
        inputType: 'manual',
        paramType: 'global',
        minVal: Number(paramForm.minVal),
        maxVal: Number(paramForm.maxVal),
        room_type_ids: [],
        isActive: paramForm.isActive,
      }
  
      if (isEditingParam.value && paramForm.id) {
        await apiClient.put(
          roomAnalyticsEndpoints.roomAnalytics.ParamDetail(paramForm.id),
          payload
        )
      } else {
        await apiClient.post(
          roomAnalyticsEndpoints.roomAnalytics.ParamsList,
          payload
        )
      }
  
      await loadGlobalParameters()
      resetParamForm()
      alert('✅ Параметр сохранён')
    } catch (error) {
      console.error('Ошибка сохранения параметра:', error)
      alert(error.response?.data?.error || 'Не удалось сохранить параметр')
    }
  }
  
  async function deleteParam(id) {
    if (!confirm('Удалить параметр? Он будет удалён из всех систем уравнений, где используется.')) return
    try {
      await apiClient.delete(roomAnalyticsEndpoints.roomAnalytics.ParamDetail(id))
      await loadGlobalParameters()
      alert('✅ Параметр удалён')
    } catch (error) {
      console.error('Ошибка удаления:', error)
      alert('Не удалось удалить параметр')
    }
  }
  
  // ==========================================
  // 🔹 ФУНКЦИИ РАБОТЫ С СИСТЕМОЙ УРАВНЕНИЙ
  // ==========================================
  function addEquation() {
    systemForm.equations.push({
      limit_equastion: '',
      equastion: '',
      recommendation: ''
    })
  }
  
  function removeEquation(idx) {
    systemForm.equations.splice(idx, 1)
  }
  
  function openMathHelperForEquation(idx, part) {
    mathTargetEquationIdx.value = idx
    mathTarget.value = part
    showMathHelper.value = true
  }
  
  function insertMath(sym) {
    if (mathTargetEquationIdx.value !== null) {
      const eq = systemForm.equations[mathTargetEquationIdx.value]
      if (mathTarget.value === 'limit_equastion') {
        eq.limit_equastion += sym
      } else {
        eq.equastion += sym
      }
    }
  }
  
  function toggleGlobalParam(paramId) {
    const idx = systemForm.used_input_ids.indexOf(paramId)
    if (idx === -1) {
      systemForm.used_input_ids.push(paramId)
    } else {
      systemForm.used_input_ids.splice(idx, 1)
    }
  }
  
  function toggleCriterion(cid) {
    const idx = systemForm.used_criterion_ids.indexOf(cid)
    if (idx === -1) {
      systemForm.used_criterion_ids.push(cid)
    } else {
      systemForm.used_criterion_ids.splice(idx, 1)
    }
  }
  
  function getGlobalParamName(paramId) {
    const param = globalParameters.value.find(p => p.id === paramId)
    if (!param) return `ID:${paramId}`
    const scopeLabel = param.cryteria_id ? '🔒' : '🌐'
    return `${scopeLabel} ${param.varName} (${param.label})`
  }
  
  function getCriterionName(cid) {
    const crit = allCriteria.value.find(c => c.id === cid)
    return crit ? `${crit.name} (${crit.var_name})` : `ID:${cid}`
  }
  
  function resetForm() {
    systemForm.equations = [{ limit_equastion: '', equastion: '', recommendation: '' }]
    systemForm.used_input_ids = []
    systemForm.used_criterion_ids = []
    isEditing.value = false
  }
  
  function cancelEdit() {
    resetForm()
  }
  
  // ==========================================
  // 🔹 ЗАГРУЗКА ДАННЫХ
  // ==========================================
  async function loadCriterionInfo() {
    try {
      const res = await apiClient.get(roomAnalyticsEndpoints.roomAnalytics.CriteriesGet)
      const crit = (res.data || []).find(c => c.id === criterionId.value)
      if (crit) {
        criterionName.value = crit.name
        criterionColor.value = crit.color || '#dc3545'
      }
    } catch (e) {
      console.error('Ошибка загрузки информации о критерии:', e)
    }
  }
  
  async function loadSystemEquation() {
    try {
      const res = await apiClient.get(
        roomAnalyticsEndpoints.roomAnalytics.CriterionSystemEquation(criterionId.value)
      )
      systemData.value = res.data || {}
      if (systemData.value.id) {
        systemForm.equations = systemData.value.equations?.length
          ? systemData.value.equations.map(eq => ({ ...eq }))
          : [{ limit_equastion: '', equastion: '', recommendation: '' }]
        systemForm.used_input_ids = [...(systemData.value.used_input_ids || [])]
        systemForm.used_criterion_ids = [...(systemData.value.used_criterion_ids || [])]
        isEditing.value = true
      }
    } catch (e) {
      console.error('Ошибка загрузки системы уравнений:', e)
      systemData.value = {}
    }
  }
  
  async function loadGlobalParameters() {
  try {
    const res = await apiClient.get(roomAnalyticsEndpoints.roomAnalytics.ParamsList, {
      criteria_id: criterionId.value  // ← передаём ID критерия
    })
    globalParameters.value = (res.data || [])
      .map(normalizeInputParam)
      .filter(p => !p.cryteria_id || p.cryteria_id === criterionId.value)
  } catch (e) {
    console.error('Ошибка загрузки параметров:', e)
    globalParameters.value = []
  }
}
  
  async function loadAllCriteria() {
    try {
      const res = await apiClient.get(roomAnalyticsEndpoints.roomAnalytics.AllCriteriaList)
      allCriteria.value = res.data || []
    } catch (e) {
      console.error('Ошибка загрузки критериев:', e)
      allCriteria.value = []
    }
  }
  
  onMounted(async () => {
    isLoading.value = true
    await loadCriterionInfo()
    await Promise.all([
      loadSystemEquation(),
      loadGlobalParameters(),
      loadAllCriteria()
    ])
    isLoading.value = false
  })
  
  // ==========================================
  // 🔹 СОХРАНЕНИЕ И УДАЛЕНИЕ СИСТЕМЫ
  // ==========================================
  async function saveSystem() {
  if (!systemForm.equations.length) {
    return alert('Добавьте хотя бы одно уравнение')
  }

  try {
    const payload = {
      equations: systemForm.equations.map(eq => ({
        // Если уравнение одно — условие не имеет смысла, отправляем пустую строку
        limit_equastion: systemForm.equations.length > 1 ? eq.limit_equastion : '',
        equastion: eq.equastion,
        recommendation: eq.recommendation
      })),
      used_input_ids: systemForm.used_input_ids,
      used_criterion_ids: systemForm.used_criterion_ids
    }

    await apiClient.post(
      roomAnalyticsEndpoints.roomAnalytics.CriterionSystemEquation(criterionId.value),
      payload
    )

    await loadSystemEquation()
    alert('✅ Система уравнений сохранена')
  } catch (e) {
    console.error('Ошибка сохранения:', e)
    alert(e.response?.data?.error || 'Не удалось сохранить')
  }
}
  
  async function deleteSystem() {
    if (!confirm('Удалить систему уравнений? Это действие нельзя отменить.')) return
  
    try {
      await apiClient.delete(
        roomAnalyticsEndpoints.roomAnalytics.CriterionSystemEquation(criterionId.value)
      )
      await loadSystemEquation()
      resetForm()
      alert('✅ Система уравнений удалена')
    } catch (e) {
      console.error('Ошибка удаления:', e)
      alert('Не удалось удалить')
    }
  }
  
  function goBack() {
    router.back()
  }
  </script>
  
  <style scoped>
  .form-label { font-weight: 500; font-size: 0.9rem; }
  code { background: #f8f9fa; padding: 2px 6px; border-radius: 4px; font-size: 0.85em; color: #d63384; }
  .table th { white-space: nowrap; }
  .btn-xs { padding: 0.15rem 0.4rem; font-size: 0.75rem; }
  .math-helper-box {
    position: absolute;
    z-index: 1000;
    width: calc(100% - 2rem);
  }
  
  tr.inactive-row {
    opacity: 0.55;
    transition: opacity 0.2s ease;
    background-color: #f8f9fa;
  }
  tr.inactive-row:hover {
    opacity: 1;
    background-color: #fff;
  }
  tr.inactive-row td {
    color: #6c757d;
  }
  tr.inactive-row code {
    color: #adb5bd;
    background: #e9ecef;
  }
  </style>