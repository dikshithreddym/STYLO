'use client'

import { useState, useEffect } from 'react'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import Image from 'next/image'
import { suggestionsAPI, V2SuggestResponse, V2Outfit, V2Item, outfitsAPI } from '@/lib/api'
import { saveSuggestHistory } from '@/lib/storage'
import { getColorHex } from '@/lib/colors'
import ProtectedRoute from '@/components/auth/ProtectedRoute'

const SUGGEST_QUERY_KEY = 'stylo.suggest.query'
const SUGGEST_RESULT_KEY = 'stylo.suggest.result'

// Helper functions to persist query and result
function saveQueryToStorage(query: string) {
  if (typeof window !== 'undefined') {
    try {
      sessionStorage.setItem(SUGGEST_QUERY_KEY, query)
    } catch { }
  }
}

function loadQueryFromStorage(): string {
  if (typeof window !== 'undefined') {
    try {
      return sessionStorage.getItem(SUGGEST_QUERY_KEY) || 'Professional business meeting at a tech startup'
    } catch { }
  }
  return 'Professional business meeting at a tech startup'
}

function saveResultToStorage(result: V2SuggestResponse | null) {
  if (typeof window !== 'undefined') {
    try {
      if (result) {
        sessionStorage.setItem(SUGGEST_RESULT_KEY, JSON.stringify(result))
      } else {
        sessionStorage.removeItem(SUGGEST_RESULT_KEY)
      }
    } catch { }
  }
}

function loadResultFromStorage(): V2SuggestResponse | null {
  if (typeof window !== 'undefined') {
    try {
      const raw = sessionStorage.getItem(SUGGEST_RESULT_KEY)
      return raw ? JSON.parse(raw) : null
    } catch { }
  }
  return null
}

