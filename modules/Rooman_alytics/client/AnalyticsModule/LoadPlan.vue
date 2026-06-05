<template>
  <div class="container-fluid vh-100 d-flex flex-column p-3 bg-light">
    <div class="card flex-grow-1 d-flex flex-column overflow-hidden">
      
      <!-- 🔹 Top buttons -->
      <div class="card-header d-flex align-items-center gap-2 py-2">
        <div class="btn-group" role="group">
          <button
            type="button"
            class="btn btn-outline-primary"
            :class="{ active: displayMode === 'rooms' }"
            @click="setMode('rooms')"
          >
            Указать комнату
          </button>
          <button
            type="button"
            class="btn btn-outline-primary"
            :class="{ active: displayMode === 'walls' }"
            @click="setMode('walls')"
          >
            Указать конструкторские элементы
          </button>
          <button
            type="button"
            class="btn btn-outline-primary"
            :class="{ active: displayMode === 'furniture' }"
            @click="setMode('furniture')"
          >
            Указать мебель
          </button>
        </div>
        <button
          type="button"
          class="btn btn-outline-danger ms-2"
          @click="clearEditor"
          title="Очистить все аннотации"
        >
          Очистить
        </button>
        <!-- 🔹 Кнопка открытия списка планов -->
        <button 
          type="button" 
          class="btn btn-outline-info ms-2"
          @click="toggleFloorplansPanel">
          Планы
        </button>
      </div>

      <div class="card-body d-flex flex-grow-1 overflow-hidden p-2">
        
        <!-- 🔹 Левая панель: инструменты -->
        <div class="d-flex flex-column border-end pe-2 me-2" style="width: 220px; min-width: 220px;">
          <div class="fw-bold mb-2 small text-muted text-uppercase">{{ leftPanelTitle }}</div>
          <div class="list-group list-group-flush overflow-auto" style="max-height: calc(100vh - 180px);">
            <button
              v-for="item in currentItems"
              :key="item.id"
              type="button"
              class="list-group-item list-group-item-action d-flex align-items-center gap-2 small"
              :class="{ active: selectedTool === item.id }"
              @click="selectedTool = selectedTool === item.id ? null : item.id"
            >
              <span
                class="rounded-circle me-1"
                :style="{ backgroundColor: item.color, width: '12px', height: '12px', display: 'inline-block' }"
              ></span>
              {{ item.label }}
            </button>
          </div>
        </div>

        <!-- 🔹 Центр: canvas -->
        <div class="flex-grow-1 d-flex flex-column align-items-center position-relative overflow-hidden">
          <div
            class="position-relative border bg-white d-flex align-items-center justify-content-center"
            style="width: 100%; height: 100%;"
            @wheel.prevent="onWheel"
          >
            <canvas
              ref="canvasRef"
              class="d-block"
              @mousedown="onMouseDown"
              @mousemove="onMouseMove"
              @mouseup="onMouseUp"
              @mouseleave="onMouseLeave"
              @dblclick="onDoubleClick"
              :style="{ cursor: cursorStyle }"
            ></canvas>

            <!-- Upload placeholder -->
            <div
              v-if="!imageLoaded"
              class="position-absolute d-flex flex-column align-items-center justify-content-center text-muted"
              style="top: 0; left: 0; right: 0; bottom: 0; z-index: 10;"
            >
              <svg width="48" height="48" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24" class="mb-2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" />
              </svg>
              <p class="mb-2">Загрузите изображение плана</p>
              <button class="btn btn-primary btn-sm" @click="triggerFileInput">
                Выбрать файл
              </button>
              <input
                ref="fileInput"
                type="file"
                accept="image/*"
                class="d-none"
                @change="onFileChange"
              />
            </div>

            <!-- Zoom controls -->
            <div v-if="imageLoaded" class="position-absolute top-0 start-0 m-2 btn-group btn-group-sm">
              <button class="btn btn-outline-secondary" @click="zoomIn">+</button>
              <button class="btn btn-outline-secondary" @click="zoomOut">-</button>
              <button class="btn btn-outline-secondary" @click="resetZoom">1:1</button>
            </div>

            <!-- 🔹 Индикатор загруженного плана -->
            <div 
              v-if="imageLoaded && selectedFloorplanId" 
              class="position-absolute top-0 end-0 m-2 badge bg-info text-dark"
            >
              План #{{ selectedFloorplanId }}
            </div>
          </div>
        </div>

        <!-- 🔹 Правая панель: информация об объекте -->
        <div class="d-flex flex-column border-start ps-2 ms-2" style="width: 240px; min-width: 240px;">
          <div class="fw-bold mb-2 small text-muted text-uppercase">Информация об объекте</div>
          <div v-if="selectedObject" class="small">
            <div class="mb-2">
              <strong>Тип:</strong> {{ selectedObject.label }}
            </div>
            <div class="mb-2">
              <strong>BBox:</strong> [{{ Math.round(selectedObject.x) }}, {{ Math.round(selectedObject.y) }}, {{ Math.round(selectedObject.width) }}, {{ Math.round(selectedObject.height) }}]
            </div>

            <template v-if="selectedObject.mode === 'rooms'">
              <div class="mb-2">
                <strong>Категория:</strong> Комната
              </div>
              <div class="mb-2">
                <label class="form-label">Площадь (м²)</label>
                <input
                  v-model.number="selectedObject.realArea"
                  type="number"
                  min="0"
                  step="0.01"
                  class="form-control form-control-sm"
                  placeholder="Введите площадь комнаты"
                />
              </div>
            </template>

            <template v-if="selectedObject.mode === 'walls'">
              <div class="mb-2">
                <strong>Категория:</strong> Конструкторский элемент
              </div>
            </template>

            <template v-if="selectedObject.mode === 'furniture'">
              <div class="mb-2">
                <strong>Категория:</strong> Мебель
              </div>
              <div class="mb-2">
                <strong>Комната:</strong>
                <span v-if="furnitureRoomMap[selectedObject.id]">{{ furnitureRoomMap[selectedObject.id] }}</span>
                <span v-else class="text-muted">Не определено</span>
              </div>
            </template>

            <button class="btn btn-sm btn-danger mt-2 w-100" @click="deleteSelectedObject">
              Удалить объект
            </button>
          </div>
          <div v-else class="text-muted small">
            Выберите объект двойным кликом для просмотра информации.
          </div>
        </div>

        <!-- 🔹 Боковая панель: список планов (выезжает справа) -->
        <transition name="slide-fade">
          <div 
            v-if="showFloorplansPanel" 
            class="position-absolute top-0 end-0 h-100 bg-white border-start shadow"
            style="width: 320px; z-index: 1050;"
          >
            <div class="d-flex align-items-center justify-content-between p-2 border-bottom bg-light">
              <strong class="small text-uppercase text-muted">Список планов</strong>
              <button class="btn btn-sm btn-outline-secondary" @click="toggleFloorplansPanel">✕</button>
            </div>
            
            <div class="p-2 overflow-auto" style="height: calc(100% - 45px);">
              <!-- Загрузка -->
              <div v-if="isFloorplansLoading" class="text-center text-muted py-4">
                <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                Загрузка...
              </div>
              
              <!-- Пусто -->
              <div v-else-if="!floorplans.length" class="text-center text-muted py-4 small">
                Нет сохранённых планов
              </div>
              
              <!-- Список -->
              <div v-else v-for="fp in floorplans" :key="fp.id" class="card mb-2">
                <!-- Превью изображения -->
                <div class="position-relative" style="height: 120px; background: #f8f9fa;">
                  <img 
                    v-if="fp.img" 
                    :src="fp.img" 
                    class="w-100 h-100"
                    style="object-fit: cover;"
                    @error="onImageError($event)"
                    alt="План"
                  >
                  <div v-else class="w-100 h-100 d-flex align-items-center justify-content-center text-muted small">
                    Нет изображения
                  </div>
                  <!-- Индикатор текущего плана -->
                  <span 
                    v-if="selectedFloorplanId === fp.id" 
                    class="position-absolute top-1 end-1 badge bg-success"
                  >
                    Открыт
                  </span>
                </div>
                
                <div class="card-body p-2">
                  <div class="d-flex justify-content-between small text-muted mb-1">
                    <span>ID: {{ fp.id }}</span>
                    <span>{{ formatDate(fp.upload_at) }}</span>
                  </div>
                  <div class="small mb-2">
                    <strong>{{ Math.round(fp.width) }}×{{ Math.round(fp.height) }} px</strong>
                    <span v-if="fp.square_of_habitation" class="text-muted ms-1">
                      • {{ fp.square_of_habitation }} м²
                    </span>
                  </div>
                  <div class="d-flex gap-1">
                    <button 
                      class="btn btn-sm btn-primary flex-grow-1"
                      :disabled="selectedFloorplanId === fp.id"
                      @click="loadFloorplan(fp.id)"
                    >
                      {{ selectedFloorplanId === fp.id ? 'Открыт' : 'Открыть' }}
                    </button>
                    <button 
                      class="btn btn-sm btn-outline-danger"
                      :disabled="selectedFloorplanId === fp.id"
                      @click="deleteFloorplan(fp.id)"
                      title="Удалить план"
                    > x</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </transition>

      </div>

      <!-- 🔹 Footer: кнопки сохранения -->
      <div class="card-footer d-flex justify-content-between py-2 align-items-center">
  
  <!-- Левая часть: настройки площади -->
  <div class="d-flex flex-column gap-1" style="min-width: 200px;">
    <div class="input-group input-group-sm">
      <span class="input-group-text">Площадь, м²</span>
      <input
        v-model.number="userSquareInput"
        type="number"
        min="0"
        step="0.01"
        class="form-control"
        placeholder="Введите общую площадь"
        @input="recalculatePixelScale"
      >
    </div>
    
    <!-- Авто-расчёт -->
    <div class="small text-muted d-flex align-items-center gap-2">
      <span>📐 Масштаб:</span>
      <span class="fw-bold" :class="{'text-success': pixelToMSquare > 0}">
        {{ formatPixelScale }}
      </span>
      <span v-if="imgWidth && imgHeight" class="text-muted small">
        ({{ Math.round(imgWidth) }}×{{ Math.round(imgHeight) }} px)
      </span>
    </div>
  </div>
  

  
  <!-- Правая часть: сохранение -->
  <button
    class="btn btn-success"
    :disabled="!imageLoaded"
    @click="saveResults"
  >
    {{ selectedFloorplanId ? 'Сохранить изменения' : 'Сохранить как новый' }}
  </button> 
  
  <button
  class="btn btn-outline-success"
  :disabled="!selectedFloorplanId"
  @click="goToQuestionnaire"
