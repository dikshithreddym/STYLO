'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'

const Navbar = () => {
  const pathname = usePathname()
  const { user, logout } = useAuth()

  const isActive = (path: string) => pathname === path

  return (
    <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-lg border-b border-gray-200 shadow-sm">
      <div className="container mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center space-x-2 group">
            <div className="w-10 h-10 bg-gradient-to-br from-primary-600 to-primary-700 rounded-xl flex items-center justify-center shadow-md group-hover:shadow-lg transition-shadow">
              <span className="text-white font-bold text-xl">S</span>
            </div>
            <span className="hidden sm:inline text-xl font-bold bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent">STYLO</span>
          </Link>

          {/* Navigation Links */}
          <div className="flex items-center gap-1 sm:gap-2">
            <Link
              href="/wardrobe"
              className={`px-3 sm:px-4 py-2 rounded-xl transition-all duration-200 text-sm sm:text-base ${isActive('/wardrobe')
                ? 'bg-gradient-to-r from-primary-500 to-primary-600 text-white shadow-md font-medium'
                : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                }`}
            >
              <span className="hidden sm:inline">Wardrobe</span>
              <svg className="w-5 h-5 sm:hidden" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            </Link>
            <Link
              href="/suggest"
              className={`px-3 sm:px-4 py-2 rounded-xl transition-all duration-200 text-sm sm:text-base ${isActive('/suggest')
                ? 'bg-gradient-to-r from-primary-500 to-primary-600 text-white shadow-md font-medium'
                : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                }`}
            >
              <span className="hidden sm:inline">Suggest</span>
              <svg className="w-5 h-5 sm:hidden" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
              </svg>
            </Link>

            <div className="h-6 w-px bg-gray-200 mx-1 sm:mx-2"></div>

            {user ? (
              <div className="flex items-center gap-2 sm:gap-4">
                <div className="hidden sm:flex flex-col items-end">
                  <span className="text-sm font-medium text-gray-700">{user.full_name || user.email.split('@')[0]}</span>
                  <span className="text-xs text-gray-500">Member</span>
                </div>
                <button
                  onClick={logout}
                  className="px-3 sm:px-4 py-2 rounded-xl text-sm font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900 transition-colors"
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link
                  href="/login"
                  className="px-3 sm:px-4 py-2 rounded-xl text-sm font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900 transition-colors"
                >
                  Sign In
                </Link>
                <Link
                  href="/signup"
                  className="hidden sm:block px-4 py-2 rounded-xl text-sm font-medium text-white bg-gray-900 hover:bg-gray-800 transition-colors shadow-sm"
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
