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
          {{ fileName ? 'Выбранный файл: ' + fileName : 'Выбрать файл' }}
        </button>
        
        <div v-if="fileError" class="text-danger small mt-1">{{ fileError }}</div>
        <div v-if="fileName" class="form-text">
          Файл выбран. Нажмите "Анализировать" для начала обработки.
        </div>
      </div>

      <div class="mb-3">
        <label class="form-label">Алгоритм</label>
        <select v-model="algorithm" class="form-select">
          <option value="pre_analyse">Получить графики методов локтя и силуэта</option>
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

    <!-- Шаг 2: Pre-analysis -->
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

    <!-- Шаг 3: Результат кластеризации (ОБНОВЛЕНО) -->
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

      <!-- Chart.js вместо картинки -->
      <div class="bg-light rounded p-2" style="position: relative; height: 500px;">
        <canvas ref="clusterChart"></canvas>
      </div>

      <!-- Легенда для переключения кластеров -->
      <div v-if="clusterDatasets?.length" class="d-flex flex-wrap gap-2 mt-3">
        <div 
          v-for="(ds, i) in clusterDatasets" 
          :key="i"
          class="d-inline-flex align-items-center small"
          @click="toggleDataset(i)"
          style="cursor: pointer; padding: 4px 8px; border-radius: 4px;"
          :class="{'text-decoration-line-through opacity-50': ds.hidden}"
        >
          <span 
            class="rounded me-1 border"
            style="width: 14px; height: 14px; display: inline-block;"
            :style="{ backgroundColor: ds.backgroundColor }"
          ></span>
          {{ ds.label }}
        </div>
      </div>

