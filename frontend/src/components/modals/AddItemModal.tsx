'use client'

import { useState, useRef, useEffect } from 'react'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import { wardrobeAPI, WardrobeItem } from '@/lib/api'
import { compressImage, needsCompression } from '@/lib/imageCompression'

interface AddItemModalProps {
  onClose: () => void
  onSuccess: (item: WardrobeItem) => void
}

export default function AddItemModal({ onClose, onSuccess }: AddItemModalProps) {
  const [type, setType] = useState('')
  const [color, setColor] = useState('')
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [category, setCategory] = useState<'top' | 'bottom' | 'footwear' | 'layer' | 'one-piece' | 'accessories'>('top')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [cameraActive, setCameraActive] = useState(false)
  const [stream, setStream] = useState<MediaStream | null>(null)

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      if (!file.type.startsWith('image/')) {
        setError('Please select an image file')
        return
      }
      
      setImageFile(file)
      
      // Compress image if needed
      try {
        const shouldCompress = needsCompression(file, 2) // Compress if > 2MB
        if (shouldCompress) {
          setLoading(true)
          const compressedDataUrl = await compressImage(file, {
            maxWidth: 1920,
            maxHeight: 1920,
            quality: 0.85,
            format: 'webp',
          })
          setImagePreview(compressedDataUrl)
          setLoading(false)
        } else {
          // Use original if no compression needed
          const reader = new FileReader()
          reader.onloadend = () => {
            setImagePreview(reader.result as string)
          }
          reader.readAsDataURL(file)
        }
      } catch (err) {
        console.error('Image compression failed, using original:', err)
        // Fallback to original
        const reader = new FileReader()
        reader.onloadend = () => {
          setImagePreview(reader.result as string)
        }
        reader.readAsDataURL(file)
      }
    }
  }

  const startCamera = async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({ 
        video: { facingMode: 'environment' },
        audio: false 
      })
      
      setStream(mediaStream)
      setCameraActive(true)
    } catch (err) {
      console.error('❌ Camera access failed:', err)
      setError('Failed to access camera. Please check permissions.')
    }
  }

  // Attach stream to video element when both are available
  useEffect(() => {
    if (stream && videoRef.current && cameraActive) {
      videoRef.current.srcObject = stream
      
      const videoElement = videoRef.current
      
      const handleLoadedMetadata = () => {
        videoElement.play().catch((err) => console.error('Play failed:', err))
      }
      
      videoElement.addEventListener('loadedmetadata', handleLoadedMetadata)
      
      // Cleanup
      return () => {
        videoElement.removeEventListener('loadedmetadata', handleLoadedMetadata)
      }
    }
  }, [stream, cameraActive])

  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop())
      setStream(null)
    }
    setCameraActive(false)
  }

  const capturePhoto = async () => {
    if (videoRef.current && canvasRef.current) {
      const video = videoRef.current
      const canvas = canvasRef.current
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      const ctx = canvas.getContext('2d')
      ctx?.drawImage(video, 0, 0)
      
      // Get initial data URL
      const initialDataUrl = canvas.toDataURL('image/jpeg', 0.9)
      
      // Compress the captured image
      try {
        const compressedDataUrl = await compressImage(initialDataUrl, {
          maxWidth: 1920,
          maxHeight: 1920,
          quality: 0.85,
          format: 'webp',
        })
        
        // Create file from compressed data
        const response = await fetch(compressedDataUrl)
        const blob = await response.blob()
        const file = new File([blob], 'camera-photo.webp', { type: 'image/webp' })
        
        setImageFile(file)
        setImagePreview(compressedDataUrl)
        stopCamera()
      } catch (err) {
        console.error('Image compression failed, using original:', err)
        // Fallback to original
        canvas.toBlob((blob) => {
          if (blob) {
            const file = new File([blob], 'camera-photo.jpg', { type: 'image/jpeg' })
            setImageFile(file)
            setImagePreview(initialDataUrl)
            stopCamera()
          }
        }, 'image/jpeg', 0.9)
      }
    }
  }

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!type.trim() || !color.trim()) {
      setError('Type and color are required')
      return
    }

    try {
      setLoading(true)
      setError(null)
      
      // Use compressed image preview (already compressed in handleFileSelect/capturePhoto)
      let imageData: string | null = null
      if (imagePreview) {
        // Ensure image is compressed before upload
        if (imageFile && needsCompression(imageFile, 2)) {
          // Re-compress if needed (should already be compressed, but double-check)
          imageData = await compressImage(imageFile, {
            maxWidth: 1920,
            maxHeight: 1920,
            quality: 0.85,
            format: 'webp',
          })
        } else {
          imageData = imagePreview
        }
      }

      const newItem = await wardrobeAPI.create({
        type: type.trim(),
        color: color.trim(),
        image_url: imageData,
        category,
      })
      onSuccess(newItem)
      stopCamera()
      onClose()
    } catch (err) {
      console.error(err)
      setError('Failed to add item. Check backend.')
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    stopCamera()
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 dark:bg-opacity-70 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-slate-800 rounded-lg max-w-md w-full p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Add Wardrobe Item</h2>
          <button
            onClick={handleClose}
            className="text-gray-400 dark:text-slate-500 hover:text-gray-600 dark:hover:text-slate-300"
            aria-label="Close"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form onSubmit={onSubmit}>
          <div className="space-y-4">
            <Input
              label="Type *"
              value={type}
              onChange={(e) => setType(e.target.value)}
              placeholder="e.g., T-Shirt, Jeans, Blazer"
              required
            />

            <Input
              label="Color *"
              value={color}
              onChange={(e) => setColor(e.target.value)}
              placeholder="e.g., Navy Blue, Black, White"
              required
            />

            {/* Image Upload Section */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-2">Photo</label>
              
              {!imagePreview && !cameraActive && (
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="flex-1 px-4 py-2 border-2 border-dashed border-gray-300 dark:border-slate-600 rounded-lg hover:border-primary-500 transition-colors"
                  >
                    <svg className="w-6 h-6 mx-auto mb-1 text-gray-400 dark:text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    <span className="text-sm text-gray-600 dark:text-slate-400">Upload Image</span>
                  </button>
                  <button
                    type="button"
                    onClick={startCamera}
                    className="flex-1 px-4 py-2 border-2 border-dashed border-gray-300 dark:border-slate-600 rounded-lg hover:border-primary-500 transition-colors"
                  >
                    <svg className="w-6 h-6 mx-auto mb-1 text-gray-400 dark:text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                    <span className="text-sm text-gray-600 dark:text-slate-400">Take Photo</span>
                  </button>
                </div>
              )}

              {cameraActive && (
                <div className="space-y-2">
                  <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    muted
                    className="w-full rounded-lg bg-black"
                  />
                  <div className="flex gap-2">
                    <Button type="button" onClick={capturePhoto} className="flex-1">
                      Capture
                    </Button>
                    <Button type="button" variant="ghost" onClick={stopCamera} className="flex-1">
                      Cancel
                    </Button>
                  </div>
                </div>
              )}

              {imagePreview && (
                <div className="space-y-2">
                  <img src={imagePreview} alt="Preview" className="w-full rounded-lg" />
                  <button
                    type="button"
                    onClick={() => {
                      setImageFile(null)
                      setImagePreview(null)
                    }}
                    className="text-sm text-red-600 hover:text-red-800"
                  >
                    Remove Image
                  </button>
                </div>
              )}

              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleFileSelect}
                className="hidden"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">Category *</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value as any)}
                className="w-full px-4 py-2 border dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-gray-900 dark:text-white bg-white dark:bg-slate-700"
              >
                <option value="top">Top</option>
                <option value="bottom">Bottom</option>
                <option value="footwear">Footwear</option>
                <option value="layer">Layer</option>
                <option value="one-piece">One-Piece</option>
                <option value="accessories">Accessories</option>
              </select>
            </div>
          </div>

          {error && <p className="text-red-600 dark:text-red-400 text-sm mt-3">{error}</p>}

          <div className="flex gap-3 mt-6">
            <Button type="submit" disabled={loading} className="flex-1">
              {loading ? 'Adding...' : 'Add Item'}
            </Button>
            <Button type="button" variant="ghost" onClick={handleClose} className="flex-1">
              Cancel
            </Button>
          </div>
        </form>

        {/* Hidden canvas for photo capture */}
        <canvas ref={canvasRef} className="hidden" />
      </div>
    </div>
  )
}
