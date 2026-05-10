<template>
  <div class="container py-4">
    <h2 class="mb-4 text-center">🎯 YOLO Object Detection</h2>
    
    <div class="row g-4">
      <!-- Левая колонка: Управление -->
      <div class="col-lg-5">
        <!-- Загрузка модели -->

        <!-- Загрузка изображения -->
        <div class="card mb-3">
          <div class="card-header bg-primary text-white">Изображение</div>
          <div class="card-body">
            <div class="drop-zone" @click="$refs.imageInput.click()" @dragover.prevent @drop="onImageDrop">
              {{ imageFile ? `${imageFile.name}` : 'Перетащите фото' }}
              <input type="file" ref="imageInput" accept="image/*" hidden @change="onImageChange">
            </div>
            <img v-if="imageUrl" :src="imageUrl" class="img-fluid mt-2 rounded" style="max-height: 180px; object-fit: contain;">
          </div>
        </div>

        <!-- Настройки -->
        <div class="card">
          <div class="card-body">
            <div class="row g-2 mb-3 align-items-center">
              <div class="col-6">
                <label class="form-label mb-0 small">Confidence</label>
                <input type="range" class="form-range" v-model.number="confThreshold" min="0.1" max="0.9" step="0.05">
              </div>
              <div class="col-6">
                <label class="form-label mb-0 small">IoU Threshold</label>
                <input type="range" class="form-range" v-model.number="iouThreshold" min="0.1" max="0.9" step="0.05">
              </div>
            </div>
            <button class="btn btn-success w-100" :disabled="!session || !imageUrl || isProcessing" @click="runDetection">
              <span v-if="isProcessing" class="spinner-border spinner-border-sm me-2"></span>
              {{ isProcessing ? 'Обработка...' : '🚀 Запустить' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Правая колонка: Результат -->
      <div class="col-lg-7">
        <div class="card">
          <div class="card-header bg-info text-white">📊 Результат</div>
          <div class="card-body d-flex align-items-center justify-content-center bg-light" style="min-height: 450px;">
            <canvas ref="canvasRef" class="img-fluid rounded shadow-sm" style="max-width: 100%; max-height: 450px;"></canvas>
            <p v-if="!imageUrl" class="text-muted position-absolute">Ожидание изображения...</p>
          </div>
        </div>
        
        <!-- Теги результатов -->
        <div class="mt-3" v-if="detections.length">
          <span class="badge bg-secondary me-1 mb-1" 
                v-for="(det, i) in detections" 
                :key="i" 
                :style="{ backgroundColor: COLORS[det.classId % COLORS.length] }">
            {{ det.label }} {{ (det.conf * 100).toFixed(0) }}%
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick,onMounted } from 'vue'
import * as ort from 'onnxruntime-web'
import bestModelUrl from '../models/best.onnx?url'

ort.env.wasm.wasmPaths = 'https://cdn.jsdelivr.net/npm/onnxruntime-web/dist/'

// --- State ---
const isModelLoading = ref(false)
const imageFile = ref(null)
const imageUrl = ref('')
const session = ref(null)
const modelError = ref('')
const isProcessing = ref(false)
const confThreshold = ref(0.25)
const iouThreshold = ref(0.45)
const canvasRef = ref(null)
const detections = ref([])

// --- Constants ---
const CLASS_NAMES = [
    "door",
    "double_door",
    "sliding_door",
    "window",
    "windows",
    "ac",
    "doors", "sofa","bed",
    "armchair",
    "table",
    "tv_stand",
    "wardrobe",
    "nightstand",
    "chair",
    "airconditioner",
    "gas_stove",
    "sink",
    "shower",
    "washing_machine",
    "toilet",
    "stairs",
]
const COLORS = ['#FF3838', '#FF9D97', '#FF701F', '#FFB21D', '#CFD231', '#48F90A', '#92CC17', '#3DDB86', '#1A9334', '#00D4BB', '#2C99A8', '#00C2FF', '#344593', '#6473FF', '#0018EC', '#8438FF', '#520085', '#CB38FF', '#FF95C8', '#FF37C7']


const onImageChange = (e) => loadImage(e.target.files[0])
const onImageDrop = (e) => { e.preventDefault(); loadImage(e.dataTransfer.files[0]) }

const loadModelFromUrl = async (url) => {
  isModelLoading.value = true
  modelError.value = ''
  const EXECUTION_PROVIDER = 'wasm'  
  try {
    console.log(`📥 Загрузка модели: ${url}`)
    const response = await fetch(url)
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    
    const buffer = await response.arrayBuffer()
    console.log(`✅ Модель загружена: ${(buffer.byteLength / 1024 / 1024).toFixed(2)} MB`)
    
    // Создание сессии ONNX Runtime
    session.value = await ort.InferenceSession.create(buffer, {
      executionProviders: [EXECUTION_PROVIDER],
      // Опции для WASM (можно настроить под вашу модель)
      wasm: {
        numThreads: 4,
        simd: true,
      }
    })
    
    console.log('🎯 Модель инициализирована:', session.value.inputNames, session.value.outputNames)
    
  } catch (err) {
    console.error('❌ Ошибка загрузки модели:', err)
    modelError.value = `Не удалось загрузить модель: ${err.message}`
  } finally {
    isModelLoading.value = false
  }
}
onMounted(async()=>{
  await loadModelFromUrl(bestModelUrl)
})

// --- Image Handling ---
const loadImage = (file) => {
  if (!file) return
  // Очистка предыдущего URL для предотвращения утечек памяти
  if (imageUrl.value) URL.revokeObjectURL(imageUrl.value)
  
  imageFile.value = file
  imageUrl.value = URL.createObjectURL(file)
  detections.value = []
  nextTick(() => drawOriginalImage())
}

const drawOriginalImage = () => {
  if (!imageUrl.value || !canvasRef.value) return
  const img = new Image()
  img.onload = () => {
    const canvas = canvasRef.value
    canvas.width = img.width
    canvas.height = img.height
    canvas.getContext('2d').drawImage(img, 0, 0)
  }
  img.src = imageUrl.value
}

const loadImageToElement = (src) => new Promise((resolve, reject) => {
  const img = new Image()
  img.onload = () => resolve(img)
  img.onerror = reject
  img.src = src
})

// --- Core Logic ---
const runDetection = async () => {
  if (!session.value || !imageUrl.value) return
  isProcessing.value = true
  detections.value = []

  try {
    const img = await loadImageToElement(imageUrl.value)
    const INPUT_SIZE = 1024
    
    // 1. Препроцессинг
    const { tensor, meta } = preprocessImage(img, INPUT_SIZE)
    
    // 2. Инференс
    const inputName = session.value.inputNames[0]
    const outputName = session.value.outputNames[0]
    const output = await session.value.run({ [inputName]: tensor })
    console.log('Model IO:', { input: inputName, output: outputName, outputDims: output[outputName]?.dims })
    
    // 3. Постпроцессинг (убраны лишние аргументы img.width/height)
    const outputTensor = output[outputName]
    const processed = postprocess(outputTensor, meta)
    
    detections.value = processed
    drawDetections(img, processed)
  } catch (err) {
    console.error('Inference error:', err)
    alert('Ошибка: ' + err.message)
  } finally {
    isProcessing.value = false
  }
}

// --- Preprocessing (Letterbox) ---
const preprocessImage = (img, size) => {
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')
  canvas.width = canvas.height = size

  // Расчет масштаба и паддингов для сохранения пропорций
  const scale = Math.min(size / img.width, size / img.height)
  const newW = img.width * scale
  const newH = img.height * scale
  const padX = (size - newW) / 2
  const padY = (size - newH) / 2

  ctx.fillStyle = '#808080'
  ctx.fillRect(0, 0, size, size)
  ctx.drawImage(img, padX, padY, newW, newH)

  const imageData = ctx.getImageData(0, 0, size, size)
  const data = new Float32Array(3 * size * size)
  
  // Конвертация в формат [R..., G..., B...] и нормализация
  for (let i = 0; i < size * size; i++) {
    data[i] = imageData.data[i * 4] / 255.0
    data[i + size * size] = imageData.data[i * 4 + 1] / 255.0
    data[i + 2 * size * size] = imageData.data[i * 4 + 2] / 255.0
  }
  
  return { 
    tensor: new ort.Tensor('float32', data, [1, 3, size, size]), 
    meta: { scale, padX, padY, originalWidth: img.width, originalHeight: img.height } 
  }
}

// --- Postprocessing ---
const sigmoid = (x) => 1 / (1 + Math.exp(-x))

const resolveClassScore = (score) => (score < 0 || score > 1 ? sigmoid(score) : score)

const postprocess = (outputTensor, meta) => {
  const data = outputTensor.data
  const dims = outputTensor.dims || []
  const numClasses = CLASS_NAMES.length

  // Поддержка двух форматов выхода:
  // 1) [1, N, 4 + classes] или [1, N, 5 + classes]
  // 2) [1, 4 + classes, N] или [1, 5 + classes, N]
  let numPredictions = 0
  let attrsPerPrediction = 0
  let rowMajor = true

  if (dims.length === 3) {
    const [, d1, d2] = dims
    if (d1 === numClasses + 4 || d1 === numClasses + 5) {
      attrsPerPrediction = d1
      numPredictions = d2
      rowMajor = false
    } else if (d2 === numClasses + 4 || d2 === numClasses + 5) {
      attrsPerPrediction = d2
      numPredictions = d1
      rowMajor = true
    }
  }

  if (!numPredictions || !attrsPerPrediction) {
    const withObjectness = numClasses + 5
    const withoutObjectness = numClasses + 4
    attrsPerPrediction = data.length % withObjectness === 0 ? withObjectness : withoutObjectness
    numPredictions = Math.floor(data.length / attrsPerPrediction)
    rowMajor = true
  }

  const hasObjectness = attrsPerPrediction === numClasses + 5
  const predictions = []

  for (let i = 0; i < numPredictions; i++) {
    const read = (attrIndex) => {
      if (rowMajor) {
        return data[i * attrsPerPrediction + attrIndex]
      }
      return data[attrIndex * numPredictions + i]
    }

    const cx = read(0)
    const cy = read(1)
    const w = read(2)
    const h = read(3)
    const objectness = hasObjectness ? resolveClassScore(read(4)) : 1

    // Поиск класса с максимальной вероятностью
    let maxConf = 0, maxClass = -1
    for (let c = 0; c < numClasses; c++) {
      const classOffset = hasObjectness ? 5 : 4
      const classScore = resolveClassScore(read(classOffset + c))
      const conf = objectness * classScore
      if (conf > maxConf) { maxConf = conf; maxClass = c }
    }

    if (maxConf > confThreshold.value) {
      // Обратный пересчет координат из 640x640 в оригинал
      const x1 = ((cx - w / 2) - meta.padX) / meta.scale
      const y1 = ((cy - h / 2) - meta.padY) / meta.scale
      const x2 = ((cx + w / 2) - meta.padX) / meta.scale
      const y2 = ((cy + h / 2) - meta.padY) / meta.scale

      predictions.push({ x1, y1, x2, y2, conf: maxConf, classId: maxClass })
    }
  }
  return applyNMS(predictions, iouThreshold.value)
}

// --- NMS (Non-Maximum Suppression) ---
const applyNMS = (boxes, iouThreshold) => {
  boxes.sort((a, b) => b.conf - a.conf)
  const result = []
  
  while (boxes.length > 0) {
    const current = boxes.shift()
    result.push(current)
    // Оставляем только те боксы, которые слабо пересекаются с текущим
    boxes = boxes.filter(box => computeIoU(current, box) <= iouThreshold)
  }
  
  return result.map(b => ({ ...b, label: CLASS_NAMES[b.classId] || `class_${b.classId}` }))
}

const computeIoU = (a, b) => {
  const x1 = Math.max(a.x1, b.x1)
  const y1 = Math.max(a.y1, b.y1)
  const x2 = Math.min(a.x2, b.x2)
  const y2 = Math.min(a.y2, b.y2)
  
  const intersection = Math.max(0, x2 - x1) * Math.max(0, y2 - y1)
  const areaA = (a.x2 - a.x1) * (a.y2 - a.y1)
  const areaB = (b.x2 - b.x1) * (b.y2 - b.y1)
  
  return intersection / (areaA + areaB - intersection + 1e-6)
}

// --- Drawing ---
const drawDetections = (img, detections) => {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  
  // Сброс канваса под размер оригинала
  canvas.width = img.width
  canvas.height = img.height
  ctx.drawImage(img, 0, 0)
  
  ctx.font = 'bold 14px sans-serif'
  ctx.lineWidth = 2

  detections.forEach(det => {
    const color = COLORS[det.classId % COLORS.length]
    const w = det.x2 - det.x1
    const h = det.y2 - det.y1

    ctx.strokeStyle = color
    ctx.strokeRect(det.x1, det.y1, w, h)

    const text = `${det.label} ${(det.conf * 100).toFixed(0)}%`
    const textWidth = ctx.measureText(text).width
    
    ctx.fillStyle = color
    ctx.fillRect(det.x1, det.y1 - 22, textWidth + 8, 22)

    ctx.fillStyle = '#fff'
    ctx.fillText(text, det.x1 + 4, det.y1 - 6)
  })
}
</script>

<style scoped>
.drop-zone {
  border: 2px dashed #ced4da;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  background: #f8f9fa;
  font-size: 0.9rem;
  color: #6c757d;
}
.drop-zone:hover { border-color: #0d6efd; background: #e9ecef; color: #0d6efd; }
</style>