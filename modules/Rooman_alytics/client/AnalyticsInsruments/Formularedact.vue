<template>
  <div class="container-fluid py-4 bg-light min-vh-100">
    <h2 class="mb-4 text-center fw-bold">Управление критериями и параметрами</h2>
    
    <!-- Карточка 1: Параметры расчёта -->
    <div class="card shadow-sm mb-4">
      <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
        <span class="fw-bold">Параметры расчёта</span>
        <button v-if="isEditingParam" class="btn btn-sm btn-light" @click="cancelEditParam">Отменить редактирование</button>
      </div>
      <div class="card-body">
        <div class="row g-3 mb-3">
          <div class="col-md-3">
            <label class="form-label">Обозначение переменной</label>
            <input v-model="paramForm.varName" type="text" class="form-control" placeholder="T_room" />
          </div>
          <div class="col-md-3">
            <label class="form-label">Метка (описание)</label>
            <input v-model="paramForm.label" type="text" class="form-control" placeholder="Температура в комнате" />
          </div>
          <div class="col-md-2">
            <label class="form-label">Область действия</label>
            <select v-model="paramForm.scope" class="form-select">
              <option value="current">Для текущего критерия</option>
              <option value="global">Для всех критериев</option>
            </select>
          </div>
          <div class="col-md-2">
            <label class="form-label">Тип ввода</label>
            <select v-model="paramForm.inputType" class="form-select">
              <option value="manual">Пользовательский ввод</option>
              <option value="auto">Автоматический расчёт</option>
            </select>
          </div>
          <div class="col-md-2" v-if="paramForm.inputType === 'manual'">
            <label class="form-label">Применимость</label>
            <select v-model="paramForm.paramType" class="form-select">
              <option value="global">Все комнаты</option>
              <option value="rooms">Выбранные комнаты</option>
            </select>
          </div>
        </div>

        <div v-if="paramForm.paramType === 'rooms'" class="col-12 mt-2">
          <label class="form-label fw-bold mb-2">Выберите типы комнат:</label>
          <div class="d-flex flex-wrap gap-2">
            <button
              v-for="rt in roomTypes"
              :key="rt.id"
              type="button"
              class="btn btn-sm rounded-pill px-3 py-2 transition-all"
              :class="paramForm.roomTypeIds.includes(rt.id) ? 'btn-primary text-white' : 'btn-outline-secondary bg-white'"
              @click="toggleRoomChip(rt.id)"
            >
              {{ rt.label }}
              <span v-if="paramForm.roomTypeIds.includes(rt.id)" class="ms-2 fw-bold">✓</span>
            </button>
          </div>
          <div v-if="paramForm.roomTypeIds.length === 0" class="text-muted mt-1 small">
            ⚠️ Необходимо выбрать хотя бы одну комнату
          </div>
        </div>

        <div v-if="paramForm.inputType === 'manual'" class="row g-3 mb-3 p-3 bg-light rounded">
          <div class="col-md-3">
            <label class="form-label">Мин. значение</label>
            <input v-model.number="paramForm.minVal" type="number" class="form-control" />
          </div>
          <div class="col-md-3">
            <label class="form-label">Макс. значение</label>
            <input v-model.number="paramForm.maxVal" type="number" class="form-control" />
          </div>
        </div>

        <div v-if="paramForm.inputType === 'auto'" class="row g-3 mb-3 p-3 bg-light rounded">
          <div class="col-md-4">
            <label class="form-label">Метод расчёта</label>
            <select v-model="paramForm.methodId" class="form-select" @change="onMethodChange">
              <option :value="null">Выберите метод...</option>
              <option v-for="m in availableMethods" :key="m.id" :value="m.id">{{ m.name }}</option>
            </select>
          </div>
          <div v-if="selectedMethod" class="col-12">
            <div class="alert alert-info py-2 mb-0 small">
              <strong>Тип метода:</strong> {{ methodTypeLabel(selectedMethod.inputType) }}
            </div>
          </div>
          <div v-if="selectedMethod?.inputType === 'rooms' || selectedMethod?.inputType === 'roomsfurniture'" class="col-md-3">
            <label class="form-label">Тип комнаты</label>
            <select v-model="paramForm.room_type_id" class="form-select">
              <option :value="null">Не выбрано</option>
              <option v-for="rt in roomTypes" :key="rt.id" :value="rt.id">{{ rt.label }}</option>
            </select>
          </div>
          <div v-if="selectedMethod?.inputType === 'furniture' || selectedMethod?.inputType === 'roomsfurniture'" class="col-md-3">
            <label class="form-label">Тип мебели</label>
            <select v-model="paramForm.furniture_type_id" class="form-select">
              <option :value="null">Не выбрано</option>
              <option v-for="ft in furnitureTypes" :key="ft.id" :value="ft.id">{{ ft.label }}</option>
            </select>
          </div>
        </div>

        <div class="d-flex gap-2">
          <button class="btn btn-primary" @click="saveParam">
            {{ isEditingParam ? '💾 Обновить параметр' : '➕ Добавить параметр' }}
          </button>
          <button class="btn btn-secondary" @click="resetParamForm">Очистить</button>
        </div>

        <div class="table-responsive mt-4">
          <table class="table table-hover table-bordered align-middle">
            <thead class="table-light">
              <tr>
                <th>Переменная</th>
                <th>Метка</th>
                <th>Область</th>
                <th>Ввод</th>
                <th>Детали</th>
                <th style="width: 100px;">Действия</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in parameters" :key="p.id">
                <td><code>{{ p.varName }}</code></td>
                <td>{{ p.label }}</td>
                <td>{{ p.cryteria_id ? 'Для этого критерия' : 'Общий параметр' }}</td>
                <td>{{ p.inputType === 'manual' ? 'Ручной' : 'Авто' }}</td>
                <td>
                  <span v-if="p.inputType === 'manual'">
                    Диапазон: [{{ p.minVal }}; {{ p.maxVal }}]
                    <span v-if="p.paramType === 'rooms'" class="ms-2">
                      Комнаты: [ {{ getRoomLabels(p.roomTypeIds) }} ]
                    </span>
                  </span>
                  <span v-else>
                    {{ p.methodName || '—' }}
                    <span v-if="p.room_type_id" class="d-block">Тип комнаты: {{ getRoomLabel(p.room_type_id) }}</span>
                    <span v-if="p.furniture_type_id" class="d-block">Тип мебели: {{ getFurnitureLabel(p.furniture_type_id) }}</span>
                  </span>
                </td>
                <td>
                  <button class="btn btn-sm btn-outline-warning me-1" @click="editParam(p)">Ред.</button>
                  <button class="btn btn-sm btn-outline-danger" @click="deleteParam(p.id)">X</button>
                </td>
              </tr>
              <tr v-if="!parameters.length">
                <td colspan="6" class="text-center text-muted">Параметры не добавлены</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Карточка 2: Параметры ограничения -->
    <div class="card shadow-sm mb-4">
      <div class="card-header bg-success text-white d-flex justify-content-between align-items-center">
        <span class="fw-bold">Параметры ограничения</span>
        <button v-if="isEditingConstraint" class="btn btn-sm btn-light" @click="cancelEditConstraint">Отменить</button>
      </div>
      <div class="card-body">
        <div class="row g-3 mb-3">
          <div class="col-md-3">
            <label class="form-label">Символ</label>
            <input v-model="constraintForm.symbol" type="text" class="form-control" placeholder="Q_min" />
          </div>
          <div class="col-md-3">
            <label class="form-label">Метка</label>
            <input v-model="constraintForm.label" type="text" class="form-control" placeholder="Мин. поток" />
          </div>
          <div class="col-md-3">
            <label class="form-label">Область действия</label>
            <select v-model="constraintForm.scope" class="form-select" @change="syncCriterionId">
              <option value="current">Для текущего критерия</option>
              <option value="global">Для всех критериев</option>
            </select>
          </div>
          <div class="col-md-3">
            <label class="form-label">Тип ограничения</label>
            <select v-model="constraintForm.type" class="form-select">
              <option value="universal">Универсальный</option>
              <option value="byRoom">По типу комнаты</option>
            </select>
          </div>
        </div>
        
        <div v-if="constraintForm.type === 'universal'" class="mb-3">
          <label class="form-label">Значение</label>
          <input v-model.number="constraintForm.universalValue" type="number" class="form-control w-25" placeholder="0.00" />
        </div>

        <div v-if="constraintForm.type === 'byRoom'" class="mb-3 p-3 bg-light rounded">
          <label class="form-label fw-bold">Значения по типам комнат</label>
          <div class="row g-2 mb-2 align-items-end">
            <div class="col-md-5">
              <label class="form-label small">Тип комнаты</label>
            <!-- Стало: показываем только те комнаты, которых ещё нет в roomValues -->
            <select v-model="roomValForm.roomId" class="form-select form-select-sm">
              <option :value="null">Выберите...</option>
              <option 
                v-for="rt in availableRoomOptions" 
                :key="rt.id" 
                :value="rt.id"
              >
                {{ rt.label }}
              </option>
            </select>
            </div>
            <div class="col-md-4">
              <label class="form-label small">Значение</label>
              <input v-model.number="roomValForm.value" type="number" class="form-control form-control-sm" />
            </div>
            <div class="col-md-3">
              <button class="btn btn-sm btn-primary w-100" @click="addRoomValue" :disabled="!roomValForm.roomId">
                {{ editingRoomValIdx === null ? '➕ Добавить' : '💾 Сохранить' }}
              </button>
            </div>
          </div>
          <table class="table table-sm table-bordered bg-white mb-0">
            <thead><tr><th>Комната</th><th>Значение</th><th style="width:80px">Действия</th></tr></thead>
            <tbody>
              <tr v-for="(rv, idx) in constraintForm.roomValues" :key="idx">
                <td>{{ getRoomLabel(rv.roomId) }}</td>
                <td>{{ rv.value }}</td>
                <td>
                  <button class="btn btn-xs btn-outline-warning me-1" @click="startEditRoomVal(idx)">Ред.</button>
                  <button class="btn btn-xs btn-outline-danger" @click="removeRoomVal(idx)">X</button>
                </td>
              </tr>
              <tr v-if="!constraintForm.roomValues.length"><td colspan="3" class="text-center text-muted small">Нет значений</td></tr>
            </tbody>
          </table>
        </div>

        <div class="d-flex gap-2">
          <button class="btn btn-success" @click="saveLimitParam">
            {{ isEditingConstraint ? '💾 Обновить ограничение' : '➕ Добавить ограничение' }}
          </button>
          <button class="btn btn-secondary" @click="resetConstraintForm">Очистить</button>
        </div>

        <div class="table-responsive mt-4">
  <table class="table table-hover table-bordered align-middle">
    <thead class="table-light">
      <tr>
        <th>Символ</th>
        <th>Метка</th>
        <th>Тип</th>
        <th>Область действия</th> <!-- ✅ НОВЫЙ СТОЛБЕЦ -->
        <th>Значения</th>
        <th style="width: 100px;">Действия</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="c in limitParams" :key="c.id">
        <td><code>{{ c.symbol }}</code></td>
        <td>{{ c.label }}</td>
        <td>{{ c.type === 'universal' ? 'Универсальный' : 'По комнате' }}</td>
        
        <!-- ✅ ЯЧЕЙКА ОБЛАСТИ ДЕЙСТВИЯ -->
        <td>
          <span class="badge" :class="c.cryteria_id ? 'bg-primary' : 'bg-secondary'">
            {{ c.cryteria_id ? 'Для текущего критерия' : 'Общий (все критерии)' }}
          </span>
        </td>

        <td>
          <span v-if="c.type === 'universal'">{{ c.universalValue }}</span>
          <ul v-else class="mb-0 small ps-3">
            <li v-for="rv in c.roomValues" :key="rv.roomId">
              {{ getRoomLabel(rv.roomId) }}: <strong>{{ rv.value }}</strong>
            </li>
          </ul>
        </td>
        <td>
          <button class="btn btn-sm btn-outline-warning me-1" @click="editConstraint(c)">Ред.</button>
          <button class="btn btn-sm btn-outline-danger" @click="deleteConstraint(c.id)">X</button>
        </td>
      </tr>
      <!-- ✅ colspan увеличен с 5 до 6 -->
      <tr v-if="!limitParams.length">
        <td colspan="6" class="text-center text-muted">Ограничения не добавлены</td>
      </tr>
    </tbody>
  </table>