>
  {{ !selectedFloorplanId ? 'Сначала сохраните или выберите  план' : 'Перейти к заполнению анкеты' }}
</button>

</div>
      
    </div>
  </div>
</template>

<script setup>
//#region Импорты
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { apiClient } from '../../../../core/client/src/js/api/manager'
import { roomAnalyticsEndpoints } from '../js/endpoints'
import { useRouter } from 'vue-router'
//#endregion

const router = useRouter()

//#region refs
const floorplans = ref([])
const selectedFloorplanId = ref(null)
const isFloorplansLoading = ref(false)
const showFloorplansPanel = ref(false)

function toggleFloorplansPanel() {
  showFloorplansPanel.value = !showFloorplansPanel.value
  if (showFloorplansPanel.value) {
    loadFloorplansList()
  }
}

const roomTypes = ref([])
const wallTypes = ref([])
const furnitureTypes = ref([])
const originalFile = ref(null)

const mode = ref('rooms')
const displayMode = ref('rooms')

const selectedTool = ref(null)
const imageLoaded = ref(false)
const canvasRef = ref(null)
const fileInput = ref(null)

const scale = ref(1)
const offsetX = ref(0)
const offsetY = ref(0)

let img = null
let imgWidth = 0
let imgHeight = 0
//#endregion