export default function SuggestPage() {
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<V2SuggestResponse | null>(null)
  const [savingOutfitIndex, setSavingOutfitIndex] = useState<number | null>(null)
  const promptIdeas = [
    'Creative brunch at an art gallery',
    'Remote work day at a coffee shop',
    'Evening rooftop party with friends',
    'Winter city stroll and warm drinks',
    'Outdoor concert in mild weather',
  ]

  // Load persisted query and result on mount
  useEffect(() => {
    const savedQuery = loadQueryFromStorage()
    const savedResult = loadResultFromStorage()
    setText(savedQuery)
    if (savedResult) {
      setResult(savedResult)
      setError(null) // Clear any previous error if we have a saved result
    }
  }, [])

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setLoading(true)
      setError(null)
      // Save query before submitting
      saveQueryToStorage(text)
      const res = await suggestionsAPI.suggestV2(text, 3)
      setResult(res)
      // Save result to storage
      saveResultToStorage(res)
      // Save to history - collect all item IDs from first outfit
      if (res.outfits.length > 0) {
        const firstOutfit = res.outfits[0]
        const ids = [
          firstOutfit.top?.id,
          firstOutfit.bottom?.id,
          firstOutfit.footwear?.id,
          firstOutfit.outerwear?.id,
          firstOutfit.accessories?.id,
        ].filter((id): id is number => id !== undefined && id !== null)
        saveSuggestHistory({ id: Math.random().toString(36).slice(2), text, timestamp: Date.now(), outfitItemIds: ids })
      }
    } catch (err: any) {
      console.error(err)
      // Extract error message from API response
      const errorMessage = err?.response?.data?.detail || 'Failed to get suggestion. Ensure backend is running.'
      setError(errorMessage)
      setResult(null)
      saveResultToStorage(null)
    } finally {
      setLoading(false)
    }
  }

  const handleSaveOutfit = async (outfit: V2Outfit, index: number) => {
    try {
      setSavingOutfitIndex(index)
      // Extract items and remove nulls/undefined for cleaner storage
      const itemsToSave = {
        top: outfit.top,
        bottom: outfit.bottom,
        footwear: outfit.footwear,
        outerwear: outfit.outerwear,
        accessories: outfit.accessories
      }

      const intentName = result?.intent || 'Outfit'
      // Capitalize first letter
      const prettyIntent = intentName.charAt(0).toUpperCase() + intentName.slice(1)

      await outfitsAPI.save({
        items: itemsToSave,
        name: `${prettyIntent} Suggestion`
      })
      alert('Outfit saved to wardrobe!')
    } catch (e) {
      console.error(e)
      alert('Failed to save outfit')
    } finally {
      setSavingOutfitIndex(null)
    }
  }

  // Save query to storage whenever it changes (debounced)
  useEffect(() => {
    const timer = setTimeout(() => {
      if (text) {
        saveQueryToStorage(text)
      }
    }, 500)
    return () => clearTimeout(timer)
  }, [text])

  const handleIdeaClick = (idea: string) => {
    setText(idea)
    saveQueryToStorage(idea)
  }

  const renderOutfitItem = (item: V2Item | null, label: string) => {
    if (!item) return null

    return (
      <div key={item.id} className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
        <div className="relative aspect-square bg-slate-100 dark:bg-slate-700">
          {item.image_url && (
            <Image
              src={item.image_url}
              alt={item.name}
              fill
              className="object-cover"
              sizes="(max-width: 640px) 50vw, 20vw"
            />
          )}
          <span className="absolute top-2 left-2 px-2 py-0.5 bg-slate-900/80 text-white text-xs font-medium rounded">
            {label}
          </span>
        </div>
        <div className="p-3">
          <h3 className="font-medium text-sm text-slate-900 dark:text-white line-clamp-1">{item.name}</h3>
          {item.color && item.color !== 'Unknown' && (
            <div className="flex items-center gap-1.5 mt-1">
              <span className="w-2.5 h-2.5 rounded-full border border-slate-200 dark:border-slate-600" style={{ backgroundColor: getColorHex(item.color) }} />
              <span className="text-xs text-slate-500 dark:text-slate-400">{item.color}</span>
            </div>
          )}
          <span className="inline-block mt-2 px-2 py-0.5 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 text-xs rounded capitalize">{item.category}</span>
        </div>
      </div>
    )
  }

  const renderOutfit = (outfit: V2Outfit, index: number) => {
    const items = [
      { item: outfit.top, label: 'Top' },
      { item: outfit.bottom, label: 'Bottom' },
      { item: outfit.footwear, label: 'Footwear' },
      { item: outfit.outerwear, label: 'Outerwear' },
      { item: outfit.accessories, label: 'Accessories' },
    ].filter(({ item }) => item !== null)

    if (items.length === 0) return null

    const score = typeof outfit.score === 'number' ? outfit.score : parseFloat(outfit.score as any) || 0
    const scoreColor = score >= 90 ? 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/30' : score >= 70 ? 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/30' : 'text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/30'
    const rationale = outfit.rationale || 'Outfit selected from your wardrobe.'

    return (
      <div key={index} className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h3 className="font-semibold text-slate-900 dark:text-white">
              {index === 0 ? 'Top Pick' : `Alternative ${index}`}
            </h3>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => handleSaveOutfit(outfit, index)}
              disabled={savingOutfitIndex === index}
            >
              {savingOutfitIndex === index ? 'Saving...' : 'Save'}
            </Button>
          </div>
          <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${scoreColor}`}>
            {score.toFixed(0)}% Match
          </span>
        </div>

        {/* Items Grid */}
        <div className="p-4">
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
            {items.map(({ item, label }) => renderOutfitItem(item, label))}
          </div>
        </div>

        {/* Rationale */}
        <div className="px-4 pb-4">
          <div className="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-xl">
            <p className="text-sm text-slate-600 dark:text-slate-300">
              <span className="font-medium text-slate-900 dark:text-white">Why this outfit? </span>
              {rationale}
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900 py-6 sm:py-8">
        <div className="container mx-auto px-4 sm:px-6 max-w-5xl">
          {/* Header */}
          <div className="mb-6">
            <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-white">Outfit Suggestions</h1>
            <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Describe your occasion and get AI-powered outfit recommendations</p>
          </div>

          {/* Prompt Card */}
          <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-6 mb-6">
            <form onSubmit={onSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  What's the occasion?
                </label>
                <textarea
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  className="w-full h-24 px-4 py-3 text-sm border border-slate-200 dark:border-slate-600 rounded-xl bg-slate-50 dark:bg-slate-700 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
                  placeholder="e.g., Business meeting, Casual dinner, Beach day..."
                />
              </div>

              {/* Quick Ideas */}
              <div className="flex flex-wrap gap-2">
                {promptIdeas.map((idea) => (
                  <button
                    type="button"
                    key={idea}
                    onClick={() => handleIdeaClick(idea)}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
                  >
                    {idea}
                  </button>
                ))}
              </div>

              <div className="flex items-center justify-between pt-2">
                <span className="text-xs text-slate-400">{text.length}/240 characters</span>
                <Button type="submit" disabled={loading || !text.trim()}>
                  {loading ? 'Analyzing...' : 'Get Suggestions'}
                </Button>
              </div>
            </form>

            {error && (
              <div className="mt-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl">
                <div className="flex items-start gap-3">
                  <svg className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                  <div>
                    <p className="text-sm font-medium text-red-800 dark:text-red-200">{error}</p>
                    {(error.includes('empty') || error.includes('Not enough')) && (
                      <p className="text-sm text-red-600 dark:text-red-300 mt-1">
                        <a href="/wardrobe" className="underline hover:no-underline">Add more items to your wardrobe</a> to get suggestions.
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>

          {result && (
            <div>
              {/* Results Header */}
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Suggested Outfits</h2>
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    Detected occasion: <span className="font-medium text-slate-700 dark:text-slate-300">{result.intent}</span>
                  </p>
                </div>
                <span className="px-3 py-1 bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400 text-xs font-medium rounded-full">
                  {result.outfits.length} outfit{result.outfits.length !== 1 ? 's' : ''}
                </span>
              </div>

              {result.outfits.length === 0 ? (
                <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-12 text-center">
                  <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-100 dark:bg-slate-700 flex items-center justify-center">
                    <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <p className="text-slate-900 dark:text-white font-medium">No matching outfits found</p>
                  <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Try adding more items or adjusting your prompt</p>
                </div>
              ) : (
                <div className="space-y-6">
                  {result.outfits.map((outfit, idx) => renderOutfit(outfit, idx))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </ProtectedRoute>
  )
}