</div>
      </div>
    </div>

    <!-- Карточка 3: Формулы и системы уравнений -->
    <div class="card shadow-sm mb-4">
      <div class="card-header bg-info text-white d-flex justify-content-between align-items-center">
        <span class="fw-bold">Формулы и системы уравнений</span>
        <button v-if="isEditingFormula" class="btn btn-sm btn-light" @click="cancelEditFormula">Отменить</button>
      </div>
      
      <div class="card-body">
        <!-- Выбор типа объекта -->
        <div class="row g-3 mb-4">
          <div class="col-md-4">
            <label class="form-label fw-bold">Тип объекта</label>
            <select v-model="formulaForm.objType" class="form-select">
              <option value="single">Обычная формула</option>
              <option value="system">Система уравнений</option>
            </select>
          </div>
        </div>
        <div class="d-flex gap-2 justify-content-start">
          <button class="btn btn-secondary" @click="resetFormulaForm">Очистить</button>
          <button class="btn btn-info text-white px-4" @click="saveFormula" 
                  :disabled="formulaForm.objType === 'system' && !formulaForm.equations.length">
            {{ isEditingFormula ? 'Обновить' : 'Добавить' }}
          </button>
        </div>
        <!-- Обычная формула -->
        <div v-if="formulaForm.objType === 'single'" class="row g-3 mb-4 p-3 bg-light rounded">
          <div class="col-md-8">
            <label class="form-label">Уравнение</label>
            <div class="input-group">
              <input v-model="formulaForm.equation" type="text" class="form-control" placeholder="Q = A * B" />
              <button class="btn btn-outline-secondary" type="button" @click="openMathHelper('equation')">🧮</button>
            </div>
          </div>
          <div class="col-md-4">
            <label class="form-label">Порог для рекомендации</label>
            <input v-model.number="formulaForm.value_recomm" type="number" class="form-control" placeholder="0.00" />
          </div>
          <div class="col-12">
            <label class="form-label">Рекомендация по улучшению</label>
            <textarea v-model="formulaForm.recommendation" class="form-control" rows="2" placeholder="Пояснение к формуле..."></textarea>
          </div>
        </div>

        <!-- Система уравнений -->
        <div v-if="formulaForm.objType === 'system'" class="mb-4 p-3 bg-light rounded">
          <div class="d-flex justify-content-between align-items-center mb-3">
            <label class="form-label fw-bold mb-0">Уравнения системы</label>
            <button class="btn btn-sm btn-success" @click="addEquation">➕ Добавить</button>
          </div>
          
          <div v-for="(eq, idx) in formulaForm.equations" :key="idx" class="card mb-3 border-start border-4 border-info">
            <div class="card-header d-flex justify-content-between py-2 bg-white">
              <span class="fw-bold text-info">Уравнение #{{ idx + 1 }}</span>
              <button class="btn btn-sm btn-outline-danger" @click="removeEquation(idx)">🗑️ Удалить</button>
            </div>
            <div class="card-body">
              <div class="row g-2">
                <div class="col-md-5">
                  <label class="form-label small">Условие (левая часть)</label>
                  <div class="input-group input-group-sm">
                    <input v-model="eq.left" type="text" class="form-control" placeholder="Q1" />
                    <button class="btn btn-outline-secondary" @click="openMathHelperForEquation(idx, 'left')">🧮</button>
                  </div>
                </div>
                <div class="col-md-5">
                  <label class="form-label small">Выражение (правая часть)</label>
                  <div class="input-group input-group-sm">
                    <input v-model="eq.right" type="text" class="form-control" placeholder="A + B" />
                    <button class="btn btn-outline-secondary" @click="openMathHelperForEquation(idx, 'right')">🧮</button>
                  </div>
                </div>
              </div>
              <div class="mt-2">
                <label class="form-label small text-muted">Рекомендации</label>
                <textarea v-model="eq.recommendation" class="form-control form-control-sm" rows="2" placeholder="Например: если ниже нормы — увеличить нагрев..."></textarea>
              </div>
            </div>
          </div>
          
          <div v-if="!formulaForm.equations.length" class="alert alert-warning py-2 small">
            Добавьте хотя бы одно уравнение
          </div>

          <!-- Лимиты и комнаты для системы (на уровне системы, не уравнения!) -->
        </div>

        <!-- Область применения (для обычных формул) -->
        <div v-if="formulaForm.objType === 'single'" class="row g-3 mb-4">
          <div class="col-md-4">
            <label class="form-label fw-bold">Область применения</label>
            <div class="d-flex gap-2">
              <button type="button" class="btn btn-sm flex-fill rounded-pill"
                :class="formulaForm.type === 'global' ? 'btn-primary text-white' : 'btn-outline-secondary'"
                @click="formulaForm.type = 'global'; formulaForm.room_type_ids = []">
                 Все помещения
              </button>
              <button type="button" class="btn btn-sm flex-fill rounded-pill"
                :class="formulaForm.type === 'rooms' ? 'btn-primary text-white' : 'btn-outline-secondary'"
                @click="formulaForm.type = 'rooms'">
                Выборочно
              </button>
            </div>
          </div>
          <div v-if="formulaForm.type === 'rooms'" class="col-12 mt-2">
            <label class="form-label fw-bold mb-2">Типы комнат:</label>
            <div class="d-flex flex-wrap gap-2">
              <button v-for="rt in roomTypes" :key="rt.id" type="button"
                class="btn btn-sm rounded-pill px-3 py-2"
                :class="formulaForm.room_type_ids.includes(rt.id) ? 'btn-primary text-white' : 'btn-outline-secondary bg-white'"
                @click="toggleFormulaRoomChip(rt.id)">
                {{ rt.label }} <span v-if="formulaForm.room_type_ids.includes(rt.id)" class="ms-1">✓</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Выбор используемых параметров -->
        <div class="card border mb-4">
          <div class="card-header bg-light py-2">
            <span class="fw-bold">Используемые параметры</span>
          </div>
          <div class="card-body">
            <!-- Фильтры -->
            <div class="btn-group mb-3" role="group">
              <button type="button" class="btn btn-sm btn-outline-dark" 
                      :class="paramFilter === 'all' ? 'active' : ''" @click="paramFilter = 'all'">Все</button>
              <button type="button" class="btn btn-sm btn-outline-success" 
                      :class="paramFilter === 'manual' ? 'active' : ''" @click="paramFilter = 'manual'">Ручной ввод</button>
              <button type="button" class="btn btn-sm btn-outline-info" 
                      :class="paramFilter === 'auto' ? 'active' : ''" @click="paramFilter = 'auto'">Авто-расчёт</button>
              <button v-if="formulaForm.objType === 'system'" type="button" class="btn btn-sm btn-outline-warning" 
                      :class="paramFilter === 'limit' ? 'active' : ''" @click="paramFilter = 'limit'">Параметры ограничения</button>
            </div>

            <!-- Список параметров -->
            <div class="list-group" style="max-height: 200px; overflow-y: auto;">
              <div v-for="p in filteredAvailableParams" :key="p.id" 
                   class="list-group-item list-group-item-action d-flex align-items-center py-2"
                   :class="{ 'bg-warning bg-opacity-10': isParamInvalid(p) }">
                <div class="form-check flex-grow-1">
                  <input class="form-check-input" type="checkbox" :id="'p-'+p.id"
                         :checked="isParamSelected(p)" @change="toggleUsedParam(p)">
                  <label class="form-check-label w-100 ps-2" :for="'p-'+p.id">
                    <div class="d-flex justify-content-between">
                      <span>
                        <code class="me-2">{{ p.varName || p.symbol }}</code> {{ p.label }}
                      </span>
                      <span class="badge bg-secondary ms-2">{{ getParamTypeLabel(p) }}</span>
                    </div>
                    <small v-if="isParamInvalid(p)" class="text-danger d-block mt-1">
                      ⚠️ Выбранные комнаты системы не совпадают с областями этого ограничения
                    </small>
                  </label>
                </div>
              </div>
              <div v-if="!filteredAvailableParams.length" class="text-center text-muted py-3">
                Нет доступных параметров для выбора
              </div>
            </div>
          </div>
        </div>
        <!-- Таблица существующих формул -->
        <div class="table-responsive mt-4">
          <table class="table table-hover table-bordered align-middle">
            <thead class="table-light">
              <tr>
                <th style="width: 100px;">Тип</th>
                <th>Содержимое</th>
                <th>Область</th>
                <th>Комнаты</th>
                <th>Параметры</th>
                <th style="width: 30%;">Рекомендации</th>
                <th style="width: 100px;">Действия</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="f in formulas" :key="f.id">
                <td>
                  <span class="badge" :class="f.objType === 'single' ? 'bg-primary' : 'bg-dark'">
                    {{ f.objType === 'single' ? 'Формула' : 'Система' }}
                  </span>
                </td>
                <td>
                  <div v-if="f.objType === 'single'" class="small"><code>{{ f.equation }}</code></div>
                  <div v-else>
                    <div v-for="(eq, i) in f.equations" :key="i" class="small mb-1 border-bottom pb-1">
                      <code>{{ eq.left }} = {{ eq.right }}</code>
                    </div>
                  </div>
                </td>
                <td>{{ f.type === 'global' ? 'Все' : 'Выборочно' }}</td>
                <td class="small">
                  {{ f.objType === 'single' && f.type === 'rooms' ? getRoomLabels(f.room_type_ids) : 
                     f.objType === 'system' && f.systemType === 'rooms' ? getRoomLabels(f.for_room_types_ids) : '—' }}
                </td>
                <td class="small">
                  <div v-if="f.used_input_ids?.length">
                    Параметры: <span class="text-success">{{ getusingParams(f) }}</span>
                  </div>
                  <div v-if="f.used_acp_ids?.length" class="text-info">
                    Авто: <span>{{ f.used_acp_ids.length }} шт.</span>
                  </div>
                  <div v-if="f.objType === 'system' && f.used_limit_ids?.length" class="text-warning">
                    Лимиты: <span>{{ f.used_limit_ids.length }} шт.</span>
                  </div>
                </td>
                <td class="small text-muted">
                  <div v-if="f.objType === 'system'">
                    <div v-for="(eq, i) in f.equations" :key="i" class="mb-1">
                      <strong>#{{i+1}}:</strong> {{ eq.recommendation || '—' }}
                    </div>
                  </div>
                  <div v-else>{{ f.recommendation || '—' }}</div>
                </td>
                <td>
                  <button class="btn btn-sm btn-outline-warning me-1" @click="editFormula(f)">✏️</button>
                  <button class="btn btn-sm btn-outline-danger" @click="deleteFormula(f.id)">🗑️</button>
                </td>
              </tr>
              <tr v-if="!formulas.length">
                <td colspan="7" class="text-center text-muted py-3">Формулы не добавлены</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Панель математических символов -->
    <div v-if="showMathHelper" class="position-fixed bottom-0 start-0 end-0 p-3 bg-white border-top shadow-lg" style="z-index: 1050;">
      <div class="container">
        <div class="d-flex flex-wrap gap-2 align-items-center">
          <span class="small text-muted me-2">Вставить символ:</span>
          <button v-for="sym in mathSymbols" :key="sym" class="btn btn-sm btn-outline-dark" @click="insertMath(sym)">
            {{ sym }}
          </button>
          <button class="btn btn-sm btn-danger ms-auto" @click="showMathHelper = false">Закрыть ✕</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted , watch} from 'vue'
