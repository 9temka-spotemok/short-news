import { CheckCircle, Globe, Search, Sparkles } from 'lucide-react'
import { useState } from 'react'
import toast from 'react-hot-toast'

interface CompanyInputStepProps {
  onAnalyze: (websiteUrl: string) => Promise<void>
  isLoading?: boolean
}

export default function CompanyInputStep({ onAnalyze, isLoading = false }: CompanyInputStepProps) {
  const [websiteUrl, setWebsiteUrl] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [inputType, setInputType] = useState<'url' | 'text' | null>(null)
  const [isValidInput, setIsValidInput] = useState(false)

  const validateUrlFormat = (url: string): boolean => {
    const trimmed = url.trim()
    if (!trimmed) return false
    
    try {
      const urlObj = new URL(trimmed)
      return urlObj.protocol === 'http:' || urlObj.protocol === 'https:'
    } catch {
      // Проверяем, является ли это доменом без протокола
      const domainPattern = /^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$/i
      return domainPattern.test(trimmed)
    }
  }

  const handleUrlChange = (value: string) => {
    setWebsiteUrl(value)
    setError(null)
    
    if (value.trim()) {
      const isUrl = validateUrlFormat(value)
      setInputType(isUrl ? 'url' : 'text')
      setIsValidInput(isUrl || value.trim().length > 2)
    } else {
      setInputType(null)
      setIsValidInput(false)
    }
  }

  const validateUrl = (url: string): boolean => {
    try {
      const urlObj = new URL(url)
      return urlObj.protocol === 'http:' || urlObj.protocol === 'https:'
    } catch {
      return false
    }
  }

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) {
      e.preventDefault()
    }
    setError(null)

    const trimmedUrl = websiteUrl.trim()
    if (!trimmedUrl) {
      setError('Please enter a website URL')
      return
    }

    // Add protocol if missing
    let finalUrl = trimmedUrl
    if (!trimmedUrl.startsWith('http://') && !trimmedUrl.startsWith('https://')) {
      finalUrl = `https://${trimmedUrl}`
    }

    if (!validateUrl(finalUrl)) {
      setError('Please enter a valid URL (e.g., https://example.com)')
      return
    }

    try {
      await onAnalyze(finalUrl)
    } catch (err: any) {
      setError(err.message || 'Error analyzing website')
      toast.error(err.message || 'Error analyzing website')
    }
  }

  return (
    <div className="max-w-3xl mx-auto">
      {/* Hero Section with Search Bar - Modern Redesign */}
      <div className="bg-gradient-to-br from-blue-50/50 via-white to-indigo-50/30 border border-blue-100/50 rounded-2xl shadow-lg p-8 md:p-12 transition-all">
        <div className="max-w-3xl mx-auto">
          {/* Header Section */}
          <div className="text-center mb-8">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-3">
              Enter Your Company Website
            </h2>
            <p className="text-gray-600 text-lg max-w-2xl mx-auto leading-relaxed">
              We'll analyze your website and identify your brand, industry, and key signals
            </p>
          </div>
          
          {/* Search Bar with Integrated Button */}
          <form onSubmit={handleSubmit} className="relative mb-4">
            <div className="relative flex items-center group">
              {/* Left Icon - Dynamic based on input type with pulse animation */}
              <div className="absolute left-4 z-10 pointer-events-none transition-all duration-300">
                {isLoading ? (
                  <div className="w-5 h-5 border-2 border-primary-600 border-t-transparent rounded-full animate-spin" />
                ) : isValidInput && inputType === 'url' ? (
                  <div className="flex items-center gap-1.5">
                    <Globe className="h-5 w-5 text-green-600 transition-colors duration-200 animate-pulse" />
                    {/* <CheckCircle className="h-3.5 w-3.5 text-green-600" /> */}
                  </div>
                ) : inputType === 'url' ? (
                  <Globe className="h-5 w-5 text-primary-600 transition-colors duration-200" />
                ) : inputType === 'text' ? (
                  <Search className="h-5 w-5 text-gray-400 group-focus-within:text-primary-600 transition-colors duration-200" />
                ) : (
                  <Sparkles className="h-5 w-5 text-gray-400" />
                )}
              </div>
              
              {/* Input Field with dynamic border color */}
              <input
                type="text"
                placeholder="Try 'openai.com', 'anthropic', or any company URL..."
                className={`input h-14 pl-12 pr-36 text-lg w-full shadow-md bg-white/90 backdrop-blur-sm focus:ring-4 focus:ring-primary-500/10 transition-all duration-200 placeholder:text-gray-400 disabled:bg-gray-50 ${
                  error
                    ? 'border-red-500 focus:border-red-500'
                    : isValidInput && inputType === 'url' 
                    ? 'border-green-500 focus:border-green-500' 
                    : inputType === 'text' && websiteUrl.trim().length > 0
                    ? 'border-primary-500 focus:border-primary-500'
                    : 'border-gray-300 focus:border-primary-500'
                }`}
                value={websiteUrl}
                onChange={(e) => handleUrlChange(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && websiteUrl.trim() && !isLoading) {
                    handleSubmit()
                  }
                }}
                disabled={isLoading}
                aria-label="Enter company website URL"
              />
              
              {/* Search Button - Inside Input with scale animation */}
              <button
                type="submit"
                disabled={!websiteUrl.trim() || isLoading}
                className="absolute right-2 top-1/2 -translate-y-1/2 h-10 px-6 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center gap-2 shadow-sm hover:shadow-md hover:scale-105 active:scale-95 disabled:hover:shadow-sm disabled:hover:scale-100 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                aria-label="Analyze company"
              >
                {isLoading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    <span className="hidden sm:inline">Analyzing...</span>
                  </>
                ) : (
                  <>
                    <Search className="h-4 w-4" />
                    <span className="hidden sm:inline">Search</span>
                  </>
                )}
              </button>
            </div>
            
            {/* Keyboard Hint - показывать только когда есть текст и не идет анализ */}
            {websiteUrl.trim() && !isLoading && (
              <div className="flex items-center justify-center gap-2 mt-3 text-xs text-gray-500 animate-fade-in duration-200">
                <kbd className="px-2 py-1 bg-gray-100 border border-gray-300 rounded text-gray-600 font-mono shadow-sm">
                  Enter
                </kbd>
                <span>to search</span>
                {isValidInput && inputType === 'url' && (
                  <span className="flex items-center gap-1 text-green-600 ml-2 animate-fade-in">
                    <CheckCircle className="h-3 w-3" />
                    Valid URL
                  </span>
                )}
              </div>
            )}

            {/* Error message */}
            {error && (
              <p className="mt-3 text-sm text-red-600 text-center animate-fade-in">
                {error}
              </p>
            )}
          </form>

          {/* Additional Info Text */}
          <p className="text-sm text-gray-500 text-center">
            Find company insights, news and suggested competitors before registering
          </p>
        </div>
      </div>
    </div>
  )
}
