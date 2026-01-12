import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Navbar from '@/components/layout/Navbar'
import SkipToContent from '@/components/ui/SkipToContent'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'STYLO - Your Smart Wardrobe',
  description: 'Manage your wardrobe with style and intelligence',
}

import { AuthProvider } from '@/context/AuthContext'
import { ThemeProvider } from '@/context/ThemeContext'
import { ToastProvider } from '@/components/ui/Toast'

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          id="theme-init"
          dangerouslySetInnerHTML={{
            __html: `(() => {
              try {
                const key = 'stylo.theme';
                const saved = localStorage.getItem(key);
                const theme = saved ? saved : 'dark';
                const root = document.documentElement;
                if (theme === 'dark') root.classList.add('dark');
                else root.classList.remove('dark');
              } catch (e) {
                document.documentElement.classList.add('dark');
              }
            })();`
          }}
        />
      </head>
      <body className={`${inter.className} bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 transition-colors duration-300`}>
        <ThemeProvider>
          <ToastProvider>
            <AuthProvider>
              <SkipToContent />
              <Navbar />
              <main
                id="main-content"
                className="min-h-[100svh] pb-[calc(5rem+env(safe-area-inset-bottom))] sm:pb-0"
                role="main"
              >
                {children}
              </main>
            </AuthProvider>
          </ToastProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