import { apiClient } from '../../../../core/client/src/js/api/manager'
import { roomAnalyticsEndpoints } from '../js/endpoints'
import { useRoute } from 'vue-router' 

const route = useRoute()
const criterionId = computed(() => {
  const id = route.params.criterionId
  return id ? Number(id) : null
})

const roomTypes = ref([])
const furnitureTypes = ref([])
const availableMethods = ref([])
const parameters = ref([])      // UserInputParam (ручной ввод + авто)
const limitParams = ref([])     // LimitParam (ограничения)
const formulas = ref([])

// Формы
const paramForm = reactive({
  id: null, varName: '', label: '', scope: 'current', inputType: 'manual',
  minVal: 0, maxVal: 100, methodId: null, paramType: 'global',
  roomTypeIds: [], room_type_id: null, furniture_type_id: null
})

watch(
  () => paramForm.inputType,
  (newVal) => {
    if (newVal === 'auto') {
      // При переключении на авто-расчёт сбрасываем поля ручного ввода
      paramForm.paramType = 'global'
      paramForm.roomTypeIds = []
      paramForm.minVal = 0
      paramForm.maxVal = 100
    }
  }
)
const isEditingParam = ref(false)

const constraintForm = reactive({
  id: null, symbol: '', label: '', type: 'universal', scope: 'current', // ← добавлено
  universalValue: 0, roomValues: [], criterion_id: null
})
function syncCriterionId() {
  constraintForm.criterion_id = constraintForm.scope === 'current' 
    ? (criterionId.value || null) 
    : null
}

