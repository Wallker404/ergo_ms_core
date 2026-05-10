<template>
  <div class="equipment-ergonomics">
    <h1>Эргономика техники</h1>
    <p class="subtitle">
      Датасет показателей по странам и годам. Данные загружаются из БД и отображаются в человекочитаемом виде.
    </p>
    <div class="analysis-nav mb-3">
      <RouterLink :to="{ name: 'EquipmentErgonomicsAnalysis' }" class="btn btn-outline-primary">
        Перейти к странице «Анализ данных»
      </RouterLink>
    </div>

    <section class="map-section card p-3 mb-3">
      <h2>Карта индекса эргономичности по странам</h2>
      <p class="hint mb-2">
        Нажмите на страну на карте — справа появится сводка по критериям.
        Границы стран после первой успешной загрузки сохраняются.
        Нажатие на строку критерия прокручивает страницу к подробному расчёту ниже.
      </p>
      <p v-if="mapError" class="error mb-2">{{ mapError }}</p>
      <div class="map-layout">
        <div class="map-wrap">
          <button type="button" class="map-reset-btn" @click="resetMapZoom">
            Сбросить зум
          </button>
          <VChart
            v-if="!mapError"
            class="world-map"
            :option="worldMapOption"
            autoresize
            @click="onWorldMapClick"
          />
        </div>
        <aside class="map-side">
          <div v-if="mapCountryLoading" class="small text-muted mb-2">Загрузка данных по стране…</div>
          <div v-if="mapCountryCard" class="map-country-card">
            <div class="map-country-card__title">
              {{ mapCountryCard.countryName }} ({{ mapCountryCard.countryCode }})
            </div>
            <div class="map-country-card__score">
              Индекс: <strong>{{ mapCountryCard.score }}</strong> / 100
              <span class="badge ms-2">{{ mapCountryCard.grade }}</span>
            </div>
            <div class="small text-muted">Опорный год: {{ mapCountryCard.referenceYear }}</div>
            <div class="small text-muted">
              Записей: {{ mapCountryCard.recordsTotal ?? '—' }}, индикаторов: {{ mapCountryCard.indicatorsTotal ?? '—' }}
            </div>
            <div v-if="mapCountryCard.criteria?.length" class="mt-2 map-criteria-table-wrap">
              <table class="table table-sm table-bordered mb-0 map-criteria-main-table">
                <thead>
                  <tr>
                    <th scope="col">Критерий</th>
                    <th scope="col" class="map-criteria-main-table__score">Балл</th>
                  </tr>
                </thead>
                <tbody>
                  <template v-for="cr in mapCountryCard.criteria" :key="cr.key">
                    <tr
                      class="map-criterion-row"
                      tabindex="0"
                      role="button"
                      :title="'Подробности: ' + cr.label"
                      @click="goToErgonomicsCriterion(cr.key)"
                      @keydown.enter.prevent="goToErgonomicsCriterion(cr.key)"
                      @keydown.space.prevent="goToErgonomicsCriterion(cr.key)"
                    >
                      <td class="map-criteria-main-table__label">{{ cr.label }}</td>
                      <td class="map-criteria-main-table__score-cell">
                        {{ cr.score ?? 'н/д' }}
                        <span v-if="cr.grade" class="text-muted small d-block">{{ cr.grade }}</span>
                      </td>
                    </tr>
                  </template>
                </tbody>
              </table>
              <p class="small text-muted mb-0 mt-1">Строка — переход к детализации в блоке «Оценка эргономичности».</p>
            </div>
          </div>
          <div v-else class="map-country-card map-country-card--empty">
            <div class="small text-muted">Выберите страну на карте, чтобы увидеть индекс.</div>
          </div>
          <div class="small text-muted mt-2">
            Карта: {{ mapPreloadDone }} / {{ mapPreloadTotal }} стран
            <span v-if="mapPreloadRunning"> (загрузка с сервера…)</span>
            <span v-else-if="mapPreloadFromCacheOnly"> (из сохранённого кэша)</span>
          </div>
          <p class="small text-muted mb-2">
            Оценки для раскраски карты сохраняются в браузере до {{ mapScoresTtlDays }} дней — при обычном обновлении страницы запросы по всем странам не повторяются.
          </p>
          <button
            type="button"
            class="btn btn-sm btn-outline-secondary"
            :disabled="mapPreloadRunning || !worldMapReady"
            @click="refreshMapScoresFromServer"
          >
            Обновить оценки с сервера
          </button>
        </aside>
      </div>
    </section>

    <section id="equipment-ergonomics-score" class="ergo-score-section card p-3 mb-3">
      <h2>Оценка эргономичности техники (по стране)</h2>
      <p class="hint mb-3">
        Сводный балл 0–100 по доступным показателям: электроснабжение и ВИЭ (WB), углеродность электроэнергии и CO₂ на душу,
        доля импорта энергоносителей (WB), объёмы ископаемого и низкоуглеродного потребления (TWh, нормировка по странам).
        Это контекст страны для эксплуатации приборов, а не оценка одной модели.
      </p>
      <div class="filters-row">
        <div class="filter-group">
          <label for="ergo-country">Код страны (ISO3)</label>
          <input
            id="ergo-country"
            v-model.trim="ergoScoreForm.countryCode"
            type="text"
            maxlength="8"
            class="form-control"
            placeholder="RUS"
          />
        </div>
        <div class="filter-group">
          <label for="ergo-year">Год (необязательно)</label>
          <input
            id="ergo-year"
            v-model.number="ergoScoreForm.year"
            type="number"
            min="1990"
            max="2030"
            class="form-control"
            placeholder="авто"
          />
        </div>
        <div class="filter-actions">
          <button
            type="button"
            class="btn btn-primary"
            :disabled="ergoScoreLoading || !ergoScoreForm.countryCode"
            @click="loadErgonomicsScore"
          >
            {{ ergoScoreLoading ? 'Расчёт…' : 'Получить оценку' }}
          </button>
        </div>
      </div>
      <p v-if="ergoScoreError" class="error mt-2 mb-0">{{ ergoScoreError }}</p>
      <div v-if="ergoScoreResult && !ergoScoreError" class="ergo-score-result mt-3">
        <div class="ergo-score-main">
          <span class="ergo-score-value">{{ ergoScoreResult.score }}</span>
          <span class="ergo-score-max">/ 100</span>
          <span class="badge ergo-grade ms-2">{{ ergoScoreResult.grade }}</span>
        </div>
        <p class="small text-muted mb-2">
          Страна: <strong>{{ ergoScoreResult.country_code }}</strong>
          · опорный год: <strong>{{ ergoScoreResult.reference_year }}</strong>
          <span v-if="ergoScoreResult.weight_coverage < 1">
            · учтено долей веса: {{ (ergoScoreResult.weight_coverage * 100).toFixed(0) }}%
          </span>
        </p>
        <p class="small text-muted">{{ ergoScoreResult.method_note }}</p>
        <div v-if="ergoScoreResult.country_profile" class="alert alert-light py-2 px-3 mb-2">
          <div class="small">
            <b>Профиль страны:</b>
            записей {{ ergoScoreResult.country_profile.records_total ?? '—' }},
            индикаторов {{ ergoScoreResult.country_profile.indicators_total ?? '—' }},
            период {{ ergoScoreResult.country_profile.first_year ?? '—' }}–{{ ergoScoreResult.country_profile.last_year ?? '—' }}.
          </div>
        </div>

        <div v-if="ergoScoreResult.score_breakdown" class="alert alert-secondary py-3 px-3 mb-3 ergo-breakdown-block">
          <h4 class="h6 mb-2">Расчёт итогового индекса</h4>
          <p class="small mb-2">{{ ergoScoreResult.score_breakdown.description_ru }}</p>
          <p class="small mb-2"><code>{{ ergoScoreResult.score_breakdown.formula }}</code></p>
          <div class="table-responsive">
            <table class="table table-sm table-bordered mb-2 bg-white">
              <thead>
                <tr>
                  <th>Показатель</th>
                  <th>Суббалл Sᵢ</th>
                  <th>Вес wᵢ</th>
                  <th>wᵢ·Sᵢ</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="t in ergoScoreResult.score_breakdown.terms" :key="t.indicator_name">
                  <td>{{ t.label }}</td>
                  <td>{{ t.subscore }}</td>
                  <td>{{ t.weight }}</td>
                  <td>{{ t.weighted_product }}</td>
                </tr>
              </tbody>
              <tfoot class="table-group-divider">
                <tr>
                  <td colspan="2"><strong>Суммы</strong></td>
                  <td><strong>{{ ergoScoreResult.score_breakdown.sum_weights }}</strong> <span class="text-muted small">Σ wᵢ</span></td>
                  <td><strong>{{ ergoScoreResult.score_breakdown.sum_weighted_subscores }}</strong> <span class="text-muted small">Σ wᵢ·Sᵢ</span></td>
                </tr>
                <tr>
                  <td colspan="4" class="small text-break">
                    Индекс = (Σ wᵢ·Sᵢ) / (Σ wᵢ) =
                    {{ ergoScoreResult.score_breakdown.sum_weighted_subscores }} /
                    {{ ergoScoreResult.score_breakdown.sum_weights }}
                    ≈ <strong>{{ ergoScoreResult.score_breakdown.score }}</strong>
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>

        <div v-if="ergoScoreResult.components?.length" class="card mb-3 ergo-custom-weights">
          <div class="card-body py-3">
            <h4 class="h6 mb-2">Пересчёт индекса с вашими весами</h4>
            <p class="small text-muted mb-2">
              Меняются только веса показателей сводного индекса (суббаллы Sᵢ те же).
              Нулевой вес исключает показатель из среднего. Показатели по критериям ниже считаются по правилам модели и от весов здесь не зависят.
            </p>
            <div class="row g-2 mb-2">
              <div
                v-for="c in ergoScoreResult.components"
                :key="'cw-' + c.indicator_name"
                class="col-md-6"
              >
                <label class="small d-block text-truncate" :title="c.label">{{ c.label }}</label>
                <input
                  v-model.number="customIndexWeights[c.indicator_name]"
                  type="number"
                  min="0"
                  step="0.01"
                  class="form-control form-control-sm"
                />
              </div>
            </div>
            <div class="d-flex flex-wrap gap-2 mb-2 align-items-center">
              <button type="button" class="btn btn-sm btn-outline-secondary" @click="resetCustomIndexWeights">
                Веса модели
              </button>
              <button type="button" class="btn btn-sm btn-outline-secondary" @click="normalizeCustomIndexWeights">
                Нормализовать сумму к 1
              </button>
              <button
                type="button"
                class="btn btn-sm btn-primary"
                :disabled="customWeightsVerifyLoading"
                @click="verifyCustomWeightsOnServer"
              >
                {{ customWeightsVerifyLoading ? 'Проверка…' : 'Сверить с сервером' }}
              </button>
            </div>
            <div v-if="customCompositePreview?.score != null" class="small">
              <strong>Ваш индекс:</strong> {{ customCompositePreview.score }} / 100
              <span class="badge ms-2">{{ customCompositePreview.grade }}</span>
              <span class="text-muted ms-2">Σ wᵢ = {{ customCompositePreview.sumWeights }}</span>
            </div>
            <p v-else class="small text-warning mb-0">Укажите хотя бы один положительный вес для показателей с данными.</p>
            <p v-if="customWeightsVerifyNote" class="small mb-0 mt-2 text-muted">{{ customWeightsVerifyNote }}</p>
          </div>
        </div>

        <div v-if="ergoScoreResult.criteria?.length" class="mb-2">
          <h4 class="mb-1">Критерии эргономичности</h4>
          <table class="table table-sm table-bordered mb-0">
            <thead>
              <tr>
                <th>Критерий</th>
                <th>Балл</th>
                <th>Уровень</th>
                <th>Покрытие веса</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="cr in ergoScoreResult.criteria" :key="cr.key">
                <tr :id="'ergo-criterion-row-' + cr.key">
                  <td>
                    <details v-if="cr.components?.length" class="nested-detail ergo-criterion-details">
                      <summary>{{ cr.label }}</summary>
                      <table class="table table-sm mb-0 mt-2">
                        <thead>
                          <tr>
                            <th>Показатель</th>
                            <th>Вес</th>
                            <th>Суббалл</th>
                            <th>Значение</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="co in cr.components" :key="co.indicator_name">
                            <td>{{ co.label }}</td>
                            <td>{{ co.weight }}</td>
                            <td>{{ co.subscore }}</td>
                            <td>{{ formatValue(co.raw_value) }} {{ co.unit || '' }}</td>
                          </tr>
                        </tbody>
                      </table>
                    </details>
                    <template v-else>{{ cr.label }}</template>
                  </td>
                  <td>{{ cr.score ?? 'н/д' }}</td>
                  <td>{{ cr.grade }}</td>
                  <td>{{ cr.weight_coverage ?? 0 }}</td>
                </tr>
              </template>
            </tbody>
          </table>
          <div class="small text-muted mt-1">{{ ergoScoreResult.criteria_note }}</div>
        </div>
        <table v-if="ergoScoreResult.components?.length" class="table table-sm table-bordered mb-0">
          <thead>
            <tr>
              <th>Показатель</th>
              <th>Значение</th>
              <th>Год</th>
              <th>Вклад (суббалл)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in ergoScoreResult.components" :key="c.indicator_name">
              <td>{{ c.label }}</td>
              <td>{{ formatValue(c.raw_value) }} {{ c.unit || '' }}</td>
              <td>{{ c.year_used }} <span v-if="c.comparison_pool_year !== c.year_used" class="text-muted">(пул {{ c.comparison_pool_year }})</span></td>
              <td>{{ c.subscore }}</td>
            </tr>
          </tbody>
        </table>
        <p v-if="ergoScoreResult.missing_indicators?.length" class="small text-warning mt-2 mb-0">
          Нет в БД для расчёта: {{ ergoScoreResult.missing_indicators.join(', ') }}
        </p>

        <div class="ergo-series-block mt-4">
          <h4 class="h6 mb-2">Динамика индекса по годам</h4>
          <p class="small text-muted mb-2">
            Для каждого года в диапазоне пересчитывается тот же сводный индекс, что и при ручном указании года выше.
          </p>
          <div class="filters-row flex-wrap align-items-end">
            <div class="filter-group">
              <label for="ergo-series-from">Год от</label>
              <input
                id="ergo-series-from"
                v-model.number="ergoSeriesForm.year_from"
                type="number"
                min="1990"
                max="2030"
                class="form-control"
              />
            </div>
            <div class="filter-group">
              <label for="ergo-series-to">Год до</label>
              <input
                id="ergo-series-to"
                v-model.number="ergoSeriesForm.year_to"
                type="number"
                min="1990"
                max="2030"
                class="form-control"
              />
            </div>
            <div class="filter-actions">
              <button
                type="button"
                class="btn btn-outline-primary"
                :disabled="ergoSeriesLoading || !ergoScoreForm.countryCode"
                @click="loadErgonomicsScoreSeries"
              >
                {{ ergoSeriesLoading ? 'Загрузка…' : 'Построить график' }}
              </button>
            </div>
          </div>
          <p v-if="ergoSeriesError" class="error mt-2 mb-0">{{ ergoSeriesError }}</p>
          <div v-if="ergoSeriesLineChartData" class="chart-container line-chart ergo-series-chart mt-3">
            <Line :data="ergoSeriesLineChartData" :options="ergoSeriesLineOptions" />
          </div>
          <p v-else-if="ergoSeriesData && !ergoSeriesLineChartData" class="hint mt-2 mb-0">
            Нет точек для графика по выбранному диапазону.
          </p>
        </div>
      </div>
    </section>

    <section class="filters-section">
      <h2>Фильтры</h2>
      <div class="filters-row">
        <div class="filter-group">
          <label for="filter-country">Код страны (ISO)</label>
          <input
            id="filter-country"
            v-model.trim="filters.country_code"
            type="text"
            placeholder="например RUS, USA"
            maxlength="8"
            class="form-control"
          />
        </div>
        <div class="filter-group">
          <label for="filter-year">Год</label>
          <input
            id="filter-year"
            v-model.number="filters.year"
            type="number"
            placeholder="например 2020"
            min="1990"
            max="2030"
            class="form-control"
          />
        </div>
        <div class="filter-group">
          <label for="filter-class">Класс техники</label>
          <select id="filter-class" v-model="filters.equipment_class_code" class="form-control">
            <option value="">— все —</option>
            <option v-for="c in electricalClasses" :key="c.code" :value="c.code">
              {{ c.name }}{{ c.is_non_eco ? ' (неэкологичная)' : '' }}
            </option>
          </select>
        </div>
        <div class="filter-actions">
          <button type="button" class="btn btn-primary" :disabled="loading" @click="loadDataset(1)">
            Применить
          </button>
          <button type="button" class="btn btn-outline-secondary" @click="resetFilters">
            Сбросить
          </button>
        </div>
      </div>
    </section>

    <section class="charts-section">
      <h2>Сравнение стран</h2>
      <p class="hint">Выберите страны (коды через запятую) и показатель — появятся графики для сравнения.</p>
      <div class="charts-filters">
        <div class="filter-group">
          <label for="chart-countries">Коды стран (ISO)</label>
          <input
            id="chart-countries"
            v-model.trim="chartParams.country_codes"
            type="text"
            placeholder="RUS, USA, DEU, FRA"
            class="form-control"
          />
        </div>
        <div class="filter-group">
          <label for="chart-indicator">Показатель</label>
          <select id="chart-indicator" v-model="chartParams.indicator_name" class="form-control">
            <option
              v-for="opt in indicatorOptions"
              :key="opt.value"
              :value="opt.value"
            >
              {{ opt.label }}
            </option>
          </select>
        </div>
        <div class="filter-group">
          <label for="chart-year-from">Год от</label>
          <input
            id="chart-year-from"
            v-model.number="chartParams.year_from"
            type="number"
            min="1990"
            max="2030"
            class="form-control"
          />
        </div>
        <div class="filter-group">
          <label for="chart-year-to">Год до</label>
          <input
            id="chart-year-to"
            v-model.number="chartParams.year_to"
            type="number"
            min="1990"
            max="2030"
            class="form-control"
          />
        </div>
        <button
          type="button"
          class="btn btn-primary"
          :disabled="chartLoading || !chartParams.country_codes || !chartParams.indicator_name"
          @click="loadChartData"
        >
          {{ chartLoading ? 'Загрузка…' : 'Построить графики' }}
        </button>
      </div>
      <p v-if="chartError" class="error">{{ chartError }}</p>
      <template v-if="chartData && chartData.years && chartData.years.length">
        <div class="chart-block">
          <h3>Динамика по годам</h3>
          <div class="chart-container line-chart">
            <Line v-if="lineChartData" :data="lineChartData" :options="lineChartOptions" />
          </div>
        </div>
        <div class="chart-block">
          <h3>Сравнение по странам за год</h3>
          <div class="filter-group chart-year-select">
            <label for="bar-year">Год</label>
            <select id="bar-year" v-model="barChartYear" class="form-control">
              <option v-for="y in chartData.years" :key="y" :value="y">{{ y }}</option>
            </select>
          </div>
          <div class="chart-container bar-chart">
            <Bar v-if="barChartData" :data="barChartData" :options="barChartOptions" />
          </div>
        </div>
      </template>
      <p v-else-if="chartData && !chartData.years?.length" class="hint">Нет данных для выбранных параметров.</p>
    </section>

    <section class="import-section">
      <h2>Очистка и импорт CSV</h2>
      <p class="hint">
        Колонки: country_code, year, indicator_name, value [, unit, equipment_class_code, source_notes]. Очистка: дубликаты
        (в т.ч. строки с совпадением ~80%+), проверка типов, заполнение пропусков value средним (колонка value_imputed),
        признаки value_log1p, year_centered, нормализация value по показателю.
      </p>
      <input
        ref="csvInputRef"
        type="file"
        accept=".csv"
        class="form-control"
        @change="onCsvSelect"
      />
      <div class="import-actions mt-2 d-flex flex-wrap align-items-center gap-2">
        <label class="d-flex align-items-center gap-1 mb-0 small">
          <input v-model="importWithCleaning" type="checkbox" />
          Импорт с очисткой
        </label>
        <button
          type="button"
          class="btn btn-outline-primary"
          :disabled="!csvFile || cleanLoading"
          @click="runCleanCsv"
        >
          {{ cleanLoading ? 'Очистка…' : 'Только очистка (отчёт + файл)' }}
        </button>
        <button
          type="button"
          class="btn btn-secondary"
          :disabled="!csvFile || importLoading"
          @click="importCsv"
        >
          {{ importLoading ? 'Импорт…' : 'Загрузить в БД' }}
        </button>
        <button
          type="button"
          class="btn btn-outline-secondary"
          :disabled="!cleanedCsvBlob"
          @click="downloadCleanedCsv"
        >
          Скачать очищенный CSV
        </button>
      </div>
      <div v-if="cleanReport" class="clean-report mt-2 small">
        <strong>Отчёт очистки:</strong>
        строк: {{ cleanReport.row_count_in }} → {{ cleanReport.row_count_out }};
        точных дублей строк: {{ cleanReport.exact_row_duplicates_removed }};
        дублей ключа: {{ cleanReport.key_duplicates_removed }};
        близких дублей удалено: {{ cleanReport.near_duplicate_rows_removed }} (кластеров: {{ cleanReport.near_duplicate_clusters }});
        заполнено value: {{ cleanReport.value_imputed_count }};
        новые колонки: {{ (cleanReport.new_columns || []).join(', ') || '—' }}.
        <span v-if="(cleanReport.type_coercion_issues || []).length">
          Предупреждения типов: {{ cleanReport.type_coercion_issues.length }} (первые записи в консоли).
        </span>
      </div>
      <span v-if="importResult" class="import-result d-block mt-2">{{ importResult }}</span>
    </section>

    <div v-if="loading" class="loading">Загрузка…</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <template v-else>
      <section class="dataset-section">
        <h2>Показатели по странам</h2>
        <p v-if="pagination.count != null" class="meta">
          Всего записей: {{ pagination.count }}. Страница {{ pagination.page }} из {{ pagination.pages }}.
        </p>
        <div class="table-wrap">
          <table class="table table-bordered table-striped dataset-table">
            <thead>
              <tr>
                <th>Страна (код)</th>
                <th>Год</th>
                <th>Показатель</th>
                <th>Значение</th>
                <th>Единица</th>
                <th>Класс техники</th>
                <th>Источник</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in dataset" :key="row.id">
                <td>{{ row.country_code }}</td>
                <td>{{ row.year || '—' }}</td>
                <td>{{ row.indicator_label || row.indicator_name }}</td>
                <td>{{ formatValue(row.value) }}</td>
                <td>{{ row.unit || '—' }}</td>
                <td>{{ row.equipment_class_name || '—' }}</td>
                <td>{{ row.source_notes || '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="dataset.length === 0" class="empty">Нет данных по выбранным фильтрам.</div>
        <div v-if="pagination.pages > 1" class="pagination">
          <button
            type="button"
            class="btn btn-sm btn-outline-primary"
            :disabled="!pagination.previous"
            @click="loadDataset(pagination.page - 1)"
          >
            Назад
          </button>
          <span class="page-info">Стр. {{ pagination.page }} / {{ pagination.pages }}</span>
          <button
            type="button"
            class="btn btn-sm btn-outline-primary"
            :disabled="!pagination.next"
            @click="loadDataset(pagination.page + 1)"
          >
            Вперёд
          </button>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, nextTick } from 'vue'
import { Line, Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'
import VChart from 'vue-echarts'
import * as echarts from 'echarts/core'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { MapChart } from 'echarts/charts'
import { TooltipComponent, VisualMapComponent } from 'echarts/components'
import { apiClient } from '@/js/api/manager'
import { endpoints } from '../js/endpoints'
import {
  migrateWorldGeoJsonFromLocalStorage,
  getCachedWorldGeoJson,
  setCachedWorldGeoJson
} from '../js/worldGeoJsonCache'
import {
  getCachedMapScores,
  setCachedMapScores,
  deleteCachedMapScores,
  MAP_SCORES_TTL_MS
} from '../js/countryMapScoresCache'
import { computeCompositeFromComponents, gradeForErgonomicsScore } from '../js/ergoCompositeScore'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend
)

use([CanvasRenderer, MapChart, TooltipComponent, VisualMapComponent])

const CHART_COLORS = [
  'rgb(54, 162, 235)',
  'rgb(255, 99, 132)',
  'rgb(75, 192, 192)',
  'rgb(255, 205, 86)',
  'rgb(153, 102, 255)',
  'rgb(201, 203, 207)',
]

const indicatorOptions = [
  { value: 'electricity_demand', label: 'Потребление электроэнергии (TWh)' },
  { value: 'electricity_demand_per_capita', label: 'Потребление электроэнергии на душу (кВт·ч)' },
  { value: 'energy_per_capita', label: 'Потребление первичной энергии на душу (кВт·ч)' },
  { value: 'primary_energy_consumption', label: 'Потребление первичной энергии (TWh)' },
  { value: 'renewable_consumption', label: 'Потребление ВИЭ (TWh)' },
  { value: 'low_carbon_consumption', label: 'Низкоуглеродное потребление энергии (TWh)' },
  { value: 'fossil_fuel_consumption', label: 'Потребление ископаемого топлива (TWh)' },
  { value: 'carbon_intensity_elec', label: 'Углеродоёмкость электроэнергии' },
  { value: 'greenhouse_gas_emissions', label: 'Выбросы ПГ от электроэнергии (Mt CO₂)' },
  { value: 'wb_eg_use_elec_kh_pc', label: 'World Bank: потребление электроэнергии на душу (кВт·ч)' },
  { value: 'wb_eg_elc_accs_zs', label: 'World Bank: доступ к электроэнергии (% населения)' },
  { value: 'wb_eg_fec_rnew_zs', label: 'World Bank: доля ВИЭ в потреблении (%)' },
  { value: 'wb_eg_imp_cons_zs', label: 'World Bank: импорт энергоносителей (% потребления)' },
  { value: 'wb_en_atm_co2e_pc', label: 'World Bank: выбросы CO₂ на душу (т)' },
]

const loading = ref(false)
const error = ref(null)
const dataset = ref([])
const electricalClasses = ref([])
const csvFile = ref(null)
const csvInputRef = ref(null)
const importLoading = ref(false)
const importResult = ref('')
const importWithCleaning = ref(false)
const cleanLoading = ref(false)
const cleanReport = ref(null)
const cleanedCsvBlob = ref(null)
const IMPORT_TIMEOUT_MS = 120000
const WORLD_GEOJSON_LEGACY_LS_KEY = 'equipment_ergonomics_world_geojson_v1'
const WORLD_GEOJSON_FALLBACK_URLS = [
  'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson',
  'https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson'
]

function worldGeoPrimaryUrl() {
  const base = (import.meta.env.BASE_URL || '/').replace(/\/?$/, '/')
  return `${base}maps/world.geo.json`
}
const mapError = ref(null)
const mapCountryLoading = ref(false)
const mapSelectedIso3 = ref('')
const mapCountryCard = ref(null)
const worldMapReady = ref(false)
const countryDisplayNames = ref({})
const countryScoresCache = ref({})
const countryFocusByIso = ref({})
const MAP_DEFAULT_VIEWPORT = { center: [0, 20], zoom: 1.02 }
const mapViewport = ref({ ...MAP_DEFAULT_VIEWPORT })
const mapPreloadRunning = ref(false)
const mapPreloadDone = ref(0)
const mapPreloadTotal = ref(0)
const mapPreloadFromCacheOnly = ref(false)

const mapScoresTtlDays = Math.round(MAP_SCORES_TTL_MS / (24 * 60 * 60 * 1000))

function clampErgonomicsScore(v) {
  const n = Number(v)
  if (!Number.isFinite(n)) return NaN
  return Math.min(100, Math.max(0, n))
}

/** Приводит ответ API к шкале 0–100 на случай старых данных или численных выбросов. */
function normalizeErgonomicsApiPayload(data) {
  if (!data || typeof data !== 'object') return data
  const out = { ...data }
  if (out.score != null && Number.isFinite(Number(out.score))) {
    out.score = Math.round(clampErgonomicsScore(out.score) * 100) / 100
    out.grade = gradeForErgonomicsScore(out.score)
  }
  if (Array.isArray(out.criteria)) {
    out.criteria = out.criteria.map((cr) => {
      if (!cr || typeof cr !== 'object') return cr
      const c2 = { ...cr }
      if (c2.score != null && Number.isFinite(Number(c2.score))) {
        c2.score = Math.round(clampErgonomicsScore(c2.score) * 100) / 100
        c2.grade = gradeForErgonomicsScore(c2.score)
      }
      return c2
    })
  }
  if (
    out.score_breakdown &&
    out.score_breakdown.score != null &&
    Number.isFinite(Number(out.score_breakdown.score))
  ) {
    out.score_breakdown = {
      ...out.score_breakdown,
      score: Math.round(clampErgonomicsScore(out.score_breakdown.score) * 100) / 100,
    }
  }
  return out
}
const COUNTRY_VIEWPORT_OVERRIDES = {
  RUS: { center: [96, 62], zoom: 1.45 }
}
const ruRegionNames = typeof Intl !== 'undefined' && Intl.DisplayNames
  ? new Intl.DisplayNames(['ru'], { type: 'region' })
  : null

const chartParams = reactive({
  country_codes: 'RUS, USA, DEU, FRA',
  indicator_name: 'electricity_demand_per_capita',
  year_from: 2000,
  year_to: 2022
})
const chartData = ref(null)
const chartLoading = ref(false)
const chartError = ref(null)
const barChartYear = ref(null)

const filters = reactive({
  country_code: '',
  year: null,
  equipment_class_code: ''
})

const pagination = reactive({
  page: 1,
  page_size: 50,
  count: null,
  next: null,
  previous: null,
  pages: 1
})

const ergoScoreForm = reactive({
  countryCode: 'RUS',
  year: null
})
const ergoScoreLoading = ref(false)
const ergoScoreError = ref(null)
const ergoScoreResult = ref(null)

const ergoSeriesForm = reactive({
  year_from: 2000,
  year_to: 2022
})
const ergoSeriesLoading = ref(false)
const ergoSeriesError = ref(null)
const ergoSeriesData = ref(null)

const customIndexWeights = reactive({})
const customWeightsVerifyLoading = ref(false)
const customWeightsVerifyNote = ref('')

watch(
  ergoScoreResult,
  (res) => {
    customWeightsVerifyNote.value = ''
    Object.keys(customIndexWeights).forEach((k) => delete customIndexWeights[k])
    if (!res?.components?.length) return
    for (const c of res.components) {
      customIndexWeights[c.indicator_name] = Number(c.weight_default ?? c.weight)
    }
  },
  { flush: 'post' }
)

watch(
  () => ergoScoreForm.year,
  async () => {
    if (!worldMapReady.value) return
    await preloadMapScores()
  }
)

const customCompositePreview = computed(() =>
  computeCompositeFromComponents(ergoScoreResult.value?.components || [], customIndexWeights)
)

function resetCustomIndexWeights() {
  customWeightsVerifyNote.value = ''
  const res = ergoScoreResult.value
  if (!res?.components?.length) return
  for (const c of res.components) {
    customIndexWeights[c.indicator_name] = Number(c.weight_default ?? c.weight)
  }
}

function normalizeCustomIndexWeights() {
  customWeightsVerifyNote.value = ''
  const comps = ergoScoreResult.value?.components || []
  let sum = 0
  for (const c of comps) {
    const w = Number(customIndexWeights[c.indicator_name])
    if (Number.isFinite(w) && w > 0) sum += w
  }
  if (sum <= 0) return
  for (const c of comps) {
    const w = Number(customIndexWeights[c.indicator_name])
    if (Number.isFinite(w) && w > 0) {
      customIndexWeights[c.indicator_name] = Math.round((w / sum) * 10000) / 10000
    }
  }
}

async function verifyCustomWeightsOnServer() {
  const code = (ergoScoreForm.countryCode || '').trim()
  if (!code || !ergoScoreResult.value?.components?.length) return
  customWeightsVerifyLoading.value = true
  customWeightsVerifyNote.value = ''
  try {
    const body = {
      country_code: code.toUpperCase(),
      weights: { ...customIndexWeights }
    }
    if (Number.isFinite(ergoScoreForm.year)) body.year = ergoScoreForm.year
    const res = await apiClient.post(endpoints.datasetCountryErgonomicsScoreCustom, body)
    if (res?.success === false) {
      customWeightsVerifyNote.value = res?.message || 'Запрос не выполнен'
      return
    }
    const data = res?.data ?? res
    if (data?.error) {
      customWeightsVerifyNote.value = typeof data.error === 'string' ? data.error : 'Ошибка сервера'
      return
    }
    const srv = Number(data.score)
    const loc = customCompositePreview.value?.score
    if (loc != null && Number.isFinite(srv) && Math.abs(srv - loc) < 0.02) {
      customWeightsVerifyNote.value = `Сервер подтвердил индекс ${srv} — совпадает с локальным пересчётом.`
    } else {
      customWeightsVerifyNote.value = `Сервер: ${srv}, локально: ${loc ?? '—'}. Сообщите о расхождении при необходимости.`
    }
  } catch (e) {
    customWeightsVerifyNote.value =
      e?.response?.data?.error || e?.response?.data?.detail || e?.message || 'Не удалось вызвать пересчёт на сервере'
  } finally {
    customWeightsVerifyLoading.value = false
  }
}

function formatValue(val) {
  if (val == null || val === '') return '—'
  const n = Number(val)
  if (Number.isNaN(n)) return val
  if (Math.abs(n) >= 1e6 || (Math.abs(n) < 0.01 && n !== 0)) return n.toExponential(2)
  return new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 4 }).format(n)
}

