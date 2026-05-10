<template>
  <div class="d-flex">

    <!-- ==================== БОКОВОЕ МЕНЮ ==================== -->
    <aside class="flex-column" style="background: #f8f9fa;">
      <!-- Заголовок -->
      <div class="px-3 pt-3 pb-2">
        <h5 class="fw-bold text-primary">Модели</h5>
      </div>

      <!-- Кнопки категорий -->
      <div class="px-3 mb-2"> 
        <div class="btn-group flex-column flex-sm-row" role="group">
          <button
            v-for="cat in categories"
            :key="cat.key"
            type="buton" 
            class="btn btn-sm btn-outline-primary"
            :class="{ active: selectedCategory === cat.key }"
            @click="toggleCategory(cat.key)"
          >
            {{ cat.label }}
          </button>
        </div>
      </div>

      <!-- Список моделей -->
      <div class="flex-grow-1 overflow-auto px-3 pb-3">
        <div v-if="selectedCategory" class="mt-2">
          <ul class="list-group list-group-flush">
            <li
              v-for="model in filteredModels"
              :key="model.id"
              class="list-group-item list-group-item-action py-2 px-3"
              :class="{ active: selectedModel && selectedModel.id === model.id }"
              style="cursor: pointer; font-size: 0.9rem;"
              @click="selectModel(model)"
            >
              <div class="d-flex align-items-center gap-2">
                <span class="badge bg-secondary" style="font-size: 0.7rem;">{{ model.status === 'active' ? '●' : '○' }}</span>
                <span>{{ model.name }}</span>
              </div>
            </li>
            <li v-if="filteredModels.length === 0" class="list-group-item text-muted text-center py-3 small">
              Нет доступных моделей
            </li>
          </ul>
        </div>
        <div v-else class="text-muted text-center mt-4 small">
          Выберите категорию
        </div>
      </div>
    </aside>

    <!-- ==================== ОСНОВНАЯ ЧАСТЬ ==================== -->
    <main class="main-content flex-grow-1 d-flex flex-column gap-3 p-4 overflow-auto" style="background: #eef1f5;">

      <!-- ====== ВЕРХНЯЯ КАРТОЧКА: Загрузка модели ====== -->
      <div class="card shadow-sm">
        <div class="card-header bg-primary text-white fw-semibold">
          Загрузка новой модели
        </div>
        <div class="card-body">
          <!-- Выбор директории -->
          <div class="mb-3">
            <label class="form-label fw-semibold">Тип модели</label>
            <div class="btn-group">
              <button
                v-for="cat in categories"
                :key="cat.key"
                type="button"
                class="btn btn-outline-primary"
                :class="{ active: selectedCategoryToSave === cat.key }"
                @click="togglecategoryload(cat.key)"
              >
                {{ cat.label }}
              </button>
            </div>
          </div>

          <!-- Выбор файла ONNX -->
          <div class="mb-3">
            <label class="form-label fw-semibold">Файл модели (.onnx)</label>
            
            <!-- Скрытый input (всё ещё нужен для работы с файлами) -->
            <input
              ref="onnxInput"
              type="file"
              accept=".onnx"
              class="d-none"
              @change="handleOnnxFile"
            />

            <!-- Единая красная кнопка -->
            <button
              class="btn btn-danger w-100"
              @click="$refs.onnxInput.click()"
            >
            {{ !onnxFile? "Загрузить файл модели":"выбранный файл модели: " + onnxFile.name }}
            </button>
          </div>

          <!-- Выбор файла меток -->
          <div class="mb-3">
            <label class="form-label fw-semibold">Файл загрузки классов (.txt или json)</label>

            <input
              ref="labelInput"
              type="file"
              accept=".txt,.json"
              class="d-none"
              @change="handleLabelFile"
            />

            <button
              class="btn btn-danger w-100"
              @click="$refs.labelInput.click()"
            >
            {{ !labelFile? "Загрузить файл классов":"выбранный файл классов: " + labelFile.name }}
            </button>
          </div>

          <!-- Кнопка загрузки -->
          <button
            class="btn btn-success py-2 fw-semibold"
            :disabled="!canUpload"
            @click="uploadModel">
            Загрузить модель
          </button>
        </div>
      </div>

      <!-- ====== НИЖНЯЯ КАРТОЧКА: Информация о модели ====== -->
      <div class="card shadow-sm">
        <div class="card-header bg-dark text-white fw-semibold">
          Информация о модели
        </div>
        <div class="card-body">
          <div v-if="selectedModel" class="table-responsive">
            <table class="table table-bordered table-striped align-middle mb-3">
              <tbody>
                <tr>
                  <th style="width: 200px;">Название модели</th>
                  <td>{{ selectedModel.name }}</td>
                </tr>
                <tr>
                  <th>Назначение / Директория</th>
                  <td>{{ getCategoryLabel(selectedModel.category) }}</td>
                </tr>
                <tr>
                  <th>Дата установки</th>
                  <td>{{ selectedModel.installDate }}</td>
                </tr>
                <tr>
                  <th>Статус активности</th>
                  <td>
                    <span
                      class="badge fs-6 px-3 py-2"
                      :class="selectedModel.status === 'active' ? 'bg-success' : 'bg-secondary'"
                    >
                      {{ selectedModel.status === 'active' ? 'Активна' : 'Неактивна' }}
                    </span>
                  </td>
                </tr>
                <tr>
                  <th>Обнаруживаемые классы</th>
                  <td>
                    <div class="d-flex flex-wrap gap-1">
                      <span
                        v-for="cls in selectedModel.classes"
                        :key="cls"
                        class="badge bg-info text-dark"
                      >
                        {{ cls }}
                      </span>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>

            <!-- Кнопки действий -->
            <div class="d-flex gap-2">
              <button
                class="btn btn-outline-success px-4"
                :class="{ 'active': selectedModel.status === 'active' }"
                @click="toggleModelStatus"
              >
                <i class="bi me-1" :class="selectedModel.status === 'active' ? 'bi-pause-circle' : 'bi-play-circle'"></i>
                {{ selectedModel.status === 'active' ? 'Деактивировать' : 'Активировать' }}
              </button>
              <button
                class="btn btn-outline-danger px-4"
                @click="deleteModel"
              >
                <i class="bi bi-trash me-1"></i>
                Удалить модель
              </button>
            </div>
          </div>

          <div v-else class="text-muted text-center py-5">
            <i class="bi bi-box-seam d-block mb-2" style="font-size: 2rem;"></i>
            Выберите модель из списка слева для просмотра информации
          </div>
        </div>
      </div>

    </main>

    <!-- Модальное окно подтверждения удаления -->
    <div
      class="modal fade"
      id="deleteModal"
      tabindex="-1"
      aria-hidden="true"
    >
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
          <div class="modal-header bg-danger text-white">
            <h5 class="modal-title">Подтверждение удаления</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            Вы действительно хотите удалить модель <strong>{{ selectedModel?.name }}</strong>?
            Это действие нельзя отменить.
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
            <button type="button" class="btn btn-danger" data-bs-dismiss="modal" @click="confirmDelete">Удалить</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Модальное окно загрузки -->
    <div
      class="modal fade"
      id="uploadModal"
      tabindex="-1"
      aria-hidden="true"
    >
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
          <div class="modal-header bg-success text-white">
            <h5 class="modal-title">Загрузка модели</h5>
          </div>
          <div class="modal-body text-center py-4">
            <div class="spinner-border text-success mb-3" role="status"></div>
            <p class="mb-0">Загрузка модели <strong>{{ onnxFile?.name }}</strong>...</p>
          </div>
        </div>
      </div>
    </div>


  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Modal } from 'bootstrap'
