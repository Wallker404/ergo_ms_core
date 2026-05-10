<template>
  <div class="container py-4">
    <h2 class="mb-4">Кластеризация данных</h2>

    <!-- Шаг 1: Загрузка и параметры -->
    <div v-if="step === 'upload'" class="card p-4">
      <div class="mb-3">
  <label class="form-label">Загрузите файл (.csv или .json)</label>
  
  <input
    type="file"
    ref="fileInput"
    @change="onFileChange"
    accept=".csv,.json"
    hidden
  />
  
  <button class="btn btn-primary w-100" @click="triggerUpload" type="button">
    {{ fileName ? 'Выбранный файл' + fileName : 'Выбрать файл' }}
  </button>
  
  <div v-if="fileError" class="text-danger small mt-1">{{ fileError }}</div>
  <div v-if="fileName" class="form-text">
    Файл выбран. Нажмите "Анализировать" для начала обработки.
  </div>
</div>

      <div class="mb-3">
        <label class="form-label">Алгоритм</label>
        <select v-model="algorithm" class="form-select">
          <option value = 'pre_analyse'>Получить графики методов локтя и силуэта</option>
          <option value="kmeans">K-Means</option>
          <option value="dbscan">DBSCAN</option>
           
        </select>
      </div>

      <!-- Параметры K-Means -->
      <div v-if="algorithm === 'kmeans'" class="mb-3">
        <label class="form-label">k (кол-во кластеров)</label>
        <input type="number" v-model.number="k" min="2" max="20" class="form-control" />
      </div>

      <!-- Параметры DBSCAN -->
      <div v-if="algorithm === 'dbscan'" class="row g-3 mb-3">
        <div class="col-md-6">
          <label class="form-label">eps</label>
          <input type="number" v-model.number="eps" step="0.1" min="0.01" class="form-control" />
        </div>
        <div class="col-md-6">
          <label class="form-label">min_samples</label>
          <input type="number" v-model.number="minSamples" min="1" class="form-control" />
        </div>
      </div>

      <button @click="submitAnalysis" :disabled="loading || !file" class="btn btn-primary">
        {{ loading ? 'Обработка...' : 'Анализировать' }}
      </button>
      <div v-if="error" class="alert alert-danger mt-3 mb-0">{{ error }}</div>
    </div>

    <div v-else-if="step === 'pre_analysis'" class="card p-4">
      <h4 class="mb-3">Выбор оптимального k</h4>
      <div class="row g-4 mb-4">
        <div class="col-md-6">
          <canvas ref="elbowChart" class="w-100" style="height: 300px;"></canvas>
        </div>
        <div class="col-md-6">
          <canvas ref="silhouetteChart" class="w-100" style="height: 300px;"></canvas>
        </div>
      </div>
      <div class="d-flex align-items-center gap-3">
        <label class="form-label mb-0">Итоговое k:</label>
        <input type="number" v-model.number="k" min="2" class="form-control" style="max-width: 100px;" />
        <button @click="runFinalClustering" class="btn btn-success">Построить кластеры</button>
        <button @click="reset" class="btn btn-outline-secondary">Назад</button>
      </div>
    </div>

    <!-- Шаг 3: Результат кластеризации -->
    <div v-else-if="step === 'results'" class="card p-4">
  <h4 class="mb-3">Результат: {{ resultInfo }}</h4>

  <div class="row g-3 mb-3">
    <div class="col-md-6">
      <label class="form-label">Ось X</label>
      <select v-model="selectedXIdx" @change="updatePlot" class="form-select">
        <option v-for="(f, i) in features" :key="i" :value="i">{{ f }}</option>
      </select>
    </div>
    <div class="col-md-6">
      <label class="form-label">Ось Y</label>
      <select v-model="selectedYIdx" @change="updatePlot" class="form-select">
        <option v-for="(f, i) in features" :key="i" :value="i">{{ f }}</option>
      </select>
    </div>
  </div>

  <div class="text-center bg-light rounded p-2">
    <img v-if="plotImage" :src="plotImage" class="img-fluid" alt="График" style="max-height: 600px;" />
    <div v-else class="text-muted p-4">Генерация графика...</div>
  </div>

  <div class="mt-3">
    <button @click="reset" class="btn btn-outline-primary">Новый анализ</button>
  </div>
</div>
  </div>
</template>

<script setup>
import { ref,watch, onBeforeUnmount } from 'vue'
import { Chart, registerables } from 'chart.js'
import { apiClient } from '../../../../core/client/src/js/api/manager'
import { roomAnalyticsEndpoints } from '../js/endpoints'

