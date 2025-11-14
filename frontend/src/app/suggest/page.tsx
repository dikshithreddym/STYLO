'use client'

import { useState } from 'react'
import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import Image from 'next/image'
import { suggestionsAPI, WardrobeItem, Outfit } from '@/lib/api'
import { saveSuggestHistory } from '@/lib/storage'
import { getColorHex } from '@/lib/colors'

interface SuggestResult {
  occasion: string
  colors: string[]
  outfit: Outfit
  alternatives: Outfit[]
  notes?: string | null
}

export default function SuggestPage() {
  const [text, setText] = useState('Casual dinner in a cold evening, prefer navy or white.')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<SuggestResult | null>(null)

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setLoading(true)
      setError(null)
      const res = await suggestionsAPI.suggest(text, { limit: 5, strategy: 'rules' })
      setResult(res)
      // Save to history
      const ids = res.outfit.items.map(i => i.id)
      saveSuggestHistory({ id: Math.random().toString(36).slice(2), text, timestamp: Date.now(), outfitItemIds: ids })
    } catch (err: any) {
      console.error(err)
      // Extract error message from API response
      const errorMessage = err?.response?.data?.detail || 'Failed to get suggestion. Ensure backend is running.'
      setError(errorMessage)
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <div className="container mx-auto px-4">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900">Outfit Suggestion</h1>
          <p className="text-gray-600">Describe your occasion, weather, and any preferences. We’ll suggest an outfit from your wardrobe.</p>
        </div>

        <Card>
          <form onSubmit={onSubmit} className="p-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">Your prompt</label>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              className="w-full h-28 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-gray-900"
              placeholder="e.g., Business meeting on a hot day. Prefer light colors."
            />
            <div className="mt-4">
              <Button type="submit" disabled={loading}>
                {loading ? 'Analyzing…' : 'Get Suggestion'}
              </Button>
            </div>
            {error && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex items-start gap-3">
                  <svg className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                  <div className="flex-1">
                    <h3 className="text-sm font-medium text-red-800 mb-1">Unable to Generate Outfit</h3>
                    <p className="text-sm text-red-700">{error}</p>
                    {error.includes('empty') || error.includes('Not enough') ? (
                      <p className="text-sm text-red-600 mt-2">
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
          <div className="mt-8 sm:mt-10">
            <div className="mb-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <h2 className="text-2xl sm:text-3xl font-bold text-gray-900">Suggested Outfit</h2>
                <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-green-500 to-green-600 text-white rounded-full text-sm font-medium shadow-md">
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                  {(result.outfit.score * 100).toFixed(0)}% Match
                </div>
              </div>
              {result.notes && <p className="text-gray-600 mt-2 text-sm sm:text-base">{result.notes}</p>}
            </div>

            {result.outfit.items.length === 0 ? (
              <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 sm:p-12 text-center">
                <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-gray-600 text-lg">No suitable items found in your wardrobe.</p>
                <p className="text-gray-500 text-sm mt-2">Try adding more items or adjusting your prompt.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
                {result.outfit.items.map((item) => (
                  <div key={item.id} className="group bg-white rounded-2xl shadow-sm hover:shadow-xl transition-all duration-300 border border-gray-100 overflow-hidden">
                    <div className="relative h-56 sm:h-64 bg-gradient-to-br from-gray-100 to-gray-200">
                      {item.image_url && (
                        <Image 
                          src={item.image_url} 
                          alt={`${item.color} ${item.type}`} 
                          fill 
                          className="object-cover group-hover:scale-110 transition-transform duration-500" 
                        />
                      )}
                    </div>
                    <div className="p-4">
                      <h3 className="font-semibold text-lg text-gray-900">{item.type}</h3>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="inline-block w-3 h-3 rounded-full border border-gray-300 shadow-sm" style={{ backgroundColor: getColorHex(item.color) }}></span>
                        <p className="text-gray-600 text-sm">{item.color}</p>
                      </div>
                      {item.category && <span className="inline-block mt-2 px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-lg font-medium">{item.category}</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Alternatives */}
            {result.alternatives.length > 0 && (
              <div className="mt-8 sm:mt-10">
                <h3 className="text-xl sm:text-2xl font-bold text-gray-900 mb-4 sm:mb-6">More Suggestions</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
                  {result.alternatives.map((alt, idx) => (
                    <div key={idx} className="bg-white rounded-2xl shadow-sm hover:shadow-md transition-shadow border border-gray-100 overflow-hidden">
                      <div className="p-4 bg-gradient-to-r from-gray-50 to-white border-b border-gray-100 flex items-center justify-between">
                        <div className="font-semibold text-gray-900">Alternative #{idx + 1}</div>
                        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-primary-50 text-primary-700 rounded-full text-xs font-medium">
                          <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                          </svg>
                          {(alt.score * 100).toFixed(0)}%
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-3 p-4">
                        {alt.items.map((it) => (
                          <div key={it.id} className="flex items-start gap-2 p-2 rounded-lg hover:bg-gray-50 transition-colors">
                            <div className="w-2.5 h-2.5 mt-1.5 rounded-full border border-gray-300 shadow-sm flex-shrink-0" style={{ backgroundColor: getColorHex(it.color) }}></div>
                            <div className="text-sm min-w-0">
                              <div className="font-medium text-gray-900 truncate">{it.type}</div>
                              <div className="text-gray-600 text-xs truncate">{it.color}</div>
                              {it.category && <div className="text-gray-500 text-xs mt-0.5">{it.category}</div>}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
