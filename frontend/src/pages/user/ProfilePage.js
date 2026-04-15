import { useState, useEffect } from "react";
import { useApi } from "@/hooks/useApi";
import { useAuth } from "@/context/AuthContext";
import { extractApiError } from "@/utils/apiError";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  User, Lock, Settings, Bell, Shield, Link2, Info,
  Save, AlertTriangle, Download, Trash2, RefreshCw, LogOut, ChevronRight,
  FileText, ExternalLink,
} from "lucide-react";
import { PageSkeleton } from "@/components/LoadingSkeleton";
import { toast } from "sonner";

const TIMEZONES = [
  "Asia/Kolkata", "Asia/Tokyo", "Asia/Shanghai", "Asia/Singapore", "Asia/Dubai",
  "Europe/London", "Europe/Berlin", "Europe/Paris", "America/New_York",
  "America/Chicago", "America/Los_Angeles", "America/Sao_Paulo",
  "Australia/Sydney", "Pacific/Auckland", "UTC",
];

const INTEGRATIONS = [
  { name: "Zerodha", desc: "Connect your Zerodha Kite account for live trading" },
  { name: "Angel One", desc: "Connect Angel One SmartAPI for automated execution" },
  { name: "Upstox", desc: "Link Upstox account for order placement" },
];

function Section({ id, title, icon: Icon, children }) {
  return (
    <div id={id} data-testid={`profile-section-${id}`}>
      <div className="flex items-center gap-2 mb-3">
        <Icon className="w-4 h-4 text-primary" />
        <h2 className="mono-label text-[10px]">{title}</h2>
      </div>
      <Card className="border-border bg-card">
        <CardContent className="p-4 sm:p-5">{children}</CardContent>
      </Card>
    </div>
  );
}