function buildParams(page = 1) {
  const params = { page, page_size: pagination.page_size }
  if (filters.country_code) params.country_code = filters.country_code
  if (filters.year) params.year = filters.year
  if (filters.equipment_class_code) params.equipment_class_code = filters.equipment_class_code
  return params
}

async function loadErgonomicsScore() {
  const code = (ergoScoreForm.countryCode || '').trim()
  if (!code) return
  ergoScoreLoading.value = true
  ergoScoreError.value = null
  ergoScoreResult.value = null
  try {
    ergoScoreResult.value = normalizeErgonomicsApiPayload(await fetchCountryErgonomics(code, ergoScoreForm.year))
    const prof = ergoScoreResult.value?.country_profile
    if (prof?.first_year != null && prof?.last_year != null) {
      const fy = Number(prof.first_year)
      const ly = Number(prof.last_year)
      if (Number.isFinite(fy) && Number.isFinite(ly)) {
        ergoSeriesForm.year_from = Math.min(fy, ly)
        ergoSeriesForm.year_to = Math.max(fy, ly)
      }
    }
  } catch (e) {
    ergoScoreError.value =
      e?.response?.data?.error || e?.response?.data?.detail || e?.message || 'Не удалось получить оценку'
  } finally {
    ergoScoreLoading.value = false
  }
}

