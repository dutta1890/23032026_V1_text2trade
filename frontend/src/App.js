import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/context/AuthContext";
import ErrorBoundary from "@/components/ErrorBoundary";
import ProtectedRoute from "@/components/ProtectedRoute";
import AdminRoute from "@/components/AdminRoute";
import ReconsentGate from "@/components/ReconsentGate";
import SessionExpiredModal from "@/components/SessionExpiredModal";
import VersionBanner from "@/components/VersionBanner";
import UserLayout from "@/components/layout/UserLayout";
import AdminLayout from "@/components/layout/AdminLayout";
import HomePage from "@/pages/HomePage";
import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import ForgotPasswordPage from "@/pages/ForgotPasswordPage";
import ResetPasswordPage from "@/pages/ResetPasswordPage";
import SharedStrategyPage from "@/pages/SharedStrategyPage";
import LegalPage from "@/pages/LegalPage";
import CompliancePage from "@/pages/CompliancePage";
import BenchmarksPage from "@/pages/BenchmarksPage";
import BacktestSnapshotPage from "@/pages/BacktestSnapshotPage";
import BacktestComparePage from "@/pages/BacktestComparePage";
import ShareViewPage from "@/pages/ShareViewPage";
import GlossaryPage from "@/pages/GlossaryPage";
import NotFoundPage from "@/pages/NotFoundPage";
import UserDashboard from "@/pages/user/UserDashboard";
import BuilderPage from "@/pages/user/BuilderPage";
import BacktestPage from "@/pages/user/BacktestPage";
import PaperTradesPage from "@/pages/user/PaperTradesPage";
import TemplatesPage from "@/pages/user/TemplatesPage";
import ScreenerPage from "@/pages/user/ScreenerPage";
import StrategyDetailPage from "@/pages/user/StrategyDetailPage";
import OptimizerPage from "@/pages/user/OptimizerPage";
import WatchlistPage from "@/pages/user/WatchlistPage";
import TrackerPage from "@/pages/user/TrackerPage";
import AlertsPage from "@/pages/user/AlertsPage";
import ProfilePage from "@/pages/user/ProfilePage";
import AdminDashboard from "@/pages/admin/AdminDashboard";
import AdminUsers from "@/pages/admin/AdminUsers";
import AdminDiagnostics from "@/pages/admin/AdminDiagnostics";
import AdminCompliance from "@/pages/admin/AdminCompliance";

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <ErrorBoundary>
          <Toaster position="top-right" richColors />
          <VersionBanner />
          <SessionExpiredModal />
          <ReconsentGate />
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
            <Route path="/shared/:shareToken" element={<SharedStrategyPage />} />
            <Route path="/legal/:docType" element={<LegalPage />} />
            <Route path="/compliance" element={<CompliancePage />} />
            <Route path="/benchmarks" element={<BenchmarksPage />} />
            <Route path="/backtest/snapshot/:snapshotId" element={<BacktestSnapshotPage />} />
            <Route path="/backtest/compare" element={<BacktestComparePage />} />
            <Route path="/s/:shareId" element={<ShareViewPage />} />


            {/* User routes */}
            <Route element={<ProtectedRoute><UserLayout /></ProtectedRoute>}>
              <Route path="/dashboard" element={<UserDashboard />} />
              <Route path="/build" element={<BuilderPage />} />
              <Route path="/backtest/:strategyId" element={<BacktestPage />} />
              <Route path="/paper-trades" element={<PaperTradesPage />} />
              <Route path="/templates" element={<TemplatesPage />} />
              <Route path="/screener" element={<ScreenerPage />} />
              <Route path="/strategy/:strategyId" element={<StrategyDetailPage />} />
              <Route path="/optimizer" element={<OptimizerPage />} />
              <Route path="/watchlist" element={<WatchlistPage />} />
              <Route path="/tracker" element={<TrackerPage />} />
              <Route path="/alerts" element={<AlertsPage />} />
              <Route path="/profile" element={<ProfilePage />} />
              <Route path="/glossary" element={<GlossaryPage />} />
            </Route>

            {/* Admin routes */}
            <Route element={<AdminRoute><AdminLayout /></AdminRoute>}>
              <Route path="/admin/dashboard" element={<AdminDashboard />} />
              <Route path="/admin/users" element={<AdminUsers />} />
              <Route path="/admin/diagnostics" element={<AdminDiagnostics />} />
              <Route path="/admin/compliance" element={<AdminCompliance />} />
            </Route>

            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </ErrorBoundary>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