//#region reactive
const roomAnnotations = reactive([])
const wallAnnotations = reactive([])
const furnitureAnnotations = reactive([])
let nextId = 1

const selectedObject = ref(null)

const drawStart = reactive({ x: 0, y: 0 })
const drawCurrent = reactive({ x: 0, y: 0 })

const interaction = reactive({
  type: 'idle',
  handle: null,
  startMouse: { x: 0, y: 0 },
  startClientMouse: { x: 0, y: 0 },
  startObj: { x: 0, y: 0, w: 0, h: 0 },
  startOffset: { x: 0, y: 0 }
})

const selectionCycle = reactive({ key: '', index: -1 })
//#endregion

//#region computed
const currentItems = computed(() => {
  if (mode.value === 'rooms') return roomTypes.value
  if (mode.value === 'walls') return wallTypes.value
  if (mode.value === 'furniture') return furnitureTypes.value
  return []
})

const leftPanelTitle = computed(() => {
  if (mode.value === 'rooms') return 'Комнаты'
  if (mode.value === 'walls') return 'Конструкторские элементы'
  if (mode.value === 'furniture') return 'Мебель'
  return ''
})

const allAnnotations = computed(() => [
  ...roomAnnotations,
  ...wallAnnotations,
  ...furnitureAnnotations
])

const visibleAnnotations = computed(() => {
  if (displayMode.value === 'all') return allAnnotations.value
  if (displayMode.value === 'rooms') return roomAnnotations
  if (displayMode.value === 'walls') return wallAnnotations
  if (displayMode.value === 'furniture') return furnitureAnnotations
  return []
})

// 🔹 Маппинг furniture_id -> room_id (по позиции центра мебели)
const furnitureRoomIdMap = computed(() => {
  const map = {}
  for (const furn of furnitureAnnotations) {
    const cx = furn.x + furn.width / 2
    const cy = furn.y + furn.height / 2
    let foundRoomId = null
    for (const room of roomAnnotations) {
      if (cx >= room.x && cx <= room.x + room.width &&
          cy >= room.y && cy <= room.y + room.height) {
        foundRoomId = room.id
        break
      }
    }
    map[furn.id] = foundRoomId
  }
  return map
})

// 🔹 Маппинг furniture_id -> label комнаты (для UI)
const furnitureRoomMap = computed(() => {
  const map = {}
  for (const furn of furnitureAnnotations) {
    const cx = furn.x + furn.width / 2
    const cy = furn.y + furn.height / 2
    let foundRoomLabel = null
    for (const room of roomAnnotations) {
      if (cx >= room.x && cx <= room.x + room.width &&
          cy >= room.y && cy <= room.y + room.height) {
        foundRoomLabel = room.label
        break
      }
    }
    map[furn.id] = foundRoomLabel
  }
  return map
})

