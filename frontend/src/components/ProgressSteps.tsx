

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
    <div className="mb-8">
      <div className="flex items-center justify-center">
        {steps.map((step, index) => {
          const isActive = index === currentIndex
          const isCompleted = index < currentIndex
          const isUpcoming = index > currentIndex
          
          return (
            <div key={step.id} className="flex items-center">
              {/* Step */}
              <div className="flex flex-col items-center">
                <div
                  className={`w-12 h-12 rounded-full flex items-center justify-center text-lg font-semibold transition-colors ${
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
                  className={`mt-2 text-sm font-medium ${
                    isActive || isCompleted ? 'text-primary-600' : 'text-gray-500'
                  }`}
                >
                  {step.label}
                </span>
              </div>
              
              {/* Connector */}
              {index < steps.length - 1 && (
                <div
                  className={`w-16 h-1 mx-4 transition-colors ${
                    isCompleted ? 'bg-green-500' : 'bg-gray-200'
                  }`}
                />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
