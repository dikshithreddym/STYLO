a"use client"

import React, { useEffect, useState } from 'react'
import { useAuth } from '@/context/AuthContext'
import apiClient from '@/lib/apiClient'

export default function ProfilePage() {
  const { user, loading, checkAuth, logout } = useAuth()
  const [fullName, setFullName] = useState('')
  const [gender, setGender] = useState<string>('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    if (user) {
      setFullName(user.full_name ?? '')
      setGender((user as any).gender ?? '')
    }
  }, [user])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      const payload: Record<string, any> = {}
      if (fullName !== undefined) payload.full_name = fullName || null
      if (gender !== undefined) payload.gender = gender || null
      const res = await apiClient.patch('/auth/me', payload)
      setSuccess('Profile updated successfully')
      // Refresh auth context to reflect latest user
      await checkAuth()
    } catch (err: any) {
      const message = err?.response?.data?.detail || 'Failed to update profile'
      setError(message)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <p>Loading...</p>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-xl">
      <h1 className="text-2xl font-semibold mb-6">Your Profile</h1>

      {error && (
        <div className="mb-4 rounded bg-red-500/15 text-red-600 dark:text-red-400 px-4 py-3">
          {error}
        </div>
      )}

      {success && (
        <div className="mb-4 rounded bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 px-4 py-3">
          {success}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label className="block text-sm font-medium mb-2" htmlFor="full_name">
            Name
          </label>
          <input
            id="full_name"
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="w-full rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="Enter your name"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2" htmlFor="gender">
            Gender
          </label>
          <select
            id="gender"
            value={gender}
            onChange={(e) => setGender(e.target.value)}
            className="w-full rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">Select gender</option>
            <option value="male">Male</option>
            <option value="female">Female</option>
            <option value="other">Other</option>
          </select>
        </div>

        <button
          type="submit"
          disabled={saving}
          className="inline-flex items-center rounded-md bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 disabled:opacity-60"
        >
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
      </form>

      {/* Bottom Sign Out button */}
      <div className="mt-10">
        <button
          type="button"
          onClick={logout}
          className="w-full inline-flex items-center justify-center rounded-md bg-red-600 hover:bg-red-700 text-white px-4 py-2"
        >
          Sign Out
        </button>
      </div>
    </div>
  )
}
