import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/context/AuthContext";
import ErrorBoundary from "@/components/ErrorBoundary";
import ProtectedRoute from "@/components/ProtectedRoute";
import AdminRoute from "@/components/AdminRoute";
import UserLayout from "@/components/layout/UserLayout";
import AdminLayout from "@/components/layout/AdminLayout";
import HomePage from "@/pages/HomePage";
import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import NotFoundPage from "@/pages/NotFoundPage";
import UserDashboard from "@/pages/user/UserDashboard";
import BuilderPage from "@/pages/user/BuilderPage";
import BacktestPage from "@/pages/user/BacktestPage";
import PaperTradesPage from "@/pages/user/PaperTradesPage";
import TemplatesPage from "@/pages/user/TemplatesPage";
import ScreenerPage from "@/pages/user/ScreenerPage";
import StrategyDetailPage from "@/pages/user/StrategyDetailPage";
import AdminDashboard from "@/pages/admin/AdminDashboard";
import AdminUsers from "@/pages/admin/AdminUsers";

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <ErrorBoundary>
          <Toaster position="top-right" richColors />
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            {/* User routes */}
            <Route element={<ProtectedRoute><UserLayout /></ProtectedRoute>}>
              <Route path="/dashboard" element={<UserDashboard />} />
              <Route path="/build" element={<BuilderPage />} />
              <Route path="/backtest/:strategyId" element={<BacktestPage />} />
              <Route path="/paper-trades" element={<PaperTradesPage />} />
              <Route path="/templates" element={<TemplatesPage />} />
              <Route path="/screener" element={<ScreenerPage />} />
              <Route path="/strategy/:strategyId" element={<StrategyDetailPage />} />
            </Route>

            {/* Admin routes */}
            <Route element={<AdminRoute><AdminLayout /></AdminRoute>}>
              <Route path="/admin/dashboard" element={<AdminDashboard />} />
              <Route path="/admin/users" element={<AdminUsers />} />
            </Route>

            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </ErrorBoundary>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
