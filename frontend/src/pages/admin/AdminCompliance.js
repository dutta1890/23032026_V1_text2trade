import { useState, useEffect, useCallback } from "react";
import { useApi } from "@/hooks/useApi";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Shield, Database, Activity, FileText, Download, Filter,
  ChevronLeft, ChevronRight, AlertTriangle, CheckCircle2,
} from "lucide-react";

const ACTION_TYPES = [
  "user_registered", "user_login", "user_logout",
  "strategy_created", "strategy_updated", "strategy_deleted",
  "backtest_run", "backtest_completed",
  "paper_trade_deployed", "paper_trade_signal", "paper_trade_closed",
  "session_started", "session_message", "session_finalized",
  "ai_call_made", "ai_response_received",
  "template_cloned", "profile_updated", "password_changed",
];

function StatCard({ label, value, icon: Icon, color = "text-primary", testId }) {
  return (
    <Card className="border-border bg-card" data-testid={testId}>
      <CardContent className="p-4 flex items-center gap-3">
        <div className={`p-2 rounded bg-secondary/50 ${color}`}>
          <Icon className="w-4 h-4" />
        </div>
        <div>
          <p className="text-[10px] font-mono text-muted-foreground uppercase">{label}</p>
          <p className="text-xl font-mono font-bold tabular-nums">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}

export default function AdminCompliance() {
  const api = useApi();
  const [status, setStatus] = useState(null);
  const [auditStats, setAuditStats] = useState(null);
  const [ops, setOps] = useState(null);
  const [classification, setClassification] = useState(null);
  const [trail, setTrail] = useState({ entries: [], total: 0, page: 1, pages: 1 });
  const [filters, setFilters] = useState({ action: "", user_id: "", start_date: "", end_date: "" });
  const [trailPage, setTrailPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);

  const loadDashboard = useCallback(async () => {
    try {
      const [sRes, aRes, oRes, cRes] = await Promise.all([
        api.get("/compliance/status"),
        api.get("/admin/compliance/audit-stats"),
        api.get("/admin/compliance/ops"),
        api.get("/admin/compliance/strategy-classification"),
      ]);
      setStatus(sRes.data);
      setAuditStats(aRes.data);
      setOps(oRes.data);
      setClassification(cRes.data);
    } catch (e) {
      console.error("Failed to load compliance dashboard", e);
    } finally {
      setLoading(false);
    }
  }, [api]);

  const loadTrail = useCallback(async (page = 1) => {
    const params = new URLSearchParams({ page, limit: 20 });
    if (filters.action) params.set("action", filters.action);
    if (filters.user_id) params.set("user_id", filters.user_id);
    if (filters.start_date) params.set("start_date", filters.start_date);
    if (filters.end_date) params.set("end_date", filters.end_date);
    try {
      const res = await api.get(`/admin/compliance/audit-trail?${params}`);
      setTrail(res.data);
      setTrailPage(page);
    } catch (e) {
      console.error("Failed to load audit trail", e);
    }
  }, [api, filters]);

  useEffect(() => { document.title = "Compliance | Admin"; loadDashboard(); }, [loadDashboard]);
  useEffect(() => { loadTrail(1); }, [loadTrail]);

  const exportCSV = async () => {
    setExporting(true);
    try {
      const params = new URLSearchParams();
      if (filters.start_date) params.set("start_date", filters.start_date);
      if (filters.end_date) params.set("end_date", filters.end_date);
      const res = await api.get(`/admin/compliance/audit-export?${params}`, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = `audit_trail_${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Export failed", e);
    } finally {
      setExporting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-5 h-5 border-2 border-primary border-t-transparent animate-spin rounded-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="admin-compliance-page">
      {/* SEBI Compliance Status */}
      <Card className="border-border bg-card" data-testid="compliance-status-card">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-mono flex items-center gap-2">
            <Shield className="w-4 h-4 text-primary" /> SEBI Compliance Status
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {status && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { label: "Framework", value: "SEBI 2025-26", ok: true },
                { label: "Audit Trail", value: status.audit_trail, ok: status.audit_trail === "active" },
                { label: "Live Trading", value: status.live_trading, ok: false },
                { label: "Strategy Type", value: status.strategy_type, ok: true },
                { label: "Data Retention", value: status.data_retention, ok: true },
                { label: "Algo Registration", value: status.algo_registration?.replace(/_/g, " "), ok: false },
                { label: "Static IP", value: status.static_ip?.replace(/_/g, " "), ok: false },
                { label: "Status", value: status.compliance_status, ok: false },
              ].map((item) => (
                <div key={item.label} className="p-2 bg-secondary/30 border border-border">
                  <div className="flex items-center gap-1.5 mb-0.5">
                    {item.ok ? (
                      <CheckCircle2 className="w-3 h-3 text-primary" />
                    ) : (
                      <AlertTriangle className="w-3 h-3 text-amber-400" />
                    )}
                    <p className="text-[9px] font-mono text-muted-foreground uppercase">{item.label}</p>
                  </div>
                  <p className="text-[11px] font-mono font-bold text-foreground">{item.value}</p>
                </div>
              ))}
            </div>
          )}
          <p className="text-[10px] text-muted-foreground">{status?.note}</p>
        </CardContent>
      </Card>

      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Total Audit Entries" value={auditStats?.total_entries?.toLocaleString() || "0"} icon={Database} testId="stat-total-audit" />
        <StatCard label="Entries Today" value={auditStats?.entries_today || 0} icon={Activity} testId="stat-today-audit" />
        <StatCard label="This Month" value={auditStats?.entries_this_month || 0} icon={FileText} testId="stat-month-audit" />
        <StatCard label="Retention" value={`${auditStats?.retention_years || 5} years`} icon={Shield} color="text-emerald-400" testId="stat-retention" />
      </div>

      {/* OPS + Classification Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <Card className="border-border bg-card" data-testid="ops-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-mono flex items-center gap-2">
              <Activity className="w-4 h-4 text-primary" /> OPS Monitoring
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between mb-2">
              <p className="text-[10px] font-mono text-muted-foreground">SEBI Threshold: {ops?.threshold} OPS</p>
              <p className="text-[10px] font-mono text-muted-foreground">Active Users: {ops?.total_active_users || 0}</p>
            </div>
            {ops?.users?.length > 0 ? (
              <div className="space-y-1">
                {ops.users.map((u) => (
                  <div key={u.user_id} className={`p-2 border text-[11px] font-mono flex justify-between ${u.above_threshold ? "border-destructive bg-destructive/10" : "border-border"}`}>
                    <span>{u.user_id.slice(0, 20)}...</span>
                    <span>{u.avg_ops} OPS ({u.total_orders_1h} orders/hr)</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-[11px] text-muted-foreground text-center py-4">No users with recent order activity</p>
            )}
          </CardContent>
        </Card>

        <Card className="border-border bg-card" data-testid="classification-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-mono flex items-center gap-2">
              <Shield className="w-4 h-4 text-primary" /> Strategy Classification
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-3">
              <div className="text-center p-3 bg-secondary/30 border border-border">
                <p className="text-2xl font-mono font-bold">{classification?.total || 0}</p>
                <p className="text-[9px] font-mono text-muted-foreground">TOTAL</p>
              </div>
              <div className="text-center p-3 bg-primary/10 border border-primary/30">
                <p className="text-2xl font-mono font-bold text-primary">{classification?.white_box || 0}</p>
                <p className="text-[9px] font-mono text-muted-foreground">WHITE BOX</p>
              </div>
              <div className="text-center p-3 bg-secondary/30 border border-border">
                <p className="text-2xl font-mono font-bold">{classification?.black_box || 0}</p>
                <p className="text-[9px] font-mono text-muted-foreground">BLACK BOX</p>
              </div>
            </div>
            <p className="text-[10px] text-muted-foreground mt-2">All strategies are white-box (full logic disclosed to users)</p>
          </CardContent>
        </Card>
      </div>

      {/* Action Breakdown */}
      {auditStats?.action_breakdown?.length > 0 && (
        <Card className="border-border bg-card" data-testid="action-breakdown-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-mono">Action Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {auditStats.action_breakdown.map((a) => (
                <div key={a.action} className="px-2.5 py-1.5 bg-secondary/40 border border-border text-[10px] font-mono">
                  <span className="text-foreground">{a.action}</span>
                  <span className="text-primary ml-1.5 font-bold">{a.count}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Audit Trail Table */}
      <Card className="border-border bg-card" data-testid="audit-trail-card">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-mono flex items-center gap-2">
              <FileText className="w-4 h-4 text-primary" /> Audit Trail ({trail.total} entries)
            </CardTitle>
            <Button size="sm" variant="outline" onClick={exportCSV} disabled={exporting} className="text-[10px] font-mono" data-testid="export-audit-btn">
              <Download className="w-3 h-3 mr-1" /> {exporting ? "Exporting..." : "Export CSV"}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {/* Filters */}
          <div className="flex flex-wrap gap-2 items-end" data-testid="audit-filters">
            <div className="w-48">
              <label className="text-[9px] font-mono text-muted-foreground block mb-1">ACTION TYPE</label>
              <Select value={filters.action || "all"} onValueChange={(v) => setFilters((p) => ({ ...p, action: v === "all" ? "" : v }))}>
                <SelectTrigger className="h-8 text-[11px] font-mono">
                  <SelectValue placeholder="All actions" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Actions</SelectItem>
                  {ACTION_TYPES.map((a) => <SelectItem key={a} value={a}>{a}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="w-40">
              <label className="text-[9px] font-mono text-muted-foreground block mb-1">USER ID</label>
              <Input className="h-8 text-[11px] font-mono" placeholder="Filter by user" value={filters.user_id} onChange={(e) => setFilters((p) => ({ ...p, user_id: e.target.value }))} />
            </div>
            <div className="w-36">
              <label className="text-[9px] font-mono text-muted-foreground block mb-1">FROM</label>
              <Input type="date" className="h-8 text-[11px] font-mono" value={filters.start_date} onChange={(e) => setFilters((p) => ({ ...p, start_date: e.target.value }))} />
            </div>
            <div className="w-36">
              <label className="text-[9px] font-mono text-muted-foreground block mb-1">TO</label>
              <Input type="date" className="h-8 text-[11px] font-mono" value={filters.end_date} onChange={(e) => setFilters((p) => ({ ...p, end_date: e.target.value }))} />
            </div>
            <Button size="sm" variant="ghost" className="h-8 text-[10px]" onClick={() => setFilters({ action: "", user_id: "", start_date: "", end_date: "" })} data-testid="clear-filters-btn">
              <Filter className="w-3 h-3 mr-1" /> Clear
            </Button>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-[11px] font-mono">
              <thead>
                <tr className="border-b border-border text-muted-foreground text-left">
                  <th className="py-2 px-2">TIMESTAMP</th>
                  <th className="py-2 px-2">ACTION</th>
                  <th className="py-2 px-2">USER</th>
                  <th className="py-2 px-2">IP</th>
                  <th className="py-2 px-2">DETAILS</th>
                </tr>
              </thead>
              <tbody>
                {trail.entries.map((e) => (
                  <tr key={e.audit_id} className="border-b border-border/50 hover:bg-secondary/20">
                    <td className="py-1.5 px-2 text-muted-foreground whitespace-nowrap">{e.timestamp?.slice(0, 19)}</td>
                    <td className="py-1.5 px-2">
                      <span className="px-1.5 py-0.5 bg-secondary/50 border border-border text-[10px]">{e.action}</span>
                    </td>
                    <td className="py-1.5 px-2 max-w-[120px] truncate" title={e.user_id}>{e.user_id}</td>
                    <td className="py-1.5 px-2 text-muted-foreground">{e.ip_address?.slice(0, 20)}</td>
                    <td className="py-1.5 px-2 text-muted-foreground max-w-[200px] truncate" title={JSON.stringify(e.details)}>
                      {JSON.stringify(e.details).slice(0, 60)}
                    </td>
                  </tr>
                ))}
                {trail.entries.length === 0 && (
                  <tr>
                    <td colSpan={5} className="text-center py-8 text-muted-foreground">No audit entries match your filters</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {trail.pages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-[10px] text-muted-foreground">Page {trailPage} of {trail.pages}</p>
              <div className="flex gap-1">
                <Button size="icon" variant="ghost" className="w-7 h-7" disabled={trailPage <= 1} onClick={() => loadTrail(trailPage - 1)}>
                  <ChevronLeft className="w-3 h-3" />
                </Button>
                <Button size="icon" variant="ghost" className="w-7 h-7" disabled={trailPage >= trail.pages} onClick={() => loadTrail(trailPage + 1)}>
                  <ChevronRight className="w-3 h-3" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
