'use client'

import { useEffect, useMemo, useState, useRef } from 'react'
import Image from 'next/image'
import Link from 'next/link'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { wardrobeAPI, WardrobeItem, outfitsAPI, SavedOutfit, V2Item } from '@/lib/api'
import { getFavorites, toggleFavorite } from '@/lib/storage'
import { getColorHex } from '@/lib/colors'
import AddItemModal from '@/components/modals/AddItemModal'
import OutfitDetailModal from '@/components/modals/OutfitDetailModal'
import { wardrobeCache, filterStateCache } from '@/lib/wardrobeCache'
import ProtectedRoute from '@/components/auth/ProtectedRoute'

export default function WardrobePage() {
  // All wardrobe items (loaded once, cached)
  const [allItems, setAllItems] = useState<WardrobeItem[]>([])
  // Filtered and paginated items (computed client-side)
  const [displayedItems, setDisplayedItems] = useState<WardrobeItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Saved Outfits
  const [savedOutfits, setSavedOutfits] = useState<SavedOutfit[]>([])
  const [activeTab, setActiveTab] = useState<'items' | 'outfits'>('items')
  const [selectedOutfit, setSelectedOutfit] = useState<SavedOutfit | null>(null)

  // Filter states
  const [q, setQ] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [colorFilter, setColorFilter] = useState('')
  const [sort, setSort] = useState<'id' | '-id' | 'type' | '-type' | 'color' | '-color'>('id')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(12)
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false)

  const [favorites, setFavorites] = useState<Set<number>>(new Set())
  const [showAddModal, setShowAddModal] = useState(false)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const isFirstMount = useRef(true)

  // Load all wardrobe items once (with caching)
  const fetchAllWardrobeItems = async (forceRefresh = false) => {
    try {
      setLoading(true)
      setError(null)

      // Check cache first (unless force refresh)
      if (!forceRefresh) {
        const cached = wardrobeCache.getCached()
        if (cached) {
          setAllItems(cached.items)
          setLoading(false)
          return
        }
      }

      // Fetch all items from backend in batches (max 100 per page)
      const allItems: WardrobeItem[] = []
      let page = 1
      const pageSize = 100
      let total = 0
      let hasMore = true

      while (hasMore) {
        const { items, total: totalCount } = await wardrobeAPI.getAllPaged({
          page,
          page_size: pageSize,
        })

        allItems.push(...items)
        total = totalCount

        // If we got fewer items than page size, we've reached the end
        if (items.length < pageSize || allItems.length >= total) {
          hasMore = false
        } else {
          page++
        }
      }

      // Cache the results
      wardrobeCache.setCached(allItems, total)
      setAllItems(allItems)
    } catch (err) {
      setError('Failed to load wardrobe items. Make sure the backend is running.')
      console.error('Error fetching wardrobe:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchAllOutfits = async () => {
    try {
      const data = await outfitsAPI.getAll()
      setSavedOutfits(data)
    } catch (e) {
      console.error("Failed to load outfits", e)
    }
  }

  const handleDeleteOutfit = async (id: number) => {
    if (!confirm('Delete this outfit?')) return
    try {
      await outfitsAPI.delete(id)
      setSavedOutfits(prev => prev.filter(o => o.id !== id))
    } catch (e) {
      alert('Failed to delete outfit')
    }
  }

  const handlePinOutfit = async (id: number) => {
    try {
      const updated = await outfitsAPI.togglePin(id)
      // Re-sort outfits: pinned first, then by created_at desc
      setSavedOutfits(prev => {
        const newList = prev.map(o => o.id === id ? updated : o)
        return newList.sort((a, b) => {
          if (a.is_pinned !== b.is_pinned) return b.is_pinned - a.is_pinned
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        })
      })
    } catch (e) {
      alert('Failed to pin/unpin outfit')
    }
  }

  // Load wardrobe items on mount
  useEffect(() => {
    // Restore filter state from cache
    const savedState = filterStateCache.get()
    if (savedState) {
      if (savedState.q) setQ(savedState.q)
      if (savedState.type) setTypeFilter(savedState.type)
      if (savedState.color) setColorFilter(savedState.color)
      if (savedState.category) setCategoryFilter(savedState.category)
      if (savedState.sort) setSort(savedState.sort as any)
      if (savedState.page) setPage(savedState.page)
      if (savedState.pageSize) setPageSize(savedState.pageSize)
    }

    fetchAllWardrobeItems()
    fetchAllOutfits()
    setFavorites(getFavorites())
  }, [])

  // Client-side filtering and sorting (no API calls)
  useEffect(() => {
    if (allItems.length === 0) {
      setDisplayedItems([])
      return
    }

    // Filter and sort client-side
    let filtered = wardrobeCache.filterAndSort(allItems, {
      q,
      type: typeFilter,
      color: colorFilter,
      category: categoryFilter,
      sort,
    })

    if (showFavoritesOnly) {
      filtered = filtered.filter((item) => favorites.has(item.id))
    }

    // Paginate
    const paginated = wardrobeCache.paginate(filtered, page, pageSize)

    setDisplayedItems(paginated)

    // Save filter state
    filterStateCache.save({
      q,
      type: typeFilter,
      color: colorFilter,
      category: categoryFilter,
      sort,
      page,
      pageSize,
    })
  }, [allItems, q, typeFilter, colorFilter, categoryFilter, sort, page, pageSize, showFavoritesOnly, favorites])

  // Calculate total for pagination
  const totalFiltered = useMemo(() => {
    if (allItems.length === 0) return 0
    let filtered = wardrobeCache.filterAndSort(allItems, {
      q,
      type: typeFilter,
      color: colorFilter,
      category: categoryFilter,
      sort,
    })
    if (showFavoritesOnly) {
      filtered = filtered.filter((item) => favorites.has(item.id))
    }
    return filtered.length
  }, [allItems, q, typeFilter, colorFilter, categoryFilter, sort, showFavoritesOnly, favorites])

  // Category filtering is now handled via the Filter dropdown only

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this item?')) return
    try {
      setDeletingId(id)
      await wardrobeAPI.delete(id)

      // Remove from local state
      setAllItems((prev) => prev.filter((item) => item.id !== id))

      // Clear cache to force refresh on next load
      wardrobeCache.clear()
    } catch (err) {
      console.error(err)
      alert('Failed to delete item')
    } finally {
      setDeletingId(null)
    }
  }

  const resetFilters = () => {
    setQ('')
    setTypeFilter('')
    setColorFilter('')
    setCategoryFilter('')
    setSort('id')
    setPage(1)
    setPageSize(12)
    setShowFavoritesOnly(false)
  }

  const favoriteCount = favorites.size

  if (loading) {
    return (
      <ProtectedRoute>
        <div className="min-h-screen bg-gray-50 dark:bg-slate-900 py-6 sm:py-12">
          <div className="container mx-auto px-4 sm:px-6">
            <div className="flex items-center justify-center h-48 sm:h-64">
              <div className="animate-spin rounded-full h-10 w-10 sm:h-12 sm:w-12 border-b-2 border-primary-600"></div>
            </div>
          </div>
        </div>
      </ProtectedRoute>
    )
  }

  if (error) {
    return (
      <ProtectedRoute>
        <div className="min-h-screen bg-gray-50 dark:bg-slate-900 py-6 sm:py-12">
          <div className="container mx-auto px-4 sm:px-6">
            <Card>
              <div className="p-6 sm:p-8 text-center">
                <div className="w-12 h-12 sm:w-16 sm:h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto mb-3 sm:mb-4">
                  <svg className="w-6 h-6 sm:w-8 sm:h-8 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <h2 className="text-lg sm:text-xl font-semibold text-gray-900 dark:text-white mb-2">Error Loading Wardrobe</h2>
                <p className="text-sm sm:text-base text-gray-600 dark:text-slate-400 mb-4 break-words">{error}</p>
                <button
                  onClick={() => fetchAllWardrobeItems(true)}
                  className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors text-sm sm:text-base"
                >
                  Try Again
                </button>
              </div>
            </Card>
          </div>
        </div>
      </ProtectedRoute>
    )
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900 py-6 sm:py-8">
        <div className="container mx-auto px-4 sm:px-6 max-w-7xl">
          
          {/* Clean Header */}
          <div className="mb-8">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
              <div>
                <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-white">My Wardrobe</h1>
                <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
                  {allItems.length} items • {favoriteCount} favorites • {savedOutfits.length} outfits
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => fetchAllWardrobeItems(true)}
                  disabled={loading}
                  className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 transition-all text-sm font-medium shadow-sm"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Refresh
                </button>
                <button
                  onClick={() => setShowAddModal(true)}
                  className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-primary-600 hover:bg-primary-700 text-white transition-all text-sm font-medium shadow-sm"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Add Item
                </button>
                <Link
                  href="/suggest"
                  className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-900 dark:bg-white text-white dark:text-slate-900 transition-all text-sm font-medium shadow-sm"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                  </svg>
                  <span className="hidden sm:inline">Get Suggestions</span>
                </Link>
              </div>
            </div>

          </div>

          {activeTab === 'items' && (
            <>

              {/* Tabs */}
              <div className="mb-3 flex items-center justify-between gap-3">
                <div className="flex items-center gap-1 p-1 bg-slate-100 dark:bg-slate-800 rounded-xl w-fit">
                  {[
                    { key: 'items', label: 'Items' },
                    { key: 'outfits', label: 'Outfits' },
                  ].map((tab) => (
                    <button
                      key={tab.key}
                      onClick={() => setActiveTab(tab.key as 'items' | 'outfits')}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === tab.key 
                        ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm' 
                        : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'}`}
                    >
                      {tab.label}
                      {tab.key === 'items' && <span className="ml-1.5 text-slate-400 dark:text-slate-500">{allItems.length}</span>}
                      {tab.key === 'outfits' && <span className="ml-1.5 text-slate-400 dark:text-slate-500">{savedOutfits.length}</span>}
                    </button>
                  ))}
                </div>
              </div>

              {/* Filters Section moved below tabs, includes Search */}
              <div className="mb-6 bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-3 sm:p-4">
                {/* Search */}
                <div className="mb-3">
                  <div className="relative">
                    <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                    <input
                      value={q}
                      onChange={(e) => { setQ(e.target.value); setPage(1) }}
                      placeholder="Search items..."
                      className="w-full pl-10 pr-4 py-2.5 text-sm border border-slate-200 dark:border-slate-600 rounded-xl bg-slate-50 dark:bg-slate-700 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                  </div>
                </div>

                {/* Advanced Filters Row */}
                <div className="pt-3 space-y-3">
                  {/* Dropdowns */}
                  <div className="grid grid-cols-2 gap-2">
                    <select
                      value={categoryFilter}
                      onChange={(e) => { setCategoryFilter(e.target.value); setPage(1) }}
                      className="w-full px-3 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    >
                      <option value="">All</option>
                      <option value="top">Top</option>
                      <option value="bottom">Bottom</option>
                      <option value="footwear">Footwear</option>
                      <option value="one-piece">One-Piece</option>
                      <option value="layer">Layer</option>
                      <option value="accessories">Accessories</option>
                    </select>
                    <select
                      value={sort}
                      onChange={(e) => { setSort(e.target.value as any); setPage(1) }}
                      className="w-full px-3 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    >
                      <option value="id">Newest</option>
                      <option value="-id">Oldest</option>
                      <option value="type">Type A-Z</option>
                      <option value="-type">Type Z-A</option>
                    </select>
                  </div>

                  {/* Bottom Row - Favorites & Pagination */}
                  <div className="flex flex-row flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-2 flex-wrap">
                      <button
                        onClick={() => { setShowFavoritesOnly(!showFavoritesOnly); setPage(1) }}
                        className={`inline-flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs sm:text-sm font-medium transition-all whitespace-nowrap ${showFavoritesOnly 
                          ? 'bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800' 
                          : 'bg-white dark:bg-slate-700 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-600 hover:border-slate-300'}`}
                      >
                        <svg className={`w-4 h-4 ${showFavoritesOnly ? 'fill-current' : ''}`} viewBox="0 0 24 24" fill="none" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                        </svg>
                        Favorites
                      </button>

                      {(q || typeFilter || colorFilter || categoryFilter || showFavoritesOnly) && (
                        <button
                          onClick={resetFilters}
                          className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 px-2"
                        >
                          Clear all
                        </button>
                      )}
                    </div>
                    <div className="flex items-center justify-between sm:justify-end gap-3">
                      <span className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">{totalFiltered} items</span>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => setPage((p) => Math.max(1, p - 1))}
                          disabled={page === 1}
                          className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-40"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                          </svg>
                        </button>
                        <span className="px-2 text-xs sm:text-sm font-medium text-slate-700 dark:text-slate-200">{page}</span>
                        <button
                          onClick={() => setPage((p) => (p * pageSize < totalFiltered ? p + 1 : p))}
                          disabled={page * pageSize >= totalFiltered}
                          className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-40"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Wardrobe Grid */}
              {displayedItems.length === 0 ? (
                <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-12 text-center">
                  <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-100 dark:bg-slate-700 flex items-center justify-center">
                    <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                    </svg>
                  </div>
                  <p className="text-slate-900 dark:text-white font-medium">No items yet</p>
                  <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Add your first wardrobe item to get started</p>
                  <button
                    onClick={() => setShowAddModal(true)}
                    className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                    </svg>
                    Add Item
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
                  {displayedItems.map((item) => (
                    <div key={item.id} className="group bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden hover:shadow-lg hover:border-slate-300 dark:hover:border-slate-600 transition-all">
                      {/* Image */}
                      <div className="relative aspect-square bg-slate-100 dark:bg-slate-700">
                        {item.image_url ? (
                          <Image
                            src={item.image_url}
                            alt={`${item.color} ${item.type}`}
                            fill
                            className="object-cover"
                            sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center">
                            <svg className="w-12 h-12 text-slate-300 dark:text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                            </svg>
                          </div>
                        )}
                        
                        {/* Category Badge */}
                        <span className="absolute top-2 left-2 px-2 py-0.5 bg-slate-900/80 text-white text-xs font-medium rounded capitalize">
                          {item.category}
                        </span>

                        {/* Favorite Button */}
                        <button
                          onClick={() => setFavorites(new Set(toggleFavorite(item.id)))}
                          className="absolute top-2 right-2 w-8 h-8 bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm rounded-full flex items-center justify-center shadow-sm hover:scale-110 transition-transform"
                        >
                          {favorites.has(item.id) ? (
                            <svg className="w-4 h-4 text-red-500" viewBox="0 0 24 24" fill="currentColor">
                              <path d="M11.645 20.91l-.007-.003-.022-.012a15.247 15.247 0 01-.383-.218 25.18 25.18 0 01-4.244-3.17C4.688 15.698 3 13.35 3 10.5 3 8.015 5.015 6 7.5 6A5.5 5.5 0 0112 8.019 5.5 5.5 0 0116.5 6C18.985 6 21 8.015 21 10.5c0 2.85-1.688 5.199-3.989 7.007a25.175 25.175 0 01-4.244 3.17 15.247 15.247 0 01-.383.218l-.022.012-.007.003-.003.002a.75.75 0 01-.718 0l-.003-.002z" />
                            </svg>
                          ) : (
                            <svg className="w-4 h-4 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                              <path d="M21 10.5c0 2.85-1.688 5.199-3.989 7.007a25.175 25.175 0 01-4.244 3.17 15.247 15.247 0 01-.383.218l-.022.012-.007.003-.003.002a.75.75 0 01-.718 0l-.003-.002-.007-.003-.022-.012a15.247 15.247 0 01-.383-.218 25.18 25.18 0 01-4.244-3.17C4.688 15.698 3 13.35 3 10.5 3 8.015 5.015 6 7.5 6A5.5 5.5 0 0112 8.019 5.5 5.5 0 0116.5 6C18.985 6 21 8.015 21 10.5z" />
                            </svg>
                          )}
                        </button>
                      </div>

                      {/* Info */}
                      <div className="p-3">
                        <h3 className="font-medium text-sm text-slate-900 dark:text-white line-clamp-1">{item.type}</h3>
                        <div className="flex items-center gap-1.5 mt-1">
                          <span 
                            className="w-3 h-3 rounded-full border border-slate-200 dark:border-slate-600 flex-shrink-0"
                            style={{ backgroundColor: getColorHex(item.color) }}
                          />
                          <span className="text-xs text-slate-500 dark:text-slate-400 truncate">{item.color}</span>
                        </div>
                        <div className="flex items-center gap-2 mt-3 pt-3 border-t border-slate-100 dark:border-slate-700">
                          <a
                            href={`/wardrobe/${item.id}`}
                            className="flex-1 text-center py-1.5 text-xs font-medium text-primary-600 dark:text-primary-400 hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded-lg transition-colors"
                          >
                            View
                          </a>
                          <button
                            onClick={(e) => { e.preventDefault(); handleDelete(item.id) }}
                            disabled={deletingId === item.id}
                            className="flex-1 text-center py-1.5 text-xs font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors disabled:opacity-50"
                          >
                            {deletingId === item.id ? '...' : 'Delete'}
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}

          {activeTab === 'outfits' && (
            <div>
              {/* Tabs */}
              <div className="mb-6 flex items-center gap-1 p-1 bg-slate-100 dark:bg-slate-800 rounded-xl w-fit">
                {[
                  { key: 'items', label: 'Items' },
                  { key: 'outfits', label: 'Outfits' },
                ].map((tab) => (
                  <button
                    key={tab.key}
                    onClick={() => setActiveTab(tab.key as 'items' | 'outfits')}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === tab.key 
                      ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm' 
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'}`}
                  >
                    {tab.label}
                    {tab.key === 'items' && <span className="ml-1.5 text-slate-400 dark:text-slate-500">{allItems.length}</span>}
                    {tab.key === 'outfits' && <span className="ml-1.5 text-slate-400 dark:text-slate-500">{savedOutfits.length}</span>}
                  </button>
                ))}
              </div>

              {savedOutfits.length === 0 ? (
                <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-12 text-center">
                  <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-100 dark:bg-slate-700 flex items-center justify-center">
                    <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                    </svg>
                  </div>
                  <p className="text-slate-900 dark:text-white font-medium">No saved outfits</p>
                  <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Get AI suggestions to create your first outfit</p>
                  <Link
                    href="/suggest"
                    className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors"
                  >
                    Get Suggestions
                  </Link>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                  {savedOutfits.map(outfit => (
                    <div 
                      key={outfit.id} 
                      onClick={() => setSelectedOutfit(outfit)}
                      className={`bg-white dark:bg-slate-800 rounded-xl border overflow-hidden transition-all hover:shadow-md cursor-pointer ${outfit.is_pinned ? 'border-primary-400 dark:border-primary-500' : 'border-slate-200 dark:border-slate-700'}`}
                    >
                      {/* Header */}
                      <div className="p-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {outfit.is_pinned === 1 && (
                            <span className="w-5 h-5 rounded bg-primary-100 dark:bg-primary-900/50 flex items-center justify-center">
                              <svg className="w-3 h-3 text-primary-600 dark:text-primary-400" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                              </svg>
                            </span>
                          )}
                          <div>
                            <h3 className="font-medium text-slate-900 dark:text-white">{outfit.name || `Outfit #${outfit.id}`}</h3>
                            <p className="text-xs text-slate-500 dark:text-slate-400">{new Date(outfit.created_at).toLocaleDateString()}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-1">
                          <button 
                            onClick={(e) => { e.stopPropagation(); handlePinOutfit(outfit.id); }}
                            className={`p-1.5 rounded-lg transition-colors ${outfit.is_pinned ? 'text-primary-600 dark:text-primary-400' : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'}`}
                          >
                            <svg className="w-4 h-4" fill={outfit.is_pinned ? 'currentColor' : 'none'} stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                            </svg>
                          </button>
                          <button 
                            onClick={(e) => { e.stopPropagation(); handleDeleteOutfit(outfit.id); }}
                            className="p-1.5 rounded-lg text-slate-400 hover:text-red-500 transition-colors"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </div>
                      </div>
                      
                      {/* Items Grid */}
                      <div className="p-4">
                        <div className="grid grid-cols-5 gap-2">
                          {['top', 'bottom', 'footwear', 'outerwear', 'accessories'].map(part => {
                            const item = outfit.items[part as keyof typeof outfit.items] as V2Item;
                            if (!item) return (
                              <div key={part} className="aspect-square rounded-lg bg-slate-100 dark:bg-slate-700 flex items-center justify-center">
                                <span className="text-xs text-slate-400">—</span>
                              </div>
                            );
                            return (
                              <div key={part} className="aspect-square relative rounded-lg overflow-hidden bg-slate-100 dark:bg-slate-700" title={item.name}>
                                {item.image_url ? (
                                  <Image src={item.image_url} alt={item.name} fill className="object-cover" />
                                ) : (
                                  <div className="w-full h-full flex items-center justify-center text-xs text-slate-400">?</div>
                                )}
                              </div>
                            )
                          })}
                        </div>
                        
                        {/* Click to view indicator */}
                        <div className="mt-3 text-center">
                          <span className="text-xs text-slate-500 dark:text-slate-400">Click to view details</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Add Item Modal */}
        {showAddModal && (
          <AddItemModal
            onClose={() => setShowAddModal(false)}
            onSuccess={(newItem) => {
              // Add new item to local state
              setAllItems((prev) => [newItem, ...prev])

              // Clear cache to ensure fresh data
              wardrobeCache.clear()

              // Reset to first page to show new item
              setPage(1)
            }}
          />
        )}

        {/* Outfit Detail Modal */}
        {selectedOutfit && (
          <OutfitDetailModal
            outfit={selectedOutfit}
            onClose={() => setSelectedOutfit(null)}
          />
        )}
      </div>
    </ProtectedRoute >
  )
}
