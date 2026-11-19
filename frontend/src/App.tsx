import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Route, Routes } from 'react-router-dom';

import Layout from './components/Layout';
import JudolLandingPage from './pages/JudolLandingPage';
import NotFoundPage from './pages/NotFoundPage';
import VideosPage from './pages/VideosPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { refetchOnWindowFocus: false, staleTime: 5_000 },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route index element={<JudolLandingPage />} />
          <Route path="/videos" element={<VideosPage />} />
          <Route element={<Layout />}>
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
