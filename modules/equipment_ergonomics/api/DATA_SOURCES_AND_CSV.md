# Внешние API, сохранение в БД и работа с CSV

## Как добавить новые данные к имеющимся

### Важно: как не удалять старые данные

- **World Bank** и **импорт из файлов** (`--import`, `--file-import`) **никогда не удаляют** существующие записи: они только добавляют новые или обновляют по (страна, год, показатель). Ваши текущие данные OWID останутся.
- **Перезагрузка OWID** (при `--source owid` или `--source all`) **удаляет все записи с источником «OWID Energy»** и заливает их заново. Используйте её только когда нужно обновить именно OWID.

**Чтобы только добавить новые источники, не трогая уже загруженные данные:**

| Что добавить   | Команда | Старые данные (OWID и др.) |
|----------------|---------|----------------------------|
| Только World Bank | `ergoms api build_equipment_dataset --source world_bank` | Не удаляются |
| Только из файла   | `ergoms api build_equipment_dataset --file-import путь.csv --file-source ключ` или `--import путь.csv` | Не удаляются |
| World Bank + экспорт в CSV | `ergoms api build_equipment_dataset --source world_bank --export-default` | Не удаляются |

Не используйте `--source all`, если не хотите перезаписать OWID: при `--source all` сначала выполняется загрузка OWID (с удалением старых записей OWID), затем World Bank.

---

**Вариант A — данные из API (World Bank)**  
Добавляет показатели World Bank к уже имеющимся (OWID не трогает):

```bash
# Только добавить World Bank (OWID и остальное остаётся)
ergoms api build_equipment_dataset --source world_bank

# То же и сразу экспорт сводного CSV
ergoms api build_equipment_dataset --source world_bank --export-default
```

**Вариант B — данные из готового файла (CSV или JSON)**  

1. **Скачайте или положите файл** в репозиторий, предпочтительно в `modules/equipment_ergonomics/data/raw/` (или `data/processed/` для уже обработанных CSV).

2. **Если в файле уже есть колонки** `country_code`, `year`, `indicator_name`, `value` (и при необходимости `unit`, `equipment_class_code`, `source_notes`) — импортируйте без конфига:
   ```bash
   ergoms api build_equipment_dataset --import путь/к/файлу.csv
   ```

3. **Если названия колонок другие** — задайте маппинг в коде:
   - Откройте `modules/equipment_ergonomics/api/scripts/build_dataset.py`.
   - В словарь **`FILE_SOURCE_CONFIG`** добавьте запись (например для e-waste):
     - ключ — короткое имя источника, например `'ewaste'`;
     - `name` — человекочитаемое имя (попадёт в колонку «Источник»);
     - `format` — `'csv'` или `'json'`;
     - `delimiter` — для CSV: `','` или `';'`;
     - `columns` — соответствие «наше поле → имя колонки в файле» (как в примере в конфиге);
     - `default_equipment_class_code` — код класса техники из справочника (`e_waste_hazardous`, `cooling`, `mercury_containing` и т.д.);
     - `default_unit` — единица по умолчанию, если в файле нет.
   - Выполните:
     ```bash
     ergoms api build_equipment_dataset --file-import путь/к/файлу.csv --file-source ewaste
     ```
   - При необходимости сохранить сырой файл в БД добавьте флаг: `--file-save-raw`.

4. **Сводный CSV** со всеми данными (OWID + World Bank + импортированные файлы) получите командой:
   ```bash
   ergoms api build_equipment_dataset --export-only modules/equipment_ergonomics/data/equipment_dataset.csv
   ```

Поддерживаемые классы техники для `equipment_class_code`: `energy_aggregate`, `energy_coal`, `energy_gas`, `energy_oil`, `energy_nuclear`, `energy_renewables`, `energy_fossil`, `energy_low_carbon`, `energy_electricity`, `energy_emissions`, `cooling`, `mercury_containing`, `heavy_metals_batteries`, `halogenated_pfas`, `e_waste_hazardous`, `household_other`, `lighting`, `ict_consumer`, `e_cooking`.

---

## Сборка общего датасета

Общий датасет, с которым ведётся работа в модуле, собирается командой и скриптами, затем экспортируется в CSV.

### Plugin lifecycle

Плагин **выключен по умолчанию**. Пока он выключен, доступ к API эндпоинтам датасета отсутствует (модуль «невидим»), а `build_equipment_dataset` не запускается без явного флага.

```bash
# статус / включение / выключение
ergoms api equipment_ergonomics_plugin status
ergoms api equipment_ergonomics_plugin enable
ergoms api equipment_ergonomics_plugin disable --archive

# форсировать сборку даже когда выключен (например, для восстановления после деплоя)
ergoms api build_equipment_dataset --force-when-disabled --export-default
```