// ======================== ЗАГЛУШКА ДАННЫХ ========================
const categories = [
  { key: 'detection', label: 'Детекция комнат и стен' },
  { key: 'classification', label: 'Классификация комнат' },
  { key: 'furniture', label: 'Детекция и классификация мебели' }
]


const modelsStub = [
  {
    id: 1,
    name: 'RoomDetect_v1.onnx',
    category: 'detection',
    installDate: '2026-01-15',
    status: 'active',
    classes: ['living_room', 'bedroom', 'kitchen', 'bathroom', 'hallway', 'wall']
  },
  {
    id: 2,
    name: 'WallDetector_v2.onnx',
    category: 'detection',
    installDate: '2026-03-22',
    status: 'inactive',
    classes: ['load_bearing_wall', 'partition_wall', 'exterior_wall']
  },
  {
    id: 3,
    name: 'RoomClassify_ResNet50.onnx',
    category: 'classification',
    installDate: '2025-11-08',
    status: 'active',
    classes: ['office', 'conference_room', 'lobby', 'storage', 'restroom']
  },
  {
    id: 4,
    name: 'FurnitureDetect_YOLOv8.onnx',
    category: 'furniture',
    installDate: '2026-04-10',
    status: 'active',
    classes: ['sofa', 'table', 'chair', 'bed', 'desk', 'shelf', 'cabinet', 'lamp']
  },
  {
    id: 5,
    name: 'FurnitureClassify_v3.onnx',
    category: 'furniture',
    installDate: '2025-09-30',
    status: 'inactive',
    classes: ['armchair', 'dining_table', 'wardrobe', 'nightstand', 'bookshelf']
  }
]

