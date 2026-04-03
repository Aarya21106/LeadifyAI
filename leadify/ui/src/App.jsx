import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/Layout';
import Queue from './pages/Queue';
import Leads from './pages/Leads';
import LiveView from './pages/LiveView';
import Settings from './pages/Settings';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5000,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/queue" element={<Queue />} />
            <Route path="/leads" element={<Leads />} />
            <Route path="/live" element={<LiveView />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/queue" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
