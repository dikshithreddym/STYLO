import React from 'react'

interface SkeletonProps {
    className?: string
    variant?: 'text' | 'circular' | 'rectangular' | 'rounded'
    width?: string | number
    height?: string | number
    animation?: 'pulse' | 'shimmer' | 'none'
}

export function Skeleton({
    className = '',
    variant = 'rectangular',
    width,
    height,
    animation = 'pulse',
}: SkeletonProps) {
    const baseStyles = 'bg-gray-200 dark:bg-slate-700'
    
    const variantStyles = {
        text: 'rounded',
        circular: 'rounded-full',
        rectangular: '',
        rounded: 'rounded-xl',
    }

    const animationStyles = {
        pulse: 'animate-pulse',
        shimmer: 'bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200 dark:from-slate-700 dark:via-slate-600 dark:to-slate-700 bg-[length:200%_100%] animate-shimmer',
        none: '',
    }

    const style: React.CSSProperties = {
        width: width,
        height: height,
    }

    return (
        <div
            className={`${baseStyles} ${variantStyles[variant]} ${animationStyles[animation]} ${className}`}
            style={style}
            aria-hidden="true"
        />
    )
}

// Pre-built skeleton patterns for common use cases
export function CardSkeleton() {
    return (
        <div className="bg-white dark:bg-slate-800 rounded-2xl border border-gray-100 dark:border-slate-700 overflow-hidden">
            <Skeleton variant="rectangular" className="w-full h-48 sm:h-56" />
            <div className="p-4 space-y-3">
                <Skeleton variant="text" className="h-5 w-3/4" />
                <Skeleton variant="text" className="h-4 w-1/2" />
                <div className="flex gap-2">
                    <Skeleton variant="rounded" className="h-6 w-16" />
                    <Skeleton variant="rounded" className="h-6 w-20" />
                </div>
            </div>
        </div>
    )
}

export function WardrobeGridSkeleton({ count = 6 }: { count?: number }) {
    return (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 sm:gap-6">
            {Array.from({ length: count }).map((_, i) => (
                <CardSkeleton key={i} />
            ))}
        </div>
    )
}

export function OutfitSkeleton() {
    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <Skeleton variant="text" className="h-6 w-40" />
                <Skeleton variant="rounded" className="h-8 w-24" />
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
                {Array.from({ length: 5 }).map((_, i) => (
                    <CardSkeleton key={i} />
                ))}
            </div>
        </div>
    )
}

export function FiltersSkeleton() {
    return (
        <div className="bg-white dark:bg-slate-800 rounded-2xl p-4 sm:p-6 space-y-4">
            <div className="flex items-center justify-between">
                <Skeleton variant="text" className="h-5 w-32" />
                <Skeleton variant="rounded" className="h-8 w-24" />
            </div>
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
                {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="space-y-2">
                        <Skeleton variant="text" className="h-4 w-16" />
                        <Skeleton variant="rounded" className="h-10 w-full" />
                    </div>
                ))}
            </div>
        </div>
    )
}

export default Skeleton
