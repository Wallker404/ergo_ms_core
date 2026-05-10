/**
 * Кэш предрасчёта индексов по странам для карты (IndexedDB).
 * Уменьшает число запросов при каждом открытии страницы.
 */

const DB_NAME = 'equipment_ergonomics_map_scores_v1'
const DB_VERSION = 1
const STORE = 'kv'

/** Увеличить при изменении формулы индекса на API — старый кэш игнорируется. */
export const MAP_SCORES_CACHE_SCHEMA_VERSION = 3

/** Срок хранения записей кэша (мс). */
export const MAP_SCORES_TTL_MS = 7 * 24 * 60 * 60 * 1000

function storageKey(year) {
  const y =
    year == null || year === '' || !Number.isFinite(Number(year)) ? 'auto' : String(Number(year))
  return `scores_${MAP_SCORES_CACHE_SCHEMA_VERSION}_${y}`
}

function openDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION)
    req.onerror = () => reject(req.error)
    req.onupgradeneeded = () => {
      const db = req.result
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE)
      }
    }
    req.onsuccess = () => resolve(req.result)
  })
}

/**
 * @param {number|null|undefined} year — как в форме «Год» карты (null = авто).
 * @returns {Promise<{ scores: Record<string, number>, savedAt: number, version: number } | null>}
 */
export async function getCachedMapScores(year) {
  try {
    const db = await openDb()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readonly')
      const getReq = tx.objectStore(STORE).get(storageKey(year))
      getReq.onerror = () => reject(getReq.error)
      getReq.onsuccess = () => {
        const row = getReq.result
        if (!row?.scores || typeof row.scores !== 'object') {
          resolve(null)
          return
        }
        if (Number(row.version) !== MAP_SCORES_CACHE_SCHEMA_VERSION) {
          resolve(null)
          return
        }
        resolve(row)
      }
      tx.oncomplete = () => db.close()
    })
  } catch (_) {
    return null
  }
}

/**
 * @param {number|null|undefined} year
 * @param {Record<string, number>} scores — ISO3 → балл 0–100
 */
export async function setCachedMapScores(year, scores) {
  try {
    const db = await openDb()
    const payload = {
      version: MAP_SCORES_CACHE_SCHEMA_VERSION,
      savedAt: Date.now(),
      year: Number.isFinite(Number(year)) ? Number(year) : null,
      scores: { ...scores },
    }
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite')
      tx.onerror = () => reject(tx.error)
      tx.objectStore(STORE).put(payload, storageKey(year))
      tx.oncomplete = () => {
        db.close()
        resolve()
      }
    })
  } catch (_) {
    // квота / приватный режим
  }
}

export async function deleteCachedMapScores(year) {
  try {
    const db = await openDb()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite')
      tx.onerror = () => reject(tx.error)
      tx.objectStore(STORE).delete(storageKey(year))
      tx.oncomplete = () => {
        db.close()
        resolve()
      }
    })
  } catch (_) {
    /* noop */
  }
}