const isEditingConstraint = ref(false)
const roomValForm = reactive({ roomId: null, value: 0 })
const editingRoomValIdx = ref(null)

const formulaForm = reactive({
  id: null, 
  objType: 'single', 
  equation: '', 
  equations: [{ left: '', right: '', recommendation: '' }],
  type: 'global', 
  recommendation: '', 
  value_recomm: null, 
  room_type_ids: [],           // для обычных формул типа 'rooms'
  for_room_types_ids: [],      // для систем типа 'rooms'
  used_input_ids: [],
  used_acp_ids: [],
  used_limit_ids: [],          // только для систем
  systemType: 'house'          // 'house' | 'rooms'
})
const isEditingFormula = ref(false)

// UI
const showMathHelper = ref(false)
const mathTarget = ref('')
const mathTargetEquationIdx = ref(null)
const mathSymbols = ['√', '^', 'sin', 'cos', 'tan', 'log', '(', ')', '+', '-', '*', '/', '>', '<', '=', 'π', 'e']
const paramFilter = ref('all')

// ==========================================
// 🧮 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
// ==========================================

// ✅ ИСПРАВЛЕННАЯ ФУНКЦИЯ: теперь использует map/join вместо for...in
function getusingParams(f) {
  if (!f?.used_input_ids?.length) return ''
  
  return f.used_input_ids
    .map(id => {
      const param = parameters.value.find(p => p.id === id)
      return param?.varName || `ID:${id}`
    })
    .filter(Boolean)
    .join(', ')
}

