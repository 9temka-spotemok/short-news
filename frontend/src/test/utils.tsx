import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactNode } from 'react'

export const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        refetchOnWindowFocus: false,
      },
    },
  })

export const withQueryClient = (ui: ReactNode, client = createTestQueryClient()) => (
  <QueryClientProvider client={client}>{ui}</QueryClientProvider>
)













