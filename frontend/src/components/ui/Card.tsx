import React from 'react'

interface CardProps {
  children: React.ReactNode
  className?: string
  hover?: boolean
}

const Card: React.FC<CardProps> = ({ children, className = '', hover = false }) => {
  const baseStyles = 'bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden transition-colors duration-200'
  const hoverStyles = hover ? 'hover:shadow-md hover:border-slate-300 dark:hover:border-slate-600 cursor-pointer' : ''
  const classes = `${baseStyles} ${hoverStyles} ${className}`
  
  return (
    <div className={classes}>
      {children}
    </div>
  )
}

export default Card
