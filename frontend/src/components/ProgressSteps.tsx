

interface ProgressStepsProps {
  current: 'select' | 'suggest' | 'analyze'
}

export default function ProgressSteps({ current }: ProgressStepsProps) {
  const steps = [
    { id: 'select', label: 'Select Company', icon: '🏢' },
    { id: 'suggest', label: 'Choose Competitors', icon: '🤖' },
    { id: 'analyze', label: 'View Analysis', icon: '📊' }
  ]
  
  const getStepIndex = (stepId: string) => {
    return steps.findIndex(step => step.id === stepId)
  }
  
  const currentIndex = getStepIndex(current)
  
  return (
    <div className="mb-6 sm:mb-8">
      <div className="flex items-center justify-center overflow-x-auto pb-2">
        <div className="flex items-center min-w-max px-2">
          {steps.map((step, index) => {
            const isActive = index === currentIndex
            const isCompleted = index < currentIndex
            
            return (
              <div key={step.id} className="flex items-center">
                {/* Step */}
                <div className="flex flex-col items-center">
                  <div
                    className={`w-10 h-10 sm:w-12 sm:h-12 rounded-full flex items-center justify-center text-base sm:text-lg font-semibold transition-colors ${
                      isCompleted
                        ? 'bg-green-500 text-white'
                        : isActive
                        ? 'bg-primary-500 text-white'
                        : 'bg-gray-200 text-gray-500'
                    }`}
                  >
                    {isCompleted ? '✓' : step.icon}
                  </div>
                  <span
                    className={`mt-1 sm:mt-2 text-xs sm:text-sm font-medium whitespace-nowrap ${
                      isActive || isCompleted ? 'text-primary-600' : 'text-gray-500'
                    }`}
                  >
                    <span className="hidden sm:inline">{step.label}</span>
                    <span className="sm:hidden">{step.label.split(' ')[0]}</span>
                  </span>
                </div>
                
                {/* Connector */}
                {index < steps.length - 1 && (
                  <div
                    className={`w-8 sm:w-16 h-1 mx-2 sm:mx-4 transition-colors ${
                      isCompleted ? 'bg-green-500' : 'bg-gray-200'
                    }`}
                  />
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