const ERGO_SCROLL_FOCUS_DELAY_MS = 380

function goToErgonomicsCriterion(criterionKey) {
  const section = document.getElementById('equipment-ergonomics-score')
  section?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  nextTick(() => {
    window.setTimeout(() => {
      const row = document.getElementById(`ergo-criterion-row-${criterionKey}`)
      const detailsEl = row?.querySelector('details')
      if (detailsEl) {
        detailsEl.open = true
      }
      row?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }, ERGO_SCROLL_FOCUS_DELAY_MS)
  })
}

function normalizeIso3FromFeature(props = {}) {
  const candidates = [
    props.ISO_A3,
    props.ADM0_A3,
    props.SU_A3,
    props.WB_A3,
    props.iso_a3,
    props.iso3,
    props.id
  ]
  for (const raw of candidates) {
    const code = String(raw || '').trim().toUpperCase()
    if (code.length === 3 && code !== '-99') return code
  }
  return ''
}

function normalizeIso2FromFeature(props = {}) {
  const candidates = [props.ISO_A2, props.iso_a2, props.ISO2, props.iso2]
  for (const raw of candidates) {
    const code = String(raw || '').trim().toUpperCase()
    if (code.length === 2 && code !== '-1') return code
  }
  return ''
}

function resolveCountryDisplayName(props = {}, iso3 = '') {
  const iso2 = normalizeIso2FromFeature(props)
  if (iso2 && ruRegionNames) {
    const localized = ruRegionNames.of(iso2)
    if (localized && !/unknown/i.test(localized)) return localized
  }
  return String(props.ADMIN || props.NAME_RU || props.NAME_EN || props.NAME || props.name || iso3).trim() || iso3
}

