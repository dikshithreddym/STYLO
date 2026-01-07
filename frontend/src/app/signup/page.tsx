'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import apiClient from '@/lib/apiClient'
import { useAuth } from '@/context/AuthContext'

export default function SignupPage() {
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [fullName, setFullName] = useState('')
    const [error, setError] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const router = useRouter()
    const { login } = useAuth()

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()

        if (password !== confirmPassword) {
            setError('Passwords do not match')
            return
        }

        setIsLoading(true)
        setError('')

        try {
            await apiClient.post('/auth/signup', {
                email,
                password,
                full_name: fullName
            })

            // Auto-login after successful registration
            const formData = new URLSearchParams()
            formData.append('username', email)
            formData.append('password', password)

            const loginResponse = await apiClient.post('/auth/login', formData, {
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            })

            // This will update auth state and redirect to /wardrobe (handled in AuthContext)
            login(loginResponse.data.access_token)
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
                setError('Registration failed')
            }
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4 py-12 sm:px-6 lg:px-8">
            <div className="w-full max-w-5xl grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-10 items-center">
                <div className="glass-panel rounded-3xl p-8 sm:p-10 border border-white/70 shadow-xl">
                    <div className="flex items-center justify-between mb-6">
                        <div>
                            <p className="text-xs font-semibold text-primary-600 dark:text-primary-400 uppercase tracking-[0.2em]">Create account</p>
                            <h2 className="text-3xl font-extrabold text-slate-900 dark:text-white leading-tight">Join STYLO</h2>
                            <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">Build your digital closet and get AI-crafted looks.</p>
                        </div>
                        <div className="px-3 py-1.5 rounded-full bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400 text-xs font-semibold border border-primary-100 dark:border-primary-800">1 min</div>
                    </div>

                    <form className="space-y-5" onSubmit={handleSubmit}>
                        {error && (
                            <div className="rounded-2xl bg-red-50 dark:bg-red-900/30 p-4 border border-red-100 dark:border-red-800 text-sm text-red-700 dark:text-red-300 flex items-start gap-3">
                                <svg className="w-5 h-5 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                <div>{typeof error === 'string' ? error : 'An unexpected error occurred'}</div>
                            </div>
                        )}

                        <div className="space-y-4">
                            <div className="space-y-2">
                                <label htmlFor="full-name" className="text-sm font-medium text-slate-700 dark:text-slate-300">
                                    Full Name <span className="text-xs text-slate-400 dark:text-slate-500">(optional)</span>
                                </label>
                                <input
                                    id="full-name"
                                    name="fullName"
                                    type="text"
                                    autoComplete="name"
                                    className="block w-full rounded-xl border border-slate-200 dark:border-slate-600 px-4 py-3 text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:border-primary-500 focus:ring-2 focus:ring-primary-200 dark:focus:ring-primary-800 focus:outline-none transition-all bg-white/70 dark:bg-slate-800/70"
                                    placeholder="Alex Fashioner"
                                    value={fullName}
                                    onChange={(e) => setFullName(e.target.value)}
                                />
                            </div>
                            <div className="space-y-2">
                                <label htmlFor="email-address" className="text-sm font-medium text-slate-700 dark:text-slate-300">Email address</label>
                                <input
                                    id="email-address"
                                    name="email"
                                    type="email"
                                    autoComplete="email"
                                    required
                                    className="block w-full rounded-xl border border-slate-200 dark:border-slate-600 px-4 py-3 text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:border-primary-500 focus:ring-2 focus:ring-primary-200 dark:focus:ring-primary-800 focus:outline-none transition-all bg-white/70 dark:bg-slate-800/70"
                                    placeholder="you@example.com"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                />
                            </div>
                            <div className="space-y-2">
                                <label htmlFor="password" className="text-sm font-medium text-slate-700 dark:text-slate-300">Password</label>
                                <input
                                    id="password"
                                    name="password"
                                    type="password"
                                    autoComplete="new-password"
                                    required
                                    className="block w-full rounded-xl border border-slate-200 dark:border-slate-600 px-4 py-3 text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:border-primary-500 focus:ring-2 focus:ring-primary-200 dark:focus:ring-primary-800 focus:outline-none transition-all bg-white/70 dark:bg-slate-800/70"
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                />
                            </div>
                            <div className="space-y-2">
                                <label htmlFor="confirm-password" className="text-sm font-medium text-slate-700 dark:text-slate-300">Confirm Password</label>
                                <input
                                    id="confirm-password"
                                    name="confirm-password"
                                    type="password"
                                    autoComplete="new-password"
                                    required
                                    className="block w-full rounded-xl border border-slate-200 dark:border-slate-600 px-4 py-3 text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:border-primary-500 focus:ring-2 focus:ring-primary-200 dark:focus:ring-primary-800 focus:outline-none transition-all bg-white/70 dark:bg-slate-800/70"
                                    placeholder="••••••••"
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                />
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={isLoading}
                            className={`group relative flex w-full justify-center rounded-xl bg-slate-900 dark:bg-primary-600 px-4 py-3 text-base font-semibold text-white hover:bg-slate-800 dark:hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-300 focus:ring-offset-2 dark:focus:ring-offset-slate-800 transition-all ${isLoading ? 'opacity-70 cursor-not-allowed' : ''
                                }`}
                        >
                            {isLoading ? (
                                <span className="flex items-center">
                                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                    Creating account...
                                </span>
                            ) : (
                                'Sign up'
                            )}
                        </button>
                    </form>

                    <div className="mt-6 text-center text-sm">
                        <span className="text-slate-500 dark:text-slate-400">Already have an account? </span>
                        <Link href="/login" className="font-semibold text-primary-700 dark:text-primary-400 hover:text-primary-800 dark:hover:text-primary-300 hover:underline">
                            Sign in
                        </Link>
                    </div>
                </div>

                <div className="hidden lg:block glass-panel rounded-3xl p-10 relative overflow-hidden">
                    <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 opacity-90" />
                    <div className="relative text-white">
                        <p className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 text-xs font-semibold border border-white/10 mb-6">
                            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                            Modern wardrobe OS
                        </p>
                        <h3 className="text-3xl font-extrabold leading-tight">Less scrolling.<br />More styling.</h3>
                        <p className="mt-3 text-sm text-slate-200 leading-relaxed max-w-md">Save your favorite looks, generate AI outfits, and keep every piece organized with smart filters and inline actions.</p>
                        <div className="mt-6 grid grid-cols-2 gap-3">
                            {[
                                { title: 'Smart filters', desc: 'Search by color, type, and intent instantly.' },
                                { title: 'Saved outfits', desc: 'Keep curated fits ready for every occasion.' },
                                { title: 'AI suggestions', desc: 'Semantic, color-aware recommendations.' },
                                { title: 'Fast actions', desc: 'Add, delete, and favorite with one tap.' },
                            ].map((feature) => (
                                <div key={feature.title} className="p-4 rounded-2xl bg-white/5 border border-white/10">
                                    <p className="text-sm font-semibold">{feature.title}</p>
                                    <p className="text-xs text-slate-200 mt-1">{feature.desc}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
