import {
  MutationCache,
  QueryCache,
  QueryClient,
  QueryClientConfig
} from '@tanstack/react-query'

const defaultConfig: QueryClientConfig = {
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes - данные считаются свежими
      gcTime: 10 * 60 * 1000, // 10 minutes (ранее cacheTime) - время хранения в кэше
      retry: 1,
      refetchOnWindowFocus: false, // Не делать запрос при фокусе окна
      refetchOnMount: 'always', // Всегда делать запрос при монтировании, если данные stale
      refetchOnReconnect: true, // Делать запрос при переподключении
      // Если данные свежие (staleTime не истек), не делать запрос при монтировании
      // Это предотвратит лишние запросы при обновлении страницы, если данные свежие
    },
    mutations: {
      retry: 1
    }
  },
  queryCache: new QueryCache(),
  mutationCache: new MutationCache()
}

export const queryClient = new QueryClient(defaultConfig)









