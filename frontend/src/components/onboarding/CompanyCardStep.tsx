import type { OnboardingCompanyData } from '@/types'
import { ArrowRight, Building2 } from 'lucide-react'

interface CompanyCardStepProps {
  company: OnboardingCompanyData
  onContinue: () => void
}

export default function CompanyCardStep({ company, onContinue }: CompanyCardStepProps) {
  return (
    <div className="max-w-3xl mx-auto">
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-gray-900 mb-2">
          We found your company
        </h2>
        <p className="text-gray-600">
          Check the information and continue to select competitors
        </p>
      </div>

      <div className="bg-white rounded-lg shadow-lg p-8 mb-6">
        <div className="flex items-start gap-6">
          {company.logo_url ? (
            <img
              src={company.logo_url}
              alt={company.name}
              className="w-20 h-20 rounded-lg object-contain border border-gray-200"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = 'none'
              }}
            />
          ) : (
            <div className="w-20 h-20 rounded-lg bg-gray-100 flex items-center justify-center border border-gray-200">
              <Building2 className="w-10 h-10 text-gray-400" />
            </div>
          )}

          <div className="flex-1">
            <h3 className="text-2xl font-bold text-gray-900 mb-2">{company.name}</h3>
            
            {company.website && (
              <a
                href={company.website}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-600 hover:text-primary-700 text-sm mb-4 inline-flex items-center gap-1"
              >
                {company.website}
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
            )}

            {/* AI Description */}
            {company.description && (
              <div className="mb-4">
                <p className="text-gray-700 leading-relaxed">{company.description}</p>
              </div>
            )}

            {/* Category and Industry Signals */}
            <div className="flex flex-wrap gap-3 mt-4">
              {company.category && (
                <span className="px-3 py-1 bg-primary-100 text-primary-700 rounded-full text-sm font-medium">
                  {company.category}
                </span>
              )}
              {company.industry_signals && company.industry_signals.length > 0 && (
                <>
                  {company.industry_signals.map((signal, idx) => (
                    <span
                      key={idx}
                      className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm"
                    >
                      {signal}
                    </span>
                  ))}
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={onContinue}
          className="bg-primary-600 text-white px-8 py-3 rounded-lg hover:bg-primary-700 transition-colors flex items-center gap-2 font-medium"
        >
          Next: select competitors
          <ArrowRight className="w-5 h-5" />
        </button>
      </div>
    </div>
  )
}