function extractFeatureFocus(feature) {
  let minLon = Infinity
  let minLat = Infinity
  let maxLon = -Infinity
  let maxLat = -Infinity
  const walk = (node) => {
    if (!Array.isArray(node)) return
    if (typeof node[0] === 'number' && typeof node[1] === 'number') {
      const lon = Number(node[0])
      const lat = Number(node[1])
      if (Number.isFinite(lon) && Number.isFinite(lat)) {
        minLon = Math.min(minLon, lon)
        minLat = Math.min(minLat, lat)
        maxLon = Math.max(maxLon, lon)
        maxLat = Math.max(maxLat, lat)
      }
      return
    }
    node.forEach(walk)
  }
  walk(feature?.geometry?.coordinates)
  if (!Number.isFinite(minLon) || !Number.isFinite(minLat) || !Number.isFinite(maxLon) || !Number.isFinite(maxLat)) {
    return null
  }
  const width = Math.max(0.01, maxLon - minLon)
  const height = Math.max(0.01, maxLat - minLat)
  const area = width * height
  let zoom = 2.2
  if (area < 10) zoom = 5.2
  else if (area < 30) zoom = 4.5
  else if (area < 80) zoom = 3.9
  else if (area < 200) zoom = 3.4
  else if (area < 500) zoom = 2.9
  else if (area < 1200) zoom = 2.5
  return {
    center: [(minLon + maxLon) / 2, (minLat + maxLat) / 2],
    zoom
  }
}

