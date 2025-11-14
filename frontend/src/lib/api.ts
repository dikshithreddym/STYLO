import apiClient from './apiClient'

export interface WardrobeItem {
  id: number
  type: string
  color: string
  image_url: string | null
  category?: 'top' | 'bottom' | 'footwear' | 'layer' | 'one-piece' | 'accessories'
  image_description?: string | null
}

// Wardrobe API endpoints
export const wardrobeAPI = {
  // Get all wardrobe items (with optional filters)
  getAll: async (params?: {
    q?: string
    type?: string
    color?: string
    sort?: 'id' | '-id' | 'type' | '-type' | 'color' | '-color'
    category?: string
  }): Promise<WardrobeItem[]> => {
    const response = await apiClient.get('/wardrobe', { params })
    return response.data
  },

  // Paged fetch returning total via header
  getAllPaged: async (params?: {
    q?: string
    type?: string
    color?: string
    sort?: 'id' | '-id' | 'type' | '-type' | 'color' | '-color' | 'category' | '-category'
    category?: string
    page?: number
    page_size?: number
  }): Promise<{ items: WardrobeItem[]; total: number }> => {
    const response = await apiClient.get('/wardrobe', { params })
    const total = Number(response.headers['x-total-count'] || 0)
    return { items: response.data, total }
  },

  // Get single wardrobe item
  getById: async (id: number): Promise<WardrobeItem> => {
    const response = await apiClient.get(`/wardrobe/${id}`)
    return response.data
  },

  // Create a new wardrobe item
  create: async (item: Omit<WardrobeItem, 'id'>): Promise<WardrobeItem> => {
    const response = await apiClient.post('/wardrobe', item)
    return response.data
  },

  // Delete a wardrobe item
  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/wardrobe/${id}`)
  },
}

// Health check
export const healthAPI = {
  check: async (): Promise<{ status: string }> => {
    const response = await apiClient.get('/health')
    return response.data
  },
}

// Suggestions API
export interface Outfit { items: WardrobeItem[]; score: number; rationale?: string | null }

export const suggestionsAPI = {
  suggest: async (text: string, options?: { limit?: number; strategy?: 'rules' | 'ml' }): Promise<{
    occasion: string
    colors: string[]
    outfit: Outfit
    alternatives: Outfit[]
    notes?: string | null
  }> => {
    const response = await apiClient.post('/suggestions', { text, ...options })
    return response.data
  },
}