Chart.register(...registerables)
// надстройки сайта
const loading = ref(false)
const error = ref('')
const algorithm = ref('kmeans')
const step = ref('upload')
const fileInput = ref(null)
const fileName = ref('')
const fileError = ref('')

// передаваемые параметры
const file = ref(null)
const k = ref(3)
const eps = ref(0.5)
const minSamples = ref(5)

// Chart refs
const elbowChart = ref(null)
const silhouetteChart = ref(null)
const clusterChart = ref(null)
let chartInstances = {}

//Работа с кластеризацией
const features = ref([])
const selectedXIdx = ref(0)
const selectedYIdx = ref(1)
const plotImage = ref('')
const clusterData = ref([])
const centroidsData = ref([])
const resultInfo = ref('')
const selectedX = ref('')
const selectedY = ref('')

//подготовка данных
const buildFormData = (params) => {
  const fd = new FormData()
  fd.append('file', file.value)
  Object.entries(params || {}).forEach(([key, val]) => {
    fd.append(key, val)
  })
  return fd
}

//вызов загрузки файла при нажатии на кнопку
const triggerUpload = () => fileInput.value?.click()

// изменение параметров при загрузке файла
const onFileChange = (e) => {
  const selected = e.target.files?.[0]
  if (!selected) {
    fileName.value = ''
    file.value = null
    return
  }

  const ext = selected.name.split('.').pop().toLowerCase()
  if (!['csv', 'json'].includes(ext)) {
    fileError.value = 'Поддерживаются только .csv и .json'
    fileName.value = ''
    file.value = null
    e.target.value = ''
    return
  }
  fileName.value = selected.name
  file.value = selected
  fileError.value = ''
}

//запуск анализа
const submitAnalysis = async () => {
  loading.value = true
  error.value = ''
  
  try {
    //вывод графиков до kmeans
    if (algorithm.value === 'pre_analyse') {
      const [elbowRes, silRes] = await Promise.all([
        apiClient.post(
          roomAnalyticsEndpoints.roomAnalytics.elbow,
          buildFormData({ k_start: 2, k_end: 10 })
        ),
        apiClient.post(
          roomAnalyticsEndpoints.roomAnalytics.silhouette,
          buildFormData({ k_start: 2, k_end: 10 })
        )
      ])
      if (!elbowRes.success || !silRes.success) {
        throw new Error(elbowRes.message || silRes.message || 'Ошибка предварительного анализа')
      }
      
      step.value = 'pre_analysis'
      renderElbowChart(elbowRes.data)   // <-- res.data уже содержит ответ от Django
      renderSilhouetteChart(silRes.data)
      
    } 
    // отработка по k-means
    else if (algorithm.value === 'kmeans') {
      if (!k.value || k.value < 2) {
        error.value = 'k должно быть >= 2'
        return
      }
      console.log(buildFormData({ k: k.value }))
      const res = await apiClient.post(
        roomAnalyticsEndpoints.roomAnalytics.kmeans,
        buildFormData({ k: k.value })
      )
      if (!res.success) throw new Error(res.message || 'Ошибка кластеризации')
      console.log(res.data)
      handleClusteringResult(res.data)
      
    } 
    //вызов dbscan
    else if (algorithm.value === 'dbscan') {
      const res = await apiClient.post(
        roomAnalyticsEndpoints.roomAnalytics.dbscan,
        buildFormData({ eps: eps.value, min_samples: minSamples.value })
      )
      if (!res.success) throw new Error(res.message || 'Ошибка кластеризации')
      console.log(res.data)
      handleClusteringResult(res.data)
    
    }
  } catch (e) {
    error.value = e.message || 'Ошибка сети'
    console.error(e)
  } finally {
    loading.value = false
  }
}

const runFinalClustering = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await apiClient.post(
      roomAnalyticsEndpoints.roomAnalytics.kmeans,
      buildFormData({ k: k.value })
    )
    if (!res.success) throw new Error(res.message || 'Ошибка кластеризации')
    console.log(res.data)
    handleClusteringResult(res.data)
  } catch (e) {
    error.value = e.message || 'Ошибка сети'
  } finally {
    loading.value = false
  }
}

