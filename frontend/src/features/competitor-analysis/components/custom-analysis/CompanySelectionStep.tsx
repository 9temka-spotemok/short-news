import { ArrowRight } from 'lucide-react'

import CompanySelector from '@/components/CompanySelector'
import type { Company } from '@/types'

const CARD_CLASSES = 'max-w-2xl mx-auto bg-white rounded-lg shadow-md p-6'

type CompanySelectionStepProps = {
  selectedCompany: Company | null
  onSelectCompany: (company: Company | null) => void
  onContinue: () => void
  onBackToMenu: () => void
}

export const CompanySelectionStep = ({
  selectedCompany,
  onSelectCompany,
  onContinue,
  onBackToMenu
}: CompanySelectionStepProps) => (
  <div className={CARD_CLASSES}>
    <h2 className="text-xl font-semibold text-gray-900 mb-4">Select Your Company</h2>
    <p className="text-gray-600 mb-6">
      Choose the company you want to analyze and find competitors for.
    </p>

    <CompanySelector onSelect={onSelectCompany} selectedCompany={selectedCompany} />

    <div className="mt-6 flex items-center justify-between">
      <button
        onClick={onBackToMenu}
        className="text-gray-600 hover:text-gray-800 flex items-center"
      >
        Back to Menu
      </button>
      <button
        onClick={onContinue}
        disabled={!selectedCompany}
        className="bg-primary-600 text-white px-6 py-3 rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
      >
        Continue
        <ArrowRight className="w-5 h-5 ml-2" />
      </button>
    </div>
  </div>
)











