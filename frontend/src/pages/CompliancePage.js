import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Shield, CheckCircle2, AlertTriangle, Clock, ExternalLink,
  ArrowLeft, Server, FileText, Lock, Activity, Eye,
} from "lucide-react";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL + "/api/v1";

function StatusBadge({ ok, label }) {
  return (
    <div className={`flex items-center gap-1.5 px-2.5 py-1 border text-[11px] font-mono ${
      ok ? "bg-primary/10 border-primary/30 text-primary" : "bg-amber-500/10 border-amber-500/30 text-amber-400"
    }`}>
      {ok ? <CheckCircle2 className="w-3 h-3" /> : <Clock className="w-3 h-3" />}
      {label}
    </div>
  );
}

export default function CompliancePage() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    document.title = "Compliance | Text2trade";
    axios.get(`${API}/compliance/status`)
      .then((r) => setStatus(r.data))
      .catch((e) => console.error("Failed to load compliance status", e))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="w-5 h-5 border-2 border-primary border-t-transparent animate-spin rounded-full" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background" data-testid="compliance-page">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <Link to="/">
            <Button variant="ghost" size="icon" className="h-8 w-8" data-testid="compliance-back-btn">
              <ArrowLeft className="w-4 h-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold tracking-tight font-mono flex items-center gap-2">
              <Shield className="w-5 h-5 text-primary" /> Compliance
            </h1>
            <p className="text-sm text-muted-foreground mt-0.5">SEBI Retail Algo Trading Framework 2025-26</p>
          </div>
        </div>

        {/* Circular Reference */}
        <Card className="border-border bg-card mb-6" data-testid="sebi-reference-card">
          <CardContent className="p-4">
            <p className="text-[11px] font-mono text-muted-foreground">
              Reference: <span className="text-foreground">{status?.circular}</span>
            </p>
            <p className="text-[11px] font-mono text-muted-foreground mt-1">
              Status: <span className={status?.compliance_status === "full" ? "text-primary" : "text-amber-400"}>
                {status?.compliance_status?.toUpperCase()}
              </span>
            </p>
          </CardContent>
        </Card>

        {/* Current Compliance */}
        <h2 className="text-sm font-mono font-bold text-foreground mb-3 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-primary" /> Currently Compliant
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-8">
          <Card className="border-primary/20 bg-card">
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-2">
                <FileText className="w-4 h-4 text-primary" />
                <h3 className="text-xs font-mono font-bold">Audit Trail</h3>
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                All user actions are logged with immutable, write-only entries. Data retained for 5+ years.
                Every entry includes user ID, IP address, user-agent, and UTC timestamps with millisecond precision.
              </p>
              <StatusBadge ok label="Active" />
            </CardContent>
          </Card>
          <Card className="border-primary/20 bg-card">
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-2">
                <Eye className="w-4 h-4 text-primary" />
                <h3 className="text-xs font-mono font-bold">White-Box Strategies</h3>
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                All strategies are white-box with full logic disclosure. Users create and inspect every condition,
                indicator parameter, and risk control. No hidden or black-box algorithms.
              </p>
              <StatusBadge ok label="All strategies transparent" />
            </CardContent>
          </Card>
          <Card className="border-primary/20 bg-card">
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-2">
                <Lock className="w-4 h-4 text-primary" />
                <h3 className="text-xs font-mono font-bold">Data Security</h3>
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                Encrypted password storage (bcrypt), JWT authentication, input sanitization (XSS stripping),
                rate limiting, and request body size limits.
              </p>
              <StatusBadge ok label="Secured" />
            </CardContent>
          </Card>
          <Card className="border-primary/20 bg-card">
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-2">
                <Activity className="w-4 h-4 text-primary" />
                <h3 className="text-xs font-mono font-bold">OPS Monitoring</h3>
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                Orders-per-second tracked per user. SEBI threshold of 10 OPS enforced.
                Strategies exceeding threshold flagged for exchange registration.
              </p>
              <StatusBadge ok label="Monitoring active" />
            </CardContent>
          </Card>
        </div>

        {/* Phase 2 */}
        <h2 className="text-sm font-mono font-bold text-foreground mb-3 flex items-center gap-2">
          <Clock className="w-4 h-4 text-amber-400" /> Phase 2 — Before Live Execution
        </h2>
        <Card className="border-amber-500/20 bg-card mb-8" data-testid="phase2-card">
          <CardContent className="p-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {[
                "Exchange-assigned Algo-IDs for every strategy",
                "Static IP infrastructure for API trading",
                "Broker OAuth integration with 2FA (Zerodha, Angel One, Upstox, Dhan)",
                "Daily session auto-logout before market pre-open",
                "Formal empanelment with stock exchanges",
                "Broker partnership with due diligence",
              ].map((item) => (
                <div key={item} className="flex items-start gap-2 text-[11px] font-mono text-muted-foreground p-1.5">
                  <AlertTriangle className="w-3 h-3 text-amber-400 mt-0.5 shrink-0" />
                  {item}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Hosting & Contact */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-8">
          <Card className="border-border bg-card" data-testid="hosting-card">
            <CardHeader className="pb-2">
              <CardTitle className="text-xs font-mono flex items-center gap-2">
                <Server className="w-3.5 h-3.5 text-primary" /> Hosting Region
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-[11px] font-mono text-foreground">{status?.hosting_region || "unknown"}</p>
              {status?.hosting_migration_required && (
                <p className="text-[10px] text-amber-400 mt-1">Migration to Indian servers required before live trading</p>
              )}
            </CardContent>
          </Card>
          <Card className="border-border bg-card">
            <CardHeader className="pb-2">
              <CardTitle className="text-xs font-mono flex items-center gap-2">
                <Shield className="w-3.5 h-3.5 text-primary" /> Live Trading
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-[11px] font-mono text-foreground">{status?.live_trading?.replace(/_/g, " ")}</p>
              <p className="text-[10px] text-muted-foreground mt-1">
                Backtesting and paper trading are fully operational. No live market orders are placed.
              </p>
            </CardContent>
          </Card>
        </div>

        <p className="text-[10px] text-muted-foreground text-center">{status?.note}</p>

        {/* Link to Benchmarks */}
        <div className="mt-6 text-center">
          <Link to="/benchmarks">
            <Button variant="outline" size="sm" className="text-xs font-mono h-8 gap-1.5" data-testid="compliance-benchmarks-link">
              <Activity className="w-3 h-3" /> View Engine Benchmarks
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
