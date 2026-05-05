<template>
  <div class="data-analysis">
    <h1>Как меняются страны</h1>
    <p class="subtitle">
      Сравните страны по годам на графиках. Расширенный расчёт — только если нужна таблица с оценками по всем странам из базы.
    </p>
    <div class="mode-switch mb-3">
      <button
        type="button"
        class="btn"
        :class="uiMode === 'dashboard' ? 'btn-primary' : 'btn-outline-primary'"
        @click="uiMode = 'dashboard'"
      >
        Графики по странам
      </button>
      <button
        type="button"
        class="btn"
        :class="uiMode === 'custom' ? 'btn-primary' : 'btn-outline-primary'"
        @click="uiMode = 'custom'"
      >
        Таблица с оценкой
      </button>
    </div>
    <div class="mb-3">
      <RouterLink :to="{ name: 'EquipmentErgonomics' }" class="btn btn-outline-secondary">
        Вернуться к странице «Эргономика техники»
      </RouterLink>
    </div>

    <section v-if="uiMode === 'dashboard'" class="card p-3 mb-3">
      <h2 class="h4">Сравнение стран по одному показателю</h2>
      <p class="small text-muted mb-3">
        Выберите показатель и страны — на графике будет видно, как значение менялось по годам.
      </p>

      <div class="d-flex flex-wrap gap-2 mb-3">
        <button
          v-for="preset in countryDashPresets"
          :key="preset.id"
          class="btn btn-sm btn-outline-primary"
          type="button"
          @click="applyCountryPreset(preset.id)"
        >
          {{ preset.title }}
        </button>
      </div>

      <div class="row g-3 align-items-end">
        <div class="col-md-4">
          <label class="form-label">Что смотрим</label>
          <select v-model="countryDashForm.indicatorName" class="form-control">
            <option v-for="opt in countryIndicatorOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </div>
        <div class="col-md-4">
          <label class="form-label">Страны (коды через запятую)</label>
          <input v-model.trim="countryDashForm.countryCodesCsv" class="form-control" placeholder="Например: RUS, USA, DEU" />
          <div class="form-text">Как в таблицах ООН: RUS — Россия, USA — США, DEU — Германия.</div>
        </div>
        <div class="col-md-2">
          <label class="form-label">Год от</label>
          <input v-model.number="countryDashForm.yearFrom" type="number" min="1960" max="2100" class="form-control" />
        </div>
        <div class="col-md-2">
          <label class="form-label">Год до</label>
          <input v-model.number="countryDashForm.yearTo" type="number" min="1960" max="2100" class="form-control" />
        </div>
      </div>

      <div class="mt-2">
        <button class="btn btn-primary" type="button" :disabled="countryDashLoading" @click="loadCountryDashboardChart">
          {{ countryDashLoading ? 'Загрузка…' : 'Показать график' }}
        </button>
      </div>
      <p v-if="countryDashError" class="text-danger mt-2 mb-0">{{ countryDashError }}</p>

      <div v-if="countryDashChart?.years?.length" class="mt-3">
        <h3 class="mb-1">{{ countryDashChart.indicator_label || countryDashChart.indicator_name }}</h3>
        <div class="small text-muted mb-2">
          Ед. измерения: {{ countryDashChart.unit || '—' }} | Период: {{ countryDashChart.years[0] }}-{{ countryDashChart.years[countryDashChart.years.length - 1] }}
        </div>

        <div class="country-chart-wrap">
          <svg viewBox="0 0 720 300" class="country-chart-svg" role="img" aria-label="Country metrics chart">
            <line :x1="countryChartGeometry.plot.left" :y1="countryChartGeometry.plot.bottom" :x2="countryChartGeometry.plot.right" :y2="countryChartGeometry.plot.bottom" class="axis" />
            <line :x1="countryChartGeometry.plot.left" :y1="countryChartGeometry.plot.top" :x2="countryChartGeometry.plot.left" :y2="countryChartGeometry.plot.bottom" class="axis" />

            <polyline
              v-for="(series, idx) in countryChartGeometry.series"
              :key="series.countryCode"
              :points="series.points"
              fill="none"
              :stroke="series.color"
              stroke-width="2"
            />
          </svg>
          <div class="country-legend">
            <span v-for="(series, idx) in countryChartGeometry.series" :key="`legend-${series.countryCode}`" class="legend-item">
              <span class="legend-dot" :style="{ backgroundColor: series.color }"></span>
              {{ series.countryCode }}
            </span>
          </div>
        </div>

        <div class="mt-2">
          <h4 class="mb-1">Последние доступные значения</h4>
          <table class="table table-sm table-bordered mb-0">
            <thead>
              <tr>
                <th>Страна</th>
                <th>Год</th>
                <th>Значение</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in latestCountryValues" :key="row.country_code">
                <td>{{ row.country_code }}</td>
                <td>{{ row.year ?? '—' }}</td>
                <td>{{ row.value ?? '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <section v-if="uiMode === 'dashboard'" class="card p-3 mb-3">
      <h2 class="h4">Несколько тем на одном экране</h2>
      <p class="small text-muted mb-2">Краткие графики по электроэнергетике и спросу — удобно сравнить страны с первого взгляда.</p>
      <button class="btn btn-outline-primary mb-3" type="button" :disabled="readyDashboardLoading" @click="loadReadyDashboardCards">
        {{ readyDashboardLoading ? 'Обновление…' : 'Обновить блоки' }}
      </button>
      <p v-if="readyDashboardError" class="text-danger">{{ readyDashboardError }}</p>

      <div class="row g-3">
        <div v-for="card in readyDashboardCards" :key="card.id" class="col-xl-6">
          <div class="mini-card">
            <div class="mini-card__title">{{ card.title }}</div>
            <div class="small text-muted mb-2">{{ card.subtitle }}</div>
            <div class="small text-muted mb-2">
              {{ card.chart?.years?.[0] }}-{{ card.chart?.years?.[card.chart?.years?.length - 1] }} | {{ card.chart?.unit || '—' }}
            </div>
            <div v-if="card.geometry?.series?.length" class="country-chart-wrap">
              <svg viewBox="0 0 640 220" class="country-chart-svg" role="img" :aria-label="card.title">
                <line :x1="card.geometry.plot.left" :y1="card.geometry.plot.bottom" :x2="card.geometry.plot.right" :y2="card.geometry.plot.bottom" class="axis" />
                <line :x1="card.geometry.plot.left" :y1="card.geometry.plot.top" :x2="card.geometry.plot.left" :y2="card.geometry.plot.bottom" class="axis" />
                <polyline
                  v-for="series in card.geometry.series"
                  :key="`${card.id}-${series.countryCode}`"
                  :points="series.points"
                  fill="none"
                  :stroke="series.color"
                  stroke-width="2"
                />
              </svg>
              <div class="country-legend">
                <span v-for="series in card.geometry.series" :key="`${card.id}-legend-${series.countryCode}`" class="legend-item">
                  <span class="legend-dot" :style="{ backgroundColor: series.color }"></span>
                  {{ series.countryCode }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section v-if="uiMode === 'custom'" class="card p-3 mb-3">
      <h2 class="h4">Таблица с оценкой по базе данных</h2>
      <p class="text-muted mb-3">
        Выберите готовый сценарий и нажмите «Запустить». Через некоторое время появится таблица по странам и годам.
        Это не официальный прогноз властей, а автоматическая оценка по открытым показателям — воспринимайте как справочную картинку.
      </p>

      <div class="row g-3 align-items-end mb-3">
        <div class="col-lg-8">
          <label class="form-label mb-1">Сценарий</label>
          <select v-model="selectedPresetId" class="form-control">
            <option value="">— что хотите посмотреть —</option>
            <option v-for="p in analysisPresets" :key="p.id" :value="p.id">{{ p.title }}</option>
          </select>
        </div>
        <div class="col-lg-4 d-flex align-items-end gap-2 flex-wrap">
          <button class="btn btn-outline-primary flex-grow-1" type="button" :disabled="!selectedPresetId" @click="applyPreset">
            Подставить настройки
          </button>
          <button
            class="btn btn-primary flex-grow-1"
            type="button"
            @click="startRun"
            :disabled="runLoading || (runForm.method !== 'kmeans' && !runForm.target.trim())"
          >
            {{ runLoading ? 'Запуск…' : 'Запустить' }}
          </button>
        </div>
      </div>
      <p class="small text-muted mb-3">
        После запуска статус обновится сам; когда будет «Готово», результат появится ниже на странице.
      </p>

      <details class="border rounded p-3 mb-3 analysis-expert-details">
        <summary class="fw-semibold mb-0 user-select-none">Все параметры — только если разбираетесь в расчётах</summary>
        <div class="mt-3 pt-2 border-top">
          <div class="row g-3 align-items-end">
            <div class="col-md-4">
              <label class="form-label">Способ расчёта</label>
              <select v-model="runForm.method" class="form-control">
                <option value="linreg">Оценить число (простая модель)</option>
                <option value="logreg">Разделить на классы (логистическая модель)</option>
                <option value="svm">Разделить на классы (гибкая граница)</option>
                <option value="rf">Разделить на классы (много правил)</option>
                <option value="nb">Разделить на классы (быстро, простые допущения)</option>
                <option value="kmeans">Сгруппировать похожие строки</option>
              </select>
            </div>
            <div class="col-md-5">
              <label class="form-label">Целевой показатель (колонка в данных)</label>
              <input
                v-model.trim="runForm.target"
                class="form-control"
                placeholder="Техническое имя столбца"
                :disabled="runForm.method === 'kmeans'"
              />
              <div v-if="runForm.method === 'kmeans'" class="small text-muted mt-1">
                Для группировки целевой столбец не нужен; можно перечислить показатели ниже или оставить поле пустым.
              </div>
            </div>
            <div class="col-md-3">
              <label class="form-label">Учитывать только эти столбцы</label>
              <input v-model.trim="runForm.featuresCsv" class="form-control" placeholder="Через запятую или пусто" />
            </div>
          </div>

          <div class="row g-3 mt-1 align-items-end">
            <div class="col-md-6">
              <label class="form-label">Свой файл данных (если загрузили ниже)</label>
              <select v-model="runForm.datasetId" class="form-control">
                <option value="">Брать данные из общей базы</option>
                <option v-for="d in customDatasets" :key="d.id" :value="d.id">{{ d.name }}</option>
              </select>
            </div>
            <div class="col-md-3">
              <button class="btn btn-outline-secondary w-100" type="button" @click="loadCustomDatasets" :disabled="customLoading">
                {{ customLoading ? 'Загрузка…' : 'Обновить список файлов' }}
              </button>
            </div>
            <div class="col-md-3">
              <button
                class="btn btn-primary w-100"
                type="button"
                @click="startRun"
                :disabled="runLoading || (runForm.method !== 'kmeans' && !runForm.target.trim())"
              >
                {{ runLoading ? 'Запуск…' : 'Запустить с этими параметрами' }}
              </button>
            </div>
          </div>

          <div v-if="runForm.method === 'kmeans'" class="row g-3 mt-1 align-items-end">
            <div class="col-md-4">
              <label class="form-label">Сколько групп выделить</label>
              <input v-model.number="runForm.n_clusters" type="number" min="2" max="40" class="form-control" />
            </div>
          </div>

          <div v-if="classificationMethods.has(runForm.method)" class="row g-3 mt-1 align-items-end">
            <div class="col-md-6">
              <label class="form-label d-block">Если показатель — непрерывное число</label>
              <label class="form-check-label">
                <input v-model="runForm.allowBinning" class="form-check-input me-2" type="checkbox" />
                Разбить самому на несколько диапазонов (уровней)
              </label>
            </div>
            <div class="col-md-3">
              <label class="form-label">Сколько уровней</label>
              <select v-model.number="runForm.bins" class="form-control" :disabled="!runForm.allowBinning">
                <option :value="2">2</option>
                <option :value="3">3</option>
                <option :value="4">4</option>
              </select>
            </div>
          </div>

          <p v-if="methodHint" class="text-warning mt-2 mb-0">
            {{ methodHint }}
            <button
              v-if="showSwitchToLinreg"
              class="btn btn-sm btn-outline-warning ms-2"
              type="button"
              @click="switchToLinreg"
            >
              Лучше оценить числом (регрессия)
            </button>
          </p>
        </div>
      </details>

      <p v-if="runError" class="text-danger mt-2 mb-0">{{ runError }}</p>

      <div v-if="currentRun" class="mt-3 p-3 rounded border bg-light">
        <div class="fw-semibold mb-1">{{ friendlyRunStatus.label }}</div>
        <p class="small text-muted mb-2">{{ friendlyRunStatus.hint }}</p>
        <div class="d-flex flex-wrap gap-2">
          <button class="btn btn-sm btn-outline-primary" type="button" :disabled="statusLoading" @click="refreshStatus">
            {{ statusLoading ? '…' : 'Обновить' }}
          </button>
          <button class="btn btn-sm btn-outline-success" type="button" :disabled="resultLoading" @click="loadResult">
            {{ resultLoading ? '…' : 'Показать результат' }}
          </button>
        </div>
        <details class="small mt-2 mb-0">
          <summary>Служебная информация</summary>
          <div class="mt-1 font-monospace text-muted">Номер задачи: {{ currentRun.run_id }}</div>
          <div class="font-monospace text-muted">Код статуса: {{ currentRun.status }}</div>
        </details>
      </div>
    </section>

    <section v-if="uiMode === 'custom'" class="card p-3 mb-3">
      <details>
        <summary class="fw-semibold">Загрузить свою таблицу (CSV)</summary>
        <p class="hint mt-2 mb-3">
          Нужно только если хотите считать по своим файлам. Для большинства пользователей достаточно базы без загрузки.
        </p>
        <div class="row g-3 align-items-end">
          <div class="col-md-5">
            <label class="form-label">Название</label>
            <input v-model.trim="uploadForm.name" class="form-control" placeholder="Например: мои страны" />
          </div>
          <div class="col-md-5">
            <label class="form-label">Файл CSV</label>
            <input ref="fileRef" class="form-control" type="file" accept=".csv,text/csv" @change="onPickFile" />
          </div>
          <div class="col-md-2">
            <button class="btn btn-primary w-100" type="button" :disabled="uploadLoading || !uploadForm.name || !uploadForm.file" @click="uploadCustom">
              {{ uploadLoading ? '…' : 'Загрузить' }}
            </button>
          </div>
        </div>
        <p v-if="uploadError" class="text-danger mt-2">{{ uploadError }}</p>
        <p v-if="uploadOk" class="text-success mt-2">{{ uploadOk }}</p>
      </details>
    </section>

    <section v-if="uiMode === 'custom' && result" class="card p-3">
      <h2 class="h4">Что получилось</h2>

      <div v-if="resultPlainSummary" class="result-plain alert alert-light border mb-4">
        <h3 class="h6 text-muted mb-2">Коротко</h3>
        <div class="fs-5 fw-semibold mb-2">{{ resultPlainSummary.title }}</div>
        <p class="mb-2">{{ resultPlainSummary.lead }}</p>
        <ul class="mb-2 ps-3">
          <li v-for="(b, bi) in resultPlainSummary.bullets" :key="'pb-' + bi">{{ b }}</li>
        </ul>
        <p v-if="resultPlainSummary.quality" class="mb-2 small text-body-secondary">{{ resultPlainSummary.quality }}</p>
        <div class="border-top pt-2 mt-2">
          <div class="fw-semibold mb-1">Дальше можно</div>
          <ul class="mb-0 ps-3 small">
            <li v-for="(s, si) in resultPlainSummary.nextSteps" :key="'ns-' + si">{{ s }}</li>
          </ul>
        </div>
      </div>

      <div v-if="metricsJsonFormatted" class="mb-3">
        <details class="metrics-details border rounded p-2 bg-body-secondary bg-opacity-10">
          <summary class="fw-semibold cursor-pointer user-select-none">Подробные числа для специалистов</summary>
          <pre class="pre mt-2 mb-0">{{ metricsJsonFormatted }}</pre>
        </details>
      </div>

      <div v-if="result.metrics_json?.predictions?.length" class="mb-3">
        <h3 class="h5">Страны и годы</h3>
        <p v-if="result.metrics_json.predictions_meta" class="small text-muted">
          В базе нашлось строк: {{ result.metrics_json.predictions_meta.total_rows }}.
          <template v-if="result.metrics_json.predictions_meta.truncated">
            На экране показываются первые {{ result.metrics_json.predictions_meta.max_exported }} — список большой, прокрутите таблицу.
          </template>
        </p>
        <div class="table-responsive predictions-scroll">
          <table class="table table-sm table-bordered mb-0">
            <thead>
              <tr>
                <th v-if="predictionColumnSet.has('country_code')">Страна</th>
                <th v-if="predictionColumnSet.has('year')">Год</th>
                <th v-if="predictionColumnSet.has('y_true')">Как в данных</th>
                <th v-if="predictionColumnSet.has('y_pred')">Оценка расчёта</th>
                <th v-if="predictionColumnSet.has('cluster')">Группа схожести</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(pr, idx) in result.metrics_json.predictions" :key="'pr-' + idx">
                <td v-if="predictionColumnSet.has('country_code')">{{ pr.country_code ?? '—' }}</td>
                <td v-if="predictionColumnSet.has('year')">{{ pr.year ?? '—' }}</td>
                <td v-if="predictionColumnSet.has('y_true')">{{ pr.y_true ?? '—' }}</td>
                <td v-if="predictionColumnSet.has('y_pred')">{{ pr.y_pred ?? '—' }}</td>
                <td v-if="predictionColumnSet.has('cluster')">{{ pr.cluster ?? '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="analysisCharts.length" class="mb-3">
        <h3 class="h5">Картинка к результату</h3>
        <p class="small text-muted mb-2">
          Кратко показывает распределение или насколько оценка близка к факту; итог всё равно в таблице выше.
        </p>
        <div v-for="(ch, idx) in analysisCharts" :key="idx" class="mb-3">
          <h4 class="h6 mb-2">{{ chartFriendlyTitle(ch) }}</h4>
          <div v-if="ch.chartType === 'clusterBars' && Array.isArray(ch.data)" class="mt-2">
            <div v-if="ch._clusterGeom?.bars?.length" class="cluster-bars-wrap">
              <svg
                :viewBox="'0 0 ' + ch._clusterGeom.width + ' ' + ch._clusterGeom.height"
                class="cluster-bars-svg"
                role="img"
                :aria-label="ch.title || 'Распределение по кластерам'"
              >
                <line
                  :x1="ch._clusterGeom.plot.left"
                  :y1="ch._clusterGeom.plot.bottom"
                  :x2="ch._clusterGeom.plot.right"
                  :y2="ch._clusterGeom.plot.bottom"
                  class="axis"
                />
                <line
                  :x1="ch._clusterGeom.plot.left"
                  :y1="ch._clusterGeom.plot.top"
                  :x2="ch._clusterGeom.plot.left"
                  :y2="ch._clusterGeom.plot.bottom"
                  class="axis"
                />
                <text
                  :x="ch._clusterGeom.plot.left - 6"
                  :y="ch._clusterGeom.plot.top + 4"
                  class="cluster-axis-tick"
                  text-anchor="end"
                >
                  {{ ch._clusterGeom.maxCount }}
                </text>
                <text
                  :x="ch._clusterGeom.plot.left - 6"
                  :y="ch._clusterGeom.plot.bottom"
                  class="cluster-axis-tick"
                  text-anchor="end"
                  dominant-baseline="middle"
                >
                  0
                </text>
                <rect
                  v-for="(b, bi) in ch._clusterGeom.bars"
                  :key="'cb-bar-' + bi"
                  :x="b.x"
                  :y="b.y"
                  :width="b.w"
                  :height="b.h"
                  class="cluster-bar-rect"
                  :fill="b.fill"
                  rx="4"
                  ry="4"
                />
                <text
                  v-for="(b, bi) in ch._clusterGeom.bars"
                  :key="'cb-n-' + bi"
                  :x="b.labelX"
                  :y="b.countTy"
                  class="cluster-bar-count"
                  text-anchor="middle"
                >
                  {{ b.count }}
                </text>
                <text
                  v-for="(b, bi) in ch._clusterGeom.bars"
                  :key="'cb-l-' + bi"
                  :x="b.labelX"
                  :y="b.clusterTy"
                  class="axis-label cluster-bar-cluster-label"
                  text-anchor="middle"
                >
                  {{ b.clusterLabel }}
                </text>
              </svg>
            </div>
            <details class="small mt-2">
              <summary>Таблица с теми же числами</summary>
              <table class="table table-sm table-bordered mb-0 mt-2">
                <thead>
                  <tr>
                    <th>Группа</th>
                    <th>Сколько строк</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(bar, bi) in ch.data" :key="'cb-' + bi">
                    <td>{{ bar.cluster }}</td>
                    <td>{{ bar.count }}</td>
                  </tr>
                </tbody>
              </table>
            </details>
          </div>
          <div v-if="ch.chartType === 'heatmap' && Array.isArray(ch.data)" class="mt-2">
            <p class="small text-muted mb-2">
              Цвет показывает величину числа в ячейке: по диагонали обычно хотят большие значения — там модель «угадала» уровень.
            </p>
            <div class="heatmap-grid">
              <div
                v-for="(row, r) in ch.data"
                :key="`hm-r-${r}`"
                class="heatmap-row"
              >
                <div
                  v-for="(cell, c) in row"
                  :key="`hm-c-${r}-${c}`"
                  class="heatmap-cell"
                  :style="heatmapCellStyle(ch.data, cell)"
                >
                  {{ cell }}
                </div>
              </div>
            </div>
            <details class="small mt-2">
              <summary>Те же числа таблицей</summary>
              <table class="table table-sm table-bordered mt-2">
                <tbody>
                  <tr v-for="(row, r) in ch.data" :key="r">
                    <td v-for="(cell, c) in row" :key="c">{{ cell }}</td>
                  </tr>
                </tbody>
              </table>
            </details>
          </div>
          <div v-if="ch.chartType === 'pairs' && Array.isArray(ch.data)" class="mt-2">
            <div v-if="buildRegressionChart(ch.data).points.length" class="scatter-wrap">
              <svg viewBox="0 0 560 260" class="scatter-svg" role="img" aria-label="Regression scatter plot">
                <line
                  :x1="buildRegressionChart(ch.data).plot.left"
                  :y1="buildRegressionChart(ch.data).plot.bottom"
                  :x2="buildRegressionChart(ch.data).plot.right"
                  :y2="buildRegressionChart(ch.data).plot.bottom"
                  class="axis"
                />
                <line
                  :x1="buildRegressionChart(ch.data).plot.left"
                  :y1="buildRegressionChart(ch.data).plot.top"
                  :x2="buildRegressionChart(ch.data).plot.left"
                  :y2="buildRegressionChart(ch.data).plot.bottom"
                  class="axis"
                />
                <line
                  :x1="buildRegressionChart(ch.data).line.x1"
                  :y1="buildRegressionChart(ch.data).line.y1"
                  :x2="buildRegressionChart(ch.data).line.x2"
                  :y2="buildRegressionChart(ch.data).line.y2"
                  class="ideal-line"
                />
                <text :x="buildRegressionChart(ch.data).plot.left" :y="buildRegressionChart(ch.data).plot.top - 2" class="axis-label">
                  Оценка расчёта
                </text>
                <text :x="buildRegressionChart(ch.data).plot.right - 96" :y="buildRegressionChart(ch.data).plot.bottom + 20" class="axis-label">
                  Как в данных
                </text>
                <text :x="buildRegressionChart(ch.data).plot.left" :y="buildRegressionChart(ch.data).plot.bottom + 20" class="axis-note">
                  min: {{ buildRegressionChart(ch.data).min.toFixed(2) }}
                </text>
                <text :x="buildRegressionChart(ch.data).plot.right - 88" :y="buildRegressionChart(ch.data).plot.bottom + 20" class="axis-note">
                  max: {{ buildRegressionChart(ch.data).max.toFixed(2) }}
                </text>
                <circle
                  v-for="(p, i) in buildRegressionChart(ch.data).points"
                  :key="`pt-${i}`"
                  :cx="p.x"
                  :cy="p.y"
                  r="3.5"
                  class="scatter-point"
                />
              </svg>
              <div class="small text-muted">
                Пунктир — если бы расчёт совпал с данными идеально.
              </div>
            </div>
            <details class="small mt-2">
              <summary>Первые пары чисел таблицей</summary>
              <table class="table table-sm table-bordered mt-2">
                <thead>
                  <tr>
                    <th>Как в данных</th>
                    <th>Оценка расчёта</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(p, i) in ch.data" :key="i">
                    <td>{{ p.y_true }}</td>
                    <td>{{ p.y_pred }}</td>
                  </tr>
                </tbody>
              </table>
            </details>
          </div>
        </div>
      </div>

      <div v-if="result.explanation_json" class="mb-1">
        <details>
          <summary class="fw-semibold">Подробности расчёта (по желанию)</summary>
          <ol class="mt-2 small text-muted mb-0">
            <li>{{ result.explanation_json.point1 }}</li>
            <li>{{ result.explanation_json.point2 }}</li>
            <li>{{ result.explanation_json.point3 }}</li>
          </ol>
        </details>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, reactive, ref } from 'vue'
import { apiClient } from '@/js/api/manager'
import { endpoints } from '../js/endpoints'

const uiMode = ref('dashboard')
const countryDashLoading = ref(false)
const countryDashError = ref(null)
const countryDashChart = ref(null)
const readyDashboardLoading = ref(false)
const readyDashboardError = ref(null)
const readyDashboardCards = ref([])
const countryDashForm = reactive({
  indicatorName: 'carbon_intensity_elec',
  countryCodesCsv: 'RUS,USA,CHN,DEU,IND',
  yearFrom: 2000,
  yearTo: 2024
})

const customLoading = ref(false)
const customDatasets = ref([])

const runLoading = ref(false)
const runError = ref(null)
const currentRun = ref(null)
const statusLoading = ref(false)
const resultLoading = ref(false)
const result = ref(null)

const friendlyRunStatus = computed(() => {
  const run = currentRun.value
  if (!run) return { label: '', hint: '' }
  const s = String(run.status || '').toLowerCase()
  if (s === 'done') {
    return { label: 'Готово', hint: 'Итог показан ниже на странице.' }
  }
  if (s === 'running') {
    return {
      label: 'Считаем…',
      hint: 'Обычно от нескольких секунд до пары минут. Можно нажать «Обновить».',
    }
  }
  if (s === 'queued') {
    return { label: 'Ждём очереди', hint: 'Расчёт скоро начнётся.' }
  }
  if (s === 'error') {
    return {
      label: 'Не получилось',
      hint: 'Попробуйте другой сценарий или откройте блок «Все параметры».',
    }
  }
  return { label: run.status || 'Ожидание', hint: '' }
})

function chartFriendlyTitle(ch) {
  if (!ch) return 'График'
  if (ch.chartType === 'clusterBars') return 'Распределение по группам'
  if (ch.chartType === 'heatmap') return 'Таблица попаданий по уровням'
  if (ch.chartType === 'pairs') return 'Близость оценки к данным'
  return ch.title || 'График'
}

const runForm = reactive({
  method: 'linreg',
  target: '',
  featuresCsv: '',
  datasetId: '',
  allowBinning: true,
  bins: 3,
  n_clusters: 5
})
const selectedPresetId = ref('')
const countryIndicatorOptions = [
  { value: 'carbon_intensity_elec', label: 'Выбросы CO₂ на электроэнергию' },
  { value: 'fossil_share_elec', label: 'Доля ископаемого топлива в электроэнергии' },
  { value: 'renewables_share_elec', label: 'Доля возобновляемых в электроэнергии' },
  { value: 'electricity_demand_per_capita', label: 'Электропотребление на человека' },
  { value: 'energy_per_capita', label: 'Энергия на человека' },
  { value: 'primary_energy_consumption', label: 'Потребление первичной энергии' },
  { value: 'energy_per_gdp', label: 'Энергозатраты на объём экономики' }
]
const countryDashPresets = [
  { id: 'carbon', title: 'CO2-интенсивность: RUS/USA/CHN/DEU/IND', indicatorName: 'carbon_intensity_elec', countryCodesCsv: 'RUS,USA,CHN,DEU,IND', yearFrom: 2000, yearTo: 2024 },
  { id: 'fossil', title: 'Доля fossil в генерации: RUS/USA/CHN/DEU/IND', indicatorName: 'fossil_share_elec', countryCodesCsv: 'RUS,USA,CHN,DEU,IND', yearFrom: 2000, yearTo: 2024 },
  { id: 'demand', title: 'Спрос на душу: RUS/USA/CHN/DEU/IND', indicatorName: 'electricity_demand_per_capita', countryCodesCsv: 'RUS,USA,CHN,DEU,IND', yearFrom: 2000, yearTo: 2024 }
]
const readyDashboardPresets = [
  { id: 'ready-carbon', title: 'CO2-интенсивность электроэнергии', subtitle: 'Сравнение декарбонизации', indicatorName: 'carbon_intensity_elec', countryCodesCsv: 'RUS,USA,CHN,DEU,IND', yearFrom: 2000, yearTo: 2024 },
  { id: 'ready-fossil', title: 'Доля ископаемой генерации', subtitle: 'Структура энергомикса', indicatorName: 'fossil_share_elec', countryCodesCsv: 'RUS,USA,CHN,DEU,IND', yearFrom: 2000, yearTo: 2024 },
  { id: 'ready-renew', title: 'Доля ВИЭ в генерации', subtitle: 'Рост чистой энергии', indicatorName: 'renewables_share_elec', countryCodesCsv: 'RUS,USA,CHN,DEU,IND', yearFrom: 2000, yearTo: 2024 },
  { id: 'ready-demand', title: 'Спрос на электроэнергию на душу', subtitle: 'Сопоставление нагрузки стран', indicatorName: 'electricity_demand_per_capita', countryCodesCsv: 'RUS,USA,CHN,DEU,IND', yearFrom: 2000, yearTo: 2024 }
]

const analysisPresets = [
  {
    id: 'reg-carbon-intensity',
    title: 'Углеродная интенсивность электроэнергии и доли в генерации',
    method: 'linreg',
    target: 'carbon_intensity_elec',
    featuresCsv: 'coal_share_elec,gas_share_elec,oil_share_elec,renewables_share_elec,fossil_share_elec,year',
    allowBinning: true,
    bins: 3
  },
  {
    id: 'reg-energy-gdp',
    title: 'Насколько «тяжёлая по энергии» экономика относительно ВВП',
    method: 'linreg',
    target: 'energy_per_gdp',
    featuresCsv: 'fossil_share_elec,renewables_share_elec,electricity_demand_per_capita,primary_energy_consumption,year',
    allowBinning: true,
    bins: 3
  },
  {
    id: 'cls-fossil-dependence',
    title: 'Группы стран по доле ископаемых в электроэнергии',
    method: 'rf',
    target: 'fossil_share_elec',
    featuresCsv: 'coal_share_elec,gas_share_elec,oil_share_elec,renewables_share_elec,carbon_intensity_elec,year',
    allowBinning: true,
    bins: 3
  },
  {
    id: 'cls-electricity-demand',
    title: 'Группы стран по электропотреблению на человека',
    method: 'svm',
    target: 'electricity_demand_per_capita',
    featuresCsv: 'energy_per_capita,per_capita_electricity,energy_per_gdp,fossil_share_elec,year',
    allowBinning: true,
    bins: 4
  },
  {
    id: 'km-energy-panel',
    title: 'Похожие страны по энергетическим показателям (несколько групп)',
    method: 'kmeans',
    target: '',
    featuresCsv:
      'fossil_fuel_consumption,renewables_consumption,carbon_intensity_elec,electricity_demand_per_capita,wb_eg_fec_rnew_zs',
    allowBinning: true,
    bins: 3,
    n_clusters: 5
  }
]

const latestCountryValues = computed(() => {
  const chart = countryDashChart.value
  if (!chart?.datasets?.length || !chart?.years?.length) return []
  return chart.datasets.map(ds => {
    let year = null
    let value = null
    for (let i = chart.years.length - 1; i >= 0; i -= 1) {
      const v = ds.data?.[i]
      if (v !== null && v !== undefined) {
        year = chart.years[i]
        value = Number(v).toFixed(3)
        break
      }
    }
    return { country_code: ds.country_code || ds.label, year, value }
  })
})

const countryChartGeometry = computed(() => {
  const chart = countryDashChart.value
  return buildCountrySeriesGeometry(chart, 720, 300)
})

function buildCountrySeriesGeometry(chart, width = 720, height = 300) {
  const pad = { left: 45, right: 20, top: 12, bottom: 28 }
  const plot = { left: pad.left, right: width - pad.right, top: pad.top, bottom: height - pad.bottom }
  if (!chart?.years?.length || !chart?.datasets?.length) return { plot, series: [] }

  const vals = []
  chart.datasets.forEach(ds => (ds.data || []).forEach(v => {
    if (v !== null && v !== undefined && Number.isFinite(Number(v))) vals.push(Number(v))
  }))
  const minVal = vals.length ? Math.min(...vals) : 0
  const maxVal = vals.length ? Math.max(...vals) : 1
  const ySpan = Math.max(1e-9, maxVal - minVal)
  const xSpan = Math.max(1, chart.years.length - 1)
  const colorMap = ['#1f6feb', '#d63384', '#198754', '#fd7e14', '#6f42c1', '#20c997', '#dc3545']

  const series = chart.datasets.map((ds, idx) => {
    const points = (ds.data || [])
      .map((v, i) => {
        if (v === null || v === undefined || !Number.isFinite(Number(v))) return null
        const x = plot.left + (i / xSpan) * (plot.right - plot.left)
        const y = plot.bottom - ((Number(v) - minVal) / ySpan) * (plot.bottom - plot.top)
        return `${x.toFixed(2)},${y.toFixed(2)}`
      })
      .filter(Boolean)
      .join(' ')
    return { countryCode: ds.country_code || ds.label || `S${idx + 1}`, points, color: colorMap[idx % colorMap.length] }
  })
  return { plot, series }
}

const uploadForm = reactive({
  name: '',
  file: null,
  csvText: ''
})
const fileRef = ref(null)
const uploadLoading = ref(false)
const uploadError = ref(null)
const uploadOk = ref('')

let pollTimer = null

const classificationMethods = new Set(['logreg', 'svm', 'rf', 'nb'])

const metricsJsonSansPredictions = computed(() => {
  const m = result.value?.metrics_json
  if (!m || typeof m !== 'object') return null
  return Object.fromEntries(
    Object.entries(m).filter(([k]) => k !== 'predictions' && k !== 'predictions_meta')
  )
})

const metricsJsonFormatted = computed(() => {
  const m = metricsJsonSansPredictions.value
  if (!m || !Object.keys(m).length) return ''
  return JSON.stringify(m, null, 2)
})

function fmtPlainPct(x) {
  if (x == null || !Number.isFinite(Number(x))) return '—'
  return `${(Number(x) * 100).toFixed(1)}%`
}

function fmtPlainNum(x, digits = 3) {
  if (x == null || !Number.isFinite(Number(x))) return '—'
  return Number(x).toFixed(digits)
}

/** Объяснение результатов простым языком для пользователей без опыта в ML. */
const resultPlainSummary = computed(() => {
  const m = result.value?.metrics_json
  if (!m || typeof m !== 'object') return null
  const tt = m.task_type

  if (tt === 'regression') {
    const r2 = Number(m.r2)
    let quality = ''
    if (Number.isFinite(r2)) {
      if (r2 >= 0.7) {
        quality =
          'По этим данным модель довольно уверенно улавливает закономерность: прогнозы можно использовать как ориентир.'
      } else if (r2 >= 0.3) {
        quality =
          'Связь между признаками и целевым показателем есть, но разброс большой — трактуйте прогнозы осторожно.'
      } else {
        quality =
          'Связь слабая: модель почти не объясняет изменения целевого показателя; имеет смысл изменить признаки, период или метод.'
      }
    }
    return {
      title: 'Оценка показателя по странам и годам',
      lead:
        'Для каждой строки таблицы программа сравнивает значение из базы и своё приближённое значение по связям между показателями. Это не официальный прогноз правительства — просто автоматическая оценка.',
      bullets: [
        `Насколько расчёт «ложится» на данные (шкала от 0 до 1, чем выше — тем лучше): ${fmtPlainNum(r2, 3)}.`,
        `Типичное отличие от данных — около ${fmtPlainNum(m.mae)} в тех же единицах, что и показатель; крупные промахи учитываются сильнее — ориентир ${fmtPlainNum(m.rmse)}.`,
      ],
      quality,
      nextSteps: [
        'Смотрите таблицу «Страны и годы» — там рядом стоят «как в базе» и «оценка расчёта».',
        'Для спокойного сравнения стран удобнее вкладка «Графики по странам».',
        'Не стоит принимать решения только по этой автоматической таблице.',
      ],
    }
  }

  if (tt === 'classification') {
    const acc = Number(m.accuracy)
    let quality = ''
    if (Number.isFinite(acc)) {
      if (acc >= 0.85) {
        quality = 'На отложенной выборке модель часто угадывает класс — разбиение можно использовать как первичный ориентир.'
      } else if (acc >= 0.6) {
        quality = 'Точность средняя: классы различимы не идеально, путаница между соседними уровнями нормальна.'
      } else {
        quality = 'Точность низкая: по этим признакам классы плохо отделяются; результат скорее для эксперимента, чем для решений.'
      }
    }
    const binNote = m.target_binned
      ? ' Показатель был числом, поэтому его автоматически разложили на несколько «ступеней».'
      : ''
    return {
      title: 'Разбиение стран по уровням',
      lead:
        `Каждая строка попала в одну из условных групп.${binNote} Это упрощённая картина для сравнения, не юридический факт.`,
      bullets: [
        `В тестовой части данных модель совпала примерно в ${fmtPlainPct(acc)} случаев.`,
      ],
      quality,
      nextSteps: [
        'В таблице ниже сравните номер группы «как в базе» и «по расчёту».',
        'Цветная таблица показывает, где чаще путаются уровни.',
      ],
    }
  }

  if (tt === 'clustering') {
    const k = m.n_clusters
    return {
      title: 'Что это значит: похожие группы',
      lead: `Строки данных (например, страна×год) разбиты на ${fmtPlainNum(k, 0)} групп так, чтобы внутри группы объекты были похожи по выбранным числовым признакам. Номера кластеров условные: «кластер 2» не хуже «кластера 0», это просто разные профили.`,
      bullets: [
        `Всего строк: ${m.n_samples != null ? fmtPlainNum(m.n_samples, 0) : '—'}.`,
        `Использовано признаков: ${m.n_features != null ? fmtPlainNum(m.n_features, 0) : '—'}.`,
        'Таблица распределения показывает, насколько группы по размеру похожи друг на друга.',
      ],
      quality:
        'Чтобы понять «кто такие» кластеры, посмотрите, какие страны чаще попадают в одну группу, или посчитайте средние признаков по кластеру в Excel/Google Таблицах — так появляется содержательная интерпретация.',
      nextSteps: [
        'Используйте колонку «Группа (кластер)» как метку профиля при отчётах или фильтрах.',
        'Поменяйте число кластеров или набор признаков и запустите анализ снова — иногда выделяются более понятные профили.',
      ],
    }
  }

  return null
})

const predictionColumnSet = computed(() => {
  const preds = result.value?.metrics_json?.predictions
  if (!preds?.length) return new Set()
  return new Set(Object.keys(preds[0]))
})

/** Элементы charts_json с предвычисленной геометрией для SVG (избегаем десятков вызовов в шаблоне). */
const analysisCharts = computed(() => {
  const list = result.value?.charts_json?.charts
  if (!Array.isArray(list)) return []
  return list.map(ch => ({
    ...ch,
    _clusterGeom:
      ch.chartType === 'clusterBars' && Array.isArray(ch.data)
        ? buildClusterBarsChart(ch.data)
        : null,
  }))
})

const showSwitchToLinreg = computed(() => {
  return classificationMethods.has(runForm.method) && runForm.target.trim().toLowerCase() === 'target'
})

const methodHint = computed(() => {
  if (!runForm.target.trim()) return ''
  if (showSwitchToLinreg.value) {
    return 'Для колонки «target» при разбиении на группы лучше подойдёт оценка числом — см. кнопку ниже.'
  }
  if (runForm.method === 'linreg' && runForm.target.trim().toLowerCase() === 'label') {
    return 'Если в данных классы «label», выберите в параметрах способ «Разделить на классы».'
  }
  return ''
})

function toNumber(value) {
  const n = Number(value)
  return Number.isFinite(n) ? n : 0
}

function heatmapCellStyle(matrix, value) {
  const allValues = (matrix || []).flat().map(toNumber)
  const maxValue = Math.max(1, ...allValues)
  const ratio = Math.max(0, toNumber(value)) / maxValue
  const alpha = 0.15 + ratio * 0.75
  return {
    backgroundColor: `rgba(13, 110, 253, ${alpha.toFixed(3)})`,
    color: ratio > 0.55 ? '#fff' : '#111'
  }
}

function buildRegressionChart(pairs) {
  const width = 560
  const height = 260
  const pad = { left: 45, right: 20, top: 15, bottom: 30 }
  const cleaned = (pairs || [])
    .map(p => ({ yTrue: toNumber(p?.y_true), yPred: toNumber(p?.y_pred) }))
    .filter(p => Number.isFinite(p.yTrue) && Number.isFinite(p.yPred))

  if (!cleaned.length) {
    return {
      points: [],
      plot: { left: pad.left, right: width - pad.right, top: pad.top, bottom: height - pad.bottom },
      line: { x1: pad.left, y1: height - pad.bottom, x2: width - pad.right, y2: pad.top },
      min: 0,
      max: 0
    }
  }

  const values = cleaned.flatMap(p => [p.yTrue, p.yPred])
  const minVal = Math.min(...values)
  const maxVal = Math.max(...values)
  const span = Math.max(1e-9, maxVal - minVal)
  const xScale = v => pad.left + ((v - minVal) / span) * (width - pad.left - pad.right)
  const yScale = v => height - pad.bottom - ((v - minVal) / span) * (height - pad.top - pad.bottom)

  return {
    points: cleaned.map(p => ({ x: xScale(p.yTrue), y: yScale(p.yPred) })),
    plot: { left: pad.left, right: width - pad.right, top: pad.top, bottom: height - pad.bottom },
    line: { x1: xScale(minVal), y1: yScale(minVal), x2: xScale(maxVal), y2: yScale(maxVal) },
    min: minVal,
    max: maxVal
  }
}

function buildClusterBarsChart(rows) {
  const width = 520
  const height = 280
  const pad = { left: 56, right: 18, top: 20, bottom: 54 }
  const plot = {
    left: pad.left,
    right: width - pad.right,
    top: pad.top,
    bottom: height - pad.bottom,
  }
  const items = (rows || [])
    .map(r => ({
      cluster: r.cluster,
      count: Math.max(0, Number(r.count)),
    }))
    .filter(r => Number.isFinite(r.count))

  if (!items.length) {
    return { plot, bars: [], width, height, maxCount: 0 }
  }

  const maxCount = Math.max(...items.map(i => i.count), 1)
  const n = items.length
  const innerW = plot.right - plot.left
  const slot = innerW / Math.max(n, 1)
  const barWidth = Math.max(16, slot * 0.72)

  const palette = ['#1f6feb', '#d63384', '#198754', '#fd7e14', '#6f42c1', '#20c997', '#dc3545']

  const bars = items.map((item, idx) => {
    const cx = plot.left + idx * slot + (slot - barWidth) / 2
    const norm = maxCount > 0 ? item.count / maxCount : 0
    const rawH = norm * (plot.bottom - plot.top)
    const h = item.count === 0 ? 0 : Math.max(rawH, 4)
    const x = cx
    const y = plot.bottom - h
    const labelX = cx + barWidth / 2
    const countTy = item.count === 0 ? plot.bottom - 14 : Math.max(plot.top + 12, y - 6)
    return {
      x,
      y,
      w: barWidth,
      h,
      cluster: item.cluster,
      count: item.count,
      labelX,
      countTy,
      clusterTy: plot.bottom + 36,
      clusterLabel: `Группа ${item.cluster}`,
      fill: palette[idx % palette.length],
    }
  })

  return { plot, bars, width, height, maxCount }
}

function applyCountryPreset(id) {
  const preset = countryDashPresets.find(p => p.id === id)
  if (!preset) return
  countryDashForm.indicatorName = preset.indicatorName
  countryDashForm.countryCodesCsv = preset.countryCodesCsv
  countryDashForm.yearFrom = preset.yearFrom
  countryDashForm.yearTo = preset.yearTo
  loadCountryDashboardChart()
}

async function loadCountryDashboardChart() {
  countryDashLoading.value = true
  countryDashError.value = null
  try {
    const countryCodes = countryDashForm.countryCodesCsv
      .split(',')
      .map(c => c.trim().toUpperCase())
      .filter(Boolean)
      .join(',')
    if (!countryCodes) throw new Error('Укажите хотя бы один код страны')
    const res = await apiClient.get(endpoints.datasetChartData, {
      indicator_name: countryDashForm.indicatorName,
      country_codes: countryCodes,
      year_from: Number(countryDashForm.yearFrom) || 1990,
      year_to: Number(countryDashForm.yearTo) || 2030
    })
    countryDashChart.value = res?.data ?? res
  } catch (e) {
    countryDashError.value = e?.response?.data?.error || e?.message || 'Ошибка построения графика по странам'
  } finally {
    countryDashLoading.value = false
  }
}

async function loadReadyDashboardCards() {
  readyDashboardLoading.value = true
  readyDashboardError.value = null
  try {
    const responses = await Promise.all(
      readyDashboardPresets.map(async preset => {
        const res = await apiClient.get(endpoints.datasetChartData, {
          indicator_name: preset.indicatorName,
          country_codes: preset.countryCodesCsv,
          year_from: preset.yearFrom,
          year_to: preset.yearTo
        })
        const chart = res?.data ?? res
        return {
          ...preset,
          chart,
          geometry: buildCountrySeriesGeometry(chart, 640, 220)
        }
      })
    )
    readyDashboardCards.value = responses
  } catch (e) {
    readyDashboardError.value = e?.response?.data?.error || e?.message || 'Ошибка загрузки виджетов дашборда'
  } finally {
    readyDashboardLoading.value = false
  }
}

async function loadCustomDatasets() {
  customLoading.value = true
  try {
    const res = await apiClient.get(endpoints.analysisCustomDatasets)
    customDatasets.value = res?.data?.results ?? res?.data ?? res ?? []
  } finally {
    customLoading.value = false
  }
}

function onPickFile(e) {
  uploadError.value = null
  uploadOk.value = ''
  const f = e.target.files?.[0]
  uploadForm.file = f || null
}

async function uploadCustom() {
  uploadLoading.value = true
  uploadError.value = null
  uploadOk.value = ''
  try {
    const file = uploadForm.file
    if (!file) throw new Error('Выберите файл')
    const text = await file.text()
    const payload = { name: uploadForm.name, content_csv: text, schema_json: null }
    const res = await apiClient.post(endpoints.analysisCustomDatasets, payload)
    uploadOk.value = 'Датасет загружен'
    uploadForm.file = null
    if (fileRef.value) fileRef.value.value = ''
    await loadCustomDatasets()
    return res
  } catch (e) {
    uploadError.value = e?.response?.data?.detail || e?.response?.data?.error || e?.message || 'Ошибка загрузки'
  } finally {
    uploadLoading.value = false
  }
}

function buildRunPayload() {
  const features = runForm.featuresCsv
    ? runForm.featuresCsv.split(',').map(s => s.trim()).filter(Boolean)
    : []
  const payload = {
    method: runForm.method,
    target: runForm.method === 'kmeans' ? '' : runForm.target,
    features,
    dataset_id: runForm.datasetId || null,
    classification: {
      allow_binning: Boolean(runForm.allowBinning),
      bins: Number(runForm.bins) || 3
    },
    coefficients: {},
    metrics: []
  }
  if (runForm.method === 'kmeans') {
    payload.n_clusters = Math.min(40, Math.max(2, Number(runForm.n_clusters) || 5))
  }
  return payload
}

function applyPreset() {
  const preset = analysisPresets.find(p => p.id === selectedPresetId.value)
  if (!preset) return
  runForm.method = preset.method
  runForm.target = preset.target
  runForm.featuresCsv = preset.featuresCsv
  runForm.allowBinning = Boolean(preset.allowBinning)
  runForm.bins = Number(preset.bins) || 3
  if (preset.n_clusters != null) runForm.n_clusters = Number(preset.n_clusters) || 5
  runError.value = null
}

async function startRun() {
  if (runForm.method !== 'kmeans' && !runForm.target.trim()) {
    runError.value = 'Укажите target'
    return
  }

  runLoading.value = true
  runError.value = null
  result.value = null
  try {
    const payload = buildRunPayload()
    const res = await apiClient.post(endpoints.analysisRuns, payload)
    const data = res?.data ?? res
    currentRun.value = data
    schedulePoll()
  } catch (e) {
    runError.value = e?.response?.data?.error || e?.message || 'Ошибка запуска анализа'
  } finally {
    runLoading.value = false
  }
}

function switchToLinreg() {
  runForm.method = 'linreg'
  runError.value = null
}

function runId() {
  return currentRun.value?.run_id
}

async function refreshStatus() {
  const id = runId()
  if (!id) return
  statusLoading.value = true
  try {
    const res = await apiClient.get(`${endpoints.analysisRuns}${id}/status/`)
    const data = res?.data ?? res
    currentRun.value = { ...currentRun.value, status: data.status }
    if (data.status === 'done') {
      clearPoll()
    }
  } finally {
    statusLoading.value = false
  }
}

async function loadResult() {
  const id = runId()
  if (!id) return
  resultLoading.value = true
  try {
    const res = await apiClient.get(`${endpoints.analysisRuns}${id}/result/`)
    result.value = res?.data ?? res
  } finally {
    resultLoading.value = false
  }
}

function schedulePoll() {
  clearPoll()
  pollTimer = setInterval(async () => {
    await refreshStatus()
    if (currentRun.value?.status === 'done') {
      await loadResult()
      clearPoll()
    }
  }, 2000)
}

function clearPoll() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

onMounted(async () => {
  await Promise.all([loadCustomDatasets(), loadCountryDashboardChart(), loadReadyDashboardCards()])
})

onBeforeUnmount(() => {
  clearPoll()
})
</script>

<style scoped>
.subtitle { color: #666; margin-bottom: 1rem; }
.mode-switch { display: flex; gap: 8px; flex-wrap: wrap; }
.hint { color: #666; }
.stat { background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; padding: 12px; }
.stat__label { font-size: 0.85rem; color: #666; }
.stat__value { font-size: 1.5rem; font-weight: 700; }
.pre { background: #0b1020; color: #e6edf3; padding: 12px; border-radius: 8px; overflow: auto; }
.chart__title { font-weight: 700; }
.chart__desc { color: #444; }
.chart__legend { color: #555; font-size: 0.9rem; }
.heatmap-grid { display: inline-flex; flex-direction: column; border: 1px solid #dbe3ef; border-radius: 6px; overflow: hidden; margin-bottom: 0.75rem; }
.heatmap-row { display: flex; }
.heatmap-cell { min-width: 56px; text-align: center; padding: 8px 10px; border-right: 1px solid rgba(255, 255, 255, 0.35); border-bottom: 1px solid rgba(255, 255, 255, 0.35); font-weight: 600; }
.scatter-wrap { border: 1px solid #dbe3ef; border-radius: 8px; padding: 10px 12px; margin-bottom: 0.75rem; background: #fff; }
.scatter-svg { width: 100%; max-width: 560px; height: auto; display: block; }
.country-chart-wrap { border: 1px solid #dbe3ef; border-radius: 8px; padding: 10px 12px; background: #fff; }
.country-chart-svg { width: 100%; max-width: 720px; height: auto; display: block; }
.mini-card { border: 1px solid #e6ecf3; border-radius: 8px; padding: 10px 12px; height: 100%; background: #fcfdff; }
.mini-card__title { font-weight: 700; color: #1b2734; }
.country-legend { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 8px; }
.legend-item { display: inline-flex; align-items: center; gap: 6px; font-size: 0.9rem; color: #46566a; }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.axis { stroke: #8ea0b5; stroke-width: 1; }
.axis-label { fill: #46566a; font-size: 11px; font-weight: 600; }
.axis-note { fill: #607080; font-size: 10px; }
.ideal-line { stroke: #1f6feb; stroke-width: 1.5; stroke-dasharray: 6 4; }
.scatter-point { fill: #d63384; opacity: 0.9; }
.cluster-bars-wrap {
  border: 1px solid #dbe3ef;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 0.75rem;
  background: #fff;
}
.cluster-bars-svg { width: 100%; max-width: 520px; height: auto; display: block; }
.cluster-bar-rect { opacity: 0.92; }
.cluster-bar-count { fill: #1b2734; font-size: 11px; font-weight: 700; }
.cluster-bar-cluster-label { font-size: 11px; }
.cluster-axis-tick { fill: #607080; font-size: 10px; }
.predictions-scroll { max-height: 420px; overflow: auto; }
.metrics-details summary { cursor: pointer; }
.analysis-expert-details summary { cursor: pointer; }
.result-plain ul:last-of-type { margin-bottom: 0; }
</style>