<!-- Статистика по кластерам (карточки) -->
<div v-if="clusterStats" class="mt-4">
  <h6 class="mb-3">Характеристики кластеров</h6>

  <!-- Переключатели кластеров -->
  <div class="d-flex flex-wrap gap-2 mb-3">
    <button
      v-for="(stats, key) in clusterStats"
      :key="key"
      class="btn btn-sm d-flex align-items-center gap-1 px-3 py-2"
      :class="selectedCluster === key ? 'btn-primary shadow-sm' : 'btn-outline-secondary'"
      @click="selectedCluster = key"
    >
      <span>{{ key === 'noise' ? 'Шум' : `Кластер ${key.split('_')[1]}` }}</span>
      <span class="badge" :class="selectedCluster === key ? 'text-bg-light' : 'bg-secondary bg-opacity-75'">
        {{ stats.size }}
      </span>
    </button>
  </div>

  <!-- Карточка с таблицей -->
  <div v-if="currentStats" class="card border shadow-sm">
    <div class="card-header bg-light py-2 d-flex justify-content-between align-items-center">
      <span class="fw-bold">{{ currentClusterLabel }}</span>
      <span class="badge bg-light text-primary border border-primary rounded-pill">
        {{ currentStats.size }} наблюдений
      </span>
    </div>
    <div class="card-body p-0">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead>
            <tr class="bg-light">
              <th scope="col" class="ps-3">Параметр</th>
              <th scope="col" class="text-center">Среднее</th>
              <th scope="col" class="text-center">Минимум</th>
              <th scope="col" class="text-center pe-3">Максимум</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="feat in features" :key="feat">
              <td class="ps-3 fw-medium">{{ feat }}</td>
              <td class="text-center fw-semibold">{{ formatNum(currentStats.features[feat]?.mean) }}</td>
              <td class="text-center text-success">{{ formatNum(currentStats.features[feat]?.min) }}</td>
              <td class="text-center text-danger pe-3">{{ formatNum(currentStats.features[feat]?.max) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</div>


      <div class="mt-3">
        <button @click="reset" class="btn btn-outline-primary">Новый анализ</button>
      </div>
    </div>
  </div>
</template>

<script setup>

//#region Импорты
import { ref, watch, onBeforeUnmount, nextTick, computed } from 'vue'
import { Chart, registerables } from 'chart.js'
import { apiClient } from '../../../../core/client/src/js/api/manager'
import { roomAnalyticsEndpoints } from '../js/endpoints'
Chart.register(...registerables)
//#endregion

//#region Vue параметры
// Состояние
const loading = ref(false)
const error = ref('')
const algorithm = ref('kmeans')
const step = ref('upload')
const fileInput = ref(null)
const fileName = ref('')
const fileError = ref('')

// Параметры
const file = ref(null)
const k = ref(3)
const eps = ref(0.5)
const minSamples = ref(5)

// Chart refs
const elbowChart = ref(null)
const silhouetteChart = ref(null)
const clusterChart = ref(null)
let chartInstances = {}

// Данные кластеризации
const features = ref([])
const selectedXIdx = ref(0)
const selectedYIdx = ref(1)
const resultInfo = ref('')
const clusterDatasets = ref([]) // для легенды
const clusterStats = ref(null)


const formatNum = (val) => {
  if (val === undefined || val === null) return '—'
  const num = Number(val)
  return (Math.abs(num) >= 100000 || Math.abs(num) < 0.01) &&Math.abs(num)!=0
    ? num.toExponential(2) 
    : num.toFixed(2)
}
//#endregion

//#region Загрузка данных
const buildFormData = (params) => {
  const fd = new FormData()
  fd.append('file', file.value)
  Object.entries(params || {}).forEach(([key, val]) => {
    fd.append(key, val)
  })
  return fd
}

const triggerUpload = () => fileInput.value?.click()

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
//#endregion

//#region Запросы api для запуска кластеризации
const submitAnalysis = async () => {
  loading.value = true
  error.value = ''
  
  try {
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
      await nextTick()
      renderElbowChart(elbowRes.data)
      renderSilhouetteChart(silRes.data)
      
    } else if (algorithm.value === 'kmeans') {
      if (!k.value || k.value < 2) {
        error.value = 'k должно быть >= 2'
        return
      }
      const res = await apiClient.post(
        roomAnalyticsEndpoints.roomAnalytics.kmeans,
        buildFormData({ k: k.value })
      )
      if (!res.success) throw new Error(res.message || 'Ошибка кластеризации')
      handleClusteringResult(res.data)
      
    } else if (algorithm.value === 'dbscan') {
      const res = await apiClient.post(
        roomAnalyticsEndpoints.roomAnalytics.dbscan,
        buildFormData({ eps: eps.value, min_samples: minSamples.value })
      )
      if (!res.success) throw new Error(res.message || 'Ошибка кластеризации')
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
    handleClusteringResult(res.data)
  } catch (e) {
    error.value = e.message || 'Ошибка сети'
  } finally {
    loading.value = false
  }
}
//#endregion

//#region ChartJs методы
const handleClusteringResult = (data) => {
  step.value = 'results'
  resultInfo.value = `${data.algorithm?.toUpperCase() || 'CLUSTERING'} | Кластеров: ${data.n_clusters}${data.n_noise ? ` | Шума: ${data.n_noise}` : ''}`
  features.value = data.features || []
  
  if (data.chart_data?.datasets) {
    clusterDatasets.value = data.chart_data.datasets.map(ds => ({
      ...ds,
      hidden: false
    }))
  }
  
  clusterStats.value = data.cluster_stats || null

  if (features.value.length >= 2) {
    selectedXIdx.value = 0
    selectedYIdx.value = 1
  }
  
  nextTick(() => {
    renderClusterChart(data.chart_data)
  })
}

// 🔹 ОБНОВЛЕНО: перерисовка с новыми осями
const updatePlot = async () => {
  if (loading.value || !file.value || features.value.length < 2) return
  loading.value = true
  try {
    const endpoint = algorithm.value === 'kmeans' 
      ? roomAnalyticsEndpoints.roomAnalytics.kmeans 
      : roomAnalyticsEndpoints.roomAnalytics.dbscan
    const payload = algorithm.value === 'kmeans' 
      ? { k: k.value } 
      : { eps: eps.value, min_samples: minSamples.value }
    
    const fd = new FormData()
    fd.append('file', file.value)
    Object.entries(payload).forEach(([key, val]) => fd.append(key, val))
    fd.append('x_axis', selectedXIdx.value)
    fd.append('y_axis', selectedYIdx.value)

    const res = await apiClient.post(endpoint, fd)
    if (!res.success) throw new Error(res.message || 'Ошибка сервера')
    
    // Обновляем данные и перерисовываем
    if (res.data.chart_data?.datasets) {
      clusterDatasets.value = res.data.chart_data.datasets.map(ds => ({
        ...ds,
        hidden: false
      }))
      clusterStats.value = res.data.cluster_stats || null 
      renderClusterChart(res.data.chart_data)
    }
  } catch (e) {
    error.value = e.message || 'Ошибка сети'
  } finally {
    loading.value = false
  }
}

// 🔹 НОВАЯ: отрисовка через Chart.js
const renderClusterChart = (chartData) => {
  if (!clusterChart.value || !chartData?.datasets) return
  
  // Уничтожаем старый
  if (chartInstances.cluster) {
    chartInstances.cluster.destroy()
  }
  
  const ctx = clusterChart.value.getContext('2d')
  
  // Подготовка датасетов с учетом hidden-состояния
  const datasets = clusterDatasets.value.map(ds => ({
    ...ds,
    hidden: ds.hidden,
    // Убеждаемся в формате цвета
    backgroundColor: ds.backgroundColor.includes('rgba') 
      ? ds.backgroundColor 
      : ds.backgroundColor.replace('rgb', 'rgba').replace(')', ', 0.7)'),
  }))
  
  chartInstances.cluster = new Chart(ctx, {
    type: 'scatter',
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const raw = ctx.raw
              return `${ctx.dataset.label}: ${chartData.xAxisLabel}=${raw.x?.toFixed(3)}, ${chartData.yAxisLabel}=${raw.y?.toFixed(3)}`
            }
          }
        }
      },
      scales: {
        x: {
          title: { display: true, text: chartData.xAxisLabel },
          type: 'linear',
          position: 'bottom',
          grid: { color: 'rgba(0,0,0,0.1)' }
        },
        y: {
          title: { display: true, text: chartData.yAxisLabel },
          grid: { color: 'rgba(0,0,0,0.1)' }
        }
      }
    }
  })
}

