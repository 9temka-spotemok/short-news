import { Download, FileJson, FileSpreadsheet, FileText } from 'lucide-react'
import React, { useState } from 'react'

interface ExportMenuProps {
  onExport: (format: 'json' | 'pdf' | 'csv') => void
  disabled?: boolean
}

export const ExportMenu: React.FC<ExportMenuProps> = ({ onExport, disabled = false }) => {
  const [isOpen, setIsOpen] = useState(false)

  const handleExport = (format: 'json' | 'pdf' | 'csv') => {
    onExport(format)
    setIsOpen(false)
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled}
        className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        <Download className="w-4 h-4" />
        Export
      </button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 z-10" 
            onClick={() => setIsOpen(false)}
          />
          
          {/* Menu */}
          <div className="absolute right-0 top-full mt-2 w-48 bg-white rounded-lg shadow-lg border z-20">
            <div className="py-2">
              <button
                onClick={() => handleExport('json')}
                className="w-full flex items-center gap-3 px-4 py-2 text-left hover:bg-gray-100 transition-colors"
              >
                <FileJson className="w-4 h-4 text-yellow-600" />
                <span>Export as JSON</span>
              </button>
              
              <button
                onClick={() => handleExport('pdf')}
                className="w-full flex items-center gap-3 px-4 py-2 text-left hover:bg-gray-100 transition-colors"
              >
                <FileText className="w-4 h-4 text-red-600" />
                <span>Export as PDF</span>
              </button>
              
              <button
                onClick={() => handleExport('csv')}
                className="w-full flex items-center gap-3 px-4 py-2 text-left hover:bg-gray-100 transition-colors"
              >
                <FileSpreadsheet className="w-4 h-4 text-green-600" />
                <span>Export as CSV</span>
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
