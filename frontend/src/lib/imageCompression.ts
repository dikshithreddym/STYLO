/**
 * Image Compression Utility
 * Compresses and resizes images client-side before upload
 */

interface CompressionOptions {
  maxWidth?: number
  maxHeight?: number
  quality?: number
  format?: 'webp' | 'jpeg' | 'png'
}

const DEFAULT_OPTIONS: Required<CompressionOptions> = {
  maxWidth: 1920,
  maxHeight: 1920,
  quality: 0.85,
  format: 'webp',
}

/**
 * Check if WebP is supported
 */
function isWebPSupported(): boolean {
  if (typeof window === 'undefined') return false
  
  const canvas = document.createElement('canvas')
  canvas.width = 1
  canvas.height = 1
  return canvas.toDataURL('image/webp').indexOf('data:image/webp') === 0
}

/**
 * Load image from file or data URL
 */
function loadImage(source: File | string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = reject
    
    if (source instanceof File) {
      const reader = new FileReader()
      reader.onload = (e) => {
        img.src = e.target?.result as string
      }
      reader.onerror = reject
      reader.readAsDataURL(source)
    } else {
      img.src = source
    }
  })
}

/**
 * Calculate new dimensions maintaining aspect ratio
 */
function calculateDimensions(
  width: number,
  height: number,
  maxWidth: number,
  maxHeight: number
): { width: number; height: number } {
  if (width <= maxWidth && height <= maxHeight) {
    return { width, height }
  }

  const aspectRatio = width / height

  if (width > height) {
    // Landscape
    if (width > maxWidth) {
      return {
        width: maxWidth,
        height: Math.round(maxWidth / aspectRatio),
      }
    }
  } else {
    // Portrait or square
    if (height > maxHeight) {
      return {
        width: Math.round(maxHeight * aspectRatio),
        height: maxHeight,
      }
    }
  }

  return { width, height }
}

/**
 * Compress image to base64 data URL
 */
export async function compressImage(
  source: File | string,
  options: CompressionOptions = {}
): Promise<string> {
  const opts = { ...DEFAULT_OPTIONS, ...options }
  
  // Determine output format
  let outputFormat: string = opts.format
  if (opts.format === 'webp' && !isWebPSupported()) {
    // Fallback to JPEG if WebP not supported
    outputFormat = 'jpeg'
  }

  try {
    // Load image
    const img = await loadImage(source)

    // Calculate new dimensions
    const { width, height } = calculateDimensions(
      img.width,
      img.height,
      opts.maxWidth,
      opts.maxHeight
    )

    // Create canvas
    const canvas = document.createElement('canvas')
    canvas.width = width
    canvas.height = height

    // Draw image to canvas
    const ctx = canvas.getContext('2d')
    if (!ctx) {
      throw new Error('Failed to get canvas context')
    }

    // Use high-quality image rendering
    ctx.imageSmoothingEnabled = true
    ctx.imageSmoothingQuality = 'high'
    ctx.drawImage(img, 0, 0, width, height)

    // Convert to data URL with compression
    const mimeType = `image/${outputFormat}`
    const dataUrl = canvas.toDataURL(mimeType, opts.quality)

    return dataUrl
  } catch (error) {
    console.error('Image compression failed:', error)
    
    // Fallback: return original as data URL if compression fails
    if (source instanceof File) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = (e) => resolve(e.target?.result as string)
        reader.onerror = reject
        reader.readAsDataURL(source)
      })
    }
    
    return source
  }
}

/**
 * Compress image to Blob
 */
export async function compressImageToBlob(
  source: File | string,
  options: CompressionOptions = {}
): Promise<Blob> {
  const dataUrl = await compressImage(source, options)
  
  // Convert data URL to Blob
  const response = await fetch(dataUrl)
  return response.blob()
}

/**
 * Get image file size in MB
 */
export function getImageSizeMB(file: File): number {
  return file.size / (1024 * 1024)
}

/**
 * Check if image needs compression
 */
export function needsCompression(
  file: File,
  maxSizeMB: number = 2
): boolean {
  return getImageSizeMB(file) > maxSizeMB
}

