import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Route, Routes } from 'react-router-dom';

import Layout from './components/Layout';
import JudolLandingPage from './pages/JudolLandingPage';
import NotFoundPage from './pages/NotFoundPage';
import VideoDetailPage from './pages/VideoDetailPage';
import VideosPage from './pages/VideosPage';
import { AppearanceProvider } from './theme/AppearanceProvider';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { refetchOnWindowFocus: false, staleTime: 5_000 },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppearanceProvider>
        <BrowserRouter>
          <Routes>
            <Route index element={<JudolLandingPage />} />
            <Route path="/videos" element={<VideosPage />} />
            <Route path="/videos/:videoId" element={<VideoDetailPage />} />
            <Route element={<Layout />}>
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AppearanceProvider>
    </QueryClientProvider>
  );
}
