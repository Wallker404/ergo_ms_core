<template>
  <div class="container-fluid py-3">
    <h4 class="mb-4">Результаты оценки эргономичности</h4>

    <!-- Общий блок -->
    <div class="card mb-4 shadow-sm border-0 overflow-hidden">
      <div class="card-body text-center py-4 bg-light">
        <h2 class="display-3 fw-bold mb-2" :style="{ color: overallGaugeColor }">
          {{ overallScore }}
        </h2>
        <p class="text-muted fs-5 mb-3">Общий индекс эргономичности помещения</p>
        <span class="badge fs-6 px-3 py-2" :style="{ backgroundColor: overallGaugeColor, color: '#fff' }">
          {{ overallLabel }}
        </span>
        <p class="small text-muted mt-3 mb-0">
          Рассчитано на основе {{ activeCriteria.length }} активных критериев с учётом весов
        </p>
      </div>
    </div>

    <!-- Карточки активных критериев -->
    <div class="row g-4 mb-4">
      <div v-for="c in activeCriteria" :key="c.id" class="col-md-6 col-xl-4">
        <div class="card h-100 shadow-sm border-0">
          <!-- Шапка -->
          <div class="card-header text-white py-2 d-flex justify-content-between align-items-center" :style="{ backgroundColor: c.color }">
            <h6 class="mb-0 fw-medium">{{ c.name }}</h6>
            <span class="badge bg-white text-dark bg-opacity-75">
              {{ Number(c.score ?? 0).toFixed(1) }}/10
            </span>
          </div>

          <!-- Тело -->
          <div class="card-body d-flex flex-column align-items-center text-center p-3">
            <!-- Спидометр -->
            <div class="position-relative my-2" style="width: 150px; height: 80px;">
              <svg viewBox="0 0 150 80" class="w-100 h-100">
                <!-- Фоновая дуга -->
                <path d="M 10 75 A 65 65 0 0 1 140 75" fill="none" stroke="#e9ecef" stroke-width="10" stroke-linecap="round" />
                <!-- Прогресс-дуга -->
                <path 
                  d="M 10 75 A 65 65 0 0 1 140 75" 
                  fill="none" 
                  :stroke="getGaugeColor(c.score)" 
                  stroke-width="10" 
                  stroke-linecap="round"
                  :stroke-dasharray="gaugeLength" 
                  :stroke-dashoffset="getDashOffset(c.score)"
                  style="transition: stroke-dashoffset 0.6s cubic-bezier(0.4, 0, 0.2, 1);"
                />
                <!-- Текст в центре -->
                <text x="75" y="68" text-anchor="middle" class="fs-4 fw-bold" :fill="getGaugeColor(c.score)">
                  {{ Number(c.score ?? 0).toFixed(1) }}
                </text>
              </svg>
            </div>

            <!-- Дополнительная информация -->
            <div class="mb-2">
              <span class="badge" :style="{ backgroundColor: getGaugeColor(c.score), color: '#fff' }">
                {{ getRangeLabel(c) }}
              </span>
            </div>
            <div class="small text-muted mb-3">
              Вес в модели: <strong class="text-dark">{{ ((c.weight ?? 0) * 100).toFixed(0) }}%</strong>
            </div>

            <!-- Рекомендации -->
            <div class="bg-light rounded p-2 w-100 text-start mb-3">
              <div class="small fw-medium text-muted mb-1">Рекомендации:</div>
              <ul class="mb-0 small ps-3 list-unstyled">
                <li v-for="(rec, i) in getRecommendations(c)" :key="i" class="mb-1">• {{ rec }}</li>
              </ul>
            </div>

            <!-- Кнопка детального просмотра -->
            <button class="btn btn-outline-primary btn-sm w-100 mt-auto" @click="viewDetails(c.id)">
              Подробный анализ
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

// Длина полуокружности спидометра (R=65)
const gaugeLength = Math.PI * 65

