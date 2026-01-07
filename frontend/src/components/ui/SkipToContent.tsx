'use client'

export default function SkipToContent() {
    const handleClick = () => {
        const main = document.querySelector('main')
        if (main) {
            main.tabIndex = -1
            main.focus()
            main.removeAttribute('tabindex')
        }
    }

    return (
        <a
            href="#main-content"
            onClick={handleClick}
            className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-[200] focus:px-4 focus:py-2 focus:bg-primary-600 focus:text-white focus:rounded-lg focus:shadow-lg focus:outline-none focus:ring-2 focus:ring-primary-300 focus:ring-offset-2 transition-all"
        >
            Skip to main content
        </a>
    )
}