const cursorStyle = computed(() => {
  if (interaction.type === 'draw') return 'crosshair'
  if (interaction.type === 'pan') return 'grab'
  if (interaction.type === 'move') return 'move'
  if (interaction.type === 'resize') {
    if (interaction.handle === 'tl' || interaction.handle === 'br') return 'nwse-resize'
    if (interaction.handle === 'tr' || interaction.handle === 'bl') return 'nesw-resize'
    return 'col-resize'
  }
  if (selectedTool.value) return 'crosshair'
  if (selectedObject.value) return 'default'
  return 'grab'
})
//#endregion

//#region ОБЩАЯ ФУНКЦИЯ СЕРИАЛИЗАЦИИ (на верхнем уровне!)
function serializeAnnotation(a) {
  const result = {
    id: a.id,
    mode: a.mode,
    type: a.type,
    label: a.label,
    bbox: [
      Math.round(a.x),
      Math.round(a.x + a.width),
      Math.round(a.y),
      Math.round(a.y + a.height)
    ],
  }

  // Для мебели — room_id по позиции центра
  if (a.mode === 'furniture') {
    result.room_id = furnitureRoomIdMap.value[a.id] || null
  }

  // Для комнат — площадь
  if (a.mode === 'rooms') {
    result.realArea = a.realArea || 0
  }

  return result
}
//#endregion

//#region Рисование
function getCanvasCoords(clientX, clientY) {
  const rect = canvasRef.value.getBoundingClientRect()
  return {
    x: (clientX - rect.left - offsetX.value) / scale.value,
    y: (clientY - rect.top - offsetY.value) / scale.value
  }
}

function draw() {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  canvas.width = canvas.parentElement.clientWidth
  canvas.height = canvas.parentElement.clientHeight
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  if (img && imageLoaded.value && img.complete && img.naturalWidth !== 0) {
    ctx.save()
    ctx.translate(offsetX.value, offsetY.value)
    ctx.scale(scale.value, scale.value)
    ctx.drawImage(img, 0, 0, imgWidth, imgHeight)

    for (const ann of visibleAnnotations.value) {
      ctx.strokeStyle = ann.color
      ctx.lineWidth = 2 / scale.value
      ctx.strokeRect(ann.x, ann.y, ann.width, ann.height)
      ctx.fillStyle = ann.color + '33'
      ctx.fillRect(ann.x, ann.y, ann.width, ann.height)
      ctx.fillStyle = ann.color
      ctx.font = `${12 / scale.value}px sans-serif`
      ctx.fillText(ann.label, ann.x + 4 / scale.value, ann.y + 14 / scale.value)
    }

    if (interaction.type === 'draw' && selectedTool.value) {
      const tool = currentItems.value.find(i => i.id === selectedTool.value)
      if (tool) {
        const x = Math.min(drawStart.x, drawCurrent.x)
        const y = Math.min(drawStart.y, drawCurrent.y)
        const w = Math.abs(drawCurrent.x - drawStart.x)
        const h = Math.abs(drawCurrent.y - drawStart.y)
        ctx.strokeStyle = tool.color
        ctx.lineWidth = 2 / scale.value
        ctx.strokeRect(x, y, w, h)
        ctx.fillStyle = tool.color + '33'
        ctx.fillRect(x, y, w, h)
      }
    }

    if (selectedObject.value) {
      const obj = selectedObject.value
      const hs = 8 / scale.value
      const half = hs / 2
      const handles = [
        { id: 'tl', x: obj.x - half, y: obj.y - half },
        { id: 'tr', x: obj.x + obj.width - half, y: obj.y - half },
        { id: 'bl', x: obj.x - half, y: obj.y + obj.height - half },
        { id: 'br', x: obj.x + obj.width - half, y: obj.y + obj.height - half }
      ]
      ctx.fillStyle = '#ffffff'
      ctx.strokeStyle = '#000000'
      ctx.lineWidth = 1.5 / scale.value
      for (const h of handles) {
        ctx.fillRect(h.x, h.y, hs, hs)
        ctx.strokeRect(h.x, h.y, hs, hs)
      }
    }
    ctx.restore()
  }
}

function centerImage() {
  if (!img || !canvasRef.value) return
  const canvas = canvasRef.value
  const parentRect = canvas.parentElement.getBoundingClientRect()
  const scaleX = parentRect.width / imgWidth
  const scaleY = parentRect.height / imgHeight
  scale.value = Math.min(scaleX, scaleY) * 0.95
  offsetX.value = (parentRect.width - imgWidth * scale.value) / 2
  offsetY.value = (parentRect.height - imgHeight * scale.value) / 2
}
//#endregion

//#region Вспомогательные
function isInside(cx, cy, obj) {
  return cx >= obj.x && cx <= obj.x + obj.width && cy >= obj.y && cy <= obj.y + obj.height
}