// Переключение видимости датасета
const toggleDataset = (index) => {
  if (!chartInstances.cluster) return
  clusterDatasets.value[index].hidden = !clusterDatasets.value[index].hidden
  const meta = chartInstances.cluster.getDatasetMeta(index)
  meta.hidden = clusterDatasets.value[index].hidden
  chartInstances.cluster.update()
}


const destroyChart = (name) => {
  if (chartInstances[name]) {
    chartInstances[name].destroy()
    delete chartInstances[name]
  }
}
//#endregion

//#region Методы для отрисовки метода локтя и метода силуэтов
const renderElbowChart = async (data) => {
  destroyChart('elbow')
  await nextTick()
  const canvas = elbowChart.value
  if (!canvas?.getContext) return

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
}

const renderSilhouetteChart = async (data) => {
  destroyChart('silhouette')
  await nextTick()
  const canvas = silhouetteChart.value
  if (!canvas?.getContext) return

  chartInstances.silhouette = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: data.k_values,
      datasets: [{
        label: 'Silhouette Score',
        data: data.silhouette,
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
        y: { min: -1, max: 1, title: { display: true, text: 'Score' } },
        x: { title: { display: true, text: 'k' } }
      }
    }
  })
}
//#endregion

//#region Методы по очистке данных
const reset = () => {
  step.value = 'upload'
  file.value = null
  fileName.value = ''
  error.value = ''
  features.value = []
  clusterDatasets.value = []
  selectedXIdx.value = 0
  selectedYIdx.value = 1
  clusterStats.value = null
  selectedCluster.value = null
  Object.keys(chartInstances).forEach(key => destroyChart(key))
  if (fileInput.value) fileInput.value.value = ''
}

onBeforeUnmount(() => Object.keys(chartInstances).forEach(key => destroyChart(key)))
//#endregion

const selectedCluster = ref(null)

// Автоматически выбираем первый кластер при загрузке данных
watch(clusterStats, (newStats) => {
  if (newStats && Object.keys(newStats).length > 0) {
    selectedCluster.value = Object.keys(newStats)[0]
  }
}, { immediate: true })

// Вычисляемые свойства для текущей карточки
const currentStats = computed(() => clusterStats.value?.[selectedCluster.value] || null)
const currentClusterLabel = computed(() => {
  if (!selectedCluster.value) return ''
  return selectedCluster.value === 'noise' ? 'Шумовые точки' : `Кластер ${selectedCluster.value.split('_')[1]}`
})

</script>