### Команда Django

```bash
# Загрузить OWID Energy в БД и экспортировать CSV в каталог модуля (data/equipment_dataset.csv)
ergoms api build_equipment_dataset --export-default

# То же с явным путём
ergoms api build_equipment_dataset --export modules/equipment_ergonomics/data/equipment_dataset.csv

# Только загрузить в БД, без экспорта
ergoms api build_equipment_dataset

# Только экспорт текущих данных из БД в CSV
ergoms api build_equipment_dataset --export-only modules/equipment_ergonomics/data/equipment_dataset.csv

# Импорт датасета из CSV в БД
ergoms api build_equipment_dataset --import path/to/dataset.csv

# Не сохранять сырой ответ API (экономия места в БД)
ergoms api build_equipment_dataset --no-raw --export-default

# Ограничить число строк из OWID (для проверки)
ergoms api build_equipment_dataset --max-rows 5000 --export test.csv

# Заполнить единицы и класс техники у уже загруженных записей OWID (без повторной загрузки)
ergoms api build_equipment_dataset --backfill-owid

# Загрузить только World Bank API (без OWID)
ergoms api build_equipment_dataset --source world_bank

# Загрузить OWID + World Bank, затем экспорт в CSV
ergoms api build_equipment_dataset --source all --export-default

# Импорт из готового файла по конфигу (CSV/JSON с маппингом колонок и классом техники)
ergoms api build_equipment_dataset --file-import modules/equipment_ergonomics/data/raw/ewaste.csv --file-source ewaste
# Опционально сохранить сырое содержимое файла в БД:
ergoms api build_equipment_dataset --file-import modules/equipment_ergonomics/data/raw/ewaste.csv --file-source ewaste --file-save-raw

# World Bank из локальных CSV (положите API_*_DS2_*.csv в data/raw модуля; при отсутствии — ищется core/data/raw)
ergoms api build_equipment_dataset --world-bank-from-raw
```

### Формат CSV общего датасета

**Экспорт** — колонки: `country_code`, `year`, `indicator_name`, `value`, `unit`, `equipment_class_code`, `source_notes`.

**Импорт** — те же колонки (часть можно опустить). Обязательные: `country_code`, `indicator_name`; при наличии `year` и `value` данные записываются в `EquipmentMetricByCountry`. При повторном импорте записи с тем же (country_code, year, indicator_name) обновляются.

При загрузке OWID: для каждой тройки (страна, год, показатель) хранится одна запись (дубликаты не создаются); заполняются поля «Единица» и «Класс техники» (подклассы энергетики: уголь, газ, ВИЭ, электроэнергия и т.д.); нулевые значения по умолчанию не записываются. Перед повторной загрузкой OWID старые записи с источником «OWID Energy» удаляются.

### Источники данных

Данные берутся **только из API (запрос → сохранение в БД) или из готовых структур (CSV/JSON/Excel → импорт в БД)**. Парсинг произвольных страниц не используется.

1. **API-источники** (ответ сохраняется в `ExternalDataFetch`, затем разбирается в `EquipmentMetricByCountry`):
   - **OWID Energy** — по умолчанию при `--source owid` или `--source all`. URL: Our World in Data, энергетические показатели по странам и годам (CSV по HTTP).
   - **World Bank API** — при `--source world_bank` или `--source all`. Запрос к `api.worldbank.org/v2/...` (JSON). Показатели: потребление электроэнергии на душу, доступ к электричеству, доля ВИЭ, выбросы CO₂ на душу и др. Сохраняются с префиксом `wb_` в `indicator_name` и привязкой к классам энергетики.

2. **Файловые источники** (готовые CSV или JSON с известной структурой):
   - **Универсальный импорт** — `--import path/to/file.csv`: колонки `country_code`, `year`, `indicator_name`, `value` (и при необходимости `unit`, `equipment_class_code`, `source_notes`). Подходит для любого CSV в этом формате.
   - **Структурированный импорт по конфигу** — `--file-import path --file-source KEY`: файл разбирается по конфигу `FILE_SOURCE_CONFIG` в `build_dataset.py`. В конфиге задаются маппинг колонок файла на поля (`country_code`, `year`, `indicator_name`, `value`, `unit`, `equipment_class_code`) и класс техники по умолчанию. Так можно подключать датасеты e-waste, ртуть, охлаждение и т.д., не меняя код парсера — достаточно добавить запись в `FILE_SOURCE_CONFIG` и положить файл (CSV/JSON) в репозиторий или указать путь. Опционально `--file-save-raw` сохраняет содержимое файла в `ExternalDataFetch`.

