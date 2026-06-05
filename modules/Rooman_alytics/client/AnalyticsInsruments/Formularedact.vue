<template>
  <div class="container-fluid py-4 bg-light min-vh-100">
    <h2 class="mb-4 text-center fw-bold">Управление критериями и параметрами</h2>

    <!-- ═══════════════════════════════════════════════════════════════
         КАРТОЧКА 1: Параметры расчёта
    ═══════════════════════════════════════════════════════════════ -->
    <div class="card shadow-sm mb-4">
      <div class="card-header text-white d-flex justify-content-between align-items-center"
           :style="{ backgroundColor: criterionColor }">
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
            <label class="form-label">Название параметра</label>
            <input v-model="paramForm.label" type="text" class="form-control" placeholder="Температура в комнате" />
          </div>
          <div class="col-md-2">
            <label class="form-label">Статус</label>
            <div class="form-check form-switch mt-2">
              <input
                class="form-check-input"
                type="checkbox"
                id="paramActiveSwitch"
                v-model="paramForm.isActive"
              />
              <label class="form-check-label" for="paramActiveSwitch">
                {{ paramForm.isActive ? 'Активен' : 'Неактивен' }}
              </label>
            </div>
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
        </div>

        <!-- Ручной ввод -->
        <div v-if="paramForm.inputType === 'manual'" class="row g-3 mb-3 p-3 bg-light rounded">
          <div class="col-md-3">
            <label class="form-label">Применимость</label>
            <select v-model="paramForm.paramType" class="form-select">
              <option value="global">Все комнаты</option>
              <option value="rooms">Выбранные комнаты</option>
            </select>
          </div>
          <div class="col-md-3">
            <label class="form-label">Мин. значение</label>
            <input v-model.number="paramForm.minVal" type="number" class="form-control" />
          </div>
          <div class="col-md-3">
            <label class="form-label">Макс. значение</label>
            <input v-model.number="paramForm.maxVal" type="number" class="form-control" />
          </div>
        </div>

        <!-- Выбор комнат для ручного параметра типа rooms -->
        <div v-if="paramForm.inputType === 'manual' && paramForm.paramType === 'rooms'" class="mb-3">
          <label class="form-label fw-bold mb-2">Выберите типы комнат:</label>
          <div class="d-flex flex-wrap gap-2">
            <button
              v-for="rt in roomTypes"
              :key="rt.id"
              type="button"
              class="btn btn-sm rounded-pill px-3 py-2"
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

        <!-- Автоматический расчёт -->
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

        <div class="d-flex gap-2 mb-4">
          <button class="btn btn-primary" @click="saveParam">
            {{ isEditingParam ? '💾 Обновить параметр' : '➕ Добавить параметр' }}
          </button>
          <button class="btn btn-secondary" @click="resetParamForm">Очистить</button>
        </div>

        <!-- Таблица параметров -->
        <div class="table-responsive">
          <table class="table table-hover table-bordered align-middle">
            <thead class="table-light">
              <tr>
                <th>Переменная</th>
                <th>Название</th>
                <th>Область</th>
                <th>Ввод</th>
                <th>Детали</th>
                <th style="width: 100px;">Статус</th>
                <th style="width: 120px;">Действия</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in parameters" :key="p.id" :class="{ 'inactive-row': !p.isActive }">
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
              <tr v-if="!parameters.length">
                <td colspan="7" class="text-center text-muted">Параметры не добавлены</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════════════════════════
         КАРТОЧКА 2: Параметры ограничения
    ═══════════════════════════════════════════════════════════════ -->
    <div class="card shadow-sm mb-4">
      <div class="card-header text-white d-flex justify-content-between align-items-center"
           :style="{ backgroundColor: criterionColor }">
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
            <label class="form-label">Название</label>
            <input v-model="constraintForm.label" type="text" class="form-control" placeholder="Мин. поток" />
          </div>
          <div class="col-md-2">
            <label class="form-label">Область действия</label>
            <select v-model="constraintForm.scope" class="form-select" @change="syncCriterionId">
              <option value="current">Для текущего критерия</option>
              <option value="global">Для всех критериев</option>
            </select>
          </div>
          <div class="col-md-2">
            <label class="form-label">Тип ограничения</label>
            <select v-model="constraintForm.type" class="form-select">
              <option value="universal">Универсальный</option>
              <option value="byRoom">По типу комнаты</option>
            </select>
          </div>
          <div class="col-md-2">
            <label class="form-label">Статус</label>
            <div class="form-check form-switch mt-2">
              <input
                class="form-check-input"
                type="checkbox"
                id="constraintActiveSwitch"
                v-model="constraintForm.isActive"
              />
              <label class="form-check-label" for="constraintActiveSwitch">
                {{ constraintForm.isActive ? 'Активен' : 'Неактивен' }}
              </label>
            </div>
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
            <thead>
              <tr>
                <th>Комната</th>
                <th>Значение</th>
                <th style="width:80px">Действия</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(rv, idx) in constraintForm.roomValues" :key="idx">
                <td>{{ getRoomLabel(rv.roomId) }}</td>
                <td>{{ rv.value }}</td>
                <td>
                  <button class="btn btn-xs btn-outline-warning me-1" @click="startEditRoomVal(idx)">Ред.</button>
                  <button class="btn btn-xs btn-outline-danger" @click="removeRoomVal(idx)">X</button>
                </td>
              </tr>
              <tr v-if="!constraintForm.roomValues.length">
                <td colspan="3" class="text-center text-muted small">Нет значений</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="d-flex gap-2 mb-4">
          <button class="btn btn-success" @click="saveLimitParam">
            {{ isEditingConstraint ? '💾 Обновить ограничение' : '➕ Добавить ограничение' }}
          </button>
          <button class="btn btn-secondary" @click="resetConstraintForm">Очистить</button>
        </div>

        <!-- Таблица ограничений -->
        <div class="table-responsive">
          <table class="table table-hover table-bordered align-middle">
            <thead class="table-light">
              <tr>
                <th>Символ</th>
                <th>Название</th>
                <th>Тип</th>
                <th>Область действия</th>
                <th>Значения</th>
                <th style="width: 100px;">Статус</th>
                <th style="width: 120px;">Действия</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="c in limitParams" :key="c.id" :class="{ 'inactive-row': !c.isActive }">
                <td><code>{{ c.symbol }}</code></td>
                <td>{{ c.label }}</td>
                <td>{{ c.type === 'universal' ? 'Универсальный' : 'По комнате' }}</td>
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
                <td class="text-center">
                  <span class="badge" :class="c.isActive ? 'bg-success' : 'bg-secondary'">
                    {{ c.isActive ? 'Активен' : 'Выкл' }}
                  </span>
                </td>
                <td>
                  <button class="btn btn-sm btn-outline-warning me-1" @click="editConstraint(c)">Ред.</button>
                  <button class="btn btn-sm btn-outline-danger" @click="deleteConstraint(c.id)">X</button>
                </td>
              </tr>
              <tr v-if="!limitParams.length">
                <td colspan="7" class="text-center text-muted">Ограничения не добавлены</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════════════════════════
         КАРТОЧКА 3: Формулы и системы уравнений
    ═══════════════════════════════════════════════════════════════ -->
    <div class="card shadow-sm mb-4">
      <div class="card-header text-white d-flex justify-content-between align-items-center"
           :style="{ backgroundColor: criterionColor }">
        <span class="fw-bold">Формулы и системы уравнений</span>
        <button v-if="isEditingFormula" class="btn btn-sm btn-light" @click="cancelEditFormula">Отменить</button>
      </div>

      <div class="card-body">
        <!-- Верхняя панель -->
        <div class="row g-3 align-items-end mb-3">
          <div class="col-md-3">
            <label class="form-label fw-bold mb-1 small">Название</label>
            <input
              v-model="formulaForm.name"
              type="text"
              class="form-control form-control-sm"
              placeholder="Например: Расчёт освещённости"
            />
          </div>
          <div class="col-md-2">
            <label class="form-label fw-bold mb-1 small">Тип объекта</label>
            <select v-model="formulaForm.objType" class="form-select form-select-sm" :disabled="isEditingFormula">
              <option value="single">Обычная формула</option>
              <option value="system">Система уравнений</option>
            </select>
          </div>
          <div class="col-md-3">
            <label class="form-label fw-bold mb-1 small">Область применения</label>
            <div class="btn-group w-100">
              <button type="button" class="btn btn-sm"
                :class="formulaForm.type === 'global' ? 'btn-primary text-white' : 'btn-outline-secondary'"
                @click="formulaForm.type = 'global'; formulaForm.for_room_types_ids = []">
                Все помещение
              </button>
              <button type="button" class="btn btn-sm"
                :class="formulaForm.type === 'rooms' ? 'btn-primary text-white' : 'btn-outline-secondary'"
                @click="formulaForm.type = 'rooms'">
                Выбранные комнаты
              </button>
            </div>
          </div>
          <div class="col-md-2">
            <label class="form-label fw-bold mb-1 small">Статус</label>
            <div class="form-check form-switch mt-2">
              <input
                class="form-check-input"
                type="checkbox"
                id="formulaActiveSwitch"
                v-model="formulaForm.isActive"
              />
              <label class="form-check-label" for="formulaActiveSwitch">
                {{ formulaForm.isActive ? 'Активна' : 'Неактивна' }}
              </label>
            </div>
          </div>
          <div class="col-md-auto ms-auto d-flex gap-2">
            <button class="btn btn-sm btn-secondary" @click="resetFormulaForm">Очистить</button>
            <button class="btn btn-sm btn-info text-white px-3" @click="saveFormula" :disabled="formulaForm.objType === 'system' && !formulaForm.equations.length">
              {{ isEditingFormula ? 'Обновить' : 'Добавить' }}
            </button>
          </div>
        </div>

        <div v-if="formulaForm.type === 'rooms'" class="mb-3">
          <label class="form-label fw-bold mb-1 small">Типы комнат:</label>
          <div class="d-flex flex-wrap gap-2">
            <button
              v-for="rt in roomTypes"
              :key="rt.id"
              type="button"
              class="btn btn-xs rounded-pill px-2 py-1"
              :class="formulaForm.for_room_types_ids.includes(rt.id) ? 'btn-primary text-white' : 'btn-outline-secondary'"
              @click="toggleFormulaRoomChip(rt.id)"
            >
              {{ rt.label }} <span v-if="formulaForm.for_room_types_ids.includes(rt.id)">✓</span>
            </button>
          </div>
        </div>

        <!-- Основной контент: 2 колонки -->
        <div class="row g-4">
          <!-- Левая колонка: Ввод выражений -->
          <div class="col-md-6">
            <div class="card h-100 border-0 shadow-sm">
              <div class="card-header bg-light py-2 fw-bold small">Ввод выражений</div>
              <div class="card-body p-3">

                <!-- Одиночная формула -->
                <div v-if="formulaForm.objType === 'single'" class="position-relative">
                  <label class="form-label small fw-bold">Уравнение</label>
                  <div class="input-group mb-2">
                    <input v-model="formulaForm.equation" type="text" class="form-control form-control-sm" placeholder="Q = A * B" />
                    <button class="btn btn-outline-secondary btn-sm" type="button" @click="openMathHelper('equation')">🧮</button>
                  </div>

                  <div v-if="showMathHelper && mathTarget === 'equation'" class="math-helper-box p-2 bg-white border rounded shadow-sm mb-2">
                    <div class="d-flex flex-wrap gap-1 align-items-center">
                      <button v-for="sym in mathSymbols" :key="sym" class="btn btn-xs btn-outline-dark" @click="insertMath(sym)">{{ sym }}</button>
                      <button class="btn btn-xs btn-danger ms-auto" @click="showMathHelper = false">✕</button>
                    </div>
                  </div>

                  <div class="row g-2 mb-2">
                    <div class="col-6">
                      <label class="form-label small fw-bold">Порог для рекомендации</label>
                      <input v-model.number="formulaForm.value_recomm" type="number" class="form-control form-control-sm" placeholder="0.00" />
                    </div>
                    <div class="col-12">
                      <label class="form-label small fw-bold">Рекомендация</label>
                      <textarea v-model="formulaForm.recommendation" class="form-control form-control-sm" rows="2" placeholder="Пояснение..."></textarea>
                    </div>
                  </div>
                </div>

                <!-- Система уравнений -->
                <div v-else>
                  <div class="d-flex justify-content-between align-items-center mb-2">
                    <span class="small fw-bold text-muted">Уравнения системы</span>
                    <button class="btn btn-xs btn-success" @click="addEquation">+ Добавить</button>
                  </div>

                  <div v-for="(eq, idx) in formulaForm.equations" :key="idx" class="card mb-2 border-start border-3 border-info bg-white">
                    <div class="card-header py-1 px-2 d-flex justify-content-between align-items-center bg-transparent border-0">
                      <small class="fw-bold text-info">Уравнение #{{ idx + 1 }}</small>
                      <button class="btn btn-xs btn-outline-danger py-0 px-1" @click="removeEquation(idx)">🗑️</button>
                    </div>
                    <div class="card-body py-2 position-relative">
                      <div class="row g-1 mb-1">
                        <div class="col-5">
                          <div class="input-group input-group-sm">
                            <input v-model="eq.limit_equastion" type="text" class="form-control" placeholder="Условие" />
                            <button class="btn btn-outline-secondary btn-sm" @click="openMathHelperForEquation(idx, 'limit_equastion')">🧮</button>
                          </div>
                        </div>
                        <div class="col-5">
                          <div class="input-group input-group-sm">
                            <input v-model="eq.equastion" type="text" class="form-control" placeholder="Уравнение" />
                            <button class="btn btn-outline-secondary btn-sm" @click="openMathHelperForEquation(idx, 'equastion')">🧮</button>
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

                  <div v-if="!formulaForm.equations.length" class="alert alert-warning py-2 small mb-0">Добавьте хотя бы одно уравнение</div>
                </div>
              </div>
            </div>
          </div>

          <!-- Правая колонка: Выбор параметров -->
          <div class="col-md-6">
            <div class="card h-100 border-0 shadow-sm">
              <div class="card-header bg-light py-2 fw-bold small">Используемые параметры</div>
              <div class="card-body p-3">

                <div class="btn-group mb-2 w-100" role="group">
                  <button type="button" class="btn btn-sm flex-fill" :class="paramFilter === 'manual' ? 'btn-success text-white' : 'btn-outline-success'" @click="paramFilter = 'manual'">Ручной</button>
                  <button type="button" class="btn btn-sm flex-fill" :class="paramFilter === 'auto' ? 'btn-info text-white' : 'btn-outline-info'" @click="paramFilter = 'auto'">Авто</button>
                  <button v-if="formulaForm.objType === 'system'" type="button" class="btn btn-sm flex-fill" :class="paramFilter === 'limit' ? 'btn-warning text-white' : 'btn-outline-warning'" @click="paramFilter = 'limit'">Лимиты</button>
                </div>

                <div class="list-group" style="max-height: 320px; overflow-y: auto;">
                  <div v-for="p in filteredAvailableParams" :key="p.id" class="list-group-item list-group-item-action d-flex align-items-center py-2 px-2" :class="{ 'bg-warning bg-opacity-10': isParamInvalid(p) }">
                    <div class="form-check flex-grow-1 m-0">
                      <input class="form-check-input mt-0" type="checkbox" :id="'p-'+p.id" :checked="isParamSelected(p)" @change="toggleUsedParam(p)">
                      <label class="form-check-label w-100 ps-2 small" :for="'p-'+p.id">
                        <div class="d-flex justify-content-between align-items-center">
                          <span><code class="me-2">{{ p.varName || p.symbol }}</code> {{ p.label }}</span>
                          <span class="badge bg-secondary ms-1" style="font-size: 0.7rem;">{{ getParamTypeLabel(p) }}</span>
                        </div>
                        <small v-if="isParamInvalid(p)" class="text-danger d-block mt-1">⚠️ Конфликт комнат</small>
                      </label>
                    </div>
                  </div>

                  <div v-if="paramFilter === 'all' || !paramFilter" class="text-center text-muted py-4 small">
                    Выберите категорию параметров
                  </div>

                  <div v-else-if="!filteredAvailableParams.length" class="text-center text-muted py-4 small">
                    Нет доступных параметров для выбранной категории
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Таблица формул -->
        <div class="table-responsive mt-4">
          <table class="table table-hover table-bordered align-middle table-sm">
            <thead class="table-light">
              <tr>
                <th style="width: 80px;">Тип</th>
                <th>Название</th>
                <th>Формула расчета</th>
                <th style="width: 100px;">Область</th>
                <th style="width: 120px;">Комнаты</th>
                <th>Параметры</th>
                <th style="width: 25%;">Рекомендации</th>
                <th style="width: 90px;">Статус</th>
                <th style="width: 80px;">Действия</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="f in formulas" :key="f.id" :class="{ 'inactive-row': !f.isActive }">
                <td>
                  <span class="badge" :class="f.objType === 'single' ? 'bg-primary' : 'bg-dark'">
                    {{ f.objType === 'single' ? 'Формула' : 'Система' }}
                  </span>
                </td>
                <td>
                  <strong>{{ f.name || '—' }}</strong>
                </td>
                <td class="small">
                  <div v-if="f.objType === 'single'"><span class="text-info">{{ f.equation }}</span></div>
                  <div v-else>
                    <div v-for="(eq, i) in f.equations" :key="i" class="mb-1 border-bottom pb-1">
                      <span>При <span class="text-warning">{{ eq.limit_equastion }}</span> формула: <span class="text-info">{{ eq.equastion }}</span></span>
                    </div>
                  </div>
                </td>
                <td class="small">
                  {{ f.type === 'global' ? 'Все помещение' : 'Выборочные комнаты' }}
                </td>
                <td class="small">
                  {{ f.type === 'rooms' ? getRoomLabels(f.for_room_types_ids) : '—' }}
                </td>
                <td class="small">
                  <div v-if="f.used_input_ids?.length">Параметры: <span class="text-success">{{ getusingParams(f) }}</span></div>
                  <div v-if="f.objType === 'system' && f.used_limit_ids?.length">Лимиты: <span class="text-warning"> {{ getUsedLimitLabels(f) }}</span></div>
                </td>
                <td class="small text-muted">
                  <div v-if="f.objType === 'system'">
                    <div v-for="(eq, i) in f.equations" :key="i" class="mb-1">
                      При <span class="text-warning">{{ eq.limit_equastion }}</span> рекомендация: <span class="text-danger">{{ eq.recommendation || '—' }}</span>
                    </div>
                  </div>
                  <div v-else>
                    {{ f.recommendation }}
                    <span class="text-warning"> при оценке меньше {{ f.value_recomm }}</span>
                  </div>
                </td>
                <td class="text-center">
                  <span class="badge" :class="f.isActive ? 'bg-success' : 'bg-secondary'">
                    {{ f.isActive ? 'Активна' : 'Выкл' }}
                  </span>
                </td>
                <td>
                  <button class="btn btn-xs btn-outline-warning me-1" @click="editFormula(f)">✏️</button>
                  <button class="btn btn-xs btn-outline-danger" @click="deleteFormula(f.id)">🗑️</button>
                </td>
              </tr>
              <tr v-if="!formulas.length">
                <td colspan="9" class="text-center text-muted py-3">Формулы не добавлены</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════════════════════════
     КАРТОЧКА 4: Методы автоподсчёта критерия