const selectedMethod = computed(() => availableMethods.value.find(m => m?.id === paramForm.methodId))

function methodTypeLabel(type) {
  const map = { 
    nothing: 'Без параметров', 
    rooms: 'По типу комнаты', 
    furniture: 'По типу мебели', 
    roomsfurniture: 'Комната + Мебель' 
  }
  return map[type] || '—'
}

const getRoomLabel = (id) => {
  if (!id) return '—'
  return roomTypes.value.find(r => r.id === id)?.label || `ID:${id}`
}

const getFurnitureLabel = (id) => {
  if (!id) return '—'
  return furnitureTypes.value.find(f => f.id === id)?.label || `ID:${id}`
}

const getRoomLabels = (ids) => {
  if (!ids || !Array.isArray(ids) || ids.length === 0) return '—'
  return ids.map(id => roomTypes.value.find(r => r.id === id)?.label || `ID:${id}`).join(', ')
}

function onMethodChange() {
  paramForm.room_type_id = null
  paramForm.furniture_type_id = null
}

function toggleRoomChip(id) {
  const idx = paramForm.roomTypeIds.indexOf(id)
  idx === -1 ? paramForm.roomTypeIds.push(id) : paramForm.roomTypeIds.splice(idx, 1)
}

function toggleFormulaRoomChip(id) {
  const idx = formulaForm.room_type_ids.indexOf(id)
  idx === -1 ? formulaForm.room_type_ids.push(id) : formulaForm.room_type_ids.splice(idx, 1)
}

function toggleSystemRoomChip(id) {
  const idx = formulaForm.for_room_types_ids.indexOf(id)
  idx === -1 ? formulaForm.for_room_types_ids.push(id) : formulaForm.for_room_types_ids.splice(idx, 1)
}

function toggleSystemLimit(id) {
  const idx = formulaForm.used_limit_ids.indexOf(id)
  idx === -1 ? formulaForm.used_limit_ids.push(id) : formulaForm.used_limit_ids.splice(idx, 1)
}

function openMathHelper(field) { mathTarget.value = field; showMathHelper.value = true }
function openMathHelperForEquation(idx, part) { mathTargetEquationIdx.value = idx; mathTarget.value = part; showMathHelper.value = true }

function insertMath(sym) {
  if (!mathTarget.value) return
  if (mathTargetEquationIdx.value !== null) {
    const eq = formulaForm.equations[mathTargetEquationIdx.value]
    mathTarget.value === 'left' ? eq.left += sym : eq.right += sym
  } else {
    formulaForm[mathTarget.value] += sym
  }
}

// 🔹 Нормализация данных из API
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
    // ✅ ИСПРАВЛЕНО: читаем camelCase как отправляет бэкенд
    methodId: p.methodId,      // было: p.method_id
    methodName: p.methodName,  // было: p.special_method_name
    methodType: p.methodType,  // было: (не было)
    room_type_id: p.room_type_id,
    furniture_type_id: p.furniture_type_id,
  }
}

function normalizeLimitParam(p) {
  return {
    id: p.id,
    symbol: p.symbol || p.varName || '',
    label: p.label || '',
    type: p.type || 'universal',
    universalValue: p.universalValue ?? p.value,
    roomValues: p.room_values || p.roomValues || [],
    paramType: 'limit',
    isLimit: true,
    cryteria_id: p.cryteria_id  // ✅ ДОБАВЛЕНО: передаём ID критерия
  }
}

