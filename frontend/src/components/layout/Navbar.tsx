'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuth } from '@/context/AuthContext'
import ThemeToggle from '@/components/ui/ThemeToggle'

const Navbar = () => {
  const pathname = usePathname()
  const { user, logout } = useAuth()

  const isActive = (path: string) => pathname === path

  return (
    <>
      <nav className="sticky top-0 z-50 bg-white/95 dark:bg-slate-900/95 backdrop-blur-sm border-b border-slate-200 dark:border-slate-800 transition-colors duration-200 pt-[env(safe-area-inset-top)]">
        <div className="container mx-auto px-4 sm:px-6 max-w-7xl">
          <div className="flex items-center justify-between h-14">
            {/* Logo */}
            <Link href="/" className="flex items-center gap-2" aria-label="Stylo home">
              <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">S</span>
              </div>
              <span className="font-semibold text-slate-900 dark:text-white hidden sm:block">Stylo</span>
            </Link>

            {/* Navigation */}
            <div className="flex items-center gap-1">
              <div className="hidden sm:flex items-center gap-1">
                <Link
                  href="/wardrobe"
                  aria-current={isActive('/wardrobe') ? 'page' : undefined}
                  className={`min-h-11 px-4 rounded-lg text-sm font-medium transition-colors flex items-center ${isActive('/wardrobe')
                    ? 'bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-50 dark:hover:bg-slate-800'
                    }`}
                >
                  Wardrobe
                </Link>
                <Link
                  href="/suggest"
                  aria-current={isActive('/suggest') ? 'page' : undefined}
                  className={`min-h-11 px-4 rounded-lg text-sm font-medium transition-colors flex items-center ${isActive('/suggest')
                    ? 'bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-50 dark:hover:bg-slate-800'
                    }`}
                >
                  Suggest
                </Link>
              </div>

              <div className="hidden sm:block w-px h-5 bg-slate-200 dark:bg-slate-700 mx-2" />

              <ThemeToggle className="min-h-11 min-w-11" />

              {user ? (
                <div className="hidden sm:flex items-center gap-2 ml-2">
                  <div className="w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-900/50 text-primary-600 dark:text-primary-400 font-medium text-sm flex items-center justify-center">
                    {user.email.charAt(0).toUpperCase()}
                  </div>
                  <button
                    onClick={logout}
                    className="min-h-11 px-4 rounded-lg text-sm font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-50 dark:hover:bg-slate-800 active:scale-[0.98] transition-all"
                  >
                    Sign Out
                  </button>
                </div>
              ) : (
                <div className="hidden sm:flex items-center gap-2 ml-2">
                  <Link
                    href="/login"
                    className="min-h-11 px-4 rounded-lg text-sm font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors flex items-center"
                  >
                    Sign In
                  </Link>
                  <Link
                    href="/signup"
                    className="min-h-11 px-4 rounded-lg text-sm font-medium bg-primary-600 text-white hover:bg-primary-700 transition-colors flex items-center"
                  >
                    Sign Up
                  </Link>
                </div>
              )}
            </div>
          </div>
        </div>
      </nav>

      <nav className="sm:hidden fixed bottom-0 left-0 right-0 z-50 bg-white/95 dark:bg-slate-900/95 border-t border-slate-200 dark:border-slate-800 pb-[env(safe-area-inset-bottom)]" aria-label="Mobile navigation">
        <div className="flex items-center justify-around h-14">
          <Link
            href="/wardrobe"
            aria-current={isActive('/wardrobe') ? 'page' : undefined}
            className={`flex flex-col items-center justify-center gap-1 px-3 min-h-11 text-xs font-medium transition-colors active:scale-[0.98] ${isActive('/wardrobe')
              ? 'text-primary-600 dark:text-primary-400'
              : 'text-slate-500 dark:text-slate-400'
              }`}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 8a2 2 0 01-2 2H5a2 2 0 01-2-2m18 0a2 2 0 00-2-2H5a2 2 0 00-2 2m18 0v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8" />
            </svg>
            Wardrobe
          </Link>
          <Link
            href="/suggest"
            aria-current={isActive('/suggest') ? 'page' : undefined}
            className={`flex flex-col items-center justify-center gap-1 px-3 min-h-11 text-xs font-medium transition-colors active:scale-[0.98] ${isActive('/suggest')
              ? 'text-primary-600 dark:text-primary-400'
              : 'text-slate-500 dark:text-slate-400'
              }`}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
            </svg>
            Suggest
          </Link>
          {user ? (
            <button
              onClick={logout}
              className="flex flex-col items-center justify-center gap-1 px-3 min-h-11 text-xs font-medium text-slate-500 dark:text-slate-400 active:scale-[0.98]"
              aria-label="Sign out"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h6a2 2 0 012 2v1" />
              </svg>
              Sign Out
            </button>
          ) : (
            <Link
              href="/login"
              className="flex flex-col items-center justify-center gap-1 px-3 min-h-11 text-xs font-medium text-slate-500 dark:text-slate-400 active:scale-[0.98]"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M13 5l7 7-7 7" />
              </svg>
              Sign In
            </Link>
          )}
        </div>
      </nav>
    </>
  )
}

export default Navbar
