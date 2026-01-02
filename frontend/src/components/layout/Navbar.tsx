'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'

const Navbar = () => {
  const pathname = usePathname()
  const { user, logout } = useAuth()

  const isActive = (path: string) => pathname === path

  return (
    <nav className="sticky top-0 z-50 bg-white/70 backdrop-blur-2xl border-b border-white/60 shadow-[0_10px_50px_-30px_rgba(15,23,42,0.6)]">
      <div className="container mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center space-x-2 group">
            <div className="w-10 h-10 bg-gradient-to-br from-primary-500 via-primary-600 to-primary-700 rounded-2xl flex items-center justify-center shadow-md group-hover:shadow-xl transition-all duration-200">
              <span className="text-white font-extrabold text-xl">S</span>
            </div>
            <div className="hidden sm:flex flex-col leading-tight">
              <span className="text-lg font-extrabold text-slate-900 tracking-tight">STYLO</span>
              <span className="text-[11px] font-medium text-slate-500">Smart Wardrobe OS</span>
            </div>
          </Link>

          {/* Navigation Links */}
          <div className="flex items-center gap-1 sm:gap-3">
            <Link
              href="/wardrobe"
              className={`group px-3 sm:px-4 py-2 rounded-full transition-all duration-200 text-sm sm:text-base inline-flex items-center gap-2 ${isActive('/wardrobe')
                ? 'bg-slate-900 text-white shadow-md shadow-primary-200/60'
                : 'text-gray-600 hover:bg-white hover:text-gray-900 border border-transparent hover:border-slate-200'
                }`}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              <span className="hidden sm:inline font-semibold">Wardrobe</span>
            </Link>
            <Link
              href="/suggest"
              className={`group px-3 sm:px-4 py-2 rounded-full transition-all duration-200 text-sm sm:text-base inline-flex items-center gap-2 ${isActive('/suggest')
                ? 'bg-slate-900 text-white shadow-md shadow-primary-200/60'
                : 'text-gray-600 hover:bg-white hover:text-gray-900 border border-transparent hover:border-slate-200'
                }`}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
              </svg>
              <span className="hidden sm:inline font-semibold">Suggest</span>
            </Link>

            <div className="hidden sm:block h-6 w-px bg-gradient-to-b from-transparent via-slate-200 to-transparent mx-1 sm:mx-2"></div>

            {user ? (
              <div className="flex items-center gap-2 sm:gap-4">
                <div className="hidden sm:flex flex-col items-end">
                  <span className="text-sm font-semibold text-gray-900">{user.full_name || user.email.split('@')[0]}</span>
                  <span className="text-xs text-gray-500">Active member</span>
                </div>
                <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary-200 to-primary-500 text-slate-900 font-bold flex items-center justify-center shadow-sm">
                  {user.email.charAt(0).toUpperCase()}
                </div>
                <button
                  onClick={logout}
                  className="px-3 sm:px-4 py-2 rounded-full text-sm font-semibold text-slate-700 bg-white border border-slate-200 hover:border-slate-300 hover:-translate-y-0.5 transition-all shadow-sm"
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link
                  href="/login"
                  className="px-3 sm:px-4 py-2 rounded-full text-sm font-semibold text-slate-700 bg-white border border-slate-200 hover:border-slate-300 transition-all shadow-sm"
                >
                  Sign In
                </Link>
                <Link
                  href="/signup"
                  className="hidden sm:block px-4 py-2 rounded-full text-sm font-semibold text-white bg-slate-900 hover:bg-slate-800 transition-all shadow-md"
                >
                  Sign Up
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}

export default Navbar