// 🔹 Фильтрация доступных параметров — ИСПРАВЛЕННАЯ ВЕРСИЯ
const filteredAvailableParams = computed(() => {
  const filter = paramFilter.value
  const isSystem = formulaForm.objType === 'system'
  
  // Объединяем все параметры в один массив с меткой типа
  const allParams = [
    ...parameters.value.map(p => ({ ...p, paramType: p.inputType === 'auto' ? 'acp' : 'input' })),
    ...(isSystem ? limitParams.value.map(p => ({ ...p, paramType: 'limit', isLimit: true })) : [])
  ]
  
  // Фильтруем по выбранному типу
  let items = allParams.filter(p => {
    if (filter === 'all') return true
    if (filter === 'manual') return p.paramType === 'input' && p.inputType === 'manual'
    if (filter === 'auto') return p.paramType === 'acp'
    if (filter === 'limit') return p.paramType === 'limit'
    return true
  })
  
  // Убираем дубликаты по ID
  const seen = new Set()
  return items.filter(p => {
    if (seen.has(p.id)) return false
    seen.add(p.id)
    return true
  })
})

// 🔹 Проверка: выбран ли параметр
function isParamSelected(p) {
  if (!p?.id) return false
  if (p.paramType === 'input') return formulaForm.used_input_ids.includes(p.id)
  if (p.paramType === 'acp') return formulaForm.used_acp_ids.includes(p.id)
  if (p.paramType === 'limit') return formulaForm.used_limit_ids.includes(p.id)
  return false
}

// 🔹 Метка типа параметра
function getParamTypeLabel(p) {
  if (!p) return '—'
  if (p.paramType === 'limit') return 'Лимит'
  if (p.paramType === 'acp') return 'Авто'
  return p.inputType === 'manual' ? 'Ручной' : 'Авто'
}

// 🔹 Проверка валидности лимита
function isParamInvalid(p) {
  if (
    p.paramType === 'limit' && 
    p.type === 'byRoom' && 
    formulaForm.objType === 'system' && 
    formulaForm.systemType === 'rooms'
  ) {
    const systemRooms = new Set(formulaForm.for_room_types_ids || [])
    const limitRooms = new Set(p.roomValues?.map(rv => rv.roomId) || [])
    if (systemRooms.size > 0 && limitRooms.size > 0) {
      const hasOverlap = [...systemRooms].some(id => limitRooms.has(id))
      return !hasOverlap
    }
  }
  return false
}

// 🔹 Переключение параметров
function toggleUsedParam(p) {
  if (!p?.id) return
  if (p.paramType === 'input') {
    const idx = formulaForm.used_input_ids.indexOf(p.id)
    idx === -1 ? formulaForm.used_input_ids.push(p.id) : formulaForm.used_input_ids.splice(idx, 1)
  } else if (p.paramType === 'acp') {
    const idx = formulaForm.used_acp_ids.indexOf(p.id)
    idx === -1 ? formulaForm.used_acp_ids.push(p.id) : formulaForm.used_acp_ids.splice(idx, 1)
  } else if (p.paramType === 'limit') {
    const idx = formulaForm.used_limit_ids.indexOf(p.id)
    idx === -1 ? formulaForm.used_limit_ids.push(p.id) : formulaForm.used_limit_ids.splice(idx, 1)
  }
}

// ==========================================
// 📡 ЗАГРУЗКА ДАННЫХ
// ==========================================

async function loadFormulas() {
  try {
    const res = await apiClient.get(roomAnalyticsEndpoints.roomAnalytics.FormulasList, 
    { criterion_id: criterionId.value }
    )
    formulas.value = res.data || []
  } catch (e) { 
    console.error('❌ Ошибка загрузки формул:', e)
    formulas.value = [] 
  }
}

async function loadParameters() {
  try {
    const params = await apiClient.get(roomAnalyticsEndpoints.roomAnalytics.ParamsList, {criteria_id: criterionId.value })
    parameters.value = (params.data || []).map(normalizeInputParam)
  } catch (error) {
    console.error('❌ Ошибка загрузки параметров:', error)
    parameters.value = []
  }
}

async function loadLimitParams() {
  try {
    const res = await apiClient.get(roomAnalyticsEndpoints.roomAnalytics.LimitParamsList, { criteria_id: criterionId.value })
    limitParams.value = (res.data || []).map(normalizeLimitParam)
  } catch (error) {
    console.error('❌ Ошибка загрузки ограничений:', error)
    limitParams.value = []
  }
}

async function loadReferenceData() {
  try {
    const [rooms, furniture, methods] = await Promise.all([
      apiClient.get(roomAnalyticsEndpoints.roomAnalytics.RoomTypesList),
      apiClient.get(roomAnalyticsEndpoints.roomAnalytics.FurnitureTypesList),
      apiClient.get(roomAnalyticsEndpoints.roomAnalytics.SpecialMethodList)
    ])
    roomTypes.value = rooms.data || []
    furnitureTypes.value = furniture.data || []
    availableMethods.value = methods.data || []
  } catch (error) {
    console.error('❌ Ошибка загрузки справочников:', error)
  }
}

onMounted(async () => {
  await loadReferenceData()
  await Promise.all([
    loadParameters(),
    loadLimitParams(),
    loadFormulas()
  ])
})

// ==========================================
// 🔹 ПАРАМЕТРЫ: CRUD
// ==========================================

function mapApiToForm(p) {
  return {
    id: p.id, varName: p.varName || p.symbol, label: p.label,
    scope: p.cryteria_id ? 'current' : 'global',
    inputType: p.inputType || 'manual', paramType: p.paramType || 'global',
    roomTypeIds: p.roomTypeIds || p.room_type_ids || [], 
    minVal: p.minVal ?? p.min_value ?? 0, 
    maxVal: p.maxVal ?? p.max_value ?? 100,
    methodId: p.methodId || p.method_id, 
    room_type_id: p.room_type_id, 
    furniture_type_id: p.furniture_type_id
  }
}

function editParam(p) {
  Object.assign(paramForm, mapApiToForm(p))
  isEditingParam.value = true
}

function resetParamForm() {
  Object.assign(paramForm, {
    id: null, varName: '', label: '', scope: 'current', inputType: 'manual',
    minVal: 0, maxVal: 100, methodId: null, paramType: 'global',
    roomTypeIds: [], room_type_id: null, furniture_type_id: null
  })
  isEditingParam.value = false
}
function cancelEditParam() { resetParamForm() }

