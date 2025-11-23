'use client'

import { useState, useEffect, useRef } from 'react'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import Image from 'next/image'
import { suggestionsAPI, V2SuggestResponse, V2Outfit, V2Item } from '@/lib/api'
import { saveSuggestHistory } from '@/lib/storage'
import { getColorHex } from '@/lib/colors'
import { suggestionCache } from '@/lib/wardrobeCache'

const PENDING_REQUEST_KEY = 'stylo.pending_suggestion_request'

export default function SuggestPage() {
  const [text, setText] = useState('Professional business meeting at a tech startup')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<V2SuggestResponse | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  // Check for pending request on mount and restore state
  useEffect(() => {
    if (typeof window === 'undefined') return

    const checkPendingRequest = async () => {
      try {
        const pendingRequest = sessionStorage.getItem(PENDING_REQUEST_KEY)
        if (pendingRequest) {
          const { query, timestamp } = JSON.parse(pendingRequest)
          // Check if request is still recent (within 3 minutes)
          const age = Date.now() - timestamp
          if (age < 180000) { // 3 minutes
            setText(query)
            
            // First check if result is already in cache (request might have completed)
            const cachedResult = suggestionCache.getCached(query)
            if (cachedResult) {
              // Request completed while away, show result immediately
              setResult(cachedResult)
              setLoading(false)
              sessionStorage.removeItem(PENDING_REQUEST_KEY)
            } else {
              // Request still pending, show loading state and retry
              // (cache will prevent duplicate work if first request completes)
              setLoading(true)
              
              // Retry the request (cache check will prevent duplicate if already completed)
              try {
                const res = await suggestionsAPI.suggestV2(query, 3)
                suggestionCache.setCached(query, res)
                setResult(res)
                
                // Save to history
                if (res.outfits.length > 0) {
                  const firstOutfit = res.outfits[0]
                  const ids = [
                    firstOutfit.top?.id,
                    firstOutfit.bottom?.id,
                    firstOutfit.footwear?.id,
                    firstOutfit.outerwear?.id,
                    firstOutfit.accessories?.id,
                  ].filter((id): id is number => id !== undefined && id !== null)
                  saveSuggestHistory({ id: Math.random().toString(36).slice(2), query, timestamp: Date.now(), outfitItemIds: ids })
                }
              } catch (err: any) {
                // If error, show it
                const errorMessage = err?.response?.data?.detail || 'Failed to get suggestion. Ensure backend is running.'
                setError(errorMessage)
              } finally {
                setLoading(false)
                sessionStorage.removeItem(PENDING_REQUEST_KEY)
              }
            }
          } else {
            // Request is too old, clear it
            sessionStorage.removeItem(PENDING_REQUEST_KEY)
          }
        }
      } catch (error) {
        console.error('Error checking pending request:', error)
      }
    }

    checkPendingRequest()

    // Cleanup on unmount
    return () => {
      // Cancel any pending request when component unmounts
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
        abortControllerRef.current = null
      }
    }
  }, [])

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Cancel any previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    
    // Create new AbortController for this request
    const abortController = new AbortController()
    abortControllerRef.current = abortController
    
    try {
      setLoading(true)
      setError(null)
      
      // Store pending request in sessionStorage
      if (typeof window !== 'undefined') {
        sessionStorage.setItem(PENDING_REQUEST_KEY, JSON.stringify({
          query: text,
          timestamp: Date.now()
        }))
      }
      
      // Check cache first
      const cachedResult = suggestionCache.getCached(text)
      if (cachedResult) {
        setResult(cachedResult)
        setLoading(false)
        
        // Clear pending request
        if (typeof window !== 'undefined') {
          sessionStorage.removeItem(PENDING_REQUEST_KEY)
        }
        
        // Save to history
        if (cachedResult.outfits.length > 0) {
          const firstOutfit = cachedResult.outfits[0]
          const ids = [
            firstOutfit.top?.id,
            firstOutfit.bottom?.id,
            firstOutfit.footwear?.id,
            firstOutfit.outerwear?.id,
            firstOutfit.accessories?.id,
          ].filter((id): id is number => id !== undefined && id !== null)
          saveSuggestHistory({ id: Math.random().toString(36).slice(2), text, timestamp: Date.now(), outfitItemIds: ids })
        }
        return
      }
      
      // Fetch from API if not cached (with abort signal)
      const res = await suggestionsAPI.suggestV2(text, 3, abortController.signal)
      
      // Check if request was aborted
      if (abortController.signal.aborted) {
        return
      }
      
      // Cache the result
      suggestionCache.setCached(text, res)
      
      setResult(res)
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
      // Don't set error if request was aborted
      if (abortController.signal.aborted || err.name === 'AbortError' || err.code === 'ERR_CANCELED') {
        return
      }
      
      console.error(err)
      // Extract error message from API response
      const errorMessage = err?.response?.data?.detail || 'Failed to get suggestion. Ensure backend is running.'
      setError(errorMessage)
      setResult(null)
    } finally {
      // Only update loading state if request wasn't aborted
      if (!abortController.signal.aborted) {
        setLoading(false)
        
        // Clear pending request
        if (typeof window !== 'undefined') {
          sessionStorage.removeItem(PENDING_REQUEST_KEY)
        }
      }
      
      // Clear abort controller ref
      if (abortControllerRef.current === abortController) {
        abortControllerRef.current = null
      }
    }
  }

  const renderOutfitItem = (item: V2Item | null, label: string) => {
    if (!item) return null
    
    return (
      <div key={item.id} className="group bg-white rounded-xl sm:rounded-2xl shadow-sm hover:shadow-xl transition-all duration-300 border border-gray-100 overflow-hidden">
        <div className="relative h-48 sm:h-56 md:h-64 bg-gradient-to-br from-gray-100 to-gray-200">
          {item.image_url && (
            <Image 
              src={item.image_url} 
              alt={`${item.name}`} 
              fill 
              className="object-cover group-hover:scale-110 transition-transform duration-500" 
              sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 20vw"
            />
          )}
          <div className="absolute top-2 left-2 px-2 py-1 bg-black/70 text-white text-xs font-medium rounded-md sm:rounded-lg backdrop-blur-sm">
            {label}
          </div>
        </div>
        <div className="p-3 sm:p-4">
          <h3 className="font-semibold text-base sm:text-lg text-gray-900 line-clamp-2">{item.name}</h3>
          <div className="flex items-center gap-2 mt-1">
            {item.color && item.color !== 'Unknown' && (
              <>
                <span className="inline-block w-3 h-3 rounded-full border border-gray-300 shadow-sm flex-shrink-0" style={{ backgroundColor: getColorHex(item.color) }}></span>
                <p className="text-gray-600 text-xs sm:text-sm truncate">{item.color}</p>
              </>
            )}
          </div>
          <span className="inline-block mt-2 px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-md sm:rounded-lg font-medium">{item.category}</span>
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

    // Ensure score is a number and handle edge cases
    const score = typeof outfit.score === 'number' ? outfit.score : parseFloat(outfit.score as any) || 0
    const scoreColor = score >= 90 ? 'text-green-600' : score >= 70 ? 'text-yellow-600' : 'text-orange-600'
    const scoreBg = score >= 90 ? 'bg-green-50 border-green-200' : score >= 70 ? 'bg-yellow-50 border-yellow-200' : 'bg-orange-50 border-orange-200'
    const rationale = outfit.rationale || 'Outfit selected from your wardrobe.'

    return (
      <div key={index} className="mb-6 sm:mb-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 sm:gap-0 mb-3 sm:mb-4">
          {index > 0 ? (
            <h3 className="text-lg sm:text-xl font-bold text-gray-900">Alternative #{index}</h3>
          ) : (
            <h3 className="text-lg sm:text-xl font-bold text-gray-900">Top Suggestion</h3>
          )}
          <div className={`inline-flex items-center gap-1.5 sm:gap-2 px-2.5 sm:px-3 py-1.5 rounded-full text-xs sm:text-sm font-semibold border ${scoreBg} ${scoreColor} self-start sm:self-auto`}>
            {score >= 90 && (
              <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            )}
            <span>{score.toFixed(0)}% Match</span>
          </div>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 sm:gap-4 md:gap-6 mb-3 sm:mb-4">
          {items.map(({ item, label }) => renderOutfitItem(item, label))}
        </div>
        <div className={`mt-3 sm:mt-4 p-3 sm:p-4 rounded-lg border ${scoreBg}`}>
          <div className="flex items-start gap-2 sm:gap-3">
            <svg className="w-4 h-4 sm:w-5 sm:h-5 flex-shrink-0 mt-0.5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
            <div className="flex-1 min-w-0">
              <h4 className="text-xs sm:text-sm font-semibold text-gray-900 mb-1">Why this outfit?</h4>
              <p className="text-xs sm:text-sm text-gray-700 leading-relaxed">{rationale}</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-6 sm:py-12">
      <div className="container mx-auto px-4 sm:px-6">
        <div className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold text-gray-900 mb-2">AI Outfit Suggestions</h1>
          <p className="text-sm sm:text-base text-gray-600 leading-relaxed">Describe your occasion, and our AI will suggest intelligent outfits using semantic matching and color harmony.</p>
        </div>

        <Card>
          <form onSubmit={onSubmit} className="p-4 sm:p-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">Your prompt</label>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              className="w-full h-24 sm:h-28 px-3 sm:px-4 py-2 text-sm sm:text-base border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-gray-900 resize-none"
              placeholder="e.g., Business meeting, Gym workout, Date night"
            />
            <div className="mt-4">
              <Button type="submit" disabled={loading} className="w-full sm:w-auto">
                {loading ? 'Analyzing…' : 'Get AI Suggestions'}
              </Button>
            </div>
            {error && (
              <div className="mt-4 p-3 sm:p-4 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex items-start gap-2 sm:gap-3">
                  <svg className="w-4 h-4 sm:w-5 sm:h-5 text-red-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-xs sm:text-sm font-medium text-red-800 mb-1">Unable to Generate Outfit</h3>
                    <p className="text-xs sm:text-sm text-red-700 break-words">{error}</p>
                    {error.includes('empty') || error.includes('Not enough') ? (
                      <p className="text-xs sm:text-sm text-red-600 mt-2">
                        💡 Tip: <a href="/wardrobe" className="underline font-medium hover:text-red-800">Add more items to your wardrobe</a> to get outfit suggestions.
                      </p>
                    ) : null}
                  </div>
                </div>
              </div>
            )}
          </form>
        </Card>

        {result && (
          <div className="mt-6 sm:mt-8 md:mt-10">
            <div className="mb-4 sm:mb-6">
              <div className="flex flex-col gap-3 sm:gap-2">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <h2 className="text-xl sm:text-2xl md:text-3xl font-bold text-gray-900">AI-Powered Suggestions</h2>
                  <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-purple-500 to-indigo-600 text-white rounded-full text-xs sm:text-sm font-medium shadow-md self-start sm:self-auto">
                    <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                      <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
                    </svg>
                    <span className="hidden xs:inline">Intent: </span>{result.intent}
                  </div>
                </div>
                <p className="text-gray-600 text-xs sm:text-sm md:text-base leading-relaxed">
                  Based on your query, our AI detected a <span className="font-semibold text-gray-900">{result.intent}</span> occasion and selected items using semantic matching, color harmony, and intent-aware rules.
                </p>
              </div>
            </div>

            {result.outfits.length === 0 ? (
              <div className="bg-white rounded-xl sm:rounded-2xl shadow-sm border border-gray-100 p-6 sm:p-8 md:p-12 text-center">
                <svg className="w-12 h-12 sm:w-16 sm:h-16 mx-auto mb-3 sm:mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-gray-600 text-base sm:text-lg">No suitable items found in your wardrobe.</p>
                <p className="text-gray-500 text-xs sm:text-sm mt-2">Try adding more items or adjusting your prompt.</p>
              </div>
            ) : (
              <div>
                {result.outfits.map((outfit, idx) => renderOutfit(outfit, idx))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
