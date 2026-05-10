/**
 * Кэш GeoJSON карты мира в IndexedDB (localStorage недостаточен для ~15 МБ файла).
 */

const DB_NAME = 'equipment_ergonomics_geo_v1'
const DB_VERSION = 1
const STORE = 'kv'
const WORLD_KEY = 'world_geojson_v1'

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

export async function getCachedWorldGeoJson() {
  const db = await openDb()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readonly')
    const getReq = tx.objectStore(STORE).get(WORLD_KEY)
    getReq.onerror = () => reject(getReq.error)
    getReq.onsuccess = () => {
      resolve(getReq.result ?? null)
    }
    tx.oncomplete = () => db.close()
  })
}

export async function setCachedWorldGeoJson(geo) {
  const db = await openDb()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readwrite')
    tx.onerror = () => reject(tx.error)
    tx.objectStore(STORE).put(geo, WORLD_KEY)
    tx.oncomplete = () => {
      db.close()
      resolve()
    }
  })
}

/**
 * Одноразовая миграция из старого localStorage (если туда когда-то попало что-то валидное).
 */
export async function migrateWorldGeoJsonFromLocalStorage(legacyKey) {
  try {
    const raw = localStorage.getItem(legacyKey)
    if (!raw) return
    const parsed = JSON.parse(raw)
    if (!parsed?.features?.length) return
    await setCachedWorldGeoJson(parsed)
    localStorage.removeItem(legacyKey)
  } catch (_) {
    // игнорируем повреждённый или непереносимый кэш
  }
}