async function fetchCountryErgonomics(countryCode, year = null, details = true) {
  const params = { country_code: String(countryCode || '').toUpperCase() }
  if (Number.isFinite(year)) params.year = year
  params.details = details ? 1 : 0
  const res = await apiClient.get(endpoints.datasetCountryErgonomicsScore, params)
  if (res?.success === false) {
    throw new Error(res?.message || res?.errors?.error || 'Ошибка запроса')
  }
  const data = res?.data ?? res
  if (data?.error) throw new Error(typeof data.error === 'string' ? data.error : 'Ошибка расчёта')
  return data
}

async function preloadMapScores(opts = {}) {
  const forceRefresh = opts.forceRefresh === true
  const isoCodes = Object.keys(countryDisplayNames.value).filter(code => code.length === 3)
  if (!isoCodes.length) return

  const year = ergoScoreForm.year
  const mergedScores = {}

  mapPreloadFromCacheOnly.value = false

  if (!forceRefresh) {
    const cached = await getCachedMapScores(year)
    const fresh =
      cached &&
      Number.isFinite(cached.savedAt) &&
      Date.now() - cached.savedAt < MAP_SCORES_TTL_MS

    if (fresh && cached.scores && typeof cached.scores === 'object') {
      for (const iso of isoCodes) {
        const v = clampErgonomicsScore(cached.scores[iso])
        if (Number.isFinite(v)) mergedScores[iso] = v
      }
    }
  }

  countryScoresCache.value = { ...mergedScores }

  const toFetch = isoCodes.filter(iso => !Number.isFinite(mergedScores[iso]))
  mapPreloadTotal.value = isoCodes.length
  mapPreloadDone.value = isoCodes.length - toFetch.length

  if (toFetch.length === 0) {
    mapPreloadRunning.value = false
    mapPreloadFromCacheOnly.value = !forceRefresh && Object.keys(mergedScores).length > 0
    if (Object.keys(mergedScores).length) {
      await setCachedMapScores(year, mergedScores)
    }
    return
  }

  mapPreloadRunning.value = true
  const queue = [...toFetch]
  const concurrency = 6
  let cursor = 0
  const workers = Array.from({ length: concurrency }, async () => {
    while (cursor < queue.length) {
      const idx = cursor
      cursor += 1
      const iso = queue[idx]
      try {
        const data = await fetchCountryErgonomics(iso, year, false)
        const sc = clampErgonomicsScore(data.score)
        if (Number.isFinite(sc)) {
          mergedScores[iso] = sc
          countryScoresCache.value = { ...countryScoresCache.value, [iso]: sc }
        }
      } catch (_) {
        // нет данных по стране — допустимо
      } finally {
        mapPreloadDone.value += 1
      }
    }
  })
  await Promise.all(workers)
  mapPreloadRunning.value = false
  mapPreloadFromCacheOnly.value = false
  await setCachedMapScores(year, mergedScores)
}

