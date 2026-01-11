'use client'

import React, { createContext, useContext, useState, useEffect } from 'react'
import apiClient from '@/lib/apiClient'
import { useRouter } from 'next/navigation'

interface User {
    id: number
    email: string
    full_name?: string
    created_at: string
}

interface AuthContextType {
    user: User | null
    loading: boolean
    login: (token: string) => Promise<void>
    logout: () => void
    checkAuth: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null)
    const [loading, setLoading] = useState(true)
    const router = useRouter()

    const checkAuth = async () => {
        // Check if code is running in browser
        if (typeof window === 'undefined') return

        const token = localStorage.getItem('token')
        if (!token) {
            setLoading(false)
            return
        }

        try {
            const response = await apiClient.get('/auth/me')
            setUser(response.data)
        } catch (error) {
            console.error('Auth check failed:', error)
            localStorage.removeItem('token')
            setUser(null)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        checkAuth()
    }, [])

    const login = async (token: string) => {
        localStorage.setItem('token', token)
        await checkAuth()
        router.push('/wardrobe')
    }

    const logout = () => {
        localStorage.removeItem('token')
        // Clear all application caches to prevent data leakage between users
        localStorage.removeItem('stylo.wardrobe.cache.v1')
        localStorage.removeItem('stylo.suggestions.cache.v1')
        localStorage.removeItem('stylo.filters.state.v1')

        setUser(null)
        router.push('/login')
    }

    return (
        <AuthContext.Provider value={{ user, loading, login, logout, checkAuth }}>
            {children}
        </AuthContext.Provider>
    )
}

export const useAuth = () => {
    const context = useContext(AuthContext)
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider')
    }
    return context
}
