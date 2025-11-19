'use client'

import { useEffect, useMemo, useState } from 'react'
import Image from 'next/image'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { wardrobeAPI } from '@/lib/api'
import { getFavorites, toggleFavorite } from '@/lib/storage'
import { getColorHex } from '@/lib/colors'
import AddItemModal from '@/components/modals/AddItemModal'
import HealthStatus from '@/components/system/HealthStatus'

interface WardrobeItem {
  id: number
  type: string
  color: string
  image_url: string | null
  category?: 'top' | 'bottom' | 'footwear' | 'layer' | 'one-piece' | 'accessories'
}

export default function WardrobePage() {
  const [items, setItems] = useState<WardrobeItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [q, setQ] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [colorFilter, setColorFilter] = useState('')
  const [sort, setSort] = useState<'id' | '-id' | 'type' | '-type' | 'color' | '-color'>('id')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(12)
  const [total, setTotal] = useState(0)
  const [favorites, setFavorites] = useState<Set<number>>(new Set())
  const [showAddModal, setShowAddModal] = useState(false)
  const [deletingId, setDeletingId] = useState<number | null>(null)

  useEffect(() => {
    fetchWardrobeItems()
  }, [])

  const fetchWardrobeItems = async (params?: { q?: string; type?: string; color?: string; category?: string; sort?: typeof sort; page?: number; page_size?: number }) => {
    try {
      setLoading(true)
      setError(null)
      const { items, total } = await wardrobeAPI.getAllPaged(params)
      setItems(items)
      setTotal(total)
    } catch (err) {
      setError('Failed to load wardrobe items. Make sure the backend is running.')
      console.error('Error fetching wardrobe:', err)
    } finally {
      setLoading(false)
    }
  }

  // Debounced refetch on filter changes
  useEffect(() => {
    const t = setTimeout(() => {
      fetchWardrobeItems({
        q: q || undefined,
        type: typeFilter || undefined,
        color: colorFilter || undefined,
        category: categoryFilter || undefined,
        sort,
        page,
        page_size: pageSize,
      })
    }, 300)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, typeFilter, colorFilter, categoryFilter, sort, page, pageSize])

  const uniqueTypes = useMemo(() => Array.from(new Set(items.map(i => i.type))).sort(), [items])
  const uniqueColors = useMemo(() => Array.from(new Set(items.map(i => i.color))).sort(), [items])

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this item?')) return
    try {
      setDeletingId(id)
      await wardrobeAPI.delete(id)
      await fetchWardrobeItems({
        q: q || undefined,
        type: typeFilter || undefined,
        color: colorFilter || undefined,
        category: categoryFilter || undefined,
        sort,
        page,
        page_size: pageSize,
      })
    } catch (err) {
      console.error(err)
      alert('Failed to delete item')
    } finally {
      setDeletingId(null)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 py-6 sm:py-12">
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
      <div className="min-h-screen bg-gray-50 py-6 sm:py-12">
        <div className="container mx-auto px-4 sm:px-6">
          <Card>
            <div className="p-6 sm:p-8 text-center">
              <div className="w-12 h-12 sm:w-16 sm:h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-3 sm:mb-4">
                <svg className="w-6 h-6 sm:w-8 sm:h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h2 className="text-lg sm:text-xl font-semibold text-gray-900 mb-2">Error Loading Wardrobe</h2>
              <p className="text-sm sm:text-base text-gray-600 mb-4 break-words">{error}</p>
              <button
                onClick={fetchWardrobeItems}
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
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-gray-50 py-6 sm:py-12">
      <div className="container mx-auto px-4 sm:px-6">
        {/* Dashboard Header */}
        <div className="mb-6 sm:mb-8">
          <h1 className="text-3xl sm:text-4xl font-bold bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent mb-2">Dashboard</h1>
          <p className="text-gray-600 text-sm sm:text-base">Welcome back! Here's an overview of your wardrobe.</p>
        </div>

        {/* API Health */}
        <div className="mb-4 sm:mb-8">
          <HealthStatus />
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4 md:gap-6 mb-6 sm:mb-8 md:mb-12">
          <div className="bg-white rounded-xl sm:rounded-2xl shadow-sm hover:shadow-md transition-shadow border border-gray-100 p-4 sm:p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs sm:text-sm text-gray-500 mb-1 font-medium">Total Items</p>
                <p className="text-xl sm:text-2xl md:text-3xl font-bold bg-gradient-to-r from-primary-600 to-primary-500 bg-clip-text text-transparent">{total}</p>
              </div>
              <div className="w-10 h-10 sm:w-12 sm:h-12 md:w-14 md:h-14 bg-gradient-to-br from-primary-500 to-primary-600 rounded-xl sm:rounded-2xl flex items-center justify-center shadow-lg">
                <svg className="w-5 h-5 sm:w-6 sm:h-6 md:w-7 md:h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl sm:rounded-2xl shadow-sm hover:shadow-md transition-shadow border border-gray-100 p-4 sm:p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs sm:text-sm text-gray-500 mb-1 font-medium">Categories</p>
                <p className="text-xl sm:text-2xl md:text-3xl font-bold bg-gradient-to-r from-green-600 to-green-500 bg-clip-text text-transparent">{new Set(items.map(i => i.category)).size}</p>
              </div>
              <div className="w-10 h-10 sm:w-12 sm:h-12 md:w-14 md:h-14 bg-gradient-to-br from-green-500 to-green-600 rounded-xl sm:rounded-2xl flex items-center justify-center shadow-lg">
                <svg className="w-5 h-5 sm:w-6 sm:h-6 md:w-7 md:h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                </svg>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl sm:rounded-2xl shadow-sm hover:shadow-md transition-shadow border border-gray-100 p-4 sm:p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs sm:text-sm text-gray-500 mb-1 font-medium">Outfits Created</p>
                <p className="text-xl sm:text-2xl md:text-3xl font-bold bg-gradient-to-r from-purple-600 to-purple-500 bg-clip-text text-transparent">0</p>
              </div>
              <div className="w-10 h-10 sm:w-12 sm:h-12 md:w-14 md:h-14 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl sm:rounded-2xl flex items-center justify-center shadow-lg">
                <svg className="w-5 h-5 sm:w-6 sm:h-6 md:w-7 md:h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                </svg>
              </div>
            </div>
          </div>
        </div>

        {/* Wardrobe Header */}
        <div className="mb-4 sm:mb-6 md:mb-8 flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4">
          <div>
            <h2 className="text-xl sm:text-2xl md:text-3xl font-bold text-gray-900 mb-1">My Wardrobe</h2>
            <p className="text-gray-600 text-xs sm:text-sm md:text-base">Browse and manage your clothing collection</p>
          </div>
          <button
            onClick={() => setShowAddModal(true)}
            className="inline-flex items-center justify-center px-4 sm:px-6 py-2.5 sm:py-3 bg-gradient-to-r from-primary-600 to-primary-700 text-white rounded-lg sm:rounded-xl shadow-md hover:shadow-lg transition-all duration-200 font-medium text-sm sm:text-base whitespace-nowrap w-full sm:w-auto"
          >
            <svg className="w-4 h-4 sm:w-5 sm:h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add Item
          </button>
        </div>

        {/* Filters */}
        <div className="mb-4 sm:mb-6 bg-white rounded-xl sm:rounded-2xl shadow-sm border border-gray-100 p-3 sm:p-4 md:p-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 sm:gap-4">
            <div>
              <label className="block text-xs sm:text-sm font-medium text-gray-700 mb-1">Search</label>
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search by type or color"
                className="w-full px-3 py-2 text-sm sm:text-base border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-gray-900"
              />
            </div>
            <div>
              <label className="block text-xs sm:text-sm font-medium text-gray-700 mb-1">Type</label>
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="w-full px-3 py-2 text-sm sm:text-base border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white text-gray-900"
              >
                <option value="">All</option>
                {uniqueTypes.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs sm:text-sm font-medium text-gray-700 mb-1">Color</label>
              <select
                value={colorFilter}
                onChange={(e) => setColorFilter(e.target.value)}
                className="w-full px-3 py-2 text-sm sm:text-base border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white text-gray-900"
              >
                <option value="">All</option>
                {uniqueColors.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs sm:text-sm font-medium text-gray-700 mb-1">Category</label>
              <select
                value={categoryFilter}
                onChange={(e) => { setCategoryFilter(e.target.value); setPage(1) }}
                className="w-full px-3 py-2 text-sm sm:text-base border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white text-gray-900"
              >
                <option value="">All</option>
                {['top','bottom','footwear','layer','one-piece','accessories'].map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs sm:text-sm font-medium text-gray-700 mb-1">Sort</label>
              <select
                value={sort}
                onChange={(e) => setSort(e.target.value as any)}
                className="w-full px-3 py-2 text-sm sm:text-base border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white text-gray-900"
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
          {/* Pagination controls */}
          <div className="mt-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-0">
            <div className="text-xs sm:text-sm text-gray-600">Total: {total}</div>
            <div className="flex items-center gap-2 w-full sm:w-auto">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-2.5 sm:px-3 py-1.5 sm:py-1 text-xs sm:text-sm border border-gray-300 rounded bg-white text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={page === 1}
              >Prev</button>
              <span className="text-xs sm:text-sm text-gray-700 font-medium px-2">Page {page}</span>
              <button
                onClick={() => setPage((p) => (p * pageSize < total ? p + 1 : p))}
                className="px-2.5 sm:px-3 py-1.5 sm:py-1 text-xs sm:text-sm border border-gray-300 rounded bg-white text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={page * pageSize >= total}
              >Next</button>
              <select
                value={pageSize}
                onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1) }}
                className="ml-0 sm:ml-2 px-2 py-1.5 sm:py-1 text-xs sm:text-sm border border-gray-300 rounded bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                {[8,12,16,24].map(n => <option key={n} value={n}>{n}/page</option>)}
              </select>
            </div>
          </div>
        </div>

        {/* Wardrobe Grid */}
        {items.length === 0 ? (
          <div className="bg-white rounded-xl sm:rounded-2xl shadow-sm border border-gray-100 p-6 sm:p-8 md:p-12 text-center">
            <svg className="w-12 h-12 sm:w-16 sm:h-16 mx-auto mb-3 sm:mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            <p className="text-gray-600 text-base sm:text-lg">No items in your wardrobe yet.</p>
            <p className="text-gray-500 text-xs sm:text-sm mt-2">Add your first item to get started!</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-2 sm:gap-3 md:gap-4 lg:gap-6">
            {items.map((item) => (
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
                      <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4 md:w-5 md:h-5 text-red-500" viewBox="0 0 24 24" fill="currentColor"><path d="M11.645 20.91l-.007-.003-.022-.012a15.247 15.247 0 01-.383-.218 25.18 25.18 0 01-4.244-3.17C4.688 15.698 3 13.35 3 10.5 3 8.015 5.015 6 7.5 6A5.5 5.5 0 0112 8.019 5.5 5.5 0 0116.5 6C18.985 6 21 8.015 21 10.5c0 2.85-1.688 5.199-3.989 7.007a25.175 25.175 0 01-4.244 3.17 15.247 15.247 0 01-.383.218l-.022.012-.007.003-.003.002a.75.75 0 01-.718 0l-.003-.002z"/></svg>
                    ) : (
                      <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4 md:w-5 md:h-5 text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path strokeWidth="1.5" d="M21 10.5c0 2.85-1.688 5.199-3.989 7.007a25.175 25.175 0 01-4.244 3.17 15.247 15.247 0 01-.383.218l-.022.012-.007.003-.003.002a.75.75 0 01-.718 0l-.003-.002-.007-.003-.022-.012a15.247 15.247 0 01-.383-.218 25.18 25.18 0 01-4.244-3.17C4.688 15.698 3 13.35 3 10.5 3 8.015 5.015 6 7.5 6A5.5 5.5 0 0112 8.019 5.5 5.5 0 0116.5 6C18.985 6 21 8.015 21 10.5z"/></svg>
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
      </div>

      {/* Add Item Modal */}
      {showAddModal && (
        <AddItemModal
          onClose={() => setShowAddModal(false)}
          onSuccess={() => {
            fetchWardrobeItems({
              q: q || undefined,
              type: typeFilter || undefined,
              color: colorFilter || undefined,
              category: categoryFilter || undefined,
              sort,
              page,
              page_size: pageSize,
            })
          }}
        />
      )}
    </div>
  )
}
