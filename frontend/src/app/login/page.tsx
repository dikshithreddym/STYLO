'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useAuth } from '@/context/AuthContext'
import apiClient from '@/lib/apiClient'

export default function LoginPage() {
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const { login } = useAuth()

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setIsLoading(true)
        setError('')

        try {
            // Backend expects form-url-encoded data for OAuth2 spec
            const formData = new URLSearchParams()
            formData.append('username', email)
            formData.append('password', password)

            const response = await apiClient.post('/auth/login', formData, {
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            })
            login(response.data.access_token)
        } catch (err: any) {
            console.error(err)
            const detail = err.response?.data?.detail
            if (typeof detail === 'string') {
                setError(detail)
            } else if (Array.isArray(detail)) {
                // Handle array of errors (e.g., validation errors)
                setError(detail.map((e: any) => e.msg).join(', '))
            } else if (typeof detail === 'object') {
                setError(JSON.stringify(detail))
            } else {
                setError('Invalid email or password')
            }
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4 py-12 sm:px-6 lg:px-8">
            <div className="w-full max-w-5xl grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-10 items-center">
                <div className="hidden lg:block glass-panel rounded-3xl p-10 relative overflow-hidden">
                    <div className="absolute inset-0 bg-gradient-to-br from-primary-100/70 via-white to-white pointer-events-none" />
                    <div className="relative">
                        <p className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white text-xs font-semibold text-primary-700 shadow-sm border border-primary-100 mb-6">
                            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                            Secure session
                        </p>
                        <h2 className="text-3xl font-extrabold text-slate-900 leading-tight">Welcome back to your curated wardrobe</h2>
                        <p className="mt-3 text-slate-600 leading-relaxed max-w-xl">Sign in to synchronize outfits, favorite looks, and access AI suggestions tailored to your style goals.</p>
                        <div className="mt-6 space-y-3">
                            {[
                                'Instant access to your saved outfits and favorites',
                                'AI suggestions tuned to your intent and colors',
                                'Fast actions to add, sort, and manage items',
                            ].map((item) => (
                                <div key={item} className="flex items-start gap-3">
                                    <span className="mt-0.5 flex h-7 w-7 items-center justify-center rounded-full bg-primary-50 text-primary-700">
                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                        </svg>
                                    </span>
                                    <p className="text-sm text-slate-700">{item}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="glass-panel rounded-3xl p-8 sm:p-10 border border-white/70 shadow-xl">
                    <div className="flex items-center justify-between mb-6">
                        <div>
                            <p className="text-xs font-semibold text-primary-600 uppercase tracking-[0.2em]">Login</p>
                            <h2 className="text-3xl font-extrabold text-slate-900 leading-tight">Access your wardrobe</h2>
                            <p className="text-sm text-slate-600 mt-1">We’ll get you back to styling in seconds.</p>
                        </div>
                        <div className="px-3 py-1.5 rounded-full bg-emerald-50 text-emerald-700 text-xs font-semibold border border-emerald-100">Live</div>
                    </div>

                    <form className="space-y-5" onSubmit={handleSubmit}>
                        {error && (
                            <div className="rounded-2xl bg-red-50 p-4 border border-red-100 text-sm text-red-700 flex items-start gap-3">
                                <svg className="w-5 h-5 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                <div>{typeof error === 'string' ? error : 'An unexpected error occurred'}</div>
                            </div>
                        )}

                        <div className="space-y-4">
                            <div className="space-y-2">
                                <label htmlFor="email-address" className="text-sm font-medium text-slate-700">Email address</label>
                                <input
                                    id="email-address"
                                    name="email"
                                    type="email"
                                    autoComplete="email"
                                    required
                                    className="block w-full rounded-xl border border-slate-200 px-4 py-3 text-slate-900 placeholder-slate-400 focus:border-primary-500 focus:ring-2 focus:ring-primary-200 focus:outline-none transition-all bg-white/70"
                                    placeholder="you@example.com"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                />
                            </div>
                            <div className="space-y-2">
                                <label htmlFor="password" className="text-sm font-medium text-slate-700 flex items-center justify-between">
                                    <span>Password</span>
                                    <span className="text-xs text-primary-600 font-semibold">Secure</span>
                                </label>
                                <input
                                    id="password"
                                    name="password"
                                    type="password"
                                    autoComplete="current-password"
                                    required
                                    className="block w-full rounded-xl border border-slate-200 px-4 py-3 text-slate-900 placeholder-slate-400 focus:border-primary-500 focus:ring-2 focus:ring-primary-200 focus:outline-none transition-all bg-white/70"
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                />
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={isLoading}
                            className={`group relative flex w-full justify-center rounded-xl bg-slate-900 px-4 py-3 text-base font-semibold text-white hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-primary-300 focus:ring-offset-2 transition-all ${isLoading ? 'opacity-70 cursor-not-allowed' : ''
                                }`}
                        >
                            {isLoading ? (
                                <span className="flex items-center">
                                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                    Signing in...
                                </span>
                            ) : (
                                'Sign in'
                            )}
                        </button>
                    </form>

                    <div className="mt-6 text-center text-sm">
                        <span className="text-slate-500">Don't have an account? </span>
                        <Link href="/signup" className="font-semibold text-primary-700 hover:text-primary-800 hover:underline">
                            Sign up
                        </Link>
                    </div>
                </div>
            </div>
        </div>
    )
}
