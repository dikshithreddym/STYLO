/**
 * Map clothing color names to CSS-compatible colors
 */
export function getColorHex(colorName: string): string {
  const color = colorName.toLowerCase().trim()
  
  // Color mapping dictionary
  const colorMap: { [key: string]: string } = {
    // Basic colors
    'black': '#000000',
    'white': '#FFFFFF',
    'red': '#DC2626',
    'blue': '#2563EB',
    'green': '#16A34A',
    'yellow': '#EAB308',
    'orange': '#EA580C',
    'purple': '#9333EA',
    'pink': '#EC4899',
    'brown': '#92400E',
    'gray': '#6B7280',
    'grey': '#6B7280',
    
    // Navy and blues
    'navy': '#1E3A8A',
    'navy blue': '#1E3A8A',
    'dark blue': '#1E40AF',
    'light blue': '#60A5FA',
    'sky blue': '#7DD3FC',
    
    // Grays
    'charcoal': '#374151',
    'charcoal grey': '#374151',
    'dark grey': '#4B5563',
    'dark gray': '#4B5563',
    'light grey': '#D1D5DB',
    'light gray': '#D1D5DB',
    
    // Earth tones
    'beige': '#D4C5B9',
    'khaki': '#C3B091',
    'tan': '#D2B48C',
    'olive': '#6B7B3E',
    'olive green': '#6B7B3E',
    'burgundy': '#800020',
    'maroon': '#800000',
    
    // Metallics
    'gold': '#FFD700',
    'silver': '#C0C0C0',
    'bronze': '#CD7F32',
    
    // Denim colors
    'denim': '#4682B4',
    'dark denim': '#1E3A5F',
    'light denim': '#7BA5D1',
    'medium denim': '#5E8DB8',
    'medium light': '#A4C8E1',
    
    // Camo patterns (use dominant color)
    'camo': '#8A9A5B',
    'brown camo': '#7A5C3E',
    'green camo': '#6B7B3E',
    'desert camo': '#C3A783',
    
    // Other common clothing colors
    'cream': '#FFFDD0',
    'ivory': '#FFFFF0',
    'coral': '#FF7F50',
    'teal': '#14B8A6',
    'turquoise': '#06B6D4',
    'lavender': '#A78BFA',
    'mint': '#86EFAC',
    'peach': '#FBBF24',
  }
  
  // Try direct match first
  if (colorMap[color]) {
    return colorMap[color]
  }
  
  // Try partial matches (e.g., "dark navy blue" -> look for "navy")
  for (const [key, value] of Object.entries(colorMap)) {
    if (color.includes(key) || key.includes(color)) {
      return value
    }
  }
  
  // Check if it's already a valid hex color
  if (/^#[0-9A-F]{6}$/i.test(color)) {
    return color
  }
  
  // Default fallback - try to use as CSS color, or return gray
  return '#9CA3AF' // gray-400 as fallback
}

/**
 * Determine if a color is light or dark (for text contrast)
 */
export function isLightColor(hex: string): boolean {
  // Convert hex to RGB
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  
  // Calculate relative luminance
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
  
  return luminance > 0.5
}
