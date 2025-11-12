import { Building2, Users } from 'lucide-react'

const cardBaseStyles =
  'bg-white rounded-lg shadow-md p-6 cursor-pointer hover:shadow-lg transition-shadow border-2 border-transparent'

type AnalysisModeSelectionProps = {
  onSelectCompanyAnalysis: () => void
  onSelectCustomAnalysis: () => void
}

export const AnalysisModeSelection = ({
  onSelectCompanyAnalysis,
  onSelectCustomAnalysis
}: AnalysisModeSelectionProps) => (
  <div className="max-w-4xl mx-auto">
    <div className="text-center mb-8">
      <h2 className="text-2xl font-bold text-gray-900 mb-4">Choose Analysis Type</h2>
      <p className="text-gray-600">
        Select the type of competitor analysis you want to perform
      </p>
    </div>

    <div className="grid md:grid-cols-2 gap-6">
      <div
        onClick={onSelectCompanyAnalysis}
        className={`${cardBaseStyles} hover:border-blue-200`}
      >
        <div className="flex items-center mb-4">
          <Building2 className="w-8 h-8 text-blue-600 mr-3" />
          <h3 className="text-xl font-semibold text-gray-900">Company Analysis</h3>
        </div>
        <p className="text-gray-600 mb-4">
          Quick analysis of a specific company with AI-suggested competitors. Perfect for getting immediate insights about a company and its competitive landscape.
        </p>
        <ul className="text-sm text-gray-500 space-y-1">
          <li>• Select target company</li>
          <li>• AI-powered competitor suggestions</li>
          <li>• Instant analysis results</li>
          <li>• Export capabilities</li>
        </ul>
      </div>

      <div
        onClick={onSelectCustomAnalysis}
        className={`${cardBaseStyles} hover:border-green-200`}
      >
        <div className="flex items-center mb-4">
          <Users className="w-8 h-8 text-green-600 mr-3" />
          <h3 className="text-xl font-semibold text-gray-900">Custom Analysis</h3>
        </div>
        <p className="text-gray-600 mb-4">
          Advanced step-by-step analysis with full control over competitor selection. Ideal for detailed research and comprehensive competitive intelligence.
        </p>
        <ul className="text-sm text-gray-500 space-y-1">
          <li>• Step-by-step process</li>
          <li>• Manual competitor selection</li>
          <li>• Detailed theme analysis</li>
          <li>• Advanced export options</li>
        </ul>
      </div>
    </div>
  </div>
)