async function refreshMapScoresFromServer() {
  await deleteCachedMapScores(ergoScoreForm.year)
  await preloadMapScores({ forceRefresh: true })
}

async function loadErgonomicsScoreSeries() {
  const code = (ergoScoreForm.countryCode || '').trim()
  if (!code) return
  ergoSeriesLoading.value = true
  ergoSeriesError.value = null
  ergoSeriesData.value = null
  try {
    const params = {
      country_code: code.toUpperCase(),
      year_from: ergoSeriesForm.year_from ?? 2000,
      year_to: ergoSeriesForm.year_to ?? 2022
    }
    const res = await apiClient.get(endpoints.datasetCountryErgonomicsScoreSeries, params)
    if (res?.success === false) {
      throw new Error(res?.message || res?.errors?.error || 'Ошибка запроса')
    }
    const data = res?.data ?? res
    if (data?.error) {
      throw new Error(typeof data.error === 'string' ? data.error : 'Ошибка расчёта')
    }
    ergoSeriesData.value = data
  } catch (e) {
    ergoSeriesError.value =
      e?.response?.data?.error || e?.response?.data?.detail || e?.message || 'Не удалось загрузить ряд по годам'
  } finally {
    ergoSeriesLoading.value = false
  }
}

async function applyWorldGeoJson(geo) {
  try {
    const features = Array.isArray(geo?.features) ? geo.features : []
    const normFeatures = []
    const names = {}
    const focus = {}
    for (const feature of features) {
      const props = feature?.properties || {}
      const iso3 = normalizeIso3FromFeature(props)
      if (!iso3) continue
      if (iso3 === 'ATA') continue
      const displayName = resolveCountryDisplayName(props, iso3)
      if (displayName.toLowerCase() === 'antarctica') continue
      names[iso3] = displayName
      const featureFocus = extractFeatureFocus(feature)
      if (featureFocus) {
        focus[iso3] = featureFocus
      }
      normFeatures.push({
        ...feature,
        properties: {
          ...props,
          name: iso3,
          display_name: displayName
        }
      })
    }
    if (!normFeatures.length) return false
    echarts.registerMap('world-iso3', { type: 'FeatureCollection', features: normFeatures })
    countryDisplayNames.value = names
    countryFocusByIso.value = focus
    worldMapReady.value = true
    await preloadMapScores()
    return true
  } catch (_) {
    return false
  }
}

async function loadWorldMap() {
  mapError.value = null
  await migrateWorldGeoJsonFromLocalStorage(WORLD_GEOJSON_LEGACY_LS_KEY)

  try {
    const idbGeo = await getCachedWorldGeoJson()
    if (idbGeo?.features?.length && (await applyWorldGeoJson(idbGeo))) {
      return
    }
  } catch (_) {
    // IndexedDB недоступен — продолжаем по сети
  }

  const urls = [worldGeoPrimaryUrl(), ...WORLD_GEOJSON_FALLBACK_URLS]
  for (const url of urls) {
    try {
      const response = await fetch(url)
      if (!response.ok) continue
      const geo = await response.json()
      if (!geo?.features?.length) continue
      try {
        await setCachedWorldGeoJson(geo)
      } catch (_) {
        // квота IndexedDB или приватный режим
      }
      if (await applyWorldGeoJson(geo)) {
        return
      }
    } catch (_) {
      // резервный источник
    }
  }

  mapError.value = 'Не удалось загрузить карту мира (offline cache/network).'
}

async function onWorldMapClick(params) {
  const iso3 = String(params?.name || '').toUpperCase()
  if (!iso3 || iso3.length !== 3) return
  mapSelectedIso3.value = iso3
  if (COUNTRY_VIEWPORT_OVERRIDES[iso3]) {
    mapViewport.value = COUNTRY_VIEWPORT_OVERRIDES[iso3]
  } else if (countryFocusByIso.value[iso3]) {
    mapViewport.value = countryFocusByIso.value[iso3]
  }
  mapCountryLoading.value = true
  try {
    const data = normalizeErgonomicsApiPayload(await fetchCountryErgonomics(iso3, ergoScoreForm.year, true))
    ergoScoreForm.countryCode = iso3
    ergoScoreResult.value = data
    ergoScoreError.value = null
    mapCountryCard.value = {
      countryCode: iso3,
      countryName: countryDisplayNames.value[iso3] || iso3,
      score: data.score,
      grade: data.grade,
      referenceYear: data.reference_year,
      recordsTotal: data?.country_profile?.records_total,
      indicatorsTotal: data?.country_profile?.indicators_total,
      criteria: data?.criteria || []
    }
    const prof = data?.country_profile
    if (prof?.first_year != null && prof?.last_year != null) {
      const fy = Number(prof.first_year)
      const ly = Number(prof.last_year)
      if (Number.isFinite(fy) && Number.isFinite(ly)) {
        ergoSeriesForm.year_from = Math.min(fy, ly)
        ergoSeriesForm.year_to = Math.max(fy, ly)
      }
    }
    countryScoresCache.value = {
      ...countryScoresCache.value,
      [iso3]: clampErgonomicsScore(data.score)
    }
  } catch (e) {
    mapCountryCard.value = {
      countryCode: iso3,
      countryName: countryDisplayNames.value[iso3] || iso3,
      score: '—',
      grade: 'нет данных',
      referenceYear: '—'
    }
  } finally {
    mapCountryLoading.value = false
  }
}

function resetMapZoom() {
  mapViewport.value = { ...MAP_DEFAULT_VIEWPORT }
}

