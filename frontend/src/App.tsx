import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useParams } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './contexts/AuthContext';
import { MainLayout } from './layouts/MainLayout';
import { DashboardLayout } from './layouts/DashboardLayout';
import { ProtectedRoute } from './components/ProtectedRoute';

import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { DashboardPage } from './pages/DashboardPage';
import { NewAnalysisPage } from './pages/NewAnalysisPage';
import { AnalysisResultsPage } from './pages/AnalysisResultsPage';
import { CaseHistoryPage } from './pages/CaseHistoryPage';
import { SavedJudgmentsPage } from './pages/SavedJudgmentsPage';
import { PrecedentsLibraryPage } from './pages/PrecedentsLibraryPage';
import { ProfilePage } from './pages/ProfilePage';
import { AdminDashboardPage } from './pages/AdminDashboardPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1
    }
  }
});

const AnalysisRedirect: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  return <Navigate to={`/dashboard/analysis/${id}`} replace />;
};

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public Layout */}
            <Route path="/" element={<MainLayout />}>
              <Route index element={<LandingPage />} />
              <Route path="login" element={<LoginPage />} />
              <Route path="register" element={<RegisterPage />} />
              <Route path="precedents" element={<div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"><PrecedentsLibraryPage /></div>} />
            </Route>

            {/* Protected Dashboard Layout */}
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <DashboardLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<DashboardPage />} />
              <Route path="new-analysis" element={<NewAnalysisPage />} />
              <Route path="analysis/:id" element={<AnalysisResultsPage />} />
              <Route path="history" element={<CaseHistoryPage />} />
              <Route path="saved" element={<SavedJudgmentsPage />} />
              <Route path="precedents" element={<PrecedentsLibraryPage />} />
              <Route path="profile" element={<ProfilePage />} />
              <Route
                path="admin"
                element={
                  <ProtectedRoute requireAdmin>
                    <AdminDashboardPage />
                  </ProtectedRoute>
                }
              />
            </Route>

            {/* Convenience Aliases */}
            <Route path="/analysis/new" element={<Navigate to="/dashboard/new-analysis" replace />} />
            <Route path="/analysis/:id" element={<AnalysisRedirect />} />
            <Route path="/cases" element={<Navigate to="/dashboard/history" replace />} />
            <Route path="/history" element={<Navigate to="/dashboard/history" replace />} />

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
};

export default App;