function getHandleAt(cx, cy, obj) {
  const hs = 12 / scale.value
  const half = hs / 2
  const handles = [
    { id: 'tl', x: obj.x, y: obj.y },
    { id: 'tr', x: obj.x + obj.width, y: obj.y },
    { id: 'bl', x: obj.x, y: obj.y + obj.height },
    { id: 'br', x: obj.x + obj.width, y: obj.y + obj.height }
  ]
  for (const h of handles) {
    if (cx >= h.x - half && cx <= h.x + half && cy >= h.y - half && cy <= h.y + half) {
      return h.id
    }
  }
  return null
}

function getAnnotationsForMode(modeName) {
  if (modeName === 'rooms') return roomAnnotations
  if (modeName === 'walls') return wallAnnotations
  if (modeName === 'furniture') return furnitureAnnotations
  return null
}

function endInteraction({ commitDraw }) {
  if (interaction.type === 'draw' && selectedTool.value) {
    if (commitDraw) {
      const x = Math.min(drawStart.x, drawCurrent.x)
      const y = Math.min(drawStart.y, drawCurrent.y)
      const w = Math.abs(drawCurrent.x - drawStart.x)
      const h = Math.abs(drawCurrent.y - drawStart.y)
      if (w > 5 && h > 5) {
        const tool = currentItems.value.find(i => i.id === selectedTool.value)
        if (tool) {
          const targetAnnotations = getAnnotationsForMode(mode.value)
          if (!targetAnnotations) return
          targetAnnotations.push({
            id: nextId++,
            mode: mode.value,
            type: tool.id,
            label: tool.label,
            color: tool.color,
            x, y, width: w, height: h,
            adjacentRoom1: null,
            adjacentRoom2: null,
            realArea: null,
          })
        }
      }
    }
  }
  interaction.type = 'idle'
  interaction.handle = null
  draw()
}

function deleteSelectedObject() {
  if (!selectedObject.value) return
  const targetAnnotations = getAnnotationsForMode(selectedObject.value.mode)
  if (targetAnnotations) {
    const idx = targetAnnotations.findIndex(a => a.id === selectedObject.value.id)
    if (idx !== -1) targetAnnotations.splice(idx, 1)
  }
  selectedObject.value = null
  draw()
}

function setMode(m) {
  mode.value = m
  displayMode.value = m
  selectedTool.value = null
  selectedObject.value = null
  selectionCycle.key = ''
  selectionCycle.index = -1
}

watch([mode, displayMode, selectedTool], () => {
  if (selectedObject.value && displayMode.value !== 'all' && selectedObject.value.mode !== displayMode.value) {
    selectedObject.value = null
  }
  draw()
})
watch(scale, () => draw())
watch(offsetX, () => draw())
watch(offsetY, () => draw())

function onWindowResize() {
  if (imageLoaded.value) draw()
}
//#endregion

//#region Масштабирование
function onWheel(e) {
  if (!imageLoaded.value) return
  const delta = e.deltaY > 0 ? 0.9 : 1.1
  const newScale = Math.max(0.1, Math.min(10, scale.value * delta))
  const rect = canvasRef.value.getBoundingClientRect()
  const mouseX = e.clientX - rect.left
  const mouseY = e.clientY - rect.top
  offsetX.value = mouseX - (mouseX - offsetX.value) * (newScale / scale.value)
  offsetY.value = mouseY - (mouseY - offsetY.value) * (newScale / scale.value)
  scale.value = newScale
}

function zoomIn() { scale.value = Math.min(10, scale.value * 1.2) }
function zoomOut() { scale.value = Math.max(0.1, scale.value / 1.2) }
function resetZoom() { centerImage() }
//#endregion

//#region Управление запросами

async function loadFloorplansList() {
  isFloorplansLoading.value = true
  try {
    const response = await apiClient.get(roomAnalyticsEndpoints.roomAnalytics.FloorplanList)
    floorplans.value = response.data.results || []
  } catch (error) {
    console.error('❌ Ошибка загрузки списка планов:', error)
    alert('Не удалось загрузить список планов')
  } finally {
    isFloorplansLoading.value = false
  }
}

