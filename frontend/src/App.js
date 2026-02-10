/**
 * Text2trade Main App Component
 * =============================
 * Root component with routing setup.
 * Routes: Home (/), Login (/login), Dashboard (/dashboard)
 * 
 * File Structure:
 * - App.js (this file): Main app with routing
 * - pages/HomePage.js: Landing page
 * - pages/LoginPage.js: Login form (static mockup)
 * - pages/DashboardPage.js: Empty dashboard placeholder
 */

import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";

// Import page components
import HomePage from "@/pages/HomePage";
import LoginPage from "@/pages/LoginPage";
import DashboardPage from "@/pages/DashboardPage";

/**
 * Main App Component
 * Sets up routing for the application.
 * No authentication logic - just navigation.
 */
function App() {
  return (
    // Main container - no center alignment to preserve natural reading flow
    <div className="min-h-screen bg-background">
      <BrowserRouter>
        <Routes>
          {/* Home/Landing page - public */}
          <Route path="/" element={<HomePage />} />
          
          {/* Login page - static mockup form */}
          <Route path="/login" element={<LoginPage />} />
          
          {/* Dashboard - empty placeholder */}
          <Route path="/dashboard" element={<DashboardPage />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