После загрузки из любого источника данные попадают в одну таблицу `EquipmentMetricByCountry` и далее экспортируются в общий CSV командой `--export` или `--export-only`.

---

## Сохранение данных из внешних API в БД

При работе с внешними API **все получаемые данные сохраняются в БД**:

1. **Кэш ответов API** — модель `ExternalDataFetch`:
   - каждый запрос к внешнему источнику (World Bank, DHS, OWID, SE4All и т.д.) после выполнения сохраняется в БД;
   - поля: `source_name`, `request_url`, `fetched_at`, `response_body` (полное тело ответа — JSON или текст), `status_code`, `error_message`;
   - это позволяет не терять сырые данные, воспроизводить импорт и отлаживать маппинг.

2. **Нормализованные показатели** — модель `EquipmentMetricByCountry`:
   - разобранные по странам/годам/классам техники показатели сохраняются здесь;
   - опциональная связь `source_fetch` с записью `ExternalDataFetch` указывает на запрос, из которого получены данные.

Рекомендуемый поток при загрузке из API:

- Выполнить запрос → сохранить ответ в `ExternalDataFetch` → распарсить и заполнить `EquipmentMetricByCountry` (и при необходимости другие таблицы) → при импорте из CSV перезаписывать/дополнять только нормализованные таблицы, не трогая кэш API.

## Данные в БД и на фронте

- Показатели хранятся в БД в таблице `EquipmentMetricByCountry`. Команда `build_equipment_dataset` при загрузке OWID записывает их в эту таблицу.
- API: `GET equipment_ergonomics/dataset/` — список с пагинацией и фильтрами (`country_code`, `year`, `equipment_class_code`). Ответ содержит человекочитаемые поля: `indicator_label`, `equipment_class_name`.
- Фронт (страница «Эргономика техники»): таблица с колонками «Страна (код)», «Год», «Показатель», «Значение», «Единица», «Класс техники», «Источник»; фильтры по коду страны, году и классу техники; импорт CSV в БД через форму.

---

## Итоговая работа с CSV

**Итоговая работа ведётся с CSV** в следующем смысле:

- **Экспорт:** агрегированные данные (показатели по странам, классам, годам, тренды) экспортируются в CSV для отчётов, передачи и анализа во внешних инструментах.
- **Импорт:** сводные датасеты из открытых источников (OWID, World Bank и т.д.), полученные в виде CSV, загружаются в БД (в т.ч. в `EquipmentMetricByCountry`) через скрипты импорта; при этом формат CSV считается основным для обмена такими сводками.

То есть: API → всегда сохранение в БД (кэш + нормализованные данные); обмен и финальная аналитика — в т.ч. через CSV (экспорт/импорт).

## Неэкологичные классы техники

В модуле заведены классы электротехники с флагом `is_non_eco=True` и причиной неэкологичности (`non_eco_reason`):

| Код | Название |
|-----|----------|
| `cooling` | Охлаждающее оборудование (хладагенты) |
| `mercury_containing` | Ртутьсодержащее оборудование |
| `heavy_metals_batteries` | Оборудование с тяжёлыми металлами и батареями |
| `halogenated_pfas` | Оборудование с галогенированными веществами / ПФАС |
| `e_waste_hazardous` | Электроника с опасными веществами при утилизации |

Их можно использовать для фильтрации отчётов и трендов по «заведомо неэкологичной» технике.

## Какие классы сейчас заполняются данными

**Сейчас данные по энергетическим классам** приходят из двух API и при разборе привязываются к подклассам:

- **OWID Energy** (по умолчанию): Энергетика (агрегированные показатели), Уголь, Газ, Нефть, Ядерная энергия, ВИЭ, Ископаемое топливо, Низкоуглеродная энергия, Электроэнергия, Выбросы и углеродоёмкость.
- **World Bank API** (`--source world_bank` или `--source all`): показатели доступа к электричеству, потребление на душу, доля ВИЭ, выбросы CO₂ — те же классы энергетики.

**Данные по остальным классам** (охлаждение, ртуть, e-waste, бытовая техника, освещение, ИКТ) можно добавить:
- выгрузив готовый датасет в CSV/JSON с колонками country_code, year, indicator_name, value (и при необходимости unit, equipment_class_code);
- добавив запись в `FILE_SOURCE_CONFIG` в `build_dataset.py` с маппингом колонок и `default_equipment_class_code` (например `e_waste_hazardous`, `cooling`);
- запустив `ergoms api build_equipment_dataset --file-import путь/к/файлу.csv --file-source ключ`.

**Остальные классы из справочника** (охлаждающее оборудование, ртутьсодержащее, тяжёлые металлы/батареи, ПФАС, электроника при утилизации, бытовая техника, освещение, ИКТ, электроприготовление) **в текущем датасете пустые**: в OWID Energy нет показателей по типам оборудования (холодильники, кондиционеры, лампы, парк бытовой техники и т.д.).

