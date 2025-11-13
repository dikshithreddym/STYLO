export type SuggestHistoryEntry = {
  id: string
  text: string
  timestamp: number
  outfitItemIds: number[]
}

const FAVORITES_KEY = 'stylo.favorites.v1'
const HISTORY_KEY = 'stylo.suggest.history.v1'

export function getFavorites(): Set<number> {
  if (typeof window === 'undefined') return new Set()
  try {
    const raw = localStorage.getItem(FAVORITES_KEY)
    const arr: number[] = raw ? JSON.parse(raw) : []
    return new Set(arr)
  } catch {
    return new Set()
  }
}

export function toggleFavorite(id: number): Set<number> {
  const favs = getFavorites()
  if (favs.has(id)) {
    favs.delete(id)
  } else {
    favs.add(id)
  }
  if (typeof window !== 'undefined') {
    localStorage.setItem(FAVORITES_KEY, JSON.stringify(Array.from(favs)))
  }
  return favs
}

export function isFavorite(id: number): boolean {
  return getFavorites().has(id)
}

export function saveSuggestHistory(entry: SuggestHistoryEntry) {
  if (typeof window === 'undefined') return
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    const arr: SuggestHistoryEntry[] = raw ? JSON.parse(raw) : []
    const updated = [entry, ...arr].slice(0, 20)
    localStorage.setItem(HISTORY_KEY, JSON.stringify(updated))
  } catch {}
}

export function getSuggestHistory(): SuggestHistoryEntry[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}