async function loadFloorplan(id) {
  try {
    const response = await apiClient.get(roomAnalyticsEndpoints.roomAnalytics.FloorplanDetail(id))
    const fp = response.data

    imageLoaded.value = false

    if (fp.img) {
      img = new Image()
      img.onload = () => {
        imgWidth = img.width
        imgHeight = img.height
        imageLoaded.value = true

        if (fp.square_of_habitation > 0) {
          userSquareInput.value = fp.square_of_habitation
        } else {
          userSquareInput.value = null
        }

        nextTick(() => {
          centerImage()
          draw()
        })
      }
      img.onerror = () => {
        imageLoaded.value = false
        img = null
        alert('Не удалось загрузить изображение плана')
      }
      img.src = fp.img
    } else {
      imageLoaded.value = false
    }

    const toAnnotation = (item, annMode) => ({
      id: item.id,
      mode: annMode,
      type: item.type,
      label: item.label,
      color: item.color,
      x: item.bbox[0],
      y: item.bbox[2],
      width: item.bbox[1] - item.bbox[0],
      height: item.bbox[3] - item.bbox[2],
      square: item.square || 0,
      realArea: item.square || item.realArea || null,
      room: item.room || null,
      room_id: item.room_id || null,
    })

    roomAnnotations.splice(0, roomAnnotations.length)
    wallAnnotations.splice(0, wallAnnotations.length)
    furnitureAnnotations.splice(0, furnitureAnnotations.length)

    for (const r of fp.rooms || []) {
      roomAnnotations.push(toAnnotation(r, 'rooms'))
    }
    for (const w of fp.walls || []) {
      wallAnnotations.push(toAnnotation(w, 'walls'))
    }
    for (const f of fp.furniture || []) {
      furnitureAnnotations.push(toAnnotation(f, 'furniture'))
    }

    const maxId = Math.max(
      ...roomAnnotations.map(a => a.id),
      ...wallAnnotations.map(a => a.id),
      ...furnitureAnnotations.map(a => a.id),
      0
    )
    nextId = maxId + 1
    selectedFloorplanId.value = id

  } catch (error) {
    console.error('❌ Ошибка загрузки плана:', error)
    alert('Не удалось загрузить план: ' + (error.response?.data?.error || error.message))
  }
}

async function updateFloorplan(id) {
  if (!originalFile.value && !selectedFloorplanId.value) {
    alert('Нет данных для обновления')
    return
  }

  try {
    const formData = new FormData()

    if (originalFile.value) {
      formData.append('image', originalFile.value)
    }

    formData.append('width', imgWidth?.toString() || '0')
    formData.append('height', imgHeight?.toString() || '0')

    const annotationsData = {
      rooms: roomAnnotations.map(serializeAnnotation),
      walls: wallAnnotations.map(serializeAnnotation),
      furniture: furnitureAnnotations.map(serializeAnnotation),
    }
    formData.append('data', JSON.stringify(annotationsData))

    const response = await apiClient.put(
      roomAnalyticsEndpoints.roomAnalytics.FloorplanDetail(id),
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )

    alert('✅ План обновлён')
    return response.data
  } catch (error) {
    console.error('❌ Ошибка обновления:', error)
    alert('Ошибка: ' + (error.response?.data?.error || error.message))
    throw error
  }
}

async function deleteFloorplan(id) {
  if (!confirm('Вы уверены, что хотите удалить этот план?')) return

  try {
    await apiClient.delete(roomAnalyticsEndpoints.roomAnalytics.FloorplanDetail(id))

    if (selectedFloorplanId.value === id) {
      imageLoaded.value = false
      img = null
      roomAnnotations.splice(0, roomAnnotations.length)
      wallAnnotations.splice(0, wallAnnotations.length)
      furnitureAnnotations.splice(0, furnitureAnnotations.length)
      selectedFloorplanId.value = null
      originalFile.value = null
      draw()
    }

    await loadFloorplansList()
    alert('План удалён')
  } catch (error) {
    console.error('❌ Ошибка удаления:', error)
    alert('Не удалось удалить: ' + (error.response?.data?.error || error.message))
  }
}

async function saveResults() {
  if (!originalFile.value && !selectedFloorplanId.value) {
    alert('Файл не выбран и план не загружен!')
    return
  }

  try {
    const formData = new FormData()
    const url = selectedFloorplanId.value
      ? roomAnalyticsEndpoints.roomAnalytics.FloorplanDetail(selectedFloorplanId.value)
      : roomAnalyticsEndpoints.roomAnalytics.FloorplanSave

    const method = selectedFloorplanId.value ? 'put' : 'post'

    if (originalFile.value) {
      formData.append('image', originalFile.value)
    }

    const annotationsData = {
      rooms: roomAnnotations.map(serializeAnnotation),
      walls: wallAnnotations.map(serializeAnnotation),
      furniture: furnitureAnnotations.map(serializeAnnotation),
    }

    formData.append('name', `floorplan_${Date.now()}`)
    formData.append('width', imgWidth?.toString() || '0')
    formData.append('height', imgHeight?.toString() || '0')
    formData.append('pixel_to_m_in_square', pixelToMSquare.value)
    formData.append('square_of_habitation', userSquareInput.value)
    formData.append('data', JSON.stringify(annotationsData))

    const response = await apiClient[method](
      url,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )

    console.log('✅ Успешно сохранено:', response.data)
    alert(`План сохранён!\nID: ${response.data.floorplan_id || selectedFloorplanId.value}`)

    if (!selectedFloorplanId.value) {
      await loadFloorplansList()
      selectedFloorplanId.value = response.data.floorplan_id
    }
  } catch (error) {
    console.error('❌ Ошибка сохранения:', error)
    alert('Ошибка: ' + (error.response?.data?.error || error.message))
  }
}
//#endregion

