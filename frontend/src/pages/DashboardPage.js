/**
 * Text2trade Dashboard Page
 * =========================
 * Protected dashboard - checks if user is logged in.
 * If not logged in, redirects to login page.
 * Shows user email and logout button.
 */

import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { 
  Card, 
  CardContent, 
  CardHeader, 
  CardTitle 
} from "@/components/ui/card";
import { 
  TrendingUp, 
  TrendingDown, 
  Activity, 
  BarChart3,
  Wallet,
  Clock,
  LogOut,
  User
} from "lucide-react";

/**
 * Dashboard Navigation Component
 * Shows user email and logout button.
 */
const DashboardNav = ({ userEmail, onLogout }) => {
  return (
    <nav 
      className="fixed top-0 left-0 right-0 z-50 glass"
      data-testid="dashboard-navbar"
    >
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        {/* Logo */}
        <Link 
          to="/" 
          className="flex items-center gap-2"
          data-testid="dashboard-logo"
        >
          <div className="w-8 h-8 bg-primary flex items-center justify-center">
            <TrendingUp className="w-5 h-5 text-primary-foreground" />
          </div>
          <span className="font-mono font-bold text-lg text-foreground">
            TEXT2TRADE
          </span>
        </Link>
        
        {/* User info and logout */}
        <div className="flex items-center gap-4">
          {/* User email display */}
          <div className="hidden sm:flex items-center gap-2 text-muted-foreground">
            <User className="w-4 h-4" />
            <span className="mono-label" data-testid="user-email">
              {userEmail}
            </span>
          </div>
          
          {/* Logout button */}
          <Button 
            variant="ghost" 
            size="sm"
            onClick={onLogout}
            className="font-mono text-sm uppercase tracking-wider gap-2"
            data-testid="logout-button"
          >
            <LogOut className="w-4 h-4" />
            <span className="hidden sm:inline">Logout</span>
          </Button>
        </div>
      </div>
    </nav>
  );
};

/**
 * Stat Card Component
 * Displays a single metric with icon and value.
 */
const StatCard = ({ icon: Icon, label, value, subtext, trend, testId }) => {
  return (
    <Card className="border-border bg-card card-hover" data-testid={testId}>
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <span className="mono-label">{label}</span>
            <p className="text-2xl font-mono font-bold text-foreground data-value">
              {value}
            </p>
            {subtext && (
              <p className="text-sm text-muted-foreground">{subtext}</p>
            )}
          </div>
          <div className={`w-10 h-10 flex items-center justify-center ${
            trend === 'up' ? 'bg-primary/10' : 
            trend === 'down' ? 'bg-destructive/10' : 
            'bg-secondary'
          }`}>
            <Icon className={`w-5 h-5 ${
              trend === 'up' ? 'text-primary' : 
              trend === 'down' ? 'text-destructive' : 
              'text-muted-foreground'
            }`} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

/**
 * Empty Widget Placeholder
 * Used to show where content will go.
 */
const EmptyWidget = ({ title, icon: Icon, span = 1, testId }) => {
  const spanClass = span === 2 ? 'md:col-span-2' : span === 3 ? 'md:col-span-3' : '';
  
  return (
    <Card 
      className={`border-border bg-card card-hover ${spanClass}`}
      data-testid={testId}
    >
      <CardHeader className="pb-4">
        <CardTitle className="text-sm font-mono uppercase tracking-wider flex items-center gap-2">
          <Icon className="w-4 h-4 text-primary" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-48 border border-dashed border-border flex items-center justify-center">
          <div className="text-center">
            <Icon className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
            <p className="mono-label">
              // PLACEHOLDER
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Content coming soon
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

/**
 * Dashboard Page Component
 * Protected page - redirects to login if not authenticated.
 * 
 * AUTH CHECK FLOW:
 * 1. On page load, check localStorage for "userEmail"
 * 2. If not found → redirect to /login
 * 3. If found → show dashboard with user's email
 * 4. On logout → clear localStorage → redirect to /login
 */
export default function DashboardPage() {
  // Store the logged-in user's email
  const [userEmail, setUserEmail] = useState(null);
  
  // Navigation hook for redirects
  const navigate = useNavigate();
  
  /**
   * Check authentication on page load
   * If no user in localStorage, redirect to login
   */
  useEffect(() => {
    const email = localStorage.getItem("userEmail");
    
    if (!email) {
      // Not logged in - redirect to login page
      navigate("/login");
    } else {
      // Logged in - show dashboard
      setUserEmail(email);
    }
  }, [navigate]);
  
  /**
   * Handle logout
   * Clear localStorage and redirect to login
   */
  const handleLogout = () => {
    // Clear the stored user
    localStorage.removeItem("userEmail");
    
    // Redirect to login page
    navigate("/login");
  };
  
  // Don't render anything until we check auth
  if (!userEmail) {
    return null;
  }
  
  return (
    <div className="min-h-screen bg-background" data-testid="dashboard-page">
      {/* Navigation with user info */}
      <DashboardNav userEmail={userEmail} onLogout={handleLogout} />
      
      {/* Main Content */}
      <main className="pt-24 pb-12 px-6">
        <div className="max-w-7xl mx-auto">
          {/* Page Header */}
          <div className="mb-8">
            <span className="mono-label text-primary mb-2 inline-block">
              // DASHBOARD
            </span>
            <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-foreground">
              Overview
            </h1>
            <p className="text-muted-foreground mt-2">
              Welcome back, <span className="text-primary">{userEmail}</span>
            </p>
          </div>
          
          {/* Stats Row */}
          <div 
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8"
            data-testid="stats-grid"
          >
            <StatCard 
              icon={Wallet}
              label="BALANCE"
              value="$0.00"
              subtext="Available funds"
              testId="stat-balance"
            />
            <StatCard 
              icon={TrendingUp}
              label="P&L TODAY"
              value="+$0.00"
              subtext="0.00%"
              trend="up"
              testId="stat-pnl"
            />
            <StatCard 
              icon={Activity}
              label="OPEN POSITIONS"
              value="0"
              subtext="No active trades"
              testId="stat-positions"
            />
            <StatCard 
              icon={Clock}
              label="PENDING ORDERS"
              value="0"
              subtext="None queued"
              testId="stat-orders"
            />
          </div>
          
          {/* Widgets Grid */}
          <div 
            className="grid grid-cols-1 md:grid-cols-3 gap-4"
            data-testid="widgets-grid"
          >
            {/* Chart placeholder - spans 2 columns */}
            <EmptyWidget 
              title="Price Chart"
              icon={BarChart3}
              span={2}
              testId="widget-chart"
            />
            
            {/* Orderbook placeholder */}
            <EmptyWidget 
              title="Order Book"
              icon={TrendingDown}
              testId="widget-orderbook"
            />
            
            {/* Recent trades placeholder - spans full width */}
            <EmptyWidget 
              title="Recent Trades"
              icon={Activity}
              span={3}
              testId="widget-trades"
            />
          </div>
          
          {/* Footer info */}
          <div className="mt-12 pt-8 border-t border-border">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
              <span className="mono-label">
                // AUTHENTICATED AS: {userEmail}
              </span>
              <div className="flex items-center gap-4">
                <span className="mono-label">
                  API Status: <span className="text-primary">CONNECTED</span>
                </span>
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={handleLogout}
                  className="font-mono text-xs uppercase tracking-wider"
                  data-testid="dashboard-logout-button"
                >
                  Logout
                </Button>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