// Исходные данные (в реальном проекте `score` придёт с бэкенда после расчёта)
const criteria = ref([
  { id: 1, name: 'Безопасность', color: '#dc3545', active: true, weight: 0.25, score: 2.2, createdAt: '2024-01-15T10:30:00', ranges: [{ label: 'Ужасно', min: 0, max: 3 }, { label: 'Плохо', min: 3, max: 5 }, { label: 'Нормально', min: 5, max: 7 }, { label: 'Хорошо', min: 7, max: 9 }, { label: 'Отлично', min: 9, max: 10 }] },
  { id: 2, name: 'Комфортность', color: '#0d6efd', active: true, weight: 0.20, score: 9.5, createdAt: '2024-01-16T14:20:00', ranges: [{ label: 'Ужасно', min: 0, max: 3 }, { label: 'Плохо', min: 3, max: 5 }, { label: 'Нормально', min: 5, max: 7 }, { label: 'Хорошо', min: 7, max: 9 }, { label: 'Отлично', min: 9, max: 10 }] },
  { id: 3, name: 'Управляемость', color: '#198754', active: false, weight: 0.15, score: 4.1, createdAt: '2024-01-17T09:15:00', ranges: [{ label: 'Ужасно', min: 0, max: 3 }, { label: 'Плохо', min: 3, max: 5 }, { label: 'Нормально', min: 5, max: 7 }, { label: 'Хорошо', min: 7, max: 9 }, { label: 'Отлично', min: 9, max: 10 }] },
  { id: 4, name: 'Функциональность', color: '#ffc107', active: true, weight: 0.18, score: 7.8, createdAt: '2024-01-18T11:45:00', ranges: [{ label: 'Ужасно', min: 0, max: 3 }, { label: 'Плохо', min: 3, max: 5 }, { label: 'Нормально', min: 5, max: 7 }, { label: 'Хорошо', min: 7, max: 9 }, { label: 'Отлично', min: 9, max: 10 }] },
  { id: 5, name: 'Обитаемость', color: '#6f42c1', active: true, weight: 0.12, score: 5.0, createdAt: '2024-01-19T16:00:00', ranges: [{ label: 'Ужасно', min: 0, max: 3 }, { label: 'Плохо', min: 3, max: 5 }, { label: 'Нормально', min: 5, max: 7 }, { label: 'Хорошо', min: 7, max: 9 }, { label: 'Отлично', min: 9, max: 10 }] },
  { id: 6, name: 'Освояемость', color: '#20c997', active: false, weight: 0.10, score: 3.5, createdAt: '2024-01-20T08:30:00', ranges: [{ label: 'Ужасно', min: 0, max: 3 }, { label: 'Плохо', min: 3, max: 5 }, { label: 'Нормально', min: 5, max: 7 }, { label: 'Хорошо', min: 7, max: 9 }, { label: 'Отлично', min: 9, max: 10 }] }
])

// Фильтр: только активные критерии
const activeCriteria = computed(() => criteria.value.filter(c => c.active))

// Общие вычисления
const overallScore = computed(() => {
  const list = activeCriteria.value
  if (list.length === 0) return '0.0'
  let wSum = 0, wTotal = 0
  list.forEach(c => { 
    wSum += (Number(c.score) || 0) * (Number(c.weight) || 0)
    wTotal += (Number(c.weight) || 0) 
  })
  return wTotal > 0 ? (wSum / wTotal).toFixed(1) : '0.0'
})

const overallLabel = computed(() => {
  const s = parseFloat(overallScore.value)
  const refRanges = activeCriteria.value[0]?.ranges || criteria.value[0]?.ranges
  if (!refRanges) return 'Н/Д'
  const r = refRanges.find(rng => s >= rng.min && s < rng.max)
  return r ? r.label : (s === 10 ? 'Отлично' : 'Н/Д')
})

const overallGaugeColor = computed(() => getGaugeColor(parseFloat(overallScore.value)))

// Логика спидометра
function getDashOffset(score) {
  const clamped = Math.min(Math.max(Number(score) || 0, 0), 10)
  return gaugeLength - (clamped / 10) * gaugeLength
}

function getGaugeColor(score) {
  const val = Number(score) || 0
  if (val < 3) return '#dc3545'   // Красный
  if (val < 5) return '#fd7e14'   // Оранжевый
  if (val < 7) return '#ffc107'   // Желтый
  if (val < 9) return '#84cc16'   // Лаймовый
  return '#198754'                // Зеленый
}

// Вспомогательные функции
function getRangeLabel(c) {
  const s = Number(c.score) || 0
  const r = c.ranges?.find(rng => s >= rng.min && s < rng.max)
  return r ? r.label : (s === 10 ? 'Отлично' : 'Н/Д')
}

function getRecommendations(c) {
  const s = Number(c.score) || 0
  if (s < 3) return [
    'Проведите срочный аудит текущего состояния.',
    'Пересмотрите базовые параметры и устраните критические дефекты.',
    'Обновите анкету для выявления корневых причин низкого балла.'
  ]
  if (s < 5) return [
    'Оптимизируйте конфигурацию пространства.',
    'Внедрите первоочередные улучшения по выявленным недостаткам.',
    'Скорректируйте весовые коэффициенты для точности модели.'
  ]
  if (s < 7) return [
    'Показатели в норме, но есть потенциал роста.',
    'Добавьте уточняющие вопросы в анкету для детализации.',
    'Проведите регулярный мониторинг изменений.'
  ]
  if (s < 9) return [
    'Хороший результат. Поддерживайте текущий уровень.',
    'Внедрите превентивные меры для сохранения показателей.',
    'Используйте зону как пилотную для масштабирования опыта.'
  ]
  return [
    'Критерий полностью соответствует стандартам эргономики.',
    'Продолжайте мониторинг для поддержания высоких показателей.',
    'Рекомендуется использовать текущую конфигурацию как эталон.'
  ]
}

function viewDetails(id) {
  console.log(`Переход к детальному анализу критерия #${id}`)
  alert(`Заготовка: открытие страницы детальной аналитики для критерия ID: ${id}`)
}
</script>