const worldMapOption = computed(() => {
  if (!worldMapReady.value) {
    return {
      backgroundColor: 'transparent',
      title: { text: 'Загрузка карты...', left: 'center', top: 'middle', textStyle: { fontSize: 14 } }
    }
  }
  const data = Object.entries(countryScoresCache.value).map(([name, value]) => ({ name, value }))
  return {
    animationDurationUpdate: 300,
    tooltip: {
      trigger: 'item',
      formatter: (p) => {
        const code = String(p?.name || '')
        const nm = countryDisplayNames.value[code] || code
        const val = countryScoresCache.value[code]
        return `${nm} (${code})<br/>Индекс: ${val == null ? 'нет данных' : formatValue(val)}`
      }
    },
    visualMap: {
      show: false,
      min: 0,
      max: 100,
      inRange: { color: ['#f8d7da', '#fff3cd', '#d1e7dd', '#9cd5b5'] }
    },
    series: [
      {
        type: 'map',
        map: 'world-iso3',
        roam: 'scale',
        scaleLimit: { min: 1, max: 12 },
        layoutCenter: ['50%', '52%'],
        layoutSize: '124%',
        center: mapViewport.value.center,
        zoom: mapViewport.value.zoom,
        selectedMode: 'single',
        data,
        label: {
          show: false,
          formatter: (p) => countryDisplayNames.value[String(p?.name || '').toUpperCase()] || p?.name || ''
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 10,
            formatter: (p) => countryDisplayNames.value[String(p?.name || '').toUpperCase()] || p?.name || ''
          },
          itemStyle: { areaColor: '#74a3ff' }
        },
        select: {
          itemStyle: { areaColor: '#4f7edb' }
        },
        itemStyle: {
          areaColor: '#e5e7eb',
          borderColor: '#9ca3af',
          borderWidth: 0.5
        }
      }
    ]
  }
})

async function loadChartData() {
  chartLoading.value = true
  chartError.value = null
  chartData.value = null
  try {
    const params = {
      indicator_name: chartParams.indicator_name,
      country_codes: chartParams.country_codes.replace(/\s/g, ''),
      year_from: chartParams.year_from || 1990,
      year_to: chartParams.year_to || 2030
    }
    const res = await apiClient.get(endpoints.datasetChartData, params)
    const data = res?.data ?? res
    chartData.value = data
    if (data?.years?.length) {
      barChartYear.value = data.years[data.years.length - 1]
    }
  } catch (e) {
    chartError.value = e?.response?.data?.error || e?.message || 'Ошибка загрузки данных для графиков'
  } finally {
    chartLoading.value = false
  }
}

const lineChartData = computed(() => {
  const d = chartData.value
  if (!d?.years?.length || !d?.datasets?.length) return null
  return {
    labels: d.years.map(String),
    datasets: d.datasets.map((ds, i) => ({
      label: ds.label || ds.country_code,
      data: ds.data,
      borderColor: CHART_COLORS[i % CHART_COLORS.length],
      backgroundColor: CHART_COLORS[i % CHART_COLORS.length].replace('rgb', 'rgba').replace(')', ', 0.1)'),
      tension: 0.2,
      fill: false
    }))
  }
})

const lineChartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: true,
  plugins: {
    legend: { position: 'top' },
    title: {
      display: !!chartData.value?.indicator_label,
      text: chartData.value?.indicator_label || '',
    },
    tooltip: {
      callbacks: {
        label: (ctx) => `${ctx.dataset.label}: ${formatValue(ctx.raw)} ${chartData.value?.unit || ''}`.trim()
      }
    }
  },
  scales: {
    y: {
      beginAtZero: true,
      title: { display: true, text: chartData.value?.unit || '' }
    }
  }
}))

const barChartData = computed(() => {
  const d = chartData.value
  const year = barChartYear.value
  if (!d?.years?.length || !d?.datasets?.length || year == null) return null
  const yearIdx = d.years.indexOf(year)
  if (yearIdx === -1) return null
  return {
    labels: d.datasets.map(ds => ds.label || ds.country_code),
    datasets: [{
      label: `${d.indicator_label || d.indicator_name} (${year})`,
      data: d.datasets.map(ds => ds.data[yearIdx]),
      backgroundColor: CHART_COLORS.slice(0, d.datasets.length).map((c, i) =>
        c.replace('rgb', 'rgba').replace(')', ', 0.7)')
      ),
      borderColor: CHART_COLORS.slice(0, d.datasets.length),
      borderWidth: 1
    }]
  }
})

const barChartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: true,
  plugins: {
    legend: { display: false },
    title: {
      display: true,
      text: chartData.value?.indicator_label ? `${chartData.value.indicator_label}, ${barChartYear.value} г.` : ''
    },
    tooltip: {
      callbacks: {
        label: (ctx) => `${formatValue(ctx.raw)} ${chartData.value?.unit || ''}`.trim()
      }
    }
  },
  scales: {
    y: {
      beginAtZero: true,
      title: { display: true, text: chartData.value?.unit || '' }
    }
  }
}))

const ergoSeriesLineChartData = computed(() => {
  const d = ergoSeriesData.value
  if (!d?.points?.length) return null
  const hasAny = d.points.some(p => p.score != null)
  if (!hasAny) return null
  return {
    labels: d.points.map(p => String(p.year)),
    datasets: [
      {
        label: `Индекс (${d.country_code})`,
        data: d.points.map((p) => {
          if (p.score == null) return null
          const s = clampErgonomicsScore(Number(p.score))
          return Number.isFinite(s) ? s : null
        }),
        borderColor: CHART_COLORS[0],
        backgroundColor: CHART_COLORS[0].replace('rgb', 'rgba').replace(')', ', 0.12)'),
        tension: 0.25,
        spanGaps: false,
        fill: true
      }
    ]
  }
})

const ergoSeriesLineOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: true,
  plugins: {
    legend: { position: 'top' },
    title: {
      display: true,
      text: 'Индекс эргономичности по годам'
    },
    tooltip: {
      callbacks: {
        label: (ctx) => {
          if (ctx.raw == null) return `${ctx.dataset.label}: нет данных`
          return `${ctx.dataset.label}: ${formatValue(ctx.raw)}`
        }
      }
    }
  },
  scales: {
    y: {
      min: 0,
      max: 100,
      title: { display: true, text: 'Балл (0–100)' }
    }
  }
}))

async function loadElectricalClasses() {
  try {
    const res = await apiClient.get(endpoints.electricalClasses)
    const data = res?.data ?? res
    electricalClasses.value = Array.isArray(data) ? data : (data?.results || [])
  } catch (e) {
    console.warn('Electrical classes load failed', e)
  }
}