═══════════════════════════════════════════════════════════════ -->
<div class="card shadow-sm mb-4">
  <div class="card-header text-white d-flex justify-content-between align-items-center"
       :style="{ backgroundColor: criterionColor }">
    <span class="fw-bold">Методы автоподсчёта</span>
    <span class="badge bg-light text-dark">
      {{ criterionMethods.length }} из {{ availableCountingMethods.length }}
    </span>
  </div>
  <div class="card-body">
    <p class="text-muted small mb-3">
      Выберите методы автоподсчёта, которые будут использоваться для этого критерия.
      Один метод может быть назначен нескольким критериям.
    </p>

    <div v-if="availableCountingMethods.length === 0" class="alert alert-warning py-2 small">
      В справочнике нет методов автоподсчёта.
    </div>

    <div v-else class="row g-2">
      <div
        v-for="m in availableCountingMethods"
        :key="m.id"
        class="col-md-6 col-lg-4"
      >
        <div
          class="border rounded p-2 d-flex align-items-center gap-2"
          :class="criterionMethods.includes(m.id) ? 'border-primary bg-primary bg-opacity-10' : 'border-light'"
          style="cursor: pointer;"
          @click="toggleCountingMethod(m.id)"
        >
          <input
            class="form-check-input m-0"
            type="checkbox"
            :id="'acm-' + m.id"
            :checked="criterionMethods.includes(m.id)"
            @change="toggleCountingMethod(m.id)"
            @click.stop
          />
          <label class="form-check-label w-100" :for="'acm-' + m.id" style="cursor: pointer;">
            <div class="d-flex justify-content-between align-items-center">
              <strong class="small">{{ m.label || m.name }}</strong>
              <span class="badge bg-secondary ms-1" style="font-size: 0.65rem;">
                {{ countingMethodTypeLabel(m.inputType) }}
              </span>
            </div>
            <small class="text-muted d-block text-truncate" style="font-size: 0.75rem;">
              {{ m.name }}
            </small>
          </label>
        </div>
      </div>
    </div>

    <div class="d-flex gap-2 mt-3">
      <button
        class="btn btn-primary btn-sm"
        @click="saveCountingMethods"
        :disabled="isSavingMethods || availableCountingMethods.length === 0"
      >
        <span v-if="isSavingMethods" class="spinner-border spinner-border-sm me-1"></span>
        {{ isSavingMethods ? 'Сохранение...' : 'Сохранить методы' }}
      </button>
      <button class="btn btn-outline-secondary btn-sm" @click="loadCriterionMethods">
        Сбросить изменения
      </button>
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

