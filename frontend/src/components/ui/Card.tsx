import React from 'react'

interface CardProps {
  children: React.ReactNode
  className?: string
  hover?: boolean
}

const Card: React.FC<CardProps> = ({ children, className = '', hover = false }) => {
  const baseStyles = 'bg-white dark:bg-slate-800 rounded-2xl shadow-sm dark:shadow-slate-900/50 border border-gray-100 dark:border-slate-700 overflow-hidden transition-colors duration-300'
  const hoverStyles = hover ? 'transition-all duration-300 hover:shadow-xl dark:hover:shadow-slate-900/70 cursor-pointer' : ''
  const classes = `${baseStyles} ${hoverStyles} ${className}`
  
  return (
    <div className={classes}>
      {children}
    </div>
  )
}

export default Card