Чтобы в них появились данные, нужно получить готовые датасеты (CSV/JSON/Excel) или использовать API, затем импортировать в БД (см. раздел «Как добавить новые данные»). Ниже — конкретные источники и что делать дальше.

### Охлаждающее оборудование (cooling)

| Источник | Как получить данные | Действие после получения |
|----------|----------------------|---------------------------|
| **IEA** | [Data & Statistics](https://www.iea.org/data-and-statistics) → Space cooling, Data browser. Бесплатный аккаунт → экспорт в CSV/Excel. | Привести к колонкам country_code (ISO3), year, indicator_name, value; положить CSV в репозиторий; добавить запись в `FILE_SOURCE_CONFIG` с `default_equipment_class_code: 'cooling'`; запустить `--file-import путь --file-source ключ`. |
| **Eurostat** | [Bulk download](https://ec.europa.eu/eurostat/databrowser/bulk?lang=en) — TSV/SDMX-CSV; или [API](https://ec.europa.eu/eurostat/web/main/data/web-services). Наборы по энергобалансу (например nrg_bal_c). | Скачать/запросить по API, преобразовать в формат country_code, year, indicator_name, value (при необходимости скриптом); импорт через `--file-import` с конфигом или `--import` если колонки уже стандартные. |

### E-waste при утилизации (e_waste_hazardous)

| Источник | Как получить данные | Действие после получения |
|----------|----------------------|---------------------------|
| **Global E-waste Monitor (ITU/UNITAR)** | [globalewaste.org](https://www.globalewaste.org), [ITU E-waste](https://www.itu.int/en/ITU-D/Environment/Pages/Toolbox/Global-Ewaste-Monitors.aspx). Отчёты (PDF); таблицы/данные по странам могут быть на сайте или по запросу. | Если есть CSV/Excel по странам и годам — привести к колонкам country_code, year, indicator_name, value; добавить в `FILE_SOURCE_CONFIG` с `default_equipment_class_code: 'e_waste_hazardous'`; `--file-import путь --file-source ewaste`. |
| **Eurostat** | Разделы по отходам (waste), электрооборудование. Bulk download / API. | Аналогично: CSV в нашем формате → `--file-import` с конфигом или `--import`. |

### Ртуть (mercury_containing)

| Источник | Как получить данные | Действие после получения |
|----------|----------------------|---------------------------|
| **UNEP / AMAP** | [AMAP Mercury emissions](https://www.amap.no/mercury-emissions/datasets) — гридданные (TXT/CSV по ячейкам), не «страна–год». | При необходимости агрегировать по странам (скриптом) в таблицу country_code, year, indicator_name, value; импорт через `--file-import` с классом `mercury_containing`. |

### Тяжёлые металлы/батареи (heavy_metals_batteries), ПФАС (halogenated_pfas)

Открытых готовых датасетов «страна–год» в одном месте мало; обычно — отраслевые отчёты, регистры. Если получите таблицу (CSV/Excel) с странами, годами и показателями: сохраните в формате country_code, year, indicator_name, value (и unit, source_notes при необходимости), добавьте конфиг в `FILE_SOURCE_CONFIG` с нужным `default_equipment_class_code` и выполните `--file-import путь --file-source ключ`.

### Бытовая техника, освещение, ИКТ, электроприготовление (household_other, lighting, ict_consumer, e_cooking)

| Источник | Как получить данные | Действие после получения |
|----------|----------------------|---------------------------|
| **IEA** | Data & Statistics → темы по зданиям, бытовым приборам, освещению. | Экспорт в CSV/Excel → приведение к нашему формату → `FILE_SOURCE_CONFIG` с нужным классом → `--file-import`. |
| **Eurostat** | Энергобаланс по секторам/продуктам, статистика домохозяйств. Bulk download / API. | То же: CSV в формате country_code, year, indicator_name, value → импорт. |

---

**Итого по недостающим классам:** ни один из этих источников не подключён в коде «из коробки». Шаги всегда одни и те же: (1) скачать или получить по API данные в CSV/JSON/Excel; (2) при необходимости преобразовать к колонкам country_code, year, indicator_name, value (и unit, equipment_class_code, source_notes); (3) при других названиях колонок — добавить запись в `FILE_SOURCE_CONFIG` в `build_dataset.py`; (4) выполнить `ergoms api build_equipment_dataset --file-import путь/к/файлу --file-source ключ` (или `--import путь`, если колонки уже стандартные). После этого данные появятся в БД и в экспорте CSV вместе с OWID и World Bank.