//#region Ввод/вывод данных
const userSquareInput = ref(null)

const pixelToMSquare = computed(() => {
  const totalPixels = (imgWidth || 0) * (imgHeight || 0)
  const totalSquare = userSquareInput.value || 0
  if (totalPixels > 0 && totalSquare > 0) {
    return totalSquare / totalPixels
  }
  return 0
})

const formatPixelScale = computed(() => {
  const val = pixelToMSquare.value
  if (val <= 0) return '—'
  return `${val.toFixed(5)} м²/px`
})

function formatDate(isoString) {
  if (!isoString) return ''
  const d = new Date(isoString)
  return d.toLocaleDateString('ru-RU', {
    day: '2-digit', month: '2-digit', year: '2-digit',
    hour: '2-digit', minute: '2-digit'
  })
}
//#endregion

//#region Очистка редактора
function clearEditor() {
  const hasAnnotations = roomAnnotations.length > 0 ||
                         wallAnnotations.length > 0 ||
                         furnitureAnnotations.length > 0
  const hasImage = imageLoaded.value
  const hasFloorplan = selectedFloorplanId.value !== null
  const hasUnsavedChanges = hasAnnotations || originalFile.value !== null

  let confirmMessage = 'Это действие полностью очистит редактор:\n\n'
  const actions = []

  if (hasImage) actions.push('• Удалит изображение плана')
  if (hasAnnotations) actions.push('• Удалит все аннотации')
  if (hasFloorplan) actions.push('• Отвяжет текущий план #' + selectedFloorplanId.value)
  if (originalFile.value) actions.push('• Сбросит загруженный файл')

  if (actions.length === 0) {
    alert('Редактор уже пуст')
    return
  }

  confirmMessage += actions.join('\n') + '\n\nПродолжить?'
  if (!confirm(confirmMessage)) return

  roomAnnotations.splice(0, roomAnnotations.length)
  wallAnnotations.splice(0, wallAnnotations.length)
  furnitureAnnotations.splice(0, furnitureAnnotations.length)
  img = null
  imgWidth = 0
  imgHeight = 0
  imageLoaded.value = false
  originalFile.value = null
  if (fileInput.value) fileInput.value.value = ''
  selectedObject.value = null
  selectedTool.value = null
  selectionCycle.key = ''
  selectionCycle.index = -1
  nextId = 1
  scale.value = 1
  offsetX.value = 0
  offsetY.value = 0
  userSquareInput.value = null
  selectedFloorplanId.value = null
  draw()
}

function goToQuestionnaire() {
  if (!selectedFloorplanId.value) {
    alert('Сначала сохраните план в базу данных')
    return
  }
  router.push({
    name: 'QuestionnaireView',
    query: { floorplanId: selectedFloorplanId.value }
  })
}
//#endregion

//#region Обработка ошибок
function onImageError(e) {
  e.target.src = 'data:image/svg+xml,' + encodeURIComponent(`
    <svg xmlns="http://www.w3.org/2000/svg" width="160" height="90">
      <rect width="100%" height="100%" fill="#e9ecef"/>
      <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle"
            fill="#6c757d" font-family="sans-serif" font-size="12">Нет изображения</text>
    </svg>
  `)
}
//#endregion

//#region События мыши
function onMouseDown(e) {
  if (!imageLoaded.value) return
  const coords = getCanvasCoords(e.clientX, e.clientY)
  interaction.startMouse = { x: coords.x, y: coords.y }
  interaction.startClientMouse = { x: e.clientX, y: e.clientY }

  if (selectedTool.value) {
    interaction.type = 'draw'
    drawStart.x = coords.x
    drawStart.y = coords.y
    drawCurrent.x = coords.x
    drawCurrent.y = coords.y
    return
  }

  if (selectedObject.value) {
    const handle = getHandleAt(coords.x, coords.y, selectedObject.value)
    if (handle) {
      interaction.type = 'resize'
      interaction.handle = handle
      interaction.startObj = { x: selectedObject.value.x, y: selectedObject.value.y, w: selectedObject.value.width, h: selectedObject.value.height }
      return
    }
    if (isInside(coords.x, coords.y, selectedObject.value)) {
      interaction.type = 'move'
      interaction.startObj = { x: selectedObject.value.x, y: selectedObject.value.y }
      return
    }
    selectedObject.value = null
  }

  interaction.type = 'pan'
  interaction.startOffset = { x: offsetX.value, y: offsetY.value }
}

