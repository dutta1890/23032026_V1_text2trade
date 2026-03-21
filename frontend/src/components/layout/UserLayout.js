import { useState } from "react";
import { Link, useLocation, Outlet } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { Button } from "@/components/ui/button";
import {
  LayoutDashboard, Hammer, BookOpen, Activity, LogOut, Menu, X,
  TrendingUp, User as UserIcon, Search, Zap
} from "lucide-react";

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/build", label: "Build Strategy", icon: Hammer },
  { to: "/screener", label: "Screener", icon: Search },
  { to: "/optimizer", label: "Optimizer", icon: Zap },
  { to: "/templates", label: "Templates", icon: BookOpen },
  { to: "/paper-trades", label: "Paper Trades", icon: Activity },
];

export default function UserLayout() {
  const { user, logout, isAdmin } = useAuth();
  const location = useLocation();
  const [open, setOpen] = useState(false);

  return (
    <div className="min-h-screen bg-background flex" data-testid="user-layout">
      {/* Sidebar */}
      <aside className={`fixed inset-y-0 left-0 z-40 w-56 bg-card border-r border-border flex flex-col transition-transform lg:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="p-4 border-b border-border">
          <Link to="/dashboard" className="flex items-center gap-2" onClick={() => setOpen(false)}>
            <TrendingUp className="w-5 h-5 text-primary" />
            <span className="font-mono font-bold text-foreground text-sm tracking-wide">TEXT2TRADE</span>
          </Link>
        </div>
        <nav className="flex-1 p-3 space-y-1">
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
                {n.label}
              </Link>
            );
          })}
        </nav>
        <div className="p-3 border-t border-border space-y-2">
          {isAdmin && (
            <Link
              to="/admin/dashboard"
              className="flex items-center gap-3 px-3 py-2 text-xs font-mono text-muted-foreground hover:text-foreground"
              onClick={() => setOpen(false)}
              data-testid="nav-admin-panel"
            >
              <UserIcon className="w-3.5 h-3.5" /> Admin Panel
            </Link>
          )}
          <div className="flex items-center justify-between px-3">
            <span className="text-[10px] font-mono text-muted-foreground truncate">{user?.email}</span>
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={logout} data-testid="logout-btn">
              <LogOut className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>
      </aside>

      {/* Mobile overlay */}
      {open && <div className="fixed inset-0 bg-black/50 z-30 lg:hidden" onClick={() => setOpen(false)} />}

      {/* Main */}
      <div className="flex-1 lg:ml-56">
        {/* Mobile header */}
        <header className="sticky top-0 z-20 bg-card border-b border-border px-4 py-3 flex items-center justify-between lg:hidden">
          <button onClick={() => setOpen(!open)} data-testid="mobile-menu-btn">
            {open ? <X className="w-5 h-5 text-foreground" /> : <Menu className="w-5 h-5 text-foreground" />}
          </button>
          <span className="font-mono font-bold text-foreground text-sm">TEXT2TRADE</span>
          <span className="text-[10px] font-mono text-muted-foreground">{user?.email?.split("@")[0]}</span>
        </header>
        <main className="p-4 sm:p-6 lg:p-8 max-w-7xl">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