const handleClusteringResult = (data) => {
  step.value = 'results'
  resultInfo.value = `${data.algorithm?.toUpperCase() || 'CLUSTERING'} | Кластеров: ${data.n_clusters}${data.n_noise ? ` | Шума: ${data.n_noise}` : ''}`
  features.value = data.features || []
  plotImage.value = data.plot || ''
  if (features.value.length >= 2) {
    selectedXIdx.value = 0
    selectedYIdx.value = 1
  }
}
const updatePlot = async () => {
  if (loading.value || !file.value || features.value.length < 2) return
  loading.value = true
  try {
    const endpoint = algorithm.value === 'kmeans' ? roomAnalyticsEndpoints.roomAnalytics.kmeans : roomAnalyticsEndpoints.roomAnalytics.dbscan
    const payload = algorithm.value === 'kmeans' ? { k: k.value } : { eps: eps.value, min_samples: minSamples.value }
    
    const fd = new FormData()
    fd.append('file', file.value)
    Object.entries(payload).forEach(([key, val]) => fd.append(key, val))
    fd.append('x_axis', selectedXIdx.value)
    fd.append('y_axis', selectedYIdx.value)

    const res = await apiClient.post(endpoint, fd)
    if (!res.success) throw new Error(res.message || 'Ошибка сервера')
    plotImage.value = res.data.plot || ''
  } catch (e) {
    error.value = e.message || 'Ошибка сети'
  } finally {
    loading.value = false
  }
}

watch([selectedX, selectedY], () => {
  if (step.value === 'results') renderClusterChart()
})




const renderClusterChart = () => {
  destroyChart('cluster')
  
  const xKey = selectedX.value
  const yKey = selectedY.value
  if (!xKey || !yKey || !clusterData.value.length) return

  // 🔹 1. Собираем все числовые значения для расчёта границ
  const allX = clusterData.value.map(p => p[xKey]).filter(v => typeof v === 'number' && isFinite(v))
  const allY = clusterData.value.map(p => p[yKey]).filter(v => typeof v === 'number' && isFinite(v))
  
  if (!allX.length || !allY.length) return

  const xMin = Math.min(...allX), xMax = Math.max(...allX)
  const yMin = Math.min(...allY), yMax = Math.max(...allY)
  
  // 🔹 2. Нормализуем координаты в диапазон [0, 100] для визуального баланса
  // Это НЕ меняет данные, только координаты для отрисовки
  const normalize = (val, min, max) => {
    if (max === min) return 50 // если все значения одинаковые — центр
    return ((val - min) / (max - min)) * 100
  }

  const uniqueLabels = [...new Set(clusterData.value.map(p => p.label))]
  const colors = ['#dc3545', '#0d6efd', '#198754', '#ffc107', '#6f42c1', '#d63384', '#0dcaf0', '#6610f2']
  
  const datasets = uniqueLabels.map((lbl, i) => ({
    label: lbl === -1 ? 'Noise' : `Cluster ${lbl}`,
    // 🔹 Нормализуем x/y для отрисовки, но сохраняем оригиналы в скрытых полях
    data: clusterData.value
      .filter(p => p.label === lbl)
      .map(p => ({
        x: normalize(p[xKey], xMin, xMax),
        y: normalize(p[yKey], yMin, yMax),
        _realX: p[xKey],  // 🔹 сохраняем реальное значение для тултипа
        _realY: p[yKey]
      })),
    backgroundColor: lbl === -1 ? '#6c757d' : colors[i % colors.length],
    pointRadius: 4,
    pointHoverRadius: 6
  }))

  if (centroidsData.value.length) {
    datasets.push({
      label: 'Centroids',
      data: centroidsData.value.map(p => ({
        x: normalize(p[xKey], xMin, xMax),
        y: normalize(p[yKey], yMin, yMax),
        _realX: p[xKey],
        _realY: p[yKey]
      })),
      backgroundColor: '#000',
      pointStyle: 'crossRot',
      pointRadius: 12,
      pointHoverRadius: 14
    })
  }

  const canvas = clusterChart.value
  if (!canvas) return

  chartInstances.cluster = new Chart(canvas, {
    type: 'scatter',
    data:{ datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      aspectRatio: 1,  // 🔹 Квадратный график — точки не сплющиваются
      animation: { duration: 0 },
      plugins: {
        legend: { position: 'right', labels: { usePointStyle: true } },
        tooltip: {
          callbacks: {
            // 🔹 Показываем РЕАЛЬНЫЕ значения в тултипе, а не нормализованные
            label: (ctx) => {
              const raw = ctx.raw
              const label = ctx.dataset.label || ''
              const realX = raw._realX ?? raw.x
              const realY = raw._realY ?? raw.y
              return `${label}: ${xKey}=${Number(realX).toLocaleString()}, ${yKey}=${Number(realY).toLocaleString()}`
            },
            // 🔹 Заголовок тултипа (опционально)
            title: () => `Точка данных`
          }
        }
      },
      scales: {
        x: {
          title: { display: true, text: xKey, font: { weight: 'bold' } },
          min: 0, max: 100,  // 🔹 Фиксированный диапазон после нормализации
          ticks: {
            // 🔹 Подписи осей: показываем реальные значения, а не 0-100
            callback: (value) => {
              // Обратное преобразование: из [0,100] в реальный диапазон
              const realVal = xMin + (value / 100) * (xMax - xMin)
              return Number(realVal).toLocaleString(undefined, { maximumFractionDigits: 1 })
            },
            maxTicksLimit: 6
          },
          grid: { color: 'rgba(0,0,0,0.05)' }
        },
        y: {
          title: { display: true, text: yKey, font: { weight: 'bold' } },
          min: 0, max: 100,
          ticks: {
            callback: (value) => {
              const realVal = yMin + (value / 100) * (yMax - yMin)
              return Number(realVal).toLocaleString(undefined, { maximumFractionDigits: 1 })
            },
            maxTicksLimit: 6
          },
          grid: { color: 'rgba(0,0,0,0.05)' }
        }
      }
    }
  })
}

