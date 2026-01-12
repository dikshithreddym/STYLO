'use client'

import { useEffect, useRef } from 'react'
import Image from 'next/image'
import { SavedOutfit, V2Item } from '@/lib/api'

interface OutfitDetailModalProps {
  outfit: SavedOutfit
  onClose: () => void
}

export default function OutfitDetailModal({ outfit, onClose }: OutfitDetailModalProps) {
  const modalRef = useRef<HTMLDivElement>(null)
  const lastActiveRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    // Prevent body scroll when modal is open
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = 'unset'
    }
  }, [])

  useEffect(() => {
    lastActiveRef.current = document.activeElement as HTMLElement | null

    const focusableSelector =
      'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])'
    const focusFirst = () => {
      const container = modalRef.current
      if (!container) return
      const focusable = Array.from(container.querySelectorAll<HTMLElement>(focusableSelector))
      if (focusable.length > 0) {
        focusable[0].focus()
      } else {
        container.focus()
      }
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
        return
      }

      if (e.key !== 'Tab') return
      const container = modalRef.current
      if (!container) return
      const focusable = Array.from(container.querySelectorAll<HTMLElement>(focusableSelector))
      if (focusable.length === 0) {
        e.preventDefault()
        container.focus()
        return
      }
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }

    focusFirst()
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      lastActiveRef.current?.focus()
    }
  }, [onClose])

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

  const outfitParts = [
    { key: 'top', label: 'Top' },
    { key: 'bottom', label: 'Bottom' },
    { key: 'footwear', label: 'Footwear' },
    { key: 'outerwear', label: 'Outerwear' },
    { key: 'accessories', label: 'Accessories' },
  ]

  return (
    <div
      onClick={handleBackdropClick}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
    >
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="outfit-detail-title"
        tabIndex={-1}
        className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto"
      >
        {/* Header */}
        <div className="sticky top-0 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 p-6 flex items-center justify-between z-10">
          <div className="flex items-center gap-3">
            {outfit.is_pinned === 1 && (
              <span className="w-8 h-8 rounded-lg bg-primary-100 dark:bg-primary-900/50 flex items-center justify-center">
                <svg className="w-4 h-4 text-primary-600 dark:text-primary-400" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                </svg>
              </span>
            )}
            <div>
              <h2 id="outfit-detail-title" className="text-2xl font-bold text-slate-900 dark:text-white">
                {outfit.name || `Outfit #${outfit.id}`}
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                Created on {new Date(outfit.created_at).toLocaleDateString('en-US', { 
                  year: 'numeric', 
                  month: 'long', 
                  day: 'numeric' 
                })}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="min-h-11 min-w-11 p-2 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 active:scale-[0.98] transition-transform"
            aria-label="Close outfit details"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Outfit Items Grid */}
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {outfitParts.map(({ key, label }) => {
              const item = outfit.items[key as keyof typeof outfit.items] as V2Item | null
              
              return (
                <div key={key} className="bg-slate-50 dark:bg-slate-900 rounded-xl overflow-hidden border border-slate-200 dark:border-slate-700">
                  {/* Label */}
                  <div className="px-4 py-2 bg-slate-100 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
                    <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wide">
                      {label}
                    </h3>
                  </div>
                  
                  {/* Item Card */}
                  {item ? (
                    <div className="p-4">
                      {/* Image */}
                      <div className="relative aspect-square rounded-lg overflow-hidden bg-white dark:bg-slate-800 mb-3">
                        {item.image_url ? (
                          <Image
                            src={item.image_url}
                            alt={item.name || label}
                            fill
                            className="object-cover"
                            sizes="(max-width: 768px) 100vw, (max-width: 1024px) 50vw, 33vw"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center">
                            <svg className="w-16 h-16 text-slate-300 dark:text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                            </svg>
                          </div>
                        )}
                        
                        {/* Category Badge */}
                        {item.category && (
                          <span className="absolute top-2 left-2 px-2 py-1 bg-slate-900/80 text-white text-xs font-medium rounded capitalize">
                            {item.category}
                          </span>
                        )}
                      </div>
                      
                      {/* Item Details */}
                      <div className="space-y-2">
                        <h4 className="font-medium text-slate-900 dark:text-white line-clamp-2">
                          {item.name || 'Unnamed Item'}
                        </h4>
                        {item.category && (
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-slate-500 dark:text-slate-400">Category:</span>
                            <span className="text-sm text-slate-700 dark:text-slate-300 capitalize">{item.category}</span>
                          </div>
                        )}
                        {item.color && (
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-slate-500 dark:text-slate-400">Color:</span>
                            <span className="text-sm text-slate-700 dark:text-slate-300 capitalize">{item.color}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="p-8 text-center">
                      <div className="w-16 h-16 mx-auto mb-3 rounded-lg bg-slate-200 dark:bg-slate-700 flex items-center justify-center">
                        <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </div>
                      <p className="text-sm text-slate-500 dark:text-slate-400">No {label.toLowerCase()} selected</p>
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* Action Buttons */}
          <div className="mt-8 flex items-center justify-end gap-3 pt-6 border-t border-slate-200 dark:border-slate-700">
            <button
              onClick={onClose}
              className="px-6 py-2.5 rounded-lg border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-200 font-medium hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
