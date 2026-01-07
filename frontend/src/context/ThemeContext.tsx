'use client'

import React, { createContext, useContext, useState, useEffect } from 'react'

type Theme = 'light' | 'dark'

interface ThemeContextType {
    theme: Theme
    toggleTheme: () => void
    setTheme: (theme: Theme) => void
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

const THEME_STORAGE_KEY = 'stylo.theme'

export function ThemeProvider({ children }: { children: React.ReactNode }) {
    const [theme, setThemeState] = useState<Theme>('light')
    const [mounted, setMounted] = useState(false)

    // Load theme from localStorage on mount
    useEffect(() => {
        setMounted(true)
        const savedTheme = localStorage.getItem(THEME_STORAGE_KEY) as Theme | null
        
        if (savedTheme) {
            setThemeState(savedTheme)
        } else {
            // Check system preference
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
            setThemeState(prefersDark ? 'dark' : 'light')
        }
    }, [])

    // Apply theme class to document
    useEffect(() => {
        if (!mounted) return
        
        const root = document.documentElement
        if (theme === 'dark') {
            root.classList.add('dark')
        } else {
            root.classList.remove('dark')
        }
        
        // Save to localStorage
        localStorage.setItem(THEME_STORAGE_KEY, theme)
    }, [theme, mounted])

    const toggleTheme = () => {
        setThemeState(prev => prev === 'light' ? 'dark' : 'light')
    }

    const setTheme = (newTheme: Theme) => {
        setThemeState(newTheme)
    }

    // Prevent flash of wrong theme
    if (!mounted) {
        return (
            <ThemeContext.Provider value={{ theme: 'light', toggleTheme, setTheme }}>
                {children}
            </ThemeContext.Provider>
        )
    }

    return (
        <ThemeContext.Provider value={{ theme, toggleTheme, setTheme }}>
            {children}
        </ThemeContext.Provider>
    )
}

export const useTheme = () => {
    const context = useContext(ThemeContext)
    if (context === undefined) {
        throw new Error('useTheme must be used within a ThemeProvider')
    }
    return context
}