// ── Charts ─────────────────────────────────────────────
const destroyChart = (name) => {
  if (chartInstances[name]) {
    chartInstances[name].destroy()
    delete chartInstances[name]
  }
}










const renderElbowChart = async (data) => {
  destroyChart('elbow')
  await new Promise(resolve => {
    const check = () => {
      if (elbowChart.value && elbowChart.value.getContext) {
        resolve()
      } else {
        setTimeout(check, 50)
      }
    }
    check()
  })
  const canvas = elbowChart.value
  if (!canvas) {
    return
  }
  if (typeof canvas.getContext !== 'function') {
    return
  }

  try {
    chartInstances.elbow = new Chart(canvas, {
      type: 'line',
      data: {
        labels: data.k_values,
        datasets: [{
          label: 'Inertia',
          data: data.inertia,
          borderColor: '#0d6efd',
          backgroundColor: 'rgba(13,110,253,0.1)',
          tension: 0.3,
          fill: true
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { title: { display: true, text: 'Метод локтя' } },
        scales: {
          x: { title: { display: true, text: 'k' } },
          y: { title: { display: true, text: 'Inertia' }, beginAtZero: true }
        }
      }
    })
  } catch (e) {
    console.error('Chart.js error:', e)
  }
}





const renderSilhouetteChart = async (data) => {
  destroyChart('silhouette')

  // Ждём, пока канвас будет готов
  await new Promise(resolve => {
    const check = () => {
      if (silhouetteChart.value && typeof silhouetteChart.value.getContext === 'function') {
        resolve()
      } else {
        setTimeout(check, 50)
      }
    }
    check()
  })
  
  const canvas = silhouetteChart.value
  if (!canvas) {
    return
  }
  if (typeof canvas.getContext !== 'function') {
    return
  }

  chartInstances.silhouette = new Chart(canvas, {
    type: 'bar',
    data: {  // 🔹 КЛЮЧ "data:" ДОБАВЛЕН
      labels: data.k_values,
      datasets: [{
        label: 'Silhouette Score',
        data: data.silhouette,  // 🔹 КЛЮЧ "data:" ДОБАВЛЕН
        backgroundColor: '#198754'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { 
        title: { display: true, text: 'Силуэт' },
        legend: { display: true, position: 'top' }
      },
      scales: {
        y: { 
          min: -1, 
          max: 1, 
          title: { display: true, text: 'Score' },
          beginAtZero: false
        },
        x: { 
          title: { display: true, text: 'k' } 
        }
      }
    }
  })
  
  console.log('✅ Silhouette chart created')
}


// ── Reset ──────────────────────────────────────────────
const reset = () => {
  step.value = 'upload'
  file.value = null
  fileName.value = ''
  error.value = ''
  preAnalysis.value = false
  features.value = []
  clusterData.value = []
  centroidsData.value = []
  selectedX.value = ''
  selectedY.value = ''
  Object.keys(chartInstances).forEach(destroyChart)
  if (fileInput.value) fileInput.value.value = ''
}

onBeforeUnmount(() => Object.keys(chartInstances).forEach(destroyChart))
</script>