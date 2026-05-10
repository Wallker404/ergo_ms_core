<template>
  <div class="container mt-5">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h3>📈 График данных</h3>
      <div class="d-flex gap-2">
        <button 
          class="btn btn-outline-secondary" 
          @click="toggleChartType"
        >
          {{ isScatter ? '🔗 Линия' : '⚫ Точки' }}
        </button>
        <button 
          class="btn btn-primary" 
          @click="loadData" 
          :disabled="loading"
        >
          <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
          {{ loading ? 'Загрузка...' : 'Обновить' }}
        </button>
      </div>
    </div>

    <!-- Контейнер для графика -->
    <div class="card shadow-sm">
      <div class="card-body">
        <canvas ref="chartCanvas" id="myChart"></canvas>
      </div>
    </div>

    <!-- Статусы -->
    <div v-if="error" class="alert alert-danger mt-3">❌ {{ error }}</div>
    <div v-if="!loading && !error && points.length === 0" class="alert alert-info mt-3">
      ℹ️ Нет данных для отображения
    </div>

    <!-- Статистика -->
    <div v-if="points.length > 0" class="row mt-3">
      <div class="col-md-3">
        <div class="card bg-light">
          <div class="card-body py-2 text-center">
            <small class="text-muted">Точек</small>
            <div class="fw-bold fs-5">{{ points.length }}</div>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card bg-light">
          <div class="card-body py-2 text-center">
            <small class="text-muted">X: мин</small>
            <div class="fw-bold fs-5">{{ stats.minX }}</div>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card bg-light">
          <div class="card-body py-2 text-center">
            <small class="text-muted">X: макс</small>
            <div class="fw-bold fs-5">{{ stats.maxX }}</div>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card bg-light">
          <div class="card-body py-2 text-center">
            <small class="text-muted">Y: среднее</small>
            <div class="fw-bold fs-5">{{ stats.avgY }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import {
  Chart,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  LineController,      
  ScatterController,
} from 'chart.js'
import { apiClient } from '@/js/api/manager'
import { roomAnalyticsEndpoints } from '../js/endpoints'

// Регистрация модулей Chart.js (обязательно!)
Chart.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  LineController, 
  ScatterController,
  Title,
  Tooltip,
  Legend,
  Filler
)

// Реактивные данные
const chartCanvas = ref(null)
const loading = ref(false)
const error = ref(null)
const points = ref([]) // [{ x: number, y: number }]
const isScatter = ref(true) // режим: точки или линия
let chartInstance = null // экземпляр графика

// Вычисляемая статистика
const stats = computed(() => {
  if (!points.value.length) return { minX: '–', maxX: '–', avgY: '–' }
  const xs = points.value.map(p => p.x)
  const ys = points.value.map(p => p.y)
  return {
    minX: Math.min(...xs).toFixed(2),
    maxX: Math.max(...xs).toFixed(2),
    avgY: (ys.reduce((a, b) => a + b, 0) / ys.length).toFixed(2)
  }
})

// Инициализация графика
const initChart = (dataPoints) => {
  // Уничтожаем старый экземпляр, если есть
  if (chartInstance) {
    chartInstance.destroy()
  }

  const ctx = chartCanvas.value.getContext('2d')
  
  chartInstance = new Chart(ctx, {
    type: isScatter.value ? 'scatter' : 'line',
    data: {
      datasets: [{
        label: 'Данные',
        data: dataPoints, // [{ x: 1, y: 10 }, ...]
        backgroundColor: 'rgba(54, 162, 235, 0.6)',
        borderColor: 'rgba(54, 162, 235, 1)',
        borderWidth: 2,
        pointRadius: 5,
        pointHoverRadius: 8,
        pointBackgroundColor: 'rgba(54, 162, 235, 1)',
        tension: 0.3, // сглаживание линии (только для line)
        fill: false
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: 500,
        easing: 'easeOutQuart'
      },
      plugins: {
        legend: {
          display: true,
          position: 'top',
          labels: {
            font: { size: 12 },
            color: '#333'
          }
        },
        title: {
          display: true,
          text: 'Распределение данных',
          font: { size: 16, weight: 'bold' },
          color: '#333',
          padding: { top: 10, bottom: 20 }
        },
        tooltip: {
          enabled: true,
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          titleColor: '#fff',
          bodyColor: '#fff',
          borderColor: '#54a2eb',
          borderWidth: 1,
          padding: 12,
          displayColors: false,
          callbacks: {
            label: (context) => {
              return `X: ${context.parsed.x} | Y: ${context.parsed.y}`
            }
          }
        }
      },
      scales: {
        x: {
          type: 'linear',
          position: 'bottom',
          title: {
            display: true,
            text: 'Значение X',
            font: { size: 13 },
            color: '#666'
          },
          grid: {
            color: 'rgba(0, 0, 0, 0.05)',
            drawBorder: false
          },
          ticks: {
            color: '#666',
            font: { size: 11 }
          }
        },
        y: {
          title: {
            display: true,
            text: 'Значение Y',
            font: { size: 13 },
            color: '#666'
          },
          grid: {
            color: 'rgba(0, 0, 0, 0.05)',
            drawBorder: false
          },
          ticks: {
            color: '#666',
            font: { size: 11 }
          },
          beginAtZero: false
        }
      },
      interaction: {
        mode: 'nearest',
        intersect: false
      }
    }
  })
}

// Загрузка данных с бэкенда
const loadData = async () => {
  loading.value = true
  error.value = null
  
  try {
    const res = await apiClient.get(roomAnalyticsEndpoints.roomAnalytics.test)
    
    // Ожидаемый формат: { points: [{ x: 1, y: 10.5 }, ...] }
    points.value = res.data.points || []
    console.log(points.value);
    if (points.value.length > 0) {
      initChart(points.value)
    }
    
  } catch (err) {
    console.error('Ошибка загрузки графика:', err)
    error.value = err.response?.data?.error || 'Не удалось загрузить данные'
    points.value = []
  } finally {
    loading.value = false
  }
}

// Переключение типа графика
const toggleChartType = () => {
  isScatter.value = !isScatter.value
  if (points.value.length > 0) {
    initChart(points.value) // перерисовать с новым типом
  }
}

// Очистка при размонтировании (важно! предотвращает утечки памяти)
onBeforeUnmount(() => {
  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = null
  }
})

// Автозагрузка при монтировании
onMounted(() => {
  loadData()
})
</script>

<style scoped>
.card {
  border-radius: 12px;
  border: none;
}
canvas {
  max-width: 100%;
  height: 400px !important; /* фиксированная высота для корректного рендера */
}
.btn {
  border-radius: 8px;
}
</style>