'use client'

import { useEffect, useState } from 'react'
import Image from 'next/image'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { wardrobeAPI, WardrobeItem } from '@/lib/api'
import { toggleFavorite, getFavorites } from '@/lib/storage'
import Link from 'next/link'

interface PageProps {
  params: { id: string }
}

export default function WardrobeItemPage({ params }: PageProps) {
  const id = Number(params.id)
  const [item, setItem] = useState<WardrobeItem | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [favorite, setFavorite] = useState(false)

  useEffect(() => {
    const run = async () => {
      try {
        setLoading(true)
        setError(null)
        const data = await wardrobeAPI.getById(id)
        setItem(data)
      } catch (e: any) {
        if (e?.response?.status === 404) {
          setError('Item not found')
        } else {
          setError('Failed to load item')
        }
      } finally {
        setLoading(false)
      }
    }
    if (!Number.isNaN(id)) run()
    setFavorite(getFavorites().has(id))
  }, [id])

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 py-12">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 py-12">
        <div className="container mx-auto px-4 max-w-3xl">
          <Card>
            <div className="p-8 text-center">
              <h1 className="text-2xl font-bold text-gray-900 mb-2">{error}</h1>
              <p className="text-gray-600 mb-4">Try returning to your wardrobe.</p>
              <Link href="/wardrobe"><Button>Back to Wardrobe</Button></Link>
            </div>
          </Card>
        </div>
      </div>
    )
  }

  if (!item) return null

  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <div className="container mx-auto px-4 max-w-5xl">
        <div className="mb-6">
          <Link href="/wardrobe" className="text-primary-700 hover:underline">← Back to Wardrobe</Link>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <Card>
            <div className="relative h-96 bg-gray-200">
              {item.image_url && (
                <Image src={item.image_url} alt={`${item.color} ${item.type}`} fill className="object-cover" />
              )}
            </div>
          </Card>
          <div>
            <Card>
              <div className="p-6">
                <div className="flex items-start justify-between">
                  <h1 className="text-3xl font-bold text-gray-900 mb-2">{item.type}</h1>
                  <button
                    aria-label="Toggle favorite"
                    onClick={() => { setFavorite(toggleFavorite(item.id).has(item.id)) }}
                    className="ml-2 text-gray-400 hover:text-red-600"
                  >
                    {favorite ? (
                      <svg className="w-7 h-7" viewBox="0 0 24 24" fill="currentColor"><path d="M11.645 20.91l-.007-.003-.022-.012a15.247 15.247 0 01-.383-.218 25.18 25.18 0 01-4.244-3.17C4.688 15.698 3 13.35 3 10.5 3 8.015 5.015 6 7.5 6A5.5 5.5 0 0112 8.019 5.5 5.5 0 0116.5 6C18.985 6 21 8.015 21 10.5c0 2.85-1.688 5.199-3.989 7.007a25.175 25.175 0 01-4.244 3.17 15.247 15.247 0 01-.383.218l-.022.012-.007.003-.003.002a.75.75 0 01-.718 0l-.003-.002z"/></svg>
                    ) : (
                      <svg className="w-7 h-7" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path strokeWidth="1.5" d="M21 10.5c0 2.85-1.688 5.199-3.989 7.007a25.175 25.175 0 01-4.244 3.17 15.247 15.247 0 01-.383.218l-.022.012-.007.003-.003.002a.75.75 0 01-.718 0l-.003-.002-.007-.003-.022-.012a15.247 15.247 0 01-.383-.218 25.18 25.18 0 01-4.244-3.17C4.688 15.698 3 13.35 3 10.5 3 8.015 5.015 6 7.5 6A5.5 5.5 0 0112 8.019 5.5 5.5 0 0116.5 6C18.985 6 21 8.015 21 10.5z"/></svg>
                    )}
                  </button>
                </div>
                <div className="flex items-center gap-3 mb-4">
                  <span className="inline-block w-6 h-6 rounded-full border border-gray-300" style={{ backgroundColor: item.color.toLowerCase() }}></span>
                  <span className="text-gray-700">{item.color}</span>
                </div>
                {item.category && <div className="text-sm text-gray-500">Category: {item.category}</div>}
                <div className="text-sm text-gray-500">Item ID: {item.id}</div>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}