async function deleteParam(id) {
  try {
    await apiClient.delete(roomAnalyticsEndpoints.roomAnalytics.ParamDetail(id))
    await loadParameters()
  } catch (error) {
    console.error('❌ Ошибка удаления:', error)
    alert('Не удалось удалить параметр')
  }
}

async function saveParam() {
  if (!paramForm.varName?.trim() || !paramForm.label?.trim()) return alert('Заполните обозначение и метку')
  if (paramForm.inputType === 'manual') {
    if (paramForm.minVal === null || paramForm.maxVal === null) return alert('Укажите min/max')
    if (paramForm.paramType === 'rooms' && paramForm.roomTypeIds.length === 0) return alert('Выберите хотя бы одну комнату')
  }
  if (paramForm.inputType === 'auto' && !paramForm.methodId) return alert('Выберите метод')

  try {
    const payload = {
      varName: paramForm.varName.trim(), 
      label: paramForm.label.trim(),
      cryteria_id: paramForm.scope === 'global' ? null : (paramForm.cryteria_id || criterionId.value),
      inputType: paramForm.inputType
    }
    
    if (paramForm.inputType === 'manual') {
      payload.minVal = Number(paramForm.minVal)
      payload.maxVal = Number(paramForm.maxVal)
      payload.paramType = paramForm.paramType
      payload.room_type_ids = paramForm.roomTypeIds
    } else {
      payload.methodId = paramForm.methodId
      payload.room_type_id = paramForm.room_type_id
      payload.furniture_type_id = paramForm.furniture_type_id
    }

    if (isEditingParam.value && paramForm.id) {
      await apiClient.put(roomAnalyticsEndpoints.roomAnalytics.ParamDetail(paramForm.id), payload)
    } else {
      await apiClient.post(roomAnalyticsEndpoints.roomAnalytics.ParamsList, payload)
    }
    await loadParameters()
    resetParamForm()
    alert('✅ Параметр сохранён')
  } catch (error) {
    console.error('❌ Ошибка:', error)
    alert(error.response?.data?.error || 'Не удалось сохранить')
  }
}

// ==========================================
// 🔹 ОГРАНИЧЕНИЯ: CRUD
// ==========================================

function mapApiToConstraintForm(c) {
  const cid = c.criterion_id ?? c.cryteria_id
  return {
    id: c.id, symbol: c.symbol, label: c.label, type: c.type,
    scope: cid ? 'current' : 'global', // ← восстановление UI-состояния
    universalValue: c.universalValue ?? c.value ?? 0,
    roomValues: c.roomValues?.map(rv => ({...rv})) || [],
    criterion_id: cid || null
  }
}
function addRoomValue() {
  if (!roomValForm.roomId) return alert('Выберите комнату')

  // ✅ Разрешаем дубликат только если это та же комната, которую мы редактируем
  const isDuplicate = constraintForm.roomValues.some(
    (rv, idx) => rv.roomId === roomValForm.roomId && idx !== editingRoomValIdx.value
  )
  if (isDuplicate) return alert('Эта комната уже добавлена в список')

  if (editingRoomValIdx.value !== null) {
    constraintForm.roomValues[editingRoomValIdx.value] = { ...roomValForm }
    editingRoomValIdx.value = null
  } else {
    constraintForm.roomValues.push({ roomId: roomValForm.roomId, value: Number(roomValForm.value) })
  }
  
  roomValForm.roomId = null
  roomValForm.value = 0
}

function startEditRoomVal(idx) {
  editingRoomValIdx.value = idx
  Object.assign(roomValForm, constraintForm.roomValues[idx])
}

function removeRoomVal(idx) {
  constraintForm.roomValues.splice(idx, 1)  // ✅ Реактивность сработает сама
  if (editingRoomValIdx.value === idx) {
    editingRoomValIdx.value = null
    roomValForm.roomId = null
    roomValForm.value = 0
  }
}

function editConstraint(c) {
  Object.assign(constraintForm, mapApiToConstraintForm(c))
  isEditingConstraint.value = true
}

function resetConstraintForm() {
  Object.assign(constraintForm, { 
    id: null, symbol: '', label: '', type: 'universal', scope: 'current',
    universalValue: 0, roomValues: [],  // ✅ Явно очищаем массив
    criterion_id: criterionId.value || null
  })
  Object.assign(roomValForm, { roomId: null, value: 0 })
  editingRoomValIdx.value = null
  isEditingConstraint.value = false
}
function cancelEditConstraint() { resetConstraintForm() }

async function saveLimitParam() {
  if (!constraintForm.symbol?.trim() || !constraintForm.label?.trim()) return alert('Заполните символ и метку')
  if (constraintForm.type === 'universal' && !constraintForm.universalValue) return alert('Укажите значение')
  if (constraintForm.type === 'byRoom' && constraintForm.roomValues.length === 0) return alert('Добавьте значения по комнатам')

  try {
    const payload = {
        symbol: constraintForm.symbol.trim(), 
        label: constraintForm.label.trim(),
        type: constraintForm.type, 
        // ✅ ИСПРАВЛЕНО: cryteria_id (как в модели), а не criterion_id
        cryteria_id: constraintForm.criterion_id,
        // ✅ universal_value — snake_case, как ждёт бэкенд
        universal_value: Number(constraintForm.universalValue),
        // ✅ ИСПРАВЛЕНО: roomValues (camelCase) и ключи внутри — roomId (camelCase)
        roomValues: constraintForm.roomValues.map(rv => ({ 
          roomId: rv.roomId,  // ✅ camelCase ключ
          value: Number(rv.value) 
        }))
    }
    
    if (isEditingConstraint.value && constraintForm.id) {
      await apiClient.put(roomAnalyticsEndpoints.roomAnalytics.LimitParamDetail(constraintForm.id), payload)
    } else {
      await apiClient.post(roomAnalyticsEndpoints.roomAnalytics.LimitParamsList, payload)
    }
    await loadLimitParams()
    resetConstraintForm()
    alert('✅ Ограничение сохранено')
  } catch (error) {
    console.error('❌ Ошибка:', error)
    alert(error.response?.data?.error || 'Не удалось сохранить')
  }
}

