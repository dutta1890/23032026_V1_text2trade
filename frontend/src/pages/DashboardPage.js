/**
 * Text2trade Dashboard Page
 * =========================
 * Protected dashboard with sidebar navigation.
 * 
 * COMPONENT STRUCTURE:
 * --------------------
 * DashboardPage (main component)
 * ├── Sidebar (left navigation)
 * │   ├── Logo
 * │   ├── Navigation Links
 * │   │   ├── Create Strategy
 * │   │   ├── My Strategies
 * │   │   └── Help
 * │   └── User Info + Logout
 * └── MainContent (right side)
 *     ├── Header (page title)
 *     └── Content Cards (based on active page)
 * 
 * HOW NAVIGATION WORKS:
 * ---------------------
 * 1. Sidebar has 3 menu items: Create Strategy, My Strategies, Help
 * 2. Clicking a menu item sets "activePage" state
 * 3. MainContent renders different placeholder cards based on activePage
 * 4. No actual page routing - just state-based content switching
 * 5. Active menu item is highlighted with primary color
 */

import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { 
  Card, 
  CardContent, 
  CardDescription,
  CardHeader, 
  CardTitle 
} from "@/components/ui/card";
import { 
  TrendingUp,
  PlusCircle,
  FolderOpen,
  HelpCircle,
  LogOut,
  User,
  ChevronRight,
  Lightbulb,
  FileText,
  Settings,
  BarChart3,
  Zap
} from "lucide-react";


// =============================================================================
// SIDEBAR COMPONENT
// =============================================================================

/**
 * Sidebar Navigation
 * 
 * Props:
 * - activePage: Currently selected page ("create" | "strategies" | "help")
 * - onPageChange: Function to call when user clicks a menu item
 * - userEmail: Logged-in user's email
 * - onLogout: Function to call when user clicks logout
 */
