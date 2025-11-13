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
      <div className="rounded-lg px-4 py-2 text-sm bg-gray-100 text-gray-600">Checking API health…</div>
    )
  }

  if (status === 'ok') {
    return (
      <div className="rounded-lg px-4 py-2 text-sm bg-green-100 text-green-800">Backend API: Healthy</div>
    )
  }

  return (
    <div className="rounded-lg px-4 py-2 text-sm bg-red-100 text-red-800">Backend API: Down</div>
  )
}
