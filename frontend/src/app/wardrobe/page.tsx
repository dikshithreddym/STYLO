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
import HealthStatus from '@/components/system/HealthStatus'
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

  // Get unique types and colors from all items (not just displayed)
  const uniqueTypes = useMemo(() => Array.from(new Set(allItems.map(i => i.type))).sort(), [allItems])
  const uniqueColors = useMemo(() => Array.from(new Set(allItems.map(i => i.color))).sort(), [allItems])

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
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 py-6 sm:py-12">
        <div className="container mx-auto px-4 sm:px-6">
          <div className="flex items-center justify-center h-48 sm:h-64">
            <div className="animate-spin rounded-full h-10 w-10 sm:h-12 sm:w-12 border-b-2 border-primary-600"></div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
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
    )
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-gray-50 dark:from-slate-900 dark:via-slate-900 dark:to-slate-800 py-6 sm:py-12">
        <div className="container mx-auto px-4 sm:px-6">
          <div className="mb-8 sm:mb-10 space-y-4">
            <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 text-white p-6 sm:p-8 md:p-10 shadow-xl">
              <div className="absolute inset-0 pointer-events-none">
                <div className="absolute -left-10 -top-10 w-56 h-56 bg-primary-500/20 rounded-full blur-3xl" />
                <div className="absolute right-0 top-0 w-72 h-72 bg-indigo-500/20 rounded-full blur-3xl" />
              </div>
              <div className="relative grid lg:grid-cols-3 gap-6 items-start">
                <div className="lg:col-span-2 space-y-4">
                  <p className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 text-xs font-semibold border border-white/10 shadow-sm">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    Live wardrobe workspace
                  </p>
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight">Wardrobe command center</h1>
                      <p className="mt-2 text-sm sm:text-base text-slate-100/90 max-w-2xl">Curate, favorite, and deploy outfits faster with refreshed navigation, smart filters, and AI-ready actions.</p>
                    </div>
                    <div className="hidden sm:flex items-center gap-2">
                      <button
                        onClick={() => fetchAllWardrobeItems(true)}
                        disabled={loading}
                        className="inline-flex items-center gap-2 px-3 py-2 rounded-full bg-white/10 text-white border border-white/15 hover:bg-white/20 transition-all text-sm font-semibold"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        Refresh
                      </button>
                      <Link
                        href="/suggest"
                        className="inline-flex items-center gap-2 px-3 py-2 rounded-full bg-white text-slate-900 shadow-md hover:-translate-y-0.5 transition-all text-sm font-semibold"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                        </svg>
                        Get suggestions
                      </Link>
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 border border-white/15 text-xs font-semibold">
                      <span className="w-6 h-6 rounded-full bg-white/20 flex items-center justify-center text-white">{allItems.length}</span>
                      Items tracked
                    </div>
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 border border-white/15 text-xs font-semibold">
                      <span className="w-6 h-6 rounded-full bg-white/20 flex items-center justify-center text-white">{favoriteCount}</span>
                      Favorites saved
                    </div>
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 border border-white/15 text-xs font-semibold">
                      <span className="w-6 h-6 rounded-full bg-white/20 flex items-center justify-center text-white">{savedOutfits.length}</span>
                      Outfits crafted
                    </div>
                  </div>
                </div>
                <div className="bg-white/10 border border-white/15 rounded-2xl p-4 sm:p-5 shadow-lg backdrop-blur">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold text-white">Quick actions</p>
                    <span className="text-xs text-slate-100/80 px-2 py-1 rounded-full bg-white/10 border border-white/15">Modernized</span>
                  </div>
                  <div className="mt-3 space-y-3">
                    <button
                      onClick={() => setShowAddModal(true)}
                      className="w-full flex items-center justify-between px-4 py-3 rounded-xl bg-white text-slate-900 font-semibold hover:-translate-y-0.5 transition-all shadow-md"
                    >
                      Add a new item
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                      </svg>
                    </button>
                    <div className="flex items-center justify-between px-4 py-3 rounded-xl bg-white/10 border border-white/15 text-sm">
                      <div className="space-y-1">
                        <p className="font-semibold text-white">AI-ready inventory</p>
                        <p className="text-slate-100/80 text-xs">Sorted with semantic + color signals</p>
                      </div>
                      <svg className="w-10 h-10 text-white/70" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v6m-3-3h6m7 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
              <div className="glass-panel rounded-2xl p-4 sm:p-6 lg:col-span-1">
                <HealthStatus />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 lg:col-span-3">
                {[
                  { label: 'Total items', value: allItems.length, accent: 'from-primary-500 to-primary-600', icon: (<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />) },
                  { label: 'Unique categories', value: new Set(allItems.map(i => i.category)).size, accent: 'from-emerald-500 to-emerald-600', icon: (<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />) },
                  { label: 'Outfits created', value: savedOutfits.length, accent: 'from-purple-500 to-indigo-600', icon: (<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />) },
                ].map((stat) => (
                  <div key={stat.label} className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm dark:shadow-slate-900/50 border border-gray-100/80 dark:border-slate-700 p-4 sm:p-6 flex items-center justify-between hover:-translate-y-1 transition-all duration-200">
                    <div>
                      <p className="text-xs sm:text-sm text-gray-500 dark:text-slate-400 font-medium">{stat.label}</p>
                      <p className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-white">{stat.value}</p>
                    </div>
                    <div className={`w-12 h-12 sm:w-14 sm:h-14 rounded-2xl bg-gradient-to-br ${stat.accent} flex items-center justify-center shadow-lg`}>
                      <svg className="w-6 h-6 sm:w-7 sm:h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        {stat.icon}
                      </svg>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>


          {/* Navigation Tabs */}
          <div className="flex flex-wrap items-center gap-3 bg-white/70 dark:bg-slate-800/70 border border-white/80 dark:border-slate-700 rounded-2xl px-3 sm:px-4 py-2 shadow-sm mb-6 sm:mb-8">
            {[
              { key: 'items', label: 'Wardrobe items' },
              { key: 'outfits', label: 'Outfits created' },
            ].map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key as 'items' | 'outfits')}
                className={`px-4 py-2 rounded-xl text-sm sm:text-base font-semibold transition-all ${activeTab === tab.key ? 'bg-slate-900 dark:bg-white text-white dark:text-slate-900 shadow-md' : 'text-slate-600 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-700 hover:text-slate-900 dark:hover:text-white border border-transparent hover:border-slate-200 dark:hover:border-slate-600'}`}
              >
                {tab.label}
              </button>
            ))}
            <div className="flex items-center gap-2 text-xs sm:text-sm text-slate-500 dark:text-slate-400 ml-auto">
              <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 font-medium">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" /> Synced
              </span>
              <span>{totalFiltered} items in view</span>
            </div>
          </div>

          {activeTab === 'items' && (
            <>
              {/* Wardrobe Header */}
              <div className="mb-4 sm:mb-6 md:mb-8 flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4">
                <div className="space-y-1">
                  <p className="text-xs font-semibold text-primary-600 dark:text-primary-400 uppercase tracking-[0.2em]">Inventory</p>
                  <h2 className="text-xl sm:text-2xl md:text-3xl font-extrabold text-gray-900 dark:text-white">My wardrobe</h2>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs font-semibold">
                      <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                      {displayedItems.length} showing
                    </span>
                    <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400 text-xs font-semibold">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      Instant actions
                    </span>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2 justify-end">
                  <button
                    onClick={() => fetchAllWardrobeItems(true)}
                    disabled={loading}
                    className="inline-flex items-center justify-center px-3 sm:px-4 py-2 sm:py-2.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-200 rounded-xl shadow-sm hover:border-slate-300 dark:hover:border-slate-500 hover:-translate-y-0.5 transition-all duration-200 font-semibold text-xs sm:text-sm"
                    title="Refresh wardrobe"
                  >
                    <svg className="w-4 h-4 sm:w-5 sm:h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    <span className="ml-2">Refresh</span>
                  </button>
                  <button
                    onClick={() => setShowAddModal(true)}
                    className="inline-flex items-center justify-center px-4 sm:px-6 py-2.5 sm:py-3 bg-slate-900 dark:bg-primary-600 text-white rounded-xl shadow-lg hover:-translate-y-0.5 transition-all duration-200 font-semibold text-sm sm:text-base whitespace-nowrap w-full sm:w-auto"
                  >
                    <svg className="w-4 h-4 sm:w-5 sm:h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                    </svg>
                    Add Item
                  </button>
                </div>
              </div>

              {/* Filters */}
              <div className="mb-4 sm:mb-6 bg-white dark:bg-slate-800 rounded-3xl shadow-sm dark:shadow-slate-900/50 border border-white/80 dark:border-slate-700 p-4 sm:p-5 md:p-6">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-slate-900 dark:text-white">Filters & sorting</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">Tune the view with quick chips and smart toggles.</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() => { setShowFavoritesOnly(!showFavoritesOnly); setPage(1) }}
                      className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold border transition-all ${showFavoritesOnly ? 'bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-800 shadow-sm' : 'bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-600 hover:border-slate-300 dark:hover:border-slate-500'}`}
                    >
                      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 21l-1.45-1.318C5.4 15.368 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.868-8.55 11.182L12 21z" />
                      </svg>
                      Favorites only
                    </button>
                    <button
                      onClick={resetFilters}
                      className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold bg-slate-50 dark:bg-slate-700 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-600 hover:border-slate-300 dark:hover:border-slate-500"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                      Reset filters
                    </button>
                  </div>
                </div>

                <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 sm:gap-4">
                  <div className="space-y-1">
                    <label className="block text-xs sm:text-sm font-medium text-gray-700 dark:text-slate-300">Search</label>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-500">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                      </span>
                      <input
                        value={q}
                        onChange={(e) => { setQ(e.target.value); setPage(1) }}
                        placeholder="Type, color, name"
                        className="w-full pl-10 pr-3 py-2.5 text-sm sm:text-base border dark:border-slate-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-200 dark:focus:ring-primary-800 focus:border-primary-500 text-gray-900 dark:text-white bg-white dark:bg-slate-700 placeholder-slate-400 dark:placeholder-slate-500"
                      />
                    </div>
                  </div>
                  <div className="space-y-1">
                    <label className="block text-xs sm:text-sm font-medium text-gray-700">Type</label>
                    <select
                      value={typeFilter}
                      onChange={(e) => { setTypeFilter(e.target.value); setPage(1) }}
                      className="w-full px-3 py-2.5 text-sm sm:text-base border rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-200 focus:border-primary-500 bg-white text-gray-900"
                    >
                      <option value="">All</option>
                      {uniqueTypes.map((t) => (
                        <option key={t} value={t}>{t}</option>
                      ))}
                    </select>
                  </div>
                  <div className="space-y-1">
                    <label className="block text-xs sm:text-sm font-medium text-gray-700">Color</label>
                    <select
                      value={colorFilter}
                      onChange={(e) => { setColorFilter(e.target.value); setPage(1) }}
                      className="w-full px-3 py-2.5 text-sm sm:text-base border rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-200 focus:border-primary-500 bg-white text-gray-900"
                    >
                      <option value="">All</option>
                      {uniqueColors.map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                  </div>
                  <div className="space-y-1">
                    <label className="block text-xs sm:text-sm font-medium text-gray-700">Category</label>
                    <select
                      value={categoryFilter}
                      onChange={(e) => { setCategoryFilter(e.target.value); setPage(1) }}
                      className="w-full px-3 py-2.5 text-sm sm:text-base border rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-200 focus:border-primary-500 bg-white text-gray-900"
                    >
                      <option value="">All</option>
                      {['top', 'bottom', 'footwear', 'layer', 'outerwear', 'one-piece', 'accessories'].map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                  </div>
                  <div className="space-y-1">
                    <label className="block text-xs sm:text-sm font-medium text-gray-700">Sort</label>
                    <select
                      value={sort}
                      onChange={(e) => { setSort(e.target.value as any); setPage(1) }}
                      className="w-full px-3 py-2.5 text-sm sm:text-base border rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-200 focus:border-primary-500 bg-white text-gray-900"
                    >
                      <option value="id">ID (asc)</option>
                      <option value="-id">ID (desc)</option>
                      <option value="type">Type (A→Z)</option>
                      <option value="-type">Type (Z→A)</option>
                      <option value="color">Color (A→Z)</option>
                      <option value="-color">Color (Z→A)</option>
                    </select>
                  </div>
                </div>

                <div className="mt-4">
                  <p className="text-xs font-semibold text-slate-500 mb-2">Quick category chips</p>
                  <div className="flex flex-wrap gap-2">
                    {['top', 'bottom', 'footwear', 'outerwear', 'layer', 'accessories'].map((chip) => {
                      const active = categoryFilter === chip
                      return (
                        <button
                          key={chip}
                          onClick={() => { setCategoryFilter(active ? '' : chip); setPage(1) }}
                          className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-all border ${active ? 'bg-slate-900 text-white border-slate-900 shadow-sm' : 'bg-slate-50 text-slate-700 border-slate-200 hover:border-slate-300'}`}
                        >
                          {chip.charAt(0).toUpperCase() + chip.slice(1)}
                        </button>
                      )
                    })}
                  </div>
                </div>

                {/* Pagination controls */}
                <div className="mt-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-0 border-t border-slate-100 pt-4">
                  <div className="text-xs sm:text-sm text-gray-600 flex items-center gap-2">
                    <span className="inline-flex items-center justify-center w-2 h-2 rounded-full bg-emerald-500" />
                    Showing {displayedItems.length} of {totalFiltered} items
                  </div>
                  <div className="flex items-center gap-2 w-full sm:w-auto">
                    <button
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      className="px-2.5 sm:px-3 py-1.5 sm:py-1 text-xs sm:text-sm border border-gray-200 rounded-lg bg-white text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-200 disabled:opacity-50 disabled:cursor-not-allowed"
                      disabled={page === 1}
                    >Prev</button>
                    <span className="text-xs sm:text-sm text-gray-700 font-semibold px-2">Page {page}</span>
                    <button
                      onClick={() => setPage((p) => (p * pageSize < totalFiltered ? p + 1 : p))}
                      className="px-2.5 sm:px-3 py-1.5 sm:py-1 text-xs sm:text-sm border border-gray-200 rounded-lg bg-white text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-200 disabled:opacity-50 disabled:cursor-not-allowed"
                      disabled={page * pageSize >= totalFiltered}
                    >Next</button>
                    <select
                      value={pageSize}
                      onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1) }}
                      className="ml-0 sm:ml-2 px-2 py-1.5 sm:py-1 text-xs sm:text-sm border border-gray-200 rounded-lg bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-primary-200"
                    >
                      {[8, 12, 16, 24].map(n => <option key={n} value={n}>{n}/page</option>)}
                    </select>
                  </div>
                </div>
              </div>

              {/* Wardrobe Grid */}
              {displayedItems.length === 0 ? (
                <div className="bg-white rounded-xl sm:rounded-2xl shadow-sm border border-gray-100 p-6 sm:p-8 md:p-12 text-center">
                  <svg className="w-12 h-12 sm:w-16 sm:h-16 mx-auto mb-3 sm:mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                  <p className="text-gray-600 text-base sm:text-lg">No items in your wardrobe yet.</p>
                  <p className="text-gray-500 text-xs sm:text-sm mt-2">Add your first item to get started!</p>
                </div>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-2 sm:gap-3 md:gap-4 lg:gap-6">
                  {displayedItems.map((item) => (
                    <div key={item.id} className="group bg-white rounded-lg sm:rounded-xl md:rounded-2xl shadow-sm hover:shadow-xl transition-all duration-300 border border-gray-100 overflow-hidden">
                      {/* Image */}
                      <div className="relative h-40 sm:h-48 md:h-56 lg:h-64 xl:h-72 bg-gradient-to-br from-gray-100 to-gray-200 overflow-hidden">
                        {item.image_url ? (
                          <Image
                            src={item.image_url}
                            alt={`${item.color} ${item.type}`}
                            fill
                            className="object-cover group-hover:scale-110 transition-transform duration-500"
                            sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center">
                            <svg className="w-10 h-10 sm:w-12 sm:h-12 md:w-16 md:h-16 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                            </svg>
                          </div>
                        )}
                        {/* Category label at top-left */}
                        {item.category && (
                          <div className="absolute top-2 left-2 px-2 py-1 bg-black/70 text-white text-xs font-medium rounded-md backdrop-blur-sm">
                            {item.category.charAt(0).toUpperCase() + item.category.slice(1)}
                          </div>
                        )}
                        {/* Favorite button overlay */}
                        <button
                          aria-label="Toggle favorite"
                          onClick={() => setFavorites(new Set(toggleFavorite(item.id)))}
                          className="absolute top-2 right-2 sm:top-3 sm:right-3 w-7 h-7 sm:w-8 sm:h-8 md:w-10 md:h-10 bg-white/90 backdrop-blur-sm rounded-full flex items-center justify-center shadow-md hover:bg-white transition-all"
                          title="Add to favorites"
                        >
                          {favorites.has(item.id) ? (
                            <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4 md:w-5 md:h-5 text-red-500" viewBox="0 0 24 24" fill="currentColor"><path d="M11.645 20.91l-.007-.003-.022-.012a15.247 15.247 0 01-.383-.218 25.18 25.18 0 01-4.244-3.17C4.688 15.698 3 13.35 3 10.5 3 8.015 5.015 6 7.5 6A5.5 5.5 0 0112 8.019 5.5 5.5 0 0116.5 6C18.985 6 21 8.015 21 10.5c0 2.85-1.688 5.199-3.989 7.007a25.175 25.175 0 01-4.244 3.17 15.247 15.247 0 01-.383.218l-.022.012-.007.003-.003.002a.75.75 0 01-.718 0l-.003-.002z" /></svg>
                          ) : (
                            <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4 md:w-5 md:h-5 text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path strokeWidth="1.5" d="M21 10.5c0 2.85-1.688 5.199-3.989 7.007a25.175 25.175 0 01-4.244 3.17 15.247 15.247 0 01-.383.218l-.022.012-.007.003-.003.002a.75.75 0 01-.718 0l-.003-.002-.007-.003-.022-.012a15.247 15.247 0 01-.383-.218 25.18 25.18 0 01-4.244-3.17C4.688 15.698 3 13.35 3 10.5 3 8.015 5.015 6 7.5 6A5.5 5.5 0 0112 8.019 5.5 5.5 0 0116.5 6C18.985 6 21 8.015 21 10.5z" /></svg>
                          )}
                        </button>
                      </div>

                      {/* Info */}
                      <div className="p-2 sm:p-3 md:p-4">
                        <h3 className="font-semibold text-xs sm:text-sm md:text-base lg:text-lg text-gray-900 mb-1 line-clamp-2">{item.type}</h3>
                        <div className="flex items-center gap-1.5 sm:gap-2 mb-1.5 sm:mb-2">
                          <span className="inline-block w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-full border border-gray-300 shadow-sm flex-shrink-0"
                            style={{ backgroundColor: getColorHex(item.color) }}
                            title={item.color}
                          ></span>
                          <p className="text-gray-600 text-xs sm:text-sm truncate">{item.color}</p>
                        </div>
                        <div className="flex gap-2 mt-2 sm:mt-3 pt-2 sm:pt-3 border-t border-gray-100">
                          <a
                            href={`/wardrobe/${item.id}`}
                            className="flex-1 text-center px-1.5 sm:px-2 md:px-3 py-1 sm:py-1.5 md:py-2 text-primary-600 hover:bg-primary-50 rounded-md sm:rounded-lg text-xs sm:text-sm font-medium transition-colors"
                          >
                            View
                          </a>
                          <button
                            onClick={(e) => { e.preventDefault(); handleDelete(item.id) }}
                            disabled={deletingId === item.id}
                            className="flex-1 text-center px-1.5 sm:px-2 md:px-3 py-1 sm:py-1.5 md:py-2 text-red-600 hover:bg-red-50 rounded-md sm:rounded-lg text-xs sm:text-sm font-medium transition-colors disabled:opacity-50"
                          >
                            {deletingId === item.id ? 'Deleting...' : 'Delete'}
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
            <div className="space-y-6">
              <div className="flex justify-between items-center mb-4">
                <div>
                  <h2 className="text-xl sm:text-2xl font-bold text-gray-900">Your Saved Outfits</h2>
                  <p className="text-gray-500 text-sm">Outfits you've created and saved.</p>
                </div>
              </div>

              {savedOutfits.length === 0 ? (
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center">
                  <p className="text-gray-600 text-lg">No saved outfits yet.</p>
                  <a href="/suggest" className="text-primary-600 hover:underline mt-2 inline-block">Generate some suggestions!</a>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                  {savedOutfits.map(outfit => (
                    <div key={outfit.id} className="bg-white rounded-xl shadow-sm hover:shadow-md transition-all border border-gray-100 overflow-hidden flex flex-col">
                      <div className="p-4 border-b border-gray-50 bg-gray-50/50 flex justify-between items-start">
                        <div>
                          <h3 className="font-bold text-gray-900">{outfit.name || `Outfit #${outfit.id}`}</h3>
                          <p className="text-xs text-gray-500">{new Date(outfit.created_at).toLocaleDateString()}</p>
                        </div>
                        <button onClick={() => handleDeleteOutfit(outfit.id)} className="text-red-500 hover:text-red-700 text-xs font-medium px-2 py-1 rounded hover:bg-red-50">Delete</button>
                      </div>
                      <div className="p-4 flex-1">
                        <div className="grid grid-cols-5 gap-2">
                          {/* We render small thumbnails of items */}
                          {['top', 'bottom', 'footwear', 'outerwear', 'accessories'].map(part => {
                            const item = outfit.items[part as keyof typeof outfit.items] as V2Item;
                            if (!item) return null;
                            return (
                              <div key={part} className="aspect-square relative rounded-lg overflow-hidden bg-gray-100 border border-gray-200" title={`${part}: ${item.name}`}>
                                {item.image_url ? (
                                  <Image src={item.image_url} alt={item.name} fill className="object-cover" />
                                ) : (
                                  <div className="w-full h-full flex items-center justify-center text-xs text-gray-400">?</div>
                                )}
                              </div>
                            )
                          })}
                        </div>
                        <div className="mt-4 flex flex-wrap gap-2">
                          {Object.values(outfit.items).filter((i): i is V2Item => !!i && typeof i === 'object').map((item) => (
                            <span key={item.id} className="inline-block px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-md truncate max-w-[100px]">{item.name}</span>
                          ))}
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
      </div>
    </ProtectedRoute >
  )
}