async function deleteConstraint(id) {
  try {
    await apiClient.delete(roomAnalyticsEndpoints.roomAnalytics.LimitParamDetail(id))
    await loadLimitParams()
  } catch (error) {
    console.error('❌ Ошибка удаления:', error)
    alert('Не удалось удалить ограничение')
  }
}

// ==========================================
// 🔹 ФОРМУЛЫ: CRUD
// ==========================================

function addEquation() { 
  formulaForm.equations.push({ left: '', right: '', recommendation: '' }) 
}
function removeEquation(idx) { formulaForm.equations.splice(idx, 1) }

function resetFormulaForm() {
  const keepType = formulaForm.objType
  Object.assign(formulaForm, { 
    id: null, objType: keepType, equation: '', 
    equations: [{ left: '', right: '', recommendation: '' }],
    type: 'global', recommendation: '', value_recomm: null, 
    room_type_ids: [],
    for_room_types_ids: [],
    used_input_ids: [], used_acp_ids: [], used_limit_ids: [],
    systemType: 'house'
  })
  isEditingFormula.value = false
}
function cancelEditFormula() { resetFormulaForm() }

async function saveFormula() {
  if (formulaForm.objType === 'single' && !formulaForm.equation.trim()) return alert('Введите уравнение')
  if (formulaForm.objType === 'system' && formulaForm.equations.length === 0) return alert('Добавьте уравнения')
  if (formulaForm.used_input_ids.length === 0 && formulaForm.used_acp_ids.length === 0) return alert('Выберите хотя бы один параметр')

  const payload = {
    objType: formulaForm.objType,
    criterion_id: criterionId.value, // ✅ Обязательно!
    type: formulaForm.type,
    recommendation: formulaForm.recommendation, 
    value_recomm: formulaForm.value_recomm,
    used_input_ids: formulaForm.used_input_ids, 
    used_acp_ids: formulaForm.used_acp_ids
  }

  if (formulaForm.objType === 'single') {
    payload.equation = formulaForm.equation
    // Для обычных формул типа 'rooms' — комнаты в room_type_ids
    if (formulaForm.type === 'rooms') {
      payload.for_room_types_ids = formulaForm.room_type_ids
    }
  } else {
    // Для систем
    payload.systemType = formulaForm.systemType
    payload.equations = formulaForm.equations.map(eq => ({
      left: eq.left, right: eq.right, recommendation: eq.recommendation
      // ❌ limit_ids и room_type_ids больше не в уравнениях!
    }))
    // Лимиты и комнаты — на уровне системы
    payload.used_limit_ids = formulaForm.used_limit_ids
    if (formulaForm.systemType === 'rooms') {
      payload.for_room_types_ids = formulaForm.for_room_types_ids
    }
  }

  try {
    if (isEditingFormula.value && formulaForm.id) {
      await apiClient.put(roomAnalyticsEndpoints.roomAnalytics.FormulaDetail(formulaForm.id), payload)
    } else {
      await apiClient.post(roomAnalyticsEndpoints.roomAnalytics.FormulasList, payload)
    }
    await loadFormulas()
    resetFormulaForm()
    alert('✅ Сохранено')
  } catch (e) { 
    console.error('❌ Ошибка сохранения формулы:', e)
    alert(e.response?.data?.error || 'Ошибка') 
  }
}

function editFormula(f) {
  Object.assign(formulaForm, {
    id: f.id, 
    objType: f.objType, 
    type: f.type || 'global',
    recommendation: f.recommendation || '', 
    value_recomm: f.value_recomm,
    room_type_ids: f.room_type_ids || [],
    for_room_types_ids: f.for_room_types_ids || [],  // для систем
    used_input_ids: f.used_input_ids || [], 
    used_acp_ids: f.used_acp_ids || [],
    used_limit_ids: f.used_limit_ids || [],          // для систем
    systemType: f.systemType || 'house',             // для систем
    equation: f.equation || '',
    equations: f.equations?.map(eq => ({
      left: eq.left || '', right: eq.right || '', recommendation: eq.recommendation || ''
    })) || [{ left: '', right: '', recommendation: '' }]
  })
  isEditingFormula.value = true
}

async function deleteFormula(id) {
  try {
    await apiClient.delete(roomAnalyticsEndpoints.roomAnalytics.FormulaDetail(id))
    await loadFormulas()
    alert('✅ Удалено')
  } catch (e) { 
    console.error('❌ Ошибка удаления:', e)
    alert('Ошибка удаления') 
  }
}



const availableRoomOptions = computed(() => {
  // ID всех комнат, которые уже есть в таблице
  const existingIds = constraintForm.roomValues.map(rv => rv.roomId)

  // Если сейчас редактируем конкретную строку
  if (editingRoomValIdx.value !== null) {
    const editingId = constraintForm.roomValues[editingRoomValIdx.value].roomId
    // Показываем: (свободные комнаты) ИЛИ (ту, которую редактируем)
    return roomTypes.value.filter(rt => 
      !existingIds.includes(rt.id) || rt.id === editingId
    )
  }

  // Если добавляем новую строку — только свободные
  return roomTypes.value.filter(rt => !existingIds.includes(rt.id))
})

watch(
  () => constraintForm.type,
  (newVal) => {
    if (newVal === 'universal') {
      constraintForm.roomValues = []  // Очищаем список комнат
      roomValForm.roomId = null       // Сбрасываем выбранный в селекте
    }
  }
)

</script>

<style scoped>
.form-label { font-weight: 500; font-size: 0.9rem; }
code { background: #f8f9fa; padding: 2px 6px; border-radius: 4px; font-size: 0.85em; color: #d63384; }
.table th { white-space: nowrap; }
.btn-xs { padding: 0.15rem 0.4rem; font-size: 0.75rem; }
.card-header { background-color: #f8f9fa; }
.list-group-item { cursor: pointer; transition: background 0.2s; }
.list-group-item:hover { background-color: #f8f9fa; }
.position-sticky { position: sticky; }
</style>