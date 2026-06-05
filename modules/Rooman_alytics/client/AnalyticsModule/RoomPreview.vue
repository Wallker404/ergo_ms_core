<template>
    <div class="room-preview-wrapper">
      <div class="room-preview-label">
      </div>
  
      <div 
        ref="containerRef"
        class="room-preview"
        :style="{ width: width + 'px', height: height + 'px' }"
      >
        <img 
          ref="imgRef"
          :src="imageUrl" 
          class="room-preview-img"
          draggable="false"
          @load="onLoad"
          alt="plan"
        />
  
        <!-- Рамка комнаты поверх плана -->
        <div
          v-if="boxStyle"
          class="room-bbox"
          :style="boxStyle"
        >
          <span 
            class="room-bbox-label"
            :style="{ backgroundColor: roomColor, color: labelColor }"
          >
            {{ roomLabel }}
          </span>
        </div>
  
        <!-- Заглушка, пока изображение не загрузилось -->
        <div v-if="!loaded" class="room-preview-loading">Загрузка плана…</div>
      </div>
    </div>
  </template>
  
  <script setup>
import { computed, ref, watch, onMounted } from 'vue'

const props = defineProps({
  imageUrl: { type: String, required: true },
  bbox:     { type: [Array, Object], required: true },
  roomColor:{ type: String, default: '#0d6efd' },
  roomLabel:{ type: String, default: 'Комната' },
  width:    { type: Number, default: 260 },
  height:   { type: Number, default: 180 }
})

const imgRef = ref(null)
const loaded = ref(false)
const naturalSize = ref({ w: 1, h: 1 })

/**
 * Нормализация bbox → {x, y, w, h}
 * Поддерживаем форматы:
 *   [x, y, w, h]                 — классический
 *   [min_x, max_x, min_y, max_y] — формат твоего бэка (x1, x2, y1, y2)
 *   {x, y, width, height}
 *   {x1, y1, x2, y2}
 */
const normalizedBbox = computed(() => {
  if (!props.bbox) return null
  
  if (Array.isArray(props.bbox)) {
    const b = props.bbox
    if (b.length !== 4) return null
    
    const [a, c, d, e] = b
    
    // Эвристика: если a < c И d < e, и при этом c > a и e > d — 
    // скорее всего это [min_x, max_x, min_y, max_y] (твой формат бэка).
    // Иначе — [x, y, w, h].
    // Надёжнее всего — явно договориться о формате. Для безопасности
    // считаем, что если b[1] > b[0] и b[3] > b[2] — это [x1, x2, y1, y2].
    // Но [x, y, w, h] тоже может иметь w>0, h>0. Различаем по "разумности"
    // значений: если a и c близки по порядку, а d и e — тоже, и при этом
    // a обычно меньше d (x-координаты часто меньше y-координат на плане
    // с альбомной ориентацией) — это неоднозначно.
    //
    // ✅ Простое решение: используем порядок твоего бэка.
    // Если у тебя всегда [min_x, max_x, min_y, max_y] — раскомментируй:
    
    return {
      x: Math.min(a, c),                 // min_x
      y: Math.min(d, e),                 // min_y
      w: Math.abs(c - a),                // max_x - min_x
      h: Math.abs(e - d)                 // max_y - min_y
    }
    
    // Если вдруг где-то ещё приходит [x, y, w, h] — замени блок выше на:
    // return { x: b[0], y: b[1], w: b[2], h: b[3] }
  }
  
  // Объектный формат
  if ('x1' in props.bbox || 'x2' in props.bbox) {
    const x1 = props.bbox.x1 ?? 0
    const x2 = props.bbox.x2 ?? 0
    const y1 = props.bbox.y1 ?? 0
    const y2 = props.bbox.y2 ?? 0
    return { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1) }
  }
  
  return {
    x: props.bbox.x ?? 0,
    y: props.bbox.y ?? 0,
    w: props.bbox.w ?? props.bbox.width ?? 0,
    h: props.bbox.h ?? props.bbox.height ?? 0
  }
})

const bboxText = computed(() => {
  const b = normalizedBbox.value
  if (!b) return ''
  return `${Math.round(b.x)},${Math.round(b.y)} ${Math.round(b.w)}×${Math.round(b.h)}`
})

function onLoad(e) {
  naturalSize.value = {
    w: e.target.naturalWidth || 1,
    h: e.target.naturalHeight || 1
  }
  loaded.value = true
}

onMounted(() => {
  if (imgRef.value?.complete && imgRef.value.naturalWidth) {
    naturalSize.value = { w: imgRef.value.naturalWidth, h: imgRef.value.naturalHeight }
    loaded.value = true
  }
})

watch(() => props.imageUrl, () => { loaded.value = false })

const boxStyle = computed(() => {
  const b = normalizedBbox.value
  if (!b || !loaded.value || !naturalSize.value.w || !b.w || !b.h) return null
  
  const nw = naturalSize.value.w
  const nh = naturalSize.value.h
  const cw = props.width
  const ch = props.height
  
  const scale = Math.min(cw / nw, ch / nh)
  const displayW = nw * scale
  const displayH = nh * scale
  const offsetX = (cw - displayW) / 2
  const offsetY = (ch - displayH) / 2
  
  const x = offsetX + b.x * scale
  const y = offsetY + b.y * scale
  const w = b.w * scale
  const h = b.h * scale
  
  return {
    left: x + 'px',
    top: y + 'px',
    width: w + 'px',
    height: h + 'px',
    borderColor: props.roomColor,
    boxShadow: `0 0 0 2px ${props.roomColor}55, inset 0 0 0 1000px ${props.roomColor}22`
  }
})

const labelColor = computed(() => {
  const c = (props.roomColor || '').replace('#', '')
  if (c.length !== 6) return '#fff'
  const r = parseInt(c.substr(0, 2), 16)
  const g = parseInt(c.substr(2, 2), 16)
  const b = parseInt(c.substr(4, 2), 16)
  const lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
  return lum > 0.6 ? '#111' : '#fff'
})
</script>
  
  <style scoped>
  .room-preview-wrapper {
    display: inline-block;
    max-width: 100%;
  }
  
  .room-preview-label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    margin-bottom: 6px;
  }
  
  .room-preview-label .dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    display: inline-block;
    flex-shrink: 0;
  }
  
  .room-preview {
    position: relative;
    background: #f0f2f5;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.12);
    border: 1px solid #e3e6ea;
  }
  
  .room-preview-img {
    width: 100%;
    height: 100%;
    object-fit: contain;
    display: block;
    user-select: none;
    pointer-events: none;
  }
  
  .room-bbox {
    position: absolute;
    border: 2.5px solid;
    border-radius: 3px;
    pointer-events: none;
    box-sizing: border-box;
  }
  
  .room-bbox-label {
    position: absolute;
    top: -10px;
    left: -2px;
    font-size: 11px;
    font-weight: 600;
    padding: 1px 6px;
    border-radius: 3px;
    white-space: nowrap;
    line-height: 1.4;
    box-shadow: 0 1px 2px rgba(0,0,0,0.2);
  }
  
  .room-preview-loading {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #888;
    font-size: 12px;
    background: #f0f2f5;
  }
  </style>