const criterionColor = ref('#f8f9fa') 

async function loadCriterionColor() {
  if (!criterionId.value) {
    isColorLoaded.value = true
    return
  }
  try {
    const res = await apiClient.get(roomAnalyticsEndpoints.roomAnalytics.CriteriesGet)
    const crit = (res.data || []).find(c => c.id === criterionId.value)
    if (crit && crit.color) {
      criterionColor.value = crit.color
    }
  } catch (e) {
    console.error('Ошибка загрузки цвета критерия:', e)
  } finally {
    isColorLoaded.value = true
  }
}

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
  roomTypeIds: [], room_type_id: null, furniture_type_id: null,
  isActive: false 
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
  universalValue: 0, roomValues: [], criterion_id: null, isActive: false  
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
  name: '',
  isActive: false, 
  equations: [{ limit_equastion: '', equastion: '', recommendation: '' }],
  type: 'global', 
  recommendation: '', 
  value_recomm: null, 
  for_room_types_ids: [],      // для систем типа 'rooms' (и для отображения в таблице)
  used_input_ids: [],
  used_acp_ids: [],
  used_limit_ids: [],
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

function getUsedLimitLabels(f) {
  if (!f?.used_limit_ids?.length) return ''
  return f.used_limit_ids
    .map(id => {
      const limit = limitParams.value.find(l => l.id === id)
      // Показываем символ (код) или метку, если символ отсутствует
      return limit?.symbol
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
  const idx = formulaForm.for_room_types_ids.indexOf(id)  // ✅ Было: room_type_ids
  if (idx === -1) {
    formulaForm.for_room_types_ids.push(id)
  } else {
    formulaForm.for_room_types_ids.splice(idx, 1)
  }
}

function openMathHelper(field) { mathTarget.value = field; showMathHelper.value = true }
function openMathHelperForEquation(idx, part) { mathTargetEquationIdx.value = idx; mathTarget.value = part; showMathHelper.value = true }

function insertMath(sym) {
  if (!mathTarget.value) return
  if (mathTargetEquationIdx.value !== null) {
    const eq = formulaForm.equations[mathTargetEquationIdx.value]
    mathTarget.value === 'limit_equastion' ? eq.limit_equastion += sym : eq.equastion += sym
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
    isActive: p.isActive ?? false, 
    methodId: p.methodId,
    methodName: p.methodName,
    methodType: p.methodType,
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
    cryteria_id: p.cryteria_id,
    isActive: p.isActive ?? false
  }
}

// 🔹 Фильтрация доступных параметров — ИСПРАВЛЕННАЯ ВЕРСИЯ
const filteredAvailableParams = computed(() => {
  const filter = paramFilter.value
  const isSystem = formulaForm.objType === 'system'
  const formulaType = formulaForm.type // 'global' или 'rooms'
  
  // Объединяем все параметры в один массив
  const allParams = [
    ...parameters.value.map(p => ({ 
      ...p, 
      category: p.inputType === 'auto' ? 'acp' : 'input'
    })),
    // Лимиты доступны только если это система уравнений
    ...(isSystem ? limitParams.value.map(p => ({ 
      ...p, 
      category: 'limit', 
      isLimit: true 
    })) : [])
  ]
  
  let items = allParams.filter(p => {
    // 1. Фильтрация ручных параметров
    if (filter === 'manual') {
      if (p.category !== 'input') return false
      if (formulaType === 'global') {
        return p.paramType === 'global' // Только универсальные
      } else {
        return true // Для rooms показываем и global, и rooms
      }
    }
    
    // 3. 🔹 ФИЛЬТРАЦИЯ ЛИМИТОВ (Строго по типу системы)
    if (filter === 'limit') {
      if (p.category !== 'limit') return false
      
      if (formulaType === 'global') {
        // Если система для ВСЕГО помещения, показываем ТОЛЬКО универсальные лимиты
        return p.type === 'universal'
      } else if (formulaType === 'rooms') {
        // Если система для ВЫБРАННЫХ комнат, показываем ТОЛЬКО лимиты по комнатам
        return p.type === 'byRoom'
      }
    }
    
    return false
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
  if (p.category === 'input') return formulaForm.used_input_ids.includes(p.id)
  if (p.category === 'acp') return formulaForm.used_acp_ids.includes(p.id)
  if (p.category === 'limit') return formulaForm.used_limit_ids.includes(p.id)
  return false
}

// 🔹 Метка типа параметра
function getParamTypeLabel(p) {
  if (!p) return '—'
  if (p.category === 'limit') return 'Лимит'
  if (p.category === 'acp') return 'Авто'
  return p.inputType === 'manual' ? 'Ручной' : 'Авто'
}

// 🔹 Проверка валидности лимита
// 🔹 Проверка валидности лимита
function isParamInvalid(p) {
  // Проверка только для лимитов в системе типа 'rooms'
  if (
    p.paramType === 'limit' && 
    p.type === 'byRoom' && 
    formulaForm.objType === 'system' && 
    formulaForm.type === 'rooms' 
  ) {
    const systemRooms = new Set(formulaForm.for_room_types_ids || [])
    const limitRooms = new Set(p.roomValues?.map(rv => rv.roomId) || [])
    
    // Если у системы выбраны комнаты, а у лимита — другие, это конфликт
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
  if (p.category === 'input') {
    const idx = formulaForm.used_input_ids.indexOf(p.id)
    idx === -1 ? formulaForm.used_input_ids.push(p.id) : formulaForm.used_input_ids.splice(idx, 1)
  } else if (p.category === 'acp') {
    const idx = formulaForm.used_acp_ids.indexOf(p.id)
    idx === -1 ? formulaForm.used_acp_ids.push(p.id) : formulaForm.used_acp_ids.splice(idx, 1)
  } else if (p.category === 'limit') {
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
const isColorLoaded = ref(false) 

onMounted(async () => {
  await loadCriterionColor()        // уже есть
  await loadReferenceData()         // уже есть (roomTypes, furnitureTypes, methods)
  await loadCountingMethods()       // 🔹 НОВОЕ
  await loadCriterionMethods()      // 🔹 НОВОЕ
  await Promise.all([
    loadParameters(),
    loadLimitParams(),
    loadFormulas()
  ])
})


function mapApiToForm(p) {
  return {
    id: p.id, 
    varName: p.varName || p.symbol, 
    label: p.label,
    scope: p.cryteria_id ? 'current' : 'global',
    inputType: p.inputType || 'manual', 
    paramType: p.paramType || 'global',
    roomTypeIds: p.roomTypeIds || p.room_type_ids || [], 
    minVal: p.minVal ?? p.min_value ?? 0, 
    maxVal: p.maxVal ?? p.max_value ?? 100,
    methodId: p.methodId || p.method_id, 
    room_type_id: p.room_type_id, 
    furniture_type_id: p.furniture_type_id,
    isActive: p.isActive ?? false
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
    roomTypeIds: [], room_type_id: null, furniture_type_id: null,
    isActive: false
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
      inputType: paramForm.inputType,
      isActive: paramForm.isActive
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

function mapApiToConstraintForm(c) {
  const cid = c.criterion_id ?? c.cryteria_id
  return {
    id: c.id, 
    symbol: c.symbol, 
    label: c.label, 
    type: c.type,
    scope: cid ? 'current' : 'global',
    universalValue: c.universalValue ?? c.value ?? 0,
    roomValues: c.roomValues?.map(rv => ({...rv})) || [],
    criterion_id: cid || null,
    isActive: c.isActive ?? false
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
    universalValue: 0, roomValues: [],
    criterion_id: criterionId.value || null,
    isActive: false
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
        universalValue: Number(constraintForm.universalValue),
        // ✅ ИСПРАВЛЕНО: roomValues (camelCase) и ключи внутри — roomId (camelCase)
        roomValues: constraintForm.roomValues.map(rv => ({ 
          roomId: rv.roomId,  // ✅ camelCase ключ
          value: Number(rv.value) 
        })),
        isActive: constraintForm.isActive 
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
  formulaForm.equations.push({ 
    limit_equastion: '',  // ✅ Как в модели EquastionOfSystemEquastion
    equastion: '',        // ✅ Как в модели (опечатка сохранена)
    recommendation: '' 
  }) 
}
function removeEquation(idx) { formulaForm.equations.splice(idx, 1) }

function resetFormulaForm() {
  const keepType = formulaForm.objType
  Object.assign(formulaForm, { 
    id: null, 
    objType: keepType, 
    name: '',           
    isActive: false,         equation: '', 
    equations: [{ limit_equastion: '', equastion: '', recommendation: '' }],
    type: 'global', 
    recommendation: '', 
    value_recomm: null, 
    for_room_types_ids: [],
    used_input_ids: [], 
    used_acp_ids: [], 
    used_limit_ids: [],
  })
  isEditingFormula.value = false
}
function cancelEditFormula() { resetFormulaForm() }

async function saveFormula() {
  if (formulaForm.objType === 'single' && !formulaForm.equation.trim()) return alert('Введите уравнение')
  if (formulaForm.objType === 'system' && formulaForm.equations.length <= 1) return alert('Минимальное количество уравнений в системе: 2')
  if (formulaForm.used_input_ids.length === 0 && formulaForm.used_acp_ids.length === 0) return alert('Выберите хотя бы один параметр') 
  if(formulaForm.type ==='rooms' && !formulaForm.for_room_types_ids.length) return alert('Для типа "Для комнат" - укажите хотябы один тип комнат.')

  const payload = {
    objType: formulaForm.objType,
    criterion_id: criterionId.value,
    name: formulaForm.name || '', 
    isActive: formulaForm.isActive, 
    recommendation: formulaForm.recommendation, 
    value_recomm: formulaForm.value_recomm,
    used_input_ids: formulaForm.used_input_ids, 
    used_acp_ids: formulaForm.used_acp_ids
  }

  if (formulaForm.objType === 'single') {
    // Для одиночной формулы
    payload.type = formulaForm.type  // 'global' или 'rooms'
    payload.equation = formulaForm.equation
    if (formulaForm.type === 'rooms') {
      payload.for_room_types_ids = formulaForm.for_room_types_ids  // маппим в правильное поле
    }
  } else {
    // Для системы
    payload.type = formulaForm.type
    payload.equations = formulaForm.equations.map(eq => ({
      limit_equastion: eq.limit_equastion,
      equastion: eq.equastion,
      recommendation: eq.recommendation
    }))
    payload.used_limit_ids = formulaForm.used_limit_ids
    if (formulaForm.type === 'rooms') {
      payload.for_room_types_ids = formulaForm.for_room_types_ids  // правильное поле
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
  const normalizedEquations = f.equations?.map(eq => ({
    limit_equastion: eq.limit_equastion || eq.left || '',
    equastion: eq.equastion || eq.right || '',
    recommendation: eq.recommendation || ''
  })) || [{ limit_equastion: '', equastion: '', recommendation: '' }]

  // ✅ Создаём глубокие копии массивов, чтобы не было ссылок на оригинальные данные
  Object.assign(formulaForm, {
    id: f.id, 
    objType: f.objType, 
    name: f.name || '',             
    isActive: f.isActive ?? false,
    type: f.type || 'global',
    recommendation: f.recommendation || '', 
    value_recomm: f.value_recomm,
    for_room_types_ids: [...(f.for_room_types_ids || [])],  // ✅ Глубокая копия
    used_input_ids: [...(f.used_input_ids || [])],          // ✅ Глубокая копия
    used_acp_ids: [...(f.used_acp_ids || [])],              // ✅ Глубокая копия
    used_limit_ids: [...(f.used_limit_ids || [])],          // ✅ Глубокая копия
    equation: f.equation || '',
    equations: normalizedEquations.map(eq => ({ ...eq }))   // ✅ Глубокая копия
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
watch(
  () => formulaForm.type,
  (newType) => {
    if (newType === 'global') {
      // 1. Сбрасываем выбранные комнаты
      formulaForm.for_room_types_ids = []
      
      // 2. Убираем ручные параметры, привязанные к комнатам
      formulaForm.used_input_ids = formulaForm.used_input_ids.filter(id => {
        const param = parameters.value.find(p => p.id === id)
        return param && param.paramType === 'global'
      })
    
      // 4. Убираем лимиты, привязанные к комнатам (только для систем)
      if (formulaForm.objType === 'system') {
        formulaForm.used_limit_ids = formulaForm.used_limit_ids.filter(id => {
          const limit = limitParams.value.find(l => l.id === id)
          return limit && limit.type === 'universal'
        })
      }
    }
    // При переключении на 'rooms' ничего не сбрасываем — пользователь сам выбирает
  }
)
watch(
  () => formulaForm.objType,
  (newVal) => {
    // При переключении между формулой и системой сбрасываем лишние поля
    if (newVal === 'single') {
      formulaForm.used_limit_ids = []  // лимиты только для систем
      formulaForm.equations = [{ limit_equastion: '', equastion: '', recommendation: '' }]
    } else {
      formulaForm.equation = '' // очищаем поле одиночной формулы
    }
  }
)
watch(
  () => ({ type: formulaForm.type, objType: formulaForm.objType }),
  ({ type, objType }) => {
    if (objType !== 'system') return
    
    if (type === 'global') {
      // Сбрасываем комнаты
      formulaForm.for_room_types_ids = []
      
      // Оставляем ТОЛЬКО универсальные лимиты
      formulaForm.used_limit_ids = formulaForm.used_limit_ids.filter(id => {
        const limit = limitParams.value.find(l => l.id === id)
        return limit && limit.type === 'universal'
      })
      
      // Оставляем ТОЛЬКО глобальные ручные параметры
      formulaForm.used_input_ids = formulaForm.used_input_ids.filter(id => {
        const param = parameters.value.find(p => p.id === id)
        return param && param.paramType === 'global'
      })
    
    } else if (type === 'rooms') {
      formulaForm.used_limit_ids = formulaForm.used_limit_ids.filter(id => {
        const limit = limitParams.value.find(l => l.id === id)
        return limit && (limit.type === 'universal' || limit.type === 'byRoom')
      })
    }
  },
  { deep: true }
)

const availableCountingMethods = ref([])   // Все методы из справочника
const criterionMethods = ref([])           // ID методов, назначенных критерию
const isSavingMethods = ref(false)

// 🔹 Загрузка справочника методов
async function loadCountingMethods() {
  try {
    const res = await apiClient.get(
      roomAnalyticsEndpoints.roomAnalytics.AutoCountingMethodsList
    )
    availableCountingMethods.value = res.data || []
  } catch (e) {
    console.error('Ошибка загрузки методов автоподсчёта:', e)
    availableCountingMethods.value = []
  }
}

//  Загрузка методов, назначенных текущему критерию
async function loadCriterionMethods() {
  if (!criterionId.value) return
  try {
    const res = await apiClient.get(
      roomAnalyticsEndpoints.roomAnalytics.CriterionMethods(criterionId.value)
    )
    criterionMethods.value = res.data || []
  } catch (e) {
    console.error('Ошибка загрузки методов критерия:', e)
    criterionMethods.value = []
  }
}

// 🔹 Переключение метода (чекбокс)
function toggleCountingMethod(methodId) {
  const idx = criterionMethods.value.indexOf(methodId)
  if (idx === -1) {
    criterionMethods.value.push(methodId)
  } else {
    criterionMethods.value.splice(idx, 1)
  }
}

// 🔹 Сохранение назначенных методов
async function saveCountingMethods() {
  if (!criterionId.value) return
  isSavingMethods.value = true
  try {
    await apiClient.put(
      roomAnalyticsEndpoints.roomAnalytics.CriterionMethods(criterionId.value),
      criterionMethods.value
    )
    alert('✅ Методы автоподсчёта сохранены')
  } catch (e) {
    console.error('Ошибка сохранения методов:', e)
    alert(e.response?.data?.error || 'Не удалось сохранить методы')
  } finally {
    isSavingMethods.value = false
  }
}

// 🔹 Хелпер: метка типа метода
function countingMethodTypeLabel(type) {
  const map = {
    nothing: 'Без параметров',
    rooms: 'По комнате',
    furniture: 'По мебели',
    roomsfurniture: 'Комната + Мебель',
  }
  return map[type] || '—'
}




</script>

<style scoped>
.form-label { font-weight: 500; font-size: 0.9rem; }
code { background: #f8f9fa; padding: 2px 6px; border-radius: 4px; font-size: 0.85em; color: #d63384; }
.table th { white-space: nowrap; }
.btn-xs { padding: 0.15rem 0.4rem; font-size: 0.75rem; }
.position-sticky { position: sticky; }

/* Неактивные строки */
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