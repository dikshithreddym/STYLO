import { WardrobeItem } from './api'

const WARDROBE_CACHE_KEY = 'stylo.wardrobe.cache.v1'
const WARDROBE_CACHE_TTL = 3600000 // 1 hour in milliseconds
const SUGGESTION_CACHE_KEY = 'stylo.suggestions.cache.v1'
const SUGGESTION_CACHE_TTL = 300000 // 5 minutes in milliseconds
const FILTER_STATE_KEY = 'stylo.filters.state.v1'

interface CachedWardrobe {
  items: WardrobeItem[]
  timestamp: number
  total: number
}

interface CachedSuggestion {
  query: string
  result: any
  timestamp: number
}

interface FilterState {
  q?: string
  type?: string
  color?: string
  category?: string
  sort?: string
  page?: number
  pageSize?: number
}

/**
 * Wardrobe Cache - Client-side caching and filtering
 */
export const wardrobeCache = {
  /**
   * Get cached wardrobe items
   */
  getCached(): CachedWardrobe | null {
    if (typeof window === 'undefined') return null
    try {
      const raw = localStorage.getItem(WARDROBE_CACHE_KEY)
      if (!raw) return null
      const cached: CachedWardrobe = JSON.parse(raw)
      
      // Check if cache is expired
      const age = Date.now() - cached.timestamp
      if (age > WARDROBE_CACHE_TTL) {
        localStorage.removeItem(WARDROBE_CACHE_KEY)
        return null
      }
      
      return cached
    } catch {
      return null
    }
  },

  /**
   * Cache wardrobe items
   */
  setCached(items: WardrobeItem[], total: number): void {
    if (typeof window === 'undefined') return
    try {
      const cached: CachedWardrobe = {
        items,
        timestamp: Date.now(),
        total,
      }
      localStorage.setItem(WARDROBE_CACHE_KEY, JSON.stringify(cached))
    } catch (error) {
      console.warn('Failed to cache wardrobe:', error)
    }
  },

  /**
   * Clear wardrobe cache
   */
  clear(): void {
    if (typeof window === 'undefined') return
    localStorage.removeItem(WARDROBE_CACHE_KEY)
  },

  /**
   * Filter and sort items client-side
   */
  filterAndSort(
    items: WardrobeItem[],
    filters: {
      q?: string
      type?: string
      color?: string
      category?: string
      sort?: string
    }
  ): WardrobeItem[] {
    let filtered = [...items]

    // Search query filter
    if (filters.q) {
      const qLower = filters.q.toLowerCase()
      filtered = filtered.filter(
        (item) =>
          item.type.toLowerCase().includes(qLower) ||
          item.color.toLowerCase().includes(qLower)
      )
    }

    // Type filter
    if (filters.type) {
      filtered = filtered.filter((item) =>
        item.type.toLowerCase().includes(filters.type!.toLowerCase())
      )
    }

    // Color filter
    if (filters.color) {
      filtered = filtered.filter((item) =>
        item.color.toLowerCase().includes(filters.color!.toLowerCase())
      )
    }

    // Category filter
    if (filters.category) {
      filtered = filtered.filter(
        (item) => item.category === filters.category
      )
    }

    // Sorting
    if (filters.sort) {
      const key = filters.sort.replace(/^-/, '') as keyof WardrobeItem
      const reverse = filters.sort.startsWith('-')
      
      filtered.sort((a, b) => {
        const aVal = a[key]
        const bVal = b[key]
        
        if (aVal === undefined || aVal === null) return 1
        if (bVal === undefined || bVal === null) return -1
        
        if (typeof aVal === 'string' && typeof bVal === 'string') {
          return reverse
            ? bVal.localeCompare(aVal)
            : aVal.localeCompare(bVal)
        }
        
        if (typeof aVal === 'number' && typeof bVal === 'number') {
          return reverse ? bVal - aVal : aVal - bVal
        }
        
        return 0
      })
    }

    return filtered
  },

  /**
   * Paginate items
   */
  paginate(items: WardrobeItem[], page: number, pageSize: number): WardrobeItem[] {
    const start = (page - 1) * pageSize
    const end = start + pageSize
    return items.slice(start, end)
  },
}

