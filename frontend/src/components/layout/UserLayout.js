import { useState, useEffect, useCallback } from "react";
import { Link, useLocation, Outlet } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { useApi } from "@/hooks/useApi";
import { Button } from "@/components/ui/button";
import OnboardingTour from "@/components/OnboardingTour";
import {
  LayoutDashboard, Hammer, BookOpen, Activity, LogOut, Menu, X,
  TrendingUp, User as UserIcon, Search, Zap, Bookmark, BarChart3, Bell,
  ToggleLeft, ToggleRight, RefreshCw,
} from "lucide-react";

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/build", label: "Build Strategy", icon: Hammer },
  { to: "/screener", label: "Screener", icon: Search },
  { to: "/optimizer", label: "Optimizer", icon: Zap },
  { to: "/tracker", label: "Tracker", icon: BarChart3 },
  { to: "/alerts", label: "Alerts", icon: Bell, badge: true },
  { to: "/watchlist", label: "Watchlist", icon: Bookmark },
  { to: "/templates", label: "Templates", icon: BookOpen },
  { to: "/paper-trades", label: "Paper Trades", icon: Activity },
];

export default function UserLayout() {
  const { user, logout, isAdmin, isDemo, switchMode } = useAuth();
  const location = useLocation();
  const api = useApi();
  const [open, setOpen] = useState(false);
  const [unreadAlerts, setUnreadAlerts] = useState(0);
  const [runTour, setRunTour] = useState(false);
  const [demoCapital, setDemoCapital] = useState(null);
  const [switching, setSwitching] = useState(false);

  const fetchSidebarData = useCallback(() => {
    api.get("/alerts/notifications")
      .then((res) => setUnreadAlerts(res.data.unread || 0))
      .catch(() => {});
    if (isDemo) {
      api.get("/account/profile")
        .then((res) => setDemoCapital(res.data.demo_capital))
        .catch(() => {});
    }
  }, [api, isDemo]);

  useEffect(() => {
    fetchSidebarData();
  }, [location.pathname, fetchSidebarData]);

  // Check onboarding status on mount
  useEffect(() => {
    if (isDemo) {
      api.get("/account/profile")
        .then((res) => {
          if (!res.data.has_completed_onboarding) {
            setTimeout(() => setRunTour(true), 800);
          }
        })
        .catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleModeSwitch = async () => {
    setSwitching(true);
    try {
      const newMode = isDemo ? "real" : "demo";
      await switchMode(newMode);
      window.location.reload();
    } catch {
      setSwitching(false);
    }
  };

  const handleRestartTour = () => setRunTour(true);

  const sidebar = (
    <>
      {/* Logo */}
      <div className="flex items-center gap-2 px-4 py-5 border-b border-border">
        <TrendingUp className="w-5 h-5 text-primary" />
        <span className="font-mono font-bold text-foreground text-sm">Text2trade</span>
      </div>

      {/* Demo capital badge */}
      {isDemo && demoCapital && (
        <div className="mx-3 mt-3 px-3 py-2 border border-primary/30 bg-primary/5" data-testid="demo-mode-badge">
          <p className="text-[9px] text-primary font-mono font-bold uppercase tracking-wider">Demo Capital</p>
          <p className="text-sm font-mono font-bold text-foreground tabular-nums mt-0.5">
            {"\u20B9"}{demoCapital.current_capital?.toLocaleString("en-IN")}
          </p>
          <p className="text-[9px] text-muted-foreground font-mono mt-0.5">
            {demoCapital.trades_made} trades made
          </p>
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 py-3 overflow-y-auto">
        {NAV.map((n) => {
          const active = location.pathname === n.to || (n.to !== "/dashboard" && location.pathname.startsWith(n.to));
          return (
            <Link
              key={n.to}
              to={n.to}
              onClick={() => setOpen(false)}
              className={`flex items-center gap-3 px-3 py-2.5 text-sm font-mono transition-colors ${active ? "bg-primary/15 text-primary" : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"}`}
              data-testid={`nav-${n.label.toLowerCase().replace(/\s+/g, "-")}`}
            >
              <n.icon className="w-4 h-4" />
              <span className="flex-1">{n.label}</span>
              {n.badge && unreadAlerts > 0 && (
                <span className="bg-destructive text-destructive-foreground text-[9px] font-mono font-bold px-1.5 py-0.5 leading-none" data-testid="alerts-badge">
                  {unreadAlerts}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-border px-3 py-3 space-y-2">
        {/* Mode toggle */}
        <button
          onClick={handleModeSwitch}
          disabled={switching}
          className="flex items-center gap-2 w-full px-2 py-1.5 text-[10px] font-mono text-muted-foreground hover:text-foreground transition-colors"
          data-testid="mode-toggle-btn"
        >
          {isDemo ? <ToggleRight className="w-4 h-4 text-primary" /> : <ToggleLeft className="w-4 h-4" />}
          <span>{switching ? "Switching..." : isDemo ? "Demo Mode" : "Real Mode"}</span>
          <span className={`ml-auto w-2 h-2 rounded-full ${isDemo ? "bg-primary" : "bg-blue-500"}`} />
        </button>

        {/* Restart tour */}
        {isDemo && (
          <button
            onClick={handleRestartTour}
            className="flex items-center gap-2 w-full px-2 py-1.5 text-[10px] font-mono text-muted-foreground hover:text-foreground transition-colors"
            data-testid="restart-tour-btn"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Restart Tour
          </button>
        )}

        {/* User info */}
        <div className="flex items-center gap-2 px-2 py-1">
          <UserIcon className="w-3.5 h-3.5 text-muted-foreground" />
          <span className="text-[10px] font-mono text-muted-foreground truncate flex-1">{user?.email}</span>
          {isAdmin && (
            <Link to="/admin" className="text-[9px] font-mono text-primary hover:underline">Admin</Link>
          )}
        </div>

        <Button variant="ghost" size="sm" onClick={logout} className="w-full justify-start font-mono text-xs text-muted-foreground hover:text-destructive gap-2" data-testid="logout-btn">
          <LogOut className="w-3.5 h-3.5" /> Logout
        </Button>
      </div>
    </>
  );

  return (
    <div className="min-h-screen bg-background flex">
      {/* Tour */}
      <OnboardingTour run={runTour} onComplete={() => setRunTour(false)} />

      {/* Demo banner */}
      {isDemo && (
        <div className="fixed top-0 left-0 right-0 z-50 bg-primary/10 border-b border-primary/20 px-4 py-1.5 flex items-center justify-center gap-3" data-testid="demo-banner">
          <span className="text-[10px] font-mono text-primary font-bold">DEMO MODE</span>
          <span className="text-[10px] font-mono text-muted-foreground">
            {"\u20B9"}{demoCapital?.current_capital?.toLocaleString("en-IN") || "10,000"} virtual capital
          </span>
          <button
            onClick={handleModeSwitch}
            className="text-[10px] font-mono text-primary hover:underline font-bold"
            data-testid="demo-banner-switch"
          >
            Switch to Real
          </button>
        </div>
      )}

      {/* Desktop sidebar */}
      <aside className={`hidden md:flex flex-col w-56 border-r border-border bg-card fixed h-full ${isDemo ? "top-7" : "top-0"}`} style={isDemo ? { height: "calc(100vh - 28px)" } : {}}>
        {sidebar}
      </aside>

      {/* Mobile header */}
      <div className={`md:hidden fixed ${isDemo ? "top-7" : "top-0"} left-0 right-0 z-40 bg-card border-b border-border px-4 py-3 flex items-center justify-between`}>
        <div className="flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-primary" />
          <span className="font-mono font-bold text-sm text-foreground">Text2trade</span>
        </div>
        <Button variant="ghost" size="icon" onClick={() => setOpen(!open)} data-testid="mobile-menu-btn">
          {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </Button>
      </div>

      {/* Mobile drawer */}
      {open && (
        <div className={`md:hidden fixed inset-0 z-50 ${isDemo ? "top-7" : ""}`}>
          <div className="absolute inset-0 bg-black/50" onClick={() => setOpen(false)} />
          <aside className="absolute left-0 top-0 bottom-0 w-64 bg-card border-r border-border flex flex-col">
            {sidebar}
          </aside>
        </div>
      )}

      {/* Main content */}
      <main className={`flex-1 md:ml-56 ${isDemo ? "pt-7" : ""}`}>
        <div className={`p-4 sm:p-6 lg:p-8 ${isDemo ? "" : "md:pt-6"} pt-16 md:pt-6`}>
          <Outlet />
        </div>
      </main>
    </div>
  );
}
