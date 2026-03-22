import { useState, useEffect, useCallback } from "react";
import { useApi } from "@/hooks/useApi";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import {
  Bell, Plus, Trash2, Play, AlertTriangle, CheckCircle2,
  RefreshCw, X, ChevronDown, ChevronUp, Clock, Shield,
} from "lucide-react";
import { PageSkeleton } from "@/components/LoadingSkeleton";
import { toast } from "sonner";

const METRICS = [
  { value: "sharpe", label: "Sharpe Ratio" },
  { value: "pnl_pct", label: "P&L %" },
  { value: "win_rate", label: "Win Rate %" },
  { value: "max_drawdown", label: "Max Drawdown %" },
];

const OPERATORS = [
  { value: "lt", label: "< (less than)" },
  { value: "gt", label: "> (greater than)" },
  { value: "lte", label: "<= (at most)" },
  { value: "gte", label: ">= (at least)" },
];

const OP_SYMBOLS = { lt: "<", gt: ">", lte: "\u2264", gte: "\u2265" };

export default function AlertsPage() {
  const api = useApi();
  const [alerts, setAlerts] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [unread, setUnread] = useState(0);
  const [strategies, setStrategies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [showNotifs, setShowNotifs] = useState(true);
  const [evaluating, setEvaluating] = useState(false);

  // Create form state
  const [formStrategy, setFormStrategy] = useState("");
  const [formMetric, setFormMetric] = useState("sharpe");
  const [formOperator, setFormOperator] = useState("lt");
  const [formThreshold, setFormThreshold] = useState("");
  const [creating, setCreating] = useState(false);

  const fetchData = useCallback(() => {
    setLoading(true);
    Promise.all([
      api.get("/alerts").catch(() => ({ data: { alerts: [] } })),
      api.get("/alerts/notifications").catch(() => ({ data: { notifications: [], unread: 0 } })),
      api.get("/tracker/dashboard").catch(() => ({ data: { strategy_rankings: [] } })),
    ]).then(([aRes, nRes, tRes]) => {
      setAlerts(aRes.data.alerts || []);
      setNotifications(nRes.data.notifications || []);
      setUnread(nRes.data.unread || 0);
      const names = (tRes.data.strategy_rankings || []).map((s) => s.strategy_name).filter(Boolean);
      setStrategies([...new Set(names)]);
    }).finally(() => setLoading(false));
  }, [api]);

  useEffect(() => {
    document.title = "Alerts | Text2trade";
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!formStrategy.trim()) { toast.error("Select a strategy"); return; }
    if (!formThreshold && formThreshold !== 0) { toast.error("Enter a threshold value"); return; }
    setCreating(true);
    try {
      await api.post("/alerts", {
        strategy_name: formStrategy.trim(),
        metric: formMetric,
        operator: formOperator,
        threshold: parseFloat(formThreshold),
      });
      toast.success("Alert created");
      setShowCreate(false);
      setFormStrategy("");
      setFormThreshold("");
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to create alert");
    } finally {
      setCreating(false);
    }
  };

  const handleToggle = async (alertId, enabled) => {
    try {
      await api.put(`/alerts/${alertId}`, { enabled: !enabled });
      setAlerts((prev) => prev.map((a) => a.alert_id === alertId ? { ...a, enabled: !enabled } : a));
    } catch {
      toast.error("Failed to toggle alert");
    }
  };

  const handleDelete = async (alertId) => {
    try {
      await api.del(`/alerts/${alertId}`);
      setAlerts((prev) => prev.filter((a) => a.alert_id !== alertId));
      toast.success("Alert deleted");
    } catch {
      toast.error("Failed to delete alert");
    }
  };

  const handleEvaluate = async () => {
    setEvaluating(true);
    try {
      const res = await api.post("/alerts/evaluate");
      const count = res.data.triggered || 0;
      if (count > 0) {
        toast.warning(`${count} alert${count > 1 ? "s" : ""} triggered!`);
      } else {
        toast.success("All clear — no alerts triggered");
      }
      fetchData();
    } catch {
      toast.error("Evaluation failed");
    } finally {
      setEvaluating(false);
    }
  };

  const handleMarkRead = async (notifId) => {
    try {
      await api.put(`/alerts/notifications/${notifId}/read`);
      setNotifications((prev) => prev.map((n) => n.notification_id === notifId ? { ...n, read: true } : n));
      setUnread((p) => Math.max(0, p - 1));
    } catch {
      toast.error("Failed to mark as read");
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await api.put("/alerts/notifications/read-all");
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
      setUnread(0);
    } catch {
      toast.error("Failed");
    }
  };

  if (loading) return <PageSkeleton />;

  return (
    <div className="space-y-8" data-testid="alerts-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">Strategy Alerts</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {alerts.length} rule{alerts.length !== 1 ? "s" : ""} active
            {unread > 0 && <span className="text-destructive font-bold"> &middot; {unread} unread</span>}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleEvaluate} disabled={evaluating} className="font-mono text-[10px] gap-1.5" data-testid="evaluate-btn">
            <Play className="w-3 h-3" /> {evaluating ? "Checking..." : "Run Check"}
          </Button>
          <Button size="sm" onClick={() => setShowCreate(!showCreate)} className="font-mono text-[10px] gap-1.5" data-testid="create-alert-btn">
            {showCreate ? <X className="w-3 h-3" /> : <Plus className="w-3 h-3" />}
            {showCreate ? "Cancel" : "New Alert"}
          </Button>
        </div>
      </div>

      {/* Create Alert Form */}
      {showCreate && (
        <Card className="border-primary/30 bg-card" data-testid="create-alert-form">
          <CardContent className="p-4">
            <h2 className="mono-label text-[10px] mb-4">CREATE ALERT RULE</h2>
            <form onSubmit={handleCreate} className="grid grid-cols-1 sm:grid-cols-5 gap-3 items-end">
              <div>
                <label className="text-[10px] text-muted-foreground font-mono block mb-1">STRATEGY</label>
                {strategies.length > 0 ? (
                  <Select value={formStrategy} onValueChange={setFormStrategy}>
                    <SelectTrigger className="font-mono text-xs" data-testid="alert-strategy-select">
                      <SelectValue placeholder="Select strategy" />
                    </SelectTrigger>
                    <SelectContent>
                      {strategies.map((s) => (
                        <SelectItem key={s} value={s} className="font-mono text-xs">{s}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <Input
                    value={formStrategy}
                    onChange={(e) => setFormStrategy(e.target.value)}
                    placeholder="Strategy name"
                    className="font-mono text-xs"
                    data-testid="alert-strategy-input"
                  />
                )}
              </div>
              <div>
                <label className="text-[10px] text-muted-foreground font-mono block mb-1">METRIC</label>
                <Select value={formMetric} onValueChange={setFormMetric}>
                  <SelectTrigger className="font-mono text-xs" data-testid="alert-metric-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {METRICS.map((m) => (
                      <SelectItem key={m.value} value={m.value} className="font-mono text-xs">{m.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-[10px] text-muted-foreground font-mono block mb-1">CONDITION</label>
                <Select value={formOperator} onValueChange={setFormOperator}>
                  <SelectTrigger className="font-mono text-xs" data-testid="alert-operator-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {OPERATORS.map((o) => (
                      <SelectItem key={o.value} value={o.value} className="font-mono text-xs">{o.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-[10px] text-muted-foreground font-mono block mb-1">THRESHOLD</label>
                <Input
                  type="number"
                  step="any"
                  value={formThreshold}
                  onChange={(e) => setFormThreshold(e.target.value)}
                  placeholder="e.g. 1.0"
                  className="font-mono text-xs"
                  data-testid="alert-threshold-input"
                />
              </div>
              <Button type="submit" disabled={creating} className="font-mono text-[10px] uppercase" data-testid="alert-submit-btn">
                {creating ? "Creating..." : "Create Alert"}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Alert Rules */}
      <div data-testid="alert-rules-section">
        <h2 className="mono-label text-[10px] mb-3">ALERT RULES</h2>
        {alerts.length === 0 ? (
          <Card className="border-border border-dashed bg-card/50" data-testid="empty-alerts">
            <CardContent className="p-8 text-center">
              <Bell className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
              <h3 className="font-mono font-bold text-foreground mb-1">No alert rules yet</h3>
              <p className="text-xs text-muted-foreground mb-4">
                Create alert rules to monitor your strategy performance. You'll get notified when metrics cross your thresholds.
              </p>
              <Button size="sm" onClick={() => setShowCreate(true)} className="font-mono text-[10px] uppercase gap-1.5" data-testid="empty-create-btn">
                <Plus className="w-3 h-3" /> Create First Alert
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-2">
            {alerts.map((a, i) => (
              <Card key={a.alert_id} className={`border-border bg-card transition-colors ${a.enabled ? "hover:border-primary/30" : "opacity-60"}`} data-testid={`alert-rule-${i}`}>
                <CardContent className="p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <Shield className={`w-4 h-4 shrink-0 ${a.enabled ? "text-primary" : "text-muted-foreground"}`} />
                    <div className="min-w-0">
                      <p className="font-mono font-bold text-sm text-foreground truncate">{a.strategy_name}</p>
                      <p className="text-[10px] text-muted-foreground font-mono mt-0.5">
                        {METRICS.find((m) => m.value === a.metric)?.label || a.metric}{" "}
                        <span className="text-foreground">{OP_SYMBOLS[a.operator] || a.operator}</span>{" "}
                        <span className="text-foreground font-bold">{a.threshold}</span>
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 ml-2">
                    <Switch
                      checked={a.enabled}
                      onCheckedChange={() => handleToggle(a.alert_id, a.enabled)}
                      data-testid={`alert-toggle-${i}`}
                    />
                    <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-destructive" onClick={() => handleDelete(a.alert_id)} data-testid={`alert-delete-${i}`}>
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Notifications */}
      <div data-testid="notifications-section">
        <div className="flex items-center justify-between mb-3">
          <button className="flex items-center gap-2" onClick={() => setShowNotifs(!showNotifs)}>
            <h2 className="mono-label text-[10px]">NOTIFICATIONS</h2>
            {unread > 0 && (
              <Badge variant="destructive" className="text-[9px] font-mono h-4 px-1.5">{unread}</Badge>
            )}
            {showNotifs ? <ChevronUp className="w-3 h-3 text-muted-foreground" /> : <ChevronDown className="w-3 h-3 text-muted-foreground" />}
          </button>
          {unread > 0 && (
            <Button variant="ghost" size="sm" className="font-mono text-[10px] h-6" onClick={handleMarkAllRead} data-testid="mark-all-read-btn">
              Mark all read
            </Button>
          )}
        </div>

        {showNotifs && (
          <>
            {notifications.length === 0 ? (
              <Card className="border-border border-dashed bg-card/50" data-testid="empty-notifications">
                <CardContent className="p-6 text-center">
                  <CheckCircle2 className="w-8 h-8 text-primary mx-auto mb-2" />
                  <p className="text-xs text-muted-foreground font-mono">All clear! No triggered alerts.</p>
                  <p className="text-[10px] text-muted-foreground mt-1">Click "Run Check" to evaluate your rules against current data.</p>
                </CardContent>
              </Card>
            ) : (
              <Card className="border-border bg-card">
                <CardContent className="p-0">
                  <div className="divide-y divide-border">
                    {notifications.map((n, i) => (
                      <div
                        key={n.notification_id}
                        className={`px-4 py-3 flex items-center justify-between transition-colors ${!n.read ? "bg-destructive/5" : ""}`}
                        data-testid={`notification-row-${i}`}
                      >
                        <div className="flex items-center gap-3 flex-1 min-w-0">
                          <AlertTriangle className={`w-3.5 h-3.5 shrink-0 ${n.severity === "critical" ? "text-destructive" : "text-yellow-500"}`} />
                          <div className="min-w-0">
                            <p className={`font-mono text-xs truncate ${!n.read ? "text-foreground font-bold" : "text-muted-foreground"}`}>
                              {n.message}
                            </p>
                            <div className="flex items-center gap-2 mt-0.5">
                              <span className="text-[10px] text-muted-foreground font-mono flex items-center gap-1">
                                <Clock className="w-2.5 h-2.5" /> {n.triggered_at?.slice(0, 16).replace("T", " ")}
                              </span>
                              <Badge variant={n.severity === "critical" ? "destructive" : "outline"} className="text-[8px] font-mono h-3.5 px-1">
                                {n.severity}
                              </Badge>
                            </div>
                          </div>
                        </div>
                        {!n.read && (
                          <Button variant="ghost" size="sm" className="h-6 font-mono text-[10px]" onClick={() => handleMarkRead(n.notification_id)} data-testid={`mark-read-${i}`}>
                            Dismiss
                          </Button>
                        )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </>
        )}
      </div>
    </div>
  );
}
