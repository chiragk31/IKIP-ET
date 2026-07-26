'use client';

/**
 * App Providers
 *
 * Wraps the entire application with global context providers.
 * - TanStack Query (server state management)
 *
 * Must wrap all pages that use useQuery, useMutation etc.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';

export function Providers({ children }: { children: React.ReactNode }) {
  // Create a stable QueryClient instance per component tree
  // Using useState ensures a new client per server render
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,      // 30 seconds before data is considered stale
            retry: 1,               // Retry failed requests once
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}
