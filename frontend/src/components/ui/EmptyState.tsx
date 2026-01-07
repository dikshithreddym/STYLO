import React from 'react'
import Button from './Button'

interface EmptyStateProps {
    icon?: 'wardrobe' | 'outfit' | 'search' | 'error' | 'ai'
    title: string
    description?: string
    actionLabel?: string
    actionHref?: string
    onAction?: () => void
    className?: string
}

const icons = {
    wardrobe: (
        <svg className="w-16 h-16 sm:w-20 sm:h-20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
    ),
    outfit: (
        <svg className="w-16 h-16 sm:w-20 sm:h-20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
        </svg>
    ),
    search: (
        <svg className="w-16 h-16 sm:w-20 sm:h-20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
    ),
    error: (
        <svg className="w-16 h-16 sm:w-20 sm:h-20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
    ),
    ai: (
        <svg className="w-16 h-16 sm:w-20 sm:h-20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
    ),
}

export default function EmptyState({
    icon = 'wardrobe',
    title,
    description,
    actionLabel,
    actionHref,
    onAction,
    className = '',
}: EmptyStateProps) {
    return (
        <div className={`flex flex-col items-center justify-center py-12 sm:py-16 px-4 text-center ${className}`}>
            {/* Decorative background */}
            <div className="relative mb-6">
                <div className="absolute inset-0 bg-gradient-to-br from-primary-100 to-accent-100 dark:from-primary-900/30 dark:to-accent-900/30 rounded-full blur-2xl opacity-60" />
                <div className="relative p-6 bg-gradient-to-br from-gray-50 to-gray-100 dark:from-slate-800 dark:to-slate-700 rounded-full text-gray-400 dark:text-slate-500">
                    {icons[icon]}
                </div>
            </div>

            <h3 className="text-lg sm:text-xl font-semibold text-gray-900 dark:text-white mb-2">
                {title}
            </h3>

            {description && (
                <p className="text-sm sm:text-base text-gray-500 dark:text-slate-400 max-w-md mb-6">
                    {description}
                </p>
            )}

            {(actionLabel && (actionHref || onAction)) && (
                actionHref ? (
                    <a href={actionHref}>
                        <Button variant="primary" size="md">
                            {actionLabel}
                        </Button>
                    </a>
                ) : (
                    <Button variant="primary" size="md" onClick={onAction}>
                        {actionLabel}
                    </Button>
                )
            )}
        </div>
    )
}