const Sidebar = ({ activePage, onPageChange, userEmail, onLogout }) => {
  // Menu items configuration
  // Each item has: id (for state), label (display text), icon (Lucide icon)
  const menuItems = [
    { id: "create", label: "Create Strategy", icon: PlusCircle },
    { id: "strategies", label: "My Strategies", icon: FolderOpen },
    { id: "help", label: "Help", icon: HelpCircle },
  ];
  
  return (
    <aside 
      className="fixed left-0 top-0 bottom-0 w-64 bg-card border-r border-border flex flex-col"
      data-testid="dashboard-sidebar"
    >
      {/* Logo Section */}
      <div className="p-6 border-b border-border">
        <Link 
          to="/" 
          className="flex items-center gap-2"
          data-testid="sidebar-logo"
        >
          <div className="w-8 h-8 bg-primary flex items-center justify-center">
            <TrendingUp className="w-5 h-5 text-primary-foreground" />
          </div>
          <span className="font-mono font-bold text-lg text-foreground">
            TEXT2TRADE
          </span>
        </Link>
      </div>
      
      {/* Navigation Menu */}
      <nav className="flex-1 p-4" data-testid="sidebar-nav">
        <div className="space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = activePage === item.id;
            
            return (
              <button
                key={item.id}
                onClick={() => onPageChange(item.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-colors ${
                  isActive 
                    ? "bg-primary/10 text-primary border-l-2 border-primary" 
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary"
                }`}
                data-testid={`sidebar-${item.id}`}
              >
                <Icon className="w-5 h-5" />
                <span className="font-mono text-sm uppercase tracking-wider">
                  {item.label}
                </span>
              </button>
            );
          })}
        </div>
      </nav>
      
      {/* User Section */}
      <div className="p-4 border-t border-border">
        {/* User email */}
        <div className="flex items-center gap-2 px-4 py-2 mb-2">
          <User className="w-4 h-4 text-muted-foreground" />
          <span 
            className="text-xs text-muted-foreground truncate"
            data-testid="sidebar-user-email"
          >
            {userEmail}
          </span>
        </div>
        
        {/* Logout button */}
        <Button
          variant="ghost"
          onClick={onLogout}
          className="w-full justify-start gap-3 font-mono text-sm uppercase tracking-wider text-muted-foreground hover:text-destructive"
          data-testid="sidebar-logout"
        >
          <LogOut className="w-5 h-5" />
          Logout
        </Button>
      </div>
    </aside>
  );
};


// =============================================================================
// CONTENT COMPONENTS (Placeholder Cards)
// =============================================================================

/**
 * Placeholder Card Component
 * A reusable card with icon, title, description, and optional action
 */
const PlaceholderCard = ({ icon: Icon, title, description, actionLabel, testId }) => {
  return (
    <Card 
      className="border-border bg-card card-hover group"
      data-testid={testId}
    >
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="w-12 h-12 bg-primary/10 flex items-center justify-center mb-4">
            <Icon className="w-6 h-6 text-primary" />
          </div>
          {actionLabel && (
            <ChevronRight className="w-5 h-5 text-muted-foreground group-hover:text-primary transition-colors" />
          )}
        </div>
        <CardTitle className="text-lg font-mono">{title}</CardTitle>
        <CardDescription className="text-muted-foreground">
          {description}
        </CardDescription>
      </CardHeader>
      {actionLabel && (
        <CardContent>
          <Button 
            variant="outline" 
            className="w-full font-mono text-xs uppercase tracking-wider"
          >
            {actionLabel}
          </Button>
        </CardContent>
      )}
    </Card>
  );
};

/**
 * Create Strategy Content
 * Shows placeholder cards for strategy creation options
 */
const CreateStrategyContent = () => {
  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          Create Strategy
        </h1>
        <p className="text-muted-foreground mt-2">
          Build a new trading strategy from scratch or use a template.
        </p>
      </div>
      
      {/* Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <PlaceholderCard
          icon={PlusCircle}
          title="Blank Strategy"
          description="Start from scratch with a blank canvas. Full control over every parameter."
          actionLabel="Create Blank"
          testId="card-blank-strategy"
        />
        <PlaceholderCard
          icon={Lightbulb}
          title="Use Template"
          description="Choose from pre-built strategy templates to get started quickly."
          actionLabel="Browse Templates"
          testId="card-use-template"
        />
        <PlaceholderCard
          icon={FileText}
          title="Import Strategy"
          description="Import an existing strategy from a file or another platform."
          actionLabel="Import"
          testId="card-import-strategy"
        />
      </div>
      
      {/* Info Section */}
      <Card className="border-border bg-secondary/30" data-testid="card-info">
        <CardContent className="p-6">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 bg-primary/10 flex items-center justify-center flex-shrink-0">
              <Zap className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h3 className="font-mono font-bold text-foreground mb-1">
                Quick Tip
              </h3>
              <p className="text-sm text-muted-foreground">
                New to strategy creation? Start with a template and customize it 
                to learn how different parameters affect trading behavior.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

/**
 * My Strategies Content
 * Shows placeholder cards for existing strategies
 */
const MyStrategiesContent = () => {
  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">
            My Strategies
          </h1>
          <p className="text-muted-foreground mt-2">
            Manage and monitor your trading strategies.
          </p>
        </div>
        <Button className="font-mono text-xs uppercase tracking-wider gap-2">
          <PlusCircle className="w-4 h-4" />
          New Strategy
        </Button>
      </div>
      
      {/* Empty State */}
      <Card 
        className="border-border border-dashed bg-card/50"
        data-testid="strategies-empty-state"
      >
        <CardContent className="p-12 text-center">
          <div className="w-16 h-16 bg-secondary flex items-center justify-center mx-auto mb-4">
            <FolderOpen className="w-8 h-8 text-muted-foreground" />
          </div>
          <h3 className="font-mono font-bold text-lg text-foreground mb-2">
            No Strategies Yet
          </h3>
          <p className="text-sm text-muted-foreground mb-6 max-w-md mx-auto">
            You haven't created any strategies. Create your first strategy to 
            start automating your trades.
          </p>
          <Button className="font-mono text-xs uppercase tracking-wider gap-2">
            <PlusCircle className="w-4 h-4" />
            Create Your First Strategy
          </Button>
        </CardContent>
      </Card>
      
      {/* Stats Row (Placeholder) */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="border-border bg-card" data-testid="stat-active">
          <CardContent className="p-6">
            <span className="mono-label">Active Strategies</span>
            <p className="text-3xl font-mono font-bold text-foreground mt-2">0</p>
          </CardContent>
        </Card>
        <Card className="border-border bg-card" data-testid="stat-paused">
          <CardContent className="p-6">
            <span className="mono-label">Paused</span>
            <p className="text-3xl font-mono font-bold text-foreground mt-2">0</p>
          </CardContent>
        </Card>
        <Card className="border-border bg-card" data-testid="stat-total">
          <CardContent className="p-6">
            <span className="mono-label">Total Created</span>
            <p className="text-3xl font-mono font-bold text-foreground mt-2">0</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

/**
 * Help Content
 * Shows placeholder cards for help resources
 */
const HelpContent = () => {
  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          Help & Support
        </h1>
        <p className="text-muted-foreground mt-2">
          Find answers and get support for Text2trade.
        </p>
      </div>
      
      {/* Help Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <PlaceholderCard
          icon={FileText}
          title="Documentation"
          description="Read the full documentation to learn how to use all features."
          actionLabel="View Docs"
          testId="card-documentation"
        />
        <PlaceholderCard
          icon={Lightbulb}
          title="Getting Started"
          description="New to Text2trade? Follow our step-by-step beginner's guide."
          actionLabel="Start Guide"
          testId="card-getting-started"
        />
        <PlaceholderCard
          icon={BarChart3}
          title="Strategy Examples"
          description="Explore example strategies to understand different approaches."
          actionLabel="View Examples"
          testId="card-examples"
        />
        <PlaceholderCard
          icon={Settings}
          title="FAQ"
          description="Find answers to frequently asked questions."
          actionLabel="View FAQ"
          testId="card-faq"
        />
      </div>
      
      {/* Contact Support */}
      <Card className="border-border bg-card" data-testid="card-support">
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 bg-primary/10 flex items-center justify-center flex-shrink-0">
                <HelpCircle className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h3 className="font-mono font-bold text-foreground mb-1">
                  Need More Help?
                </h3>
                <p className="text-sm text-muted-foreground">
                  Can't find what you're looking for? Contact our support team.
                </p>
              </div>
            </div>
            <Button 
              variant="outline"
              className="font-mono text-xs uppercase tracking-wider"
            >
              Contact Support
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};


// =============================================================================
// MAIN DASHBOARD PAGE COMPONENT
// =============================================================================

/**
 * Dashboard Page
 * 
 * This is the main dashboard component that:
 * 1. Checks if user is authenticated (via localStorage)
 * 2. Manages which page/content is shown via "activePage" state
 * 3. Renders Sidebar + MainContent layout
 * 
 * State Flow:
 * - activePage: "create" | "strategies" | "help"
 * - When user clicks sidebar item, activePage changes
 * - MainContent renders different component based on activePage
 */
export default function DashboardPage() {
  // Which dashboard page is currently active
  const [activePage, setActivePage] = useState("create");
  
  // Logged-in user's email (from localStorage)
  const [userEmail, setUserEmail] = useState(null);
  
  // Navigation hook for redirects
  const navigate = useNavigate();
  
  /**
   * Auth Check on Mount
   * If no user in localStorage, redirect to login
   */
  useEffect(() => {
    const email = localStorage.getItem("userEmail");
    
    if (!email) {
      navigate("/login");
    } else {
      setUserEmail(email);
    }
  }, [navigate]);
  
  /**
   * Handle Logout
   * Clear localStorage and redirect to login
   */
  const handleLogout = () => {
    localStorage.removeItem("userEmail");
    navigate("/login");
  };
  
  /**
   * Handle Page Change
   * Called when user clicks a sidebar menu item
   */
  const handlePageChange = (pageId) => {
    setActivePage(pageId);
  };
  
  /**
   * Render Content Based on Active Page
   * Returns the appropriate content component
   */
  const renderContent = () => {
    switch (activePage) {
      case "create":
        return <CreateStrategyContent />;
      case "strategies":
        return <MyStrategiesContent />;
      case "help":
        return <HelpContent />;
      default:
        return <CreateStrategyContent />;
    }
  };
  
  // Don't render until auth check completes
  if (!userEmail) {
    return null;
  }
  
  return (
    <div className="min-h-screen bg-background" data-testid="dashboard-page">
      {/* Sidebar Navigation (Fixed Left) */}
      <Sidebar
        activePage={activePage}
        onPageChange={handlePageChange}
        userEmail={userEmail}
        onLogout={handleLogout}
      />
      
      {/* Main Content Area (Right of Sidebar) */}
      <main 
        className="ml-64 min-h-screen p-8"
        data-testid="dashboard-main-content"
      >
        <div className="max-w-5xl">
          {renderContent()}
        </div>
        
        {/* Footer */}
        <div className="max-w-5xl mt-12 pt-8 border-t border-border">
          <div className="flex items-center justify-between">
            <span className="mono-label">
              // TEXT2TRADE v0.2.0
            </span>
            <span className="mono-label">
              UI PLACEHOLDER - NO TRADING LOGIC
            </span>
          </div>
        </div>
      </main>
    </div>
  );
}
