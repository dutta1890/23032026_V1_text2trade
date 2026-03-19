import { useState } from "react";
import { Link, useLocation, Outlet } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { Button } from "@/components/ui/button";
import { LayoutDashboard, Users, LogOut, Menu, X, ArrowLeft, Shield } from "lucide-react";

const NAV = [
  { to: "/admin/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/admin/users", label: "Users", icon: Users },
];

export default function AdminLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [open, setOpen] = useState(false);

  return (
    <div className="min-h-screen bg-background flex" data-testid="admin-layout">
      <aside className={`fixed inset-y-0 left-0 z-40 w-56 bg-card border-r border-border flex flex-col transition-transform lg:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="p-4 border-b border-border">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-destructive" />
            <span className="font-mono font-bold text-foreground text-sm tracking-wide">ADMIN</span>
          </div>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {NAV.map((n) => {
            const active = location.pathname === n.to;
            return (
              <Link
                key={n.to}
                to={n.to}
                onClick={() => setOpen(false)}
                className={`flex items-center gap-3 px-3 py-2.5 text-sm font-mono transition-colors ${active ? "bg-primary/15 text-primary" : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"}`}
                data-testid={`admin-nav-${n.label.toLowerCase()}`}
              >
                <n.icon className="w-4 h-4" />
                {n.label}
              </Link>
            );
          })}
        </nav>
        <div className="p-3 border-t border-border space-y-2">
          <Link
            to="/dashboard"
            className="flex items-center gap-3 px-3 py-2 text-xs font-mono text-muted-foreground hover:text-foreground"
            onClick={() => setOpen(false)}
            data-testid="admin-back-to-app"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to App
          </Link>
          <div className="flex items-center justify-between px-3">
            <span className="text-[10px] font-mono text-muted-foreground truncate">{user?.email}</span>
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={logout} data-testid="admin-logout-btn">
              <LogOut className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>
      </aside>
      {open && <div className="fixed inset-0 bg-black/50 z-30 lg:hidden" onClick={() => setOpen(false)} />}
      <div className="flex-1 lg:ml-56">
        <header className="sticky top-0 z-20 bg-card border-b border-border px-4 py-3 flex items-center justify-between lg:hidden">
          <button onClick={() => setOpen(!open)} data-testid="admin-mobile-menu">
            {open ? <X className="w-5 h-5 text-foreground" /> : <Menu className="w-5 h-5 text-foreground" />}
          </button>
          <span className="font-mono font-bold text-foreground text-sm">ADMIN PANEL</span>
          <span className="w-5" />
        </header>
        <main className="p-4 sm:p-6 lg:p-8 max-w-7xl">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