function onMouseMove(e) {
  if (!imageLoaded.value || interaction.type === 'idle') return
  const coords = getCanvasCoords(e.clientX, e.clientY)

  if (interaction.type === 'draw') {
    drawCurrent.x = coords.x
    drawCurrent.y = coords.y
  } else if (interaction.type === 'pan') {
    offsetX.value = interaction.startOffset.x + (e.clientX - interaction.startClientMouse.x)
    offsetY.value = interaction.startOffset.y + (e.clientY - interaction.startClientMouse.y)
  } else if (interaction.type === 'move') {
    const dx = coords.x - interaction.startMouse.x
    const dy = coords.y - interaction.startMouse.y
    selectedObject.value.x = interaction.startObj.x + dx
    selectedObject.value.y = interaction.startObj.y + dy
  } else if (interaction.type === 'resize') {
    const dx = coords.x - interaction.startMouse.x
    const dy = coords.y - interaction.startMouse.y
    const obj = selectedObject.value
    let { x, y, w, h } = interaction.startObj
    if (interaction.handle.includes('r')) w += dx
    if (interaction.handle.includes('l')) { x += dx; w -= dx }
    if (interaction.handle.includes('b')) h += dy
    if (interaction.handle.includes('t')) { y += dy; h -= dy }
    if (w < 5) { w = 5; if (interaction.handle.includes('l')) x = interaction.startObj.x + interaction.startObj.w - 5 }
    if (h < 5) { h = 5; if (interaction.handle.includes('t')) y = interaction.startObj.y + interaction.startObj.h - 5 }
    obj.x = x; obj.y = y; obj.width = w; obj.height = h
  }
  draw()
}

function onMouseUp() { endInteraction({ commitDraw: true }) }
function onMouseLeave() { endInteraction({ commitDraw: false }) }

function onDoubleClick(e) {
  if (!imageLoaded.value) return
  const coords = getCanvasCoords(e.clientX, e.clientY)
  const hits = visibleAnnotations.value
    .filter(ann => isInside(coords.x, coords.y, ann))
    .sort((a, b) => b.id - a.id)
  if (hits.length > 0) {
    const cycleKey = hits.map(h => h.id).join('|')
    let nextIdx = 0
    if (selectionCycle.key === cycleKey && selectionCycle.index >= 0) {
      nextIdx = (selectionCycle.index + 1) % hits.length
    }
    selectedObject.value = hits[nextIdx]
    selectionCycle.key = cycleKey
    selectionCycle.index = nextIdx
    selectedTool.value = null
  } else {
    selectedObject.value = null
    selectionCycle.key = ''
    selectionCycle.index = -1
  }
  draw()
}

function onWindowKeydown(e) {
  if (e.key !== 'Escape') return
  if (interaction.type === 'draw') endInteraction({ commitDraw: false })
  if (selectedTool.value) selectedTool.value = null
  if (interaction.type === 'resize') interaction.type = 'idle'
  if (selectedObject.value) selectedObject.value = null
  draw()
}
//#endregion

//#region File handling
function triggerFileInput() { fileInput.value.click() }

function onFileChange(e) {
  const file = e.target.files[0]
  if (!file) return
  originalFile.value = file
  userSquareInput.value = null
  const reader = new FileReader()
  reader.onload = (ev) => {
    img = new Image()
    img.onload = () => {
      imgWidth = img.width
      imgHeight = img.height
      imageLoaded.value = true
      nextTick(() => { centerImage(); draw() })
    }
    img.src = ev.target.result
  }
  reader.readAsDataURL(file)
}
//#endregion

//#region ONNX
function runONNXDetection() {
  alert('Функция детекции объектов через ONNX будет доступна после подключения модели.')
}
//#endregion

//#region Жизненный цикл
onMounted(async () => {
  nextTick(() => draw())

  try {
    const [roomsRes, wallsRes, furnitureRes] = await Promise.allSettled([
      apiClient.get(roomAnalyticsEndpoints.roomAnalytics.RoomTypesList),
      apiClient.get(roomAnalyticsEndpoints.roomAnalytics.ConstrucElementTypesList),
      apiClient.get(roomAnalyticsEndpoints.roomAnalytics.FurnitureTypesList),
    ])

    const extractData = (result) => {
      if (result.status !== 'fulfilled') return []
      const data = result.value?.data || result.value
      if (!Array.isArray(data)) return []
      return data
    }

    roomTypes.value = extractData(roomsRes).map(rt => ({
      id: rt.id, label: rt.label, color: rt.color || '#0d6efd'
    }))
    wallTypes.value = extractData(wallsRes).map(wt => ({
      id: wt.id, label: wt.label, color: wt.color
    }))
    furnitureTypes.value = extractData(furnitureRes).map(ft => ({
      id: ft.id, label: ft.label, color: ft.color
    }))
  } catch (error) {
    console.error('❌ Failed to load types:', error)
  }

  window.addEventListener('resize', onWindowResize)
  window.addEventListener('mouseup', onMouseUp)
  window.addEventListener('keydown', onWindowKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onWindowResize)
  window.removeEventListener('mouseup', onMouseUp)
  window.removeEventListener('keydown', onWindowKeydown)
})
//#endregion

</script>

<style scoped>
/* Анимация выезжания панели */
.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: transform 0.25s ease;
}
.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateX(100%);
}

/* Чтобы контент под панелью не дёргался */
.position-relative {
  will-change: transform;
}
</style>