export default function ProfilePage() {
  const api = useApi();
  const { user, logout, isDemo, switchMode } = useAuth();
  const [profile, setProfile] = useState(null);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  // Editable fields
  const [displayName, setDisplayName] = useState("");
  const [phone, setPhone] = useState("");
  const [tz, setTz] = useState("Asia/Kolkata");
  const [capital, setCapital] = useState(100000);
  const [instruments, setInstruments] = useState("");
  const [notifPrefs, setNotifPrefs] = useState({});
  const [saving, setSaving] = useState(false);

  // Password change
  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [changingPw, setChangingPw] = useState(false);

  // Account delete
  const [showDelete, setShowDelete] = useState(false);
  const [deletePw, setDeletePw] = useState("");
  const [deleting, setDeleting] = useState(false);

  // Export
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    document.title = "Profile & Settings | Text2trade";
    Promise.all([
      api.get("/account/profile"),
      api.get("/account/summary"),
    ]).then(([pRes, sRes]) => {
      const p = pRes.data;
      setProfile(p);
      setSummary(sRes.data);
      setDisplayName(p.display_name || "");
      setPhone(p.phone || "");
      setTz(p.timezone || "Asia/Kolkata");
      setCapital(p.default_capital || 100000);
      setInstruments((p.preferred_instruments || []).join(", "));
      setNotifPrefs(p.notification_preferences || {});
    }).catch(() => toast.error("Failed to load profile"))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSaveProfile = async () => {
    setSaving(true);
    try {
      const instrArr = instruments.split(",").map(s => s.trim()).filter(Boolean);
      await api.put("/account/profile", {
        display_name: displayName,
        phone,
        timezone: tz,
        default_capital: parseFloat(capital) || 100000,
        preferred_instruments: instrArr,
        notification_preferences: notifPrefs,
      });
      toast.success("Profile updated");
    } catch (err) {
      toast.error(extractApiError(err, "Update failed"));
    } finally { setSaving(false); }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    if (newPw !== confirmPw) { toast.error("Passwords don't match"); return; }
    setChangingPw(true);
    try {
      await api.put("/profile/change-password", {
        current_password: currentPw,
        new_password: newPw,
      });
      toast.success("Password changed");
      setCurrentPw(""); setNewPw(""); setConfirmPw("");
    } catch (err) {
      toast.error(extractApiError(err, "Password change failed"));
    } finally { setChangingPw(false); }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const res = await api.post("/account/export-data");
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `text2trade_export_${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Data exported");
    } catch {
      toast.error("Export failed");
    } finally { setExporting(false); }
  };

  const handleDelete = async () => {
    if (!deletePw) { toast.error("Enter your password to confirm"); return; }
    setDeleting(true);
    try {
      await api.del("/account", { data: { password: deletePw } });
      toast.success("Account deactivated");
      setTimeout(() => logout(), 1500);
    } catch (err) {
      toast.error(extractApiError(err, "Deletion failed"));
    } finally { setDeleting(false); }
  };

  const handleModeSwitch = async () => {
    try {
      await switchMode(isDemo ? "real" : "demo");
      window.location.reload();
    } catch { toast.error("Mode switch failed"); }
  };

  const handleRestartTour = async () => {
    try {
      await api.post("/account/restart-tour");
      toast.success("Tour restarted. Navigate to Dashboard to begin.");
    } catch { toast.error("Failed"); }
  };

  if (loading) return <PageSkeleton />;

  return (
    <div className="space-y-6 max-w-2xl" data-testid="profile-page">
      {/* Header */}
      <div className="flex items-center gap-4">
        <div className="w-12 h-12 bg-primary/15 border border-primary/30 flex items-center justify-center font-mono font-bold text-lg text-primary" data-testid="profile-avatar">
          {profile?.avatar_initial || "?"}
        </div>
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-foreground">{profile?.display_name || profile?.email}</h1>
          <p className="text-xs text-muted-foreground font-mono">{profile?.email} &middot; Member since {profile?.created_at?.slice(0, 10)}</p>
        </div>
      </div>

      {/* Personal Info */}
      <Section id="personal" title="PERSONAL INFO" icon={User}>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="text-[10px] text-muted-foreground font-mono block mb-1">DISPLAY NAME</label>
            <Input value={displayName} onChange={(e) => setDisplayName(e.target.value)} maxLength={50}
              className="font-mono text-sm" placeholder="Your name" data-testid="input-display-name" />
          </div>
          <div>
            <label className="text-[10px] text-muted-foreground font-mono block mb-1">EMAIL (read-only)</label>
            <Input value={profile?.email || ""} disabled className="font-mono text-sm opacity-60" data-testid="input-email" />
          </div>
          <div>
            <label className="text-[10px] text-muted-foreground font-mono block mb-1">PHONE (optional)</label>
            <Input value={phone} onChange={(e) => setPhone(e.target.value)} maxLength={20}
              className="font-mono text-sm" placeholder="+91 9876543210" data-testid="input-phone" />
          </div>
          <div>
            <label className="text-[10px] text-muted-foreground font-mono block mb-1">MEMBER SINCE</label>
            <Input value={profile?.created_at?.slice(0, 10) || ""} disabled className="font-mono text-sm opacity-60" />
          </div>
        </div>
      </Section>

      {/* Password */}
      <Section id="password" title="PASSWORD" icon={Lock}>
        <form onSubmit={handleChangePassword} className="space-y-3 max-w-sm">
          <div>
            <label className="text-[10px] text-muted-foreground font-mono block mb-1">CURRENT PASSWORD</label>
            <Input type="password" value={currentPw} onChange={(e) => setCurrentPw(e.target.value)}
              className="font-mono text-sm" data-testid="input-current-password" />
          </div>
          <div>
            <label className="text-[10px] text-muted-foreground font-mono block mb-1">NEW PASSWORD</label>
            <Input type="password" value={newPw} onChange={(e) => setNewPw(e.target.value)}
              className="font-mono text-sm" placeholder="Min 8 characters" data-testid="input-new-password" />
          </div>
          <div>
            <label className="text-[10px] text-muted-foreground font-mono block mb-1">CONFIRM NEW PASSWORD</label>
            <Input type="password" value={confirmPw} onChange={(e) => setConfirmPw(e.target.value)}
              className="font-mono text-sm" data-testid="input-confirm-password" />
          </div>
          <Button type="submit" size="sm" disabled={changingPw} className="font-mono text-[10px] uppercase gap-1.5" data-testid="change-password-btn">
            <Lock className="w-3 h-3" /> {changingPw ? "Changing..." : "Change Password"}
          </Button>
        </form>
      </Section>

      {/* Preferences */}
      <Section id="preferences" title="PREFERENCES" icon={Settings}>
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-[10px] text-muted-foreground font-mono block mb-1">TIMEZONE</label>
              <Select value={tz} onValueChange={setTz}>
                <SelectTrigger className="font-mono text-xs" data-testid="select-timezone">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TIMEZONES.map((t) => <SelectItem key={t} value={t} className="font-mono text-xs">{t}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-[10px] text-muted-foreground font-mono block mb-1">DEFAULT CAPITAL</label>
              <Input type="number" value={capital} onChange={(e) => setCapital(e.target.value)}
                className="font-mono text-sm" data-testid="input-default-capital" />
            </div>
          </div>
          <div>
            <label className="text-[10px] text-muted-foreground font-mono block mb-1">PREFERRED INSTRUMENTS (comma-separated)</label>
            <Input value={instruments} onChange={(e) => setInstruments(e.target.value)}
              className="font-mono text-sm" placeholder="RELIANCE, TCS, INFY" data-testid="input-instruments" />
          </div>
        </div>
      </Section>

      {/* Notifications */}
      <Section id="notifications" title="NOTIFICATIONS" icon={Bell}>
        <div className="space-y-3">
          {[
            { key: "email_on_backtest_complete", label: "Email when backtest completes" },
            { key: "email_on_paper_trade_signal", label: "Email on paper trade signals" },
            { key: "email_weekly_summary", label: "Weekly performance summary" },
          ].map((n) => (
            <div key={n.key} className="flex items-center justify-between py-1">
              <span className="text-xs font-mono text-foreground">{n.label}</span>
              <Switch
                checked={!!notifPrefs[n.key]}
                onCheckedChange={(v) => setNotifPrefs((p) => ({ ...p, [n.key]: v }))}
                data-testid={`toggle-${n.key}`}
              />
            </div>
          ))}
          <p className="text-[9px] text-muted-foreground font-mono mt-2">
            Email notifications will be enabled in a future update. Preferences are saved for when they go live.
          </p>
        </div>
      </Section>

      {/* Save All */}
      <Button onClick={handleSaveProfile} disabled={saving} className="font-mono text-xs uppercase gap-1.5" data-testid="save-profile-btn">
        <Save className="w-3 h-3" /> {saving ? "Saving..." : "Save Profile"}
      </Button>

      {/* Account */}
      <Section id="account" title="ACCOUNT" icon={Shield}>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-mono text-foreground">Account Mode</p>
              <p className="text-[10px] text-muted-foreground font-mono mt-0.5">
                {isDemo ? "Demo Mode — virtual capital, sample strategies" : "Real Mode — your strategies and data"}
              </p>
            </div>
            <Button variant="outline" size="sm" onClick={handleModeSwitch} className="font-mono text-[10px] gap-1.5" data-testid="profile-mode-switch">
              {isDemo ? "Switch to Real" : "Switch to Demo"}
            </Button>
          </div>

          {summary && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 py-2 border-t border-border pt-3">
              <div><p className="text-[9px] text-muted-foreground font-mono">Real Strategies</p><p className="font-mono font-bold text-sm">{summary.total_strategies_real}</p></div>
              <div><p className="text-[9px] text-muted-foreground font-mono">Demo Strategies</p><p className="font-mono font-bold text-sm">{summary.total_strategies_demo}</p></div>
              <div><p className="text-[9px] text-muted-foreground font-mono">Backtests</p><p className="font-mono font-bold text-sm">{summary.total_backtests}</p></div>
              <div><p className="text-[9px] text-muted-foreground font-mono">Paper Trades</p><p className="font-mono font-bold text-sm">{summary.total_paper_trades}</p></div>
            </div>
          )}

          <div className="flex items-center gap-3 pt-2 border-t border-border">
            <Button variant="outline" size="sm" onClick={handleExport} disabled={exporting} className="font-mono text-[10px] gap-1.5" data-testid="export-data-btn">
              <Download className="w-3 h-3" /> {exporting ? "Exporting..." : "Export My Data"}
            </Button>
          </div>

          {/* Danger Zone */}
          <div className="pt-3 border-t border-destructive/30">
            <button
              onClick={() => setShowDelete(!showDelete)}
              className="flex items-center gap-2 text-[10px] font-mono text-destructive hover:underline"
              data-testid="delete-account-toggle"
            >
              <AlertTriangle className="w-3 h-3" />
              {showDelete ? "Cancel" : "Delete Account"}
            </button>
            {showDelete && (
              <div className="mt-3 p-3 border border-destructive/30 bg-destructive/5 space-y-2">
                <p className="text-[10px] text-destructive font-mono">This will deactivate your account. Your data will be preserved but you won't be able to log in.</p>
                <Input type="password" value={deletePw} onChange={(e) => setDeletePw(e.target.value)}
                  placeholder="Enter password to confirm" className="font-mono text-xs max-w-xs" data-testid="delete-password-input" />
                <Button variant="destructive" size="sm" onClick={handleDelete} disabled={deleting}
                  className="font-mono text-[10px] uppercase gap-1.5" data-testid="confirm-delete-btn">
                  <Trash2 className="w-3 h-3" /> {deleting ? "Deleting..." : "Confirm Delete"}
                </Button>
              </div>
            )}
          </div>
        </div>
      </Section>

      {/* Integrations (Phase 2 Placeholder) */}
      <Section id="integrations" title="INTEGRATIONS" icon={Link2}>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {INTEGRATIONS.map((itg) => (
            <div key={itg.name} className="p-3 border border-border bg-secondary/20 opacity-60 cursor-not-allowed" data-testid={`integration-${itg.name.toLowerCase().replace(/\s+/g, "-")}`}>
              <div className="flex items-center justify-between mb-1">
                <span className="font-mono font-bold text-xs text-foreground">{itg.name}</span>
                <Badge variant="outline" className="text-[8px] font-mono h-4">Coming Soon</Badge>
              </div>
              <p className="text-[9px] text-muted-foreground font-mono">{itg.desc}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* App */}
      <Section id="app" title="APP" icon={Info}>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-foreground">Restart Onboarding Tour</span>
            <Button variant="outline" size="sm" onClick={handleRestartTour} className="font-mono text-[10px] gap-1.5" data-testid="restart-tour-profile-btn">
              <RefreshCw className="w-3 h-3" /> Restart Tour
            </Button>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-foreground">App Version</span>
            <span className="text-[10px] font-mono text-muted-foreground" data-testid="profile-version">v{process.env.REACT_APP_VERSION || "0.2.0"}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-foreground">Report a Bug</span>
            <a href="mailto:support@text2trade.com" className="text-[10px] font-mono text-primary hover:underline" data-testid="report-bug-link">
              support@text2trade.com
            </a>
          </div>
        </div>
      </Section>

      {/* Regulatory Information */}
      <Section icon={FileText} title="Regulatory Information" testId="regulatory-section">
        <div className="space-y-3">
          <p className="text-[11px] text-muted-foreground leading-relaxed">
            This platform complies with SEBI's Algo Trading Framework (2025-26).
          </p>
          <div className="space-y-2 text-[11px] text-muted-foreground">
            <div className="flex items-start gap-2">
              <span className="text-primary mt-0.5">&#8226;</span>
              <span>Your strategies are classified as <span className="text-foreground font-bold">white-box</span> — all logic is fully visible to you.</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-primary mt-0.5">&#8226;</span>
              <span>Backtesting and paper trading do not require exchange registration.</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-amber-400 mt-0.5">&#8226;</span>
              <span>Live execution (coming in Phase 2) will require: your own broker account (Zerodha, Angel One, Upstox, or Dhan), static IP configuration, and an exchange-assigned Algo-ID for your strategy.</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-primary mt-0.5">&#8226;</span>
              <span>All your activity is logged for regulatory compliance (5-year retention).</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-primary mt-0.5">&#8226;</span>
              <span>We do not execute trades on your behalf. All execution happens through YOUR broker.</span>
            </div>
          </div>
          <a
            href="/compliance"
            className="inline-flex items-center gap-1 text-[10px] font-mono text-primary hover:underline"
            data-testid="view-compliance-link"
          >
            View SEBI Compliance Details <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </Section>

      {/* Logout */}
      <Button variant="outline" onClick={logout} className="font-mono text-xs gap-2 text-destructive border-destructive/30 hover:bg-destructive/10" data-testid="profile-logout-btn">
        <LogOut className="w-3.5 h-3.5" /> Logout
      </Button>
    </div>
  );
}
