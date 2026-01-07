'use client'

import { useEffect, useState } from 'react'
import { healthAPI } from '@/lib/api'

export default function HealthStatus() {
  const [status, setStatus] = useState<'ok' | 'down' | 'loading'>('loading')

  const check = async () => {
    try {
      const res = await healthAPI.check()
      setStatus(res.status === 'ok' ? 'ok' : 'down')
    } catch {
      setStatus('down')
    }
  }

  useEffect(() => {
    check()
    const id = setInterval(check, 15000)
    return () => clearInterval(id)
  }, [])

  if (status === 'loading') {
    return (
      <div className="rounded-lg px-3 sm:px-4 py-1.5 sm:py-2 text-xs sm:text-sm bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-slate-300">Checking API health…</div>
    )
  }

  if (status === 'ok') {
    return (
      <div className="rounded-lg px-3 sm:px-4 py-1.5 sm:py-2 text-xs sm:text-sm bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400">Backend API: Healthy</div>
    )
  }

  return (
    <div className="rounded-lg px-3 sm:px-4 py-1.5 sm:py-2 text-xs sm:text-sm bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400">Backend API: Down</div>
  )
}
