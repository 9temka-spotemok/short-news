import type { OnboardingCompanyData, OnboardingCompetitor } from '@/types'
import { LogIn, CheckCircle2 } from 'lucide-react'

interface OnboardingCompleteStepProps {
  company: OnboardingCompanyData
  competitors: OnboardingCompetitor[]
  onAuthRequired: () => void
}

export default function OnboardingCompleteStep({ 
  company, 
  competitors,
  onAuthRequired 
}: OnboardingCompleteStepProps) {

  return (
    <div className="max-w-3xl mx-auto">
      <div className="text-center mb-8">
        <CheckCircle2 className="w-16 h-16 text-green-500 mx-auto mb-4" />
        <h2 className="text-3xl font-bold text-gray-900 mb-2">
          Ваш наблюдательный центр готов
        </h2>
        <p className="text-gray-600">
          Каждый день вы будете получать дайджест изменений по вашим конкурентам: новости, маркетинг, продуктовые обновления и многое другое
        </p>
      </div>

      {/* Company card */}
      <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Ваша компания</h3>
        <div className="flex items-center gap-4">
          {company.logo_url ? (
            <img
              src={company.logo_url}
              alt={company.name}
              className="w-12 h-12 rounded-lg object-contain"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = 'none'
              }}
            />
          ) : null}
          <div>
            <p className="font-medium text-gray-900">{company.name}</p>
            {company.website && (
              <p className="text-sm text-gray-500">{company.website}</p>
            )}
          </div>
        </div>
      </div>

      {/* Selected competitors */}
      <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Выбранные конкуренты ({competitors.length})
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {competitors.map((competitor) => (
            <div key={competitor.id} className="flex items-center gap-2">
              {competitor.logo_url ? (
                <img
                  src={competitor.logo_url}
                  alt={competitor.name}
                  className="w-8 h-8 rounded object-contain"
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = 'none'
                  }}
                />
              ) : (
                <div className="w-8 h-8 rounded bg-gray-100 flex items-center justify-center">
                  <span className="text-gray-400 text-xs font-medium">
                    {competitor.name.charAt(0).toUpperCase()}
                  </span>
                </div>
              )}
              <p className="text-sm text-gray-700 truncate">{competitor.name}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="flex flex-col items-center gap-4">
        <p className="text-gray-600 text-center mb-2">
          Для продолжения работы с платформой и получения новостей о конкурентах необходимо зарегистрироваться или войти в систему
        </p>
        <button
          onClick={onAuthRequired}
          className="bg-primary-600 text-white px-8 py-3 rounded-lg hover:bg-primary-700 transition-colors flex items-center gap-2 font-medium"
        >
          <LogIn className="w-5 h-5" />
          Зарегистрироваться или войти
        </button>
      </div>
    </div>
  )
}