/**
 * Suggestion Cache - Cache suggestion results
 */
export const suggestionCache = {
  /**
   * Generate cache key from query
   */
  getCacheKey(query: string): string {
    return `${SUGGESTION_CACHE_KEY}:${query.toLowerCase().trim()}`
  },

  /**
   * Get cached suggestion
   */
  getCached(query: string): any | null {
    if (typeof window === 'undefined') return null
    try {
      const key = this.getCacheKey(query)
      const raw = localStorage.getItem(key)
      if (!raw) return null
      
      const cached: CachedSuggestion = JSON.parse(raw)
      
      // Check if cache is expired
      const age = Date.now() - cached.timestamp
      if (age > SUGGESTION_CACHE_TTL) {
        localStorage.removeItem(key)
        return null
      }
      
      return cached.result
    } catch {
      return null
    }
  },

  /**
   * Cache suggestion result
   */
  setCached(query: string, result: any): void {
    if (typeof window === 'undefined') return
    try {
      const key = this.getCacheKey(query)
      const cached: CachedSuggestion = {
        query: query.toLowerCase().trim(),
        result,
        timestamp: Date.now(),
      }
      localStorage.setItem(key, JSON.stringify(cached))
      
      // Clean up old cache entries (keep last 20)
      this.cleanup()
    } catch (error) {
      console.warn('Failed to cache suggestion:', error)
    }
  },

  /**
   * Clear suggestion cache
   */
  clear(): void {
    if (typeof window === 'undefined') return
    try {
      const keys = Object.keys(localStorage)
      keys.forEach((key) => {
        if (key.startsWith(SUGGESTION_CACHE_KEY)) {
          localStorage.removeItem(key)
        }
      })
    } catch (error) {
      console.warn('Failed to clear suggestion cache:', error)
    }
  },

  /**
   * Clean up old cache entries (keep last 20)
   */
  cleanup(): void {
    if (typeof window === 'undefined') return
    try {
      const keys = Object.keys(localStorage)
      const suggestionKeys = keys
        .filter((key) => key.startsWith(SUGGESTION_CACHE_KEY + ':'))
        .map((key) => {
          const raw = localStorage.getItem(key)
          if (!raw) return null
          try {
            const cached: CachedSuggestion = JSON.parse(raw)
            return { key, timestamp: cached.timestamp }
          } catch {
            return null
          }
        })
        .filter((item): item is { key: string; timestamp: number } => item !== null)
        .sort((a, b) => b.timestamp - a.timestamp)

      // Remove entries beyond the 20 most recent
      suggestionKeys.slice(20).forEach(({ key }) => {
        localStorage.removeItem(key)
      })
    } catch (error) {
      console.warn('Failed to cleanup suggestion cache:', error)
    }
  },
}

/**
 * Filter State Cache - Save and restore filter states
 */
export const filterStateCache = {
  /**
   * Save filter state
   */
  save(state: FilterState): void {
    if (typeof window === 'undefined') return
    try {
      localStorage.setItem(FILTER_STATE_KEY, JSON.stringify(state))
    } catch (error) {
      console.warn('Failed to save filter state:', error)
    }
  },

  /**
   * Get saved filter state
   */
  get(): FilterState | null {
    if (typeof window === 'undefined') return null
    try {
      const raw = localStorage.getItem(FILTER_STATE_KEY)
      return raw ? JSON.parse(raw) : null
    } catch {
      return null
    }
  },

  /**
   * Clear filter state
   */
  clear(): void {
    if (typeof window === 'undefined') return
    localStorage.removeItem(FILTER_STATE_KEY)
  },
}

