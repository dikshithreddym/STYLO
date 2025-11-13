import React from 'react'

interface CardProps {
  children: React.ReactNode
  className?: string
  hover?: boolean
}

const Card: React.FC<CardProps> = ({ children, className = '', hover = false }) => {
  const baseStyles = 'bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden'
  const hoverStyles = hover ? 'transition-all duration-300 hover:shadow-xl cursor-pointer' : ''
  const classes = `${baseStyles} ${hoverStyles} ${className}`
  
  return (
    <div className={classes}>
      {children}
    </div>
  )
}

export default Card