// ======================== СОСТОЯНИЕ ========================
const selectedCategory = ref(null)
const selectedModel = ref(null)
const selectedCategoryToSave = ref(null)

const onnxFile = ref(null)
const labelFile = ref(null)
const onnxInput = ref(null)
const labelInput = ref(null)

// ======================== ВЫЧИСЛЯЕМЫЕ ========================
const filteredModels = computed(() => {
  if (!selectedCategory.value) return []
  return modelsStub.filter(m => m.category === selectedCategory.value)
})

const canUpload = computed(() => {
  return selectedCategoryToSave.value && onnxFile.value && labelFile.value
})

// ======================== МЕТОДЫ ========================
const getCategoryLabel = (key) => {
  const cat = categories.find(c => c.key === key)
  return cat ? cat.label : key
}

const toggleCategory = (key) => {
  // Переключаем категорию в меню
  if (selectedCategory.value === key) {
    selectedCategory.value = null 
  } 
  else {
    selectedCategory.value = key 
  }
  selectedModel.value = null  
}

const togglecategoryload=(key)=>{
  if (selectedCategoryToSave.value === key) {
    selectedCategoryToSave.value = null 
  } else {
    selectedCategoryToSave.value = key 
  }
}

const selectModel = (model) => {
  selectedModel.value = model
}

const handleOnnxFile = (e) => {
  const file = e.target.files[0]
  if (file && file.name.endsWith('.onnx')) {
    onnxFile.value = file
  }
}

const handleLabelFile = (e) => {
  const file = e.target.files[0]
  if (file && (file.name.endsWith('.txt') || file.name.endsWith('.json'))) {
    labelFile.value = file
    console.log(labelFile.value)
  }
}

const clearOnnx = () => {
  onnxFile.value = null
  if (onnxInput.value) onnxInput.value.value = ''
}

const clearLabel = () => {
  labelFile.value = null
  if (labelInput.value) labelInput.value.value = ''
}

const uploadModel = () => {
  // Заглушка API запроса
  console.log('[API] POST /api/models/upload', {
    directory: selectedCategoryToSave.value,
    onnxFile: onnxFile.value.name,
    labelFile: labelFile.value.name
  })


  const modalEl = document.getElementById('uploadModal')
  if (modalEl) {
    const modal = new Modal(modalEl)
    modal.show()

  setTimeout(() => {
    modal.hide()
    alert('Модель успешно загружена! (заглушка)')
    clearOnnx()
    clearLabel()
    selectedCategoryToSave.value = null
  }, 2000)
}
}



const toggleModelStatus = () => {
  if (!selectedModel.value) return
  selectedModel.value.status = selectedModel.value.status === 'active' ? 'inactive' : 'active'
  // Заглушка API
  console.log('[API] POST /api/models/' + selectedModel.value.id + '/toggle-status')
}

const deleteModel = () => {
  const modalEl = document.getElementById('deleteModal')
  if (modalEl) {
    const modal = new Modal(modalEl)
    modal.show()
  }
}

const confirmDelete = () => {
  if (!selectedModel.value) return
  console.log('[API] DELETE /api/models/' + selectedModel.value.id)

  const id = selectedModel.value.id
  modelsStub.splice(modelsStub.findIndex(m => m.id === id), 1)
  selectedModel.value = null

  alert('Модель удалена! (заглушка)')
  
  // Закрываем модалку после удаления
  const modalEl = document.getElementById('deleteModal')
  if (modalEl) {
    const modal = Modal.getInstance(modalEl)
    modal?.hide()
  }
}

onMounted(() => {
  // Инициализация Bootstrap JS если нужно
  console.log('ModelsManager mounted')
})
</script>