async function loadDataset(page = 1) {
  loading.value = true
  error.value = null
  try {
    const res = await apiClient.get(endpoints.dataset, buildParams(page))
    const data = res?.data ?? res
    dataset.value = data?.results || []
    pagination.count = data?.count ?? null
    pagination.next = data?.next ?? null
    pagination.previous = data?.previous ?? null
    pagination.page = page
    if (pagination.count != null && pagination.page_size) {
      pagination.pages = Math.max(1, Math.ceil(pagination.count / pagination.page_size))
    }
  } catch (e) {
    error.value = e?.response?.data?.error || e?.response?.data?.message || e?.message || 'Ошибка загрузки'
    dataset.value = []
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.country_code = ''
  filters.year = null
  filters.equipment_class_code = ''
  loadDataset(1)
}

function onCsvSelect(event) {
  const file = event.target.files?.[0]
  csvFile.value = file || null
  importResult.value = ''
  cleanReport.value = null
  cleanedCsvBlob.value = null
}

async function runCleanCsv() {
  if (!csvFile.value) return
  cleanLoading.value = true
  cleanReport.value = null
  cleanedCsvBlob.value = null
  importResult.value = ''
  try {
    const formData = new FormData()
    formData.append('file', csvFile.value)
    const res = await apiClient.upload(endpoints.datasetCleanCsv, formData)
    if (res?.success === false) {
      importResult.value = 'Ошибка очистки: ' + (res?.message || 'запрос не удался')
      return
    }
    const data = res?.data ?? res
    cleanReport.value = data?.report ?? null
    const text = data?.cleaned_csv
    if (typeof text === 'string') {
      cleanedCsvBlob.value = new Blob([text], { type: 'text/csv;charset=utf-8' })
    }
    const issues = data?.report?.type_coercion_issues
    if (Array.isArray(issues) && issues.length) {
      console.warn('CSV type warnings (first 20)', issues.slice(0, 20))
    }
  } catch (e) {
    importResult.value = 'Ошибка очистки: ' + (e?.response?.data?.error || e?.message || 'запрос не удался')
  } finally {
    cleanLoading.value = false
  }
}

function downloadCleanedCsv() {
  const blob = cleanedCsvBlob.value
  if (!blob) return
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = (csvFile.value?.name || 'dataset').replace(/\.csv$/i, '') + '_cleaned.csv'
  a.click()
  URL.revokeObjectURL(url)
}

async function importCsv() {
  if (!csvFile.value) return
  importLoading.value = true
  importResult.value = ''
  try {
    const formData = new FormData()
    formData.append('file', csvFile.value)
    const url = importWithCleaning.value
      ? `${endpoints.datasetImportCsv}?apply_cleaning=1`
      : endpoints.datasetImportCsv
    const res = await Promise.race([
      apiClient.upload(url, formData),
      new Promise((_, reject) => {
        setTimeout(() => reject(new Error('Превышено время ожидания ответа сервера (120с).')), IMPORT_TIMEOUT_MS)
      })
    ])
    if (res?.success === false) {
      importResult.value = 'Ошибка: ' + (res?.message || 'импорт не удался')
      return
    }
    const data = res?.data ?? res
    const taskId = data?.task_id
    if (!taskId) {
      importResult.value = 'Ошибка: сервер не вернул task_id импорта.'
      return
    }

    importResult.value = 'Импорт запущен, ожидайте завершения...'
    const startedAt = Date.now()
    while (Date.now() - startedAt < 30 * 60 * 1000) {
      await new Promise(resolve => setTimeout(resolve, 1500))
      const stRes = await apiClient.get(endpoints.datasetImportCsvStatus, { task_id: taskId })
      if (stRes?.success === false) {
        importResult.value = 'Ошибка статуса импорта: ' + (stRes?.message || 'не удалось получить статус')
        return
      }
      const st = stRes?.data ?? stRes
      const status = (st?.status || '').toLowerCase()
      if (status === 'success') {
        const resultData = st?.result || {}
        let msg = `Создано: ${resultData?.created ?? 0}, пропущено: ${resultData?.skipped ?? 0}.`
        const cr = resultData?.cleaning_report
        if (cr) {
          msg += ` После очистки строк: ${cr.row_count_out ?? '—'}; заполнено value: ${cr.value_imputed_count ?? 0}.`
        }
        importResult.value = msg
        loadDataset(pagination.page)
        return
      }
      if (status === 'failure') {
        importResult.value = 'Ошибка: ' + (st?.error || 'импорт завершился с ошибкой')
        return
      }
    }
    importResult.value = 'Импорт выполняется слишком долго. Проверьте позже по этому же экрану.'
    loadDataset(pagination.page)
  } catch (e) {
    importResult.value = 'Ошибка: ' + (e?.response?.data?.error || e?.message || 'импорт не удался')
  } finally {
    importLoading.value = false
  }
}

onMounted(() => {
  loadWorldMap()
  loadElectricalClasses()
  loadDataset(1)
})
</script>

<script>
export default {
  name: 'EquipmentErgonomics'
}
</script>

<style scoped lang="scss">
.equipment-ergonomics {
  padding: 1.5rem;
  max-width: 1200px;
}

.subtitle {
  color: var(--color-text-secondary, #666);
  margin-bottom: 1.5rem;
}

.map-section {
  margin-bottom: 2rem;
}

.map-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 1rem;
  align-items: start;
}

.map-wrap {
  position: relative;
  width: 100%;
  border: 1px solid var(--bs-border-color, #dee2e6);
  border-radius: 0.375rem;
  overflow: hidden;
}

.world-map {
  height: 620px;
  width: 100%;
}

.map-reset-btn {
  position: absolute;
  top: 0.75rem;
  right: 0.75rem;
  z-index: 5;
  border: 0;
  border-radius: 999px;
  padding: 0.4rem 0.8rem;
  font-size: 0.8rem;
  font-weight: 600;
  color: #fff;
  background: #1d4ed8;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.map-reset-btn:hover {
  background: #1e40af;
}

.map-side {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.map-country-card {
  border: 1px solid var(--bs-border-color, #dee2e6);
  border-radius: 0.375rem;
  padding: 0.75rem;
  background: var(--bs-light, #f8f9fa);
  min-width: 0;
}

.map-criteria-table-wrap {
  min-width: 0;
  overflow-x: auto;
}

.map-criteria-main-table {
  table-layout: fixed;
  width: 100%;
}

.map-criteria-main-table__label {
  width: 72%;
  vertical-align: top;
  word-break: break-word;
  overflow-wrap: anywhere;
}

.map-criteria-main-table__score,
.map-criteria-main-table__score-cell {
  width: 28%;
  vertical-align: top;
  white-space: normal;
  word-break: break-word;
}

.map-criterion-row {
  cursor: pointer;
  transition: background-color 0.12s ease;
}

.map-criterion-row:hover,
.map-criterion-row:focus-visible {
  background-color: rgba(13, 110, 253, 0.08);
  outline: none;
}

.map-country-card__title {
  font-weight: 600;
  margin-bottom: 0.25rem;
}

.map-country-card__score {
  margin-bottom: 0.15rem;
}

.map-country-card--empty {
  min-height: 88px;
  display: flex;
  align-items: center;
}

@media (max-width: 1200px) {
  .map-layout {
    grid-template-columns: 1fr;
  }

  .world-map {
    height: 560px;
  }
}

.ergo-score-section {
  margin-bottom: 2rem;
}

.ergo-score-main {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-bottom: 0.5rem;
}

.ergo-score-value {
  font-size: 2.25rem;
  font-weight: 700;
  line-height: 1;
}

.ergo-score-max {
  font-size: 1.1rem;
  color: var(--color-text-secondary, #666);
}

.ergo-grade {
  font-size: 0.9rem;
  font-weight: 600;
  text-transform: capitalize;
}

.filters-section,
.import-section,
.charts-section,
.dataset-section {
  margin-bottom: 2rem;
}

.charts-section h2 {
  margin-bottom: 0.5rem;
}

.charts-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: flex-end;
  margin-bottom: 1rem;
}

.chart-block {
  margin-bottom: 2rem;
}

.chart-block h3 {
  font-size: 1rem;
  margin-bottom: 0.5rem;
}

.chart-container {
  max-width: 800px;
  height: 320px;
  margin-bottom: 0.5rem;
}

.chart-year-select {
  margin-bottom: 0.5rem;
}

.filters-row {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: flex-end;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 140px;
}

.filter-group label {
  font-size: 0.875rem;
  font-weight: 500;
}

.filter-actions {
  display: flex;
  gap: 0.5rem;
}

.hint,
.meta {
  font-size: 0.875rem;
  color: var(--color-text-secondary, #666);
  margin-bottom: 0.5rem;
}

.import-result {
  margin-left: 0.75rem;
  font-size: 0.875rem;
}

.loading,
.error {
  margin: 1rem 0;
}

.error {
  color: var(--bs-danger, #dc3545);
}

.table-wrap {
  overflow-x: auto;
}

.dataset-table {
  font-size: 0.875rem;
}

.dataset-table th,
.dataset-table td {
  white-space: nowrap;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dataset-table td:nth-child(4) {
  white-space: normal;
  text-align: right;
}

.empty {
  padding: 2rem;
  text-align: center;
  color: var(--color-text-secondary, #666);
}

.pagination {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-top: 1rem;
}

.nested-detail summary {
  cursor: pointer;
  font-weight: 500;
}

.ergo-series-chart {
  max-height: 380px;
}

.page-info {
  font-size: 0.875rem;
}

.mt-2 {
  margin-top: 0.5rem;
}
</style>
