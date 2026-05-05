/**
 * Локальный пересчёт сводного индекса по тем же формулам, что на API:
 * score = (Σ wᵢ·Sᵢ) / Σ wᵢ, где учитываются только показатели из components с wᵢ > 0.
 */

export function gradeForErgonomicsScore(score) {
  if (score == null || Number.isNaN(score)) return 'н/д'
  const s = Number(score)
  if (s >= 80) return 'высокая'
  if (s >= 65) return 'хорошая'
  if (s >= 50) return 'удовлетворительная'
  if (s >= 35) return 'низкая'
  return 'очень низкая'
}

export function roundScore(score) {
  if (score == null || Number.isNaN(score)) return null
  return Math.round(Number(score) * 100) / 100
}

/**
 * @param {Array<{ indicator_name: string, subscore: number, weight?: number, weight_default?: number }>} components
 * @param {Record<string, number|string>} weightsByIndicator — если ключа нет, берётся weight_default ?? weight
 */
export function computeCompositeFromComponents(components, weightsByIndicator) {
  if (!Array.isArray(components) || !components.length) {
    return {
      score: null,
      grade: 'н/д',
      sumWeights: 0,
      sumWeightedSubscores: 0,
      terms: []
    }
  }

  let sumW = 0
  let sumWS = 0
  const terms = []

  for (const c of components) {
    const key = c.indicator_name
    let wRaw = weightsByIndicator[key]
    if (wRaw === '' || wRaw == null) {
      wRaw = Number(c.weight_default ?? c.weight)
    } else {
      wRaw = Number(wRaw)
    }
    if (!Number.isFinite(wRaw) || wRaw <= 0) continue

    const sub = Number(c.subscore)
    if (!Number.isFinite(sub)) continue

    sumW += wRaw
    sumWS += wRaw * sub
    terms.push({
      indicator_name: key,
      label: c.label,
      subscore: sub,
      weight: wRaw,
      weighted_product: Math.round(sub * wRaw * 10000) / 10000
    })
  }

  if (sumW <= 0) {
    return {
      score: null,
      grade: 'н/д',
      sumWeights: 0,
      sumWeightedSubscores: 0,
      terms
    }
  }

  const raw = sumWS / sumW
  const score = Math.min(100, Math.max(0, raw))
  return {
    score: roundScore(score),
    grade: gradeForErgonomicsScore(score),
    sumWeights: Math.round(sumW * 1e6) / 1e6,
    sumWeightedSubscores: Math.round(sumWS * 1e6) / 1e6,
    terms
  }
}
