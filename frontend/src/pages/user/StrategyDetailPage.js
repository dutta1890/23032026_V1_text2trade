import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useApi } from "@/hooks/useApi";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Loader2, ArrowLeft, Play, Activity, Pencil, Trash2,
  ChevronRight, Shield, Clock, Target, TrendingUp, Zap, Share2, Copy, History,
  Download, FileText, Eye, Users, Link2, XCircle, ArrowRight,
} from "lucide-react";
import { PageSkeleton } from "@/components/LoadingSkeleton";
import { toast } from "sonner";

const ConditionRow = ({ cond, index }) => {
  const name = cond.name || "—";
  const op = cond.operator || "—";
  const val = cond.value;
  const params = cond.params || {};
  const paramStr = Object.entries(params).map(([k, v]) => `${k}=${v}`).join(", ");

  return (
    <div className="flex items-center gap-3 py-2.5 px-3 bg-secondary/20 border border-border" data-testid={`condition-row-${index}`}>
      <span className="text-[10px] font-mono text-muted-foreground w-5 tabular-nums">{index + 1}</span>
      <span className="font-mono text-sm font-bold text-primary">{name}</span>
      {paramStr && <span className="text-[10px] font-mono text-muted-foreground">({paramStr})</span>}
      <span className="font-mono text-xs text-foreground">{op}</span>
      {val !== undefined && val !== null && <span className="font-mono text-sm font-bold text-foreground tabular-nums">{val}</span>}
    </div>
  );
};

const RiskItem = ({ label, value, icon: Icon, color = "text-foreground" }) => (
  <div className="flex items-center gap-3 py-2 px-3 bg-secondary/20 border border-border">
    {Icon && <Icon className={`w-4 h-4 ${color}`} />}
    <div>
      <p className="mono-label text-[10px]">{label}</p>
      <p className={`font-mono text-sm font-bold ${color}`}>{value}</p>
    </div>
  </div>
);

export default function StrategyDetailPage() {
  const { strategyId } = useParams();
  const api = useApi();
  const navigate = useNavigate();
  const [strategy, setStrategy] = useState(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const [shareToken, setShareToken] = useState(null);
  const [sharing, setSharing] = useState(false);
  const [versions, setVersions] = useState([]);
  const [showVersions, setShowVersions] = useState(false);
  const [shareStats, setShareStats] = useState(null);
  const [broker, setBroker] = useState(null);
  const [brokerData, setBrokerData] = useState(null);
  const [brokerLoading, setBrokerLoading] = useState(false);

  useEffect(() => {
    document.title = "Strategy | Text2trade";
    api.get(`/strategy/${strategyId}`)
      .then((r) => {
        const s = r.data.strategy || r.data;
        setStrategy(s);
        if (s?.metadata?.name) document.title = `${s.metadata.name} | Text2trade`;
      })
      .catch(() => {
        toast.error("Strategy not found");
        navigate("/dashboard");
      })
      .finally(() => setLoading(false));
    api.get(`/strategy/${strategyId}/versions`)
      .then((r) => setVersions(r.data.versions || []))
      .catch(() => {});
    api.get(`/strategies/${strategyId}/share-stats`)
      .then((r) => setShareStats(r.data))
      .catch(() => {});
  }, [strategyId]);

  const handleDelete = async () => {
    if (!window.confirm("Delete this strategy? This cannot be undone.")) return;
    setDeleting(true);
    try {
      await api.del(`/strategy/${strategyId}`);
      toast.success("Strategy deleted");
      navigate("/dashboard");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Delete failed");
    } finally {
      setDeleting(false);
    }
  };

  const handleShare = async () => {
    setSharing(true);
    try {
      const res = await api.post(`/strategies/${strategyId}/share`);
      const sid = res.data.share_id;
      setShareToken(sid);
      setShareStats((prev) => prev ? { ...prev, ...res.data } : res.data);
      const url = `${window.location.origin}/s/${sid}`;
      navigator.clipboard.writeText(url).then(
        () => toast.success("Share link copied to clipboard!"),
        () => toast.success("Share link generated")
      );
    } catch (err) {
      toast.error(err.response?.data?.detail || "Share failed");
    } finally {
      setSharing(false);
    }
  };

  const handleCopyText = async () => {
    try {
      const res = await api.get(`/strategies/${strategyId}/copy-text`);
      await navigator.clipboard.writeText(res.data.text);
      toast.success("Strategy text copied to clipboard!");
    } catch {
      toast.error("Copy failed");
    }
  };

  const handlePdf = () => {
    window.open(`${process.env.REACT_APP_BACKEND_URL}/api/v1/strategies/${strategyId}/pdf?token=${localStorage.getItem("t2t_token")}`, "_blank");
  };

  const handleBroker = async (b) => {
    setBroker(b);
    setBrokerLoading(true);
    try {
      const res = await api.get(`/strategies/${strategyId}/broker-instructions/${b}`);
      setBrokerData(res.data);
    } catch {
      toast.error("Failed to load instructions");
    } finally {
      setBrokerLoading(false);
    }
  };

  const handleRevoke = async (sid) => {
    try {
      await api.del(`/strategies/${strategyId}/share/${sid}`);
      toast.success("Share revoked");
      setShareToken(null);
      setShareStats((prev) => prev ? { ...prev, active_shares: Math.max(0, (prev.active_shares || 1) - 1) } : prev);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Revoke failed");
    }
  };

  if (loading) return <PageSkeleton />;
  if (!strategy) return null;

  const rm = strategy.risk_management || {};
  const entry = strategy.entry_conditions || [];
  const exit = strategy.exit_conditions || [];
  const instrument = strategy.instrument || {};
  const timeframe = strategy.timeframe || {};
  const meta = strategy.metadata || {};

  return (
    <div className="space-y-6" data-testid="strategy-detail-page">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate("/dashboard")} data-testid="back-btn">
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-foreground">{meta.name || "Unnamed Strategy"}</h1>
            <div className="flex flex-wrap items-center gap-2 mt-1">
              <span className="text-[10px] font-mono px-1.5 py-0.5 bg-primary/15 text-primary border border-primary/20">{instrument.symbol || "—"}</span>
              <span className="text-[10px] font-mono text-muted-foreground">{timeframe.interval || "—"}</span>
              {strategy.version && <span className="text-[10px] font-mono text-muted-foreground">v{strategy.version}</span>}
              {meta.created_at && <span className="text-[10px] font-mono text-muted-foreground">{new Date(meta.created_at).toLocaleDateString()}</span>}
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <Button size="sm" className="font-mono text-[10px] uppercase gap-1.5" onClick={() => navigate(`/backtest/${strategyId}`)} data-testid="run-backtest-btn">
            <Play className="w-3 h-3" /> Run Backtest
          </Button>
          <Button size="sm" variant="outline" className="font-mono text-[10px] uppercase gap-1.5" onClick={() => navigate(`/optimizer?strategy=${strategyId}`)} data-testid="optimize-btn">
            <Zap className="w-3 h-3" /> Optimize
          </Button>
          <Button size="sm" variant="outline" className="font-mono text-[10px] uppercase gap-1.5" onClick={() => navigate(`/build?edit=${strategyId}`)} data-testid="edit-btn">
            <Pencil className="w-3 h-3" /> Edit
          </Button>
          <Button size="sm" variant="outline" className="font-mono text-[10px] uppercase gap-1.5" onClick={handleShare} disabled={sharing} data-testid="share-btn">
            {sharing ? <Loader2 className="w-3 h-3 animate-spin" /> : <Share2 className="w-3 h-3" />} Share
          </Button>
          <Button size="sm" variant="outline" className="font-mono text-[10px] uppercase gap-1.5 text-destructive hover:text-destructive" onClick={handleDelete} disabled={deleting} data-testid="delete-btn">
            {deleting ? <Loader2 className="w-3 h-3 animate-spin" /> : <Trash2 className="w-3 h-3" />} Delete
          </Button>
        </div>
      </div>

      {/* Share Link */}
      {shareToken && (
        <div className="flex items-center gap-2 px-4 py-3 bg-primary/5 border border-primary/30" data-testid="share-link-banner">
          <Link2 className="w-4 h-4 text-primary shrink-0" />
          <p className="text-xs font-mono text-muted-foreground flex-1 truncate">
            {window.location.origin}/s/{shareToken}
          </p>
          <Button variant="ghost" size="sm" className="h-6 text-[10px] font-mono gap-1" onClick={() => {
            navigator.clipboard.writeText(`${window.location.origin}/s/${shareToken}`);
            toast.success("Copied!");
          }} data-testid="copy-share-link">
            <Copy className="w-3 h-3" /> Copy
          </Button>
          <Button variant="ghost" size="sm" className="h-6 text-[10px] font-mono gap-1 text-destructive hover:text-destructive" onClick={() => handleRevoke(shareToken)} data-testid="revoke-share-btn">
            <XCircle className="w-3 h-3" /> Revoke
          </Button>
        </div>
      )}

      {/* Share & Export Section */}
      <Card className="border-border bg-card" data-testid="share-export-section">
        <CardHeader className="py-3 px-4 border-b border-border">
          <CardTitle className="text-sm font-mono flex items-center gap-2">
            <Share2 className="w-4 h-4 text-primary" /> SHARE & EXPORT
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <div className="flex flex-wrap gap-2 mb-4">
            <Button size="sm" variant="outline" className="font-mono text-[10px] uppercase gap-1.5" onClick={handleCopyText} data-testid="copy-text-btn">
              <Copy className="w-3 h-3" /> Copy as Text
            </Button>
            <Button size="sm" variant="outline" className="font-mono text-[10px] uppercase gap-1.5" onClick={handlePdf} data-testid="download-pdf-btn">
              <Download className="w-3 h-3" /> Download PDF
            </Button>
            <Button size="sm" variant="outline" className="font-mono text-[10px] uppercase gap-1.5" onClick={handleShare} disabled={sharing} data-testid="gen-share-link-btn">
              {sharing ? <Loader2 className="w-3 h-3 animate-spin" /> : <Link2 className="w-3 h-3" />}
              {shareToken ? "Copy Share Link" : "Generate Share Link"}
            </Button>
          </div>
          {shareStats && (shareStats.total_views > 0 || shareStats.total_clones > 0) && (
            <div className="flex items-center gap-4 text-[10px] font-mono text-muted-foreground" data-testid="share-stats">
              <span className="flex items-center gap-1"><Eye className="w-3 h-3" /> {shareStats.total_views} views</span>
              <span className="flex items-center gap-1"><Users className="w-3 h-3" /> {shareStats.total_clones} clones</span>
              <span>{shareStats.active_shares || 0} active share{(shareStats.active_shares || 0) !== 1 ? "s" : ""}</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Broker Instructions */}
      <Card className="border-border bg-card" data-testid="broker-instructions-section">
        <CardHeader className="py-3 px-4 border-b border-border">
          <CardTitle className="text-sm font-mono flex items-center gap-2">
            <FileText className="w-4 h-4 text-primary" /> HOW TO EXECUTE THIS STRATEGY
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <p className="text-xs text-muted-foreground mb-3">Select your broker for step-by-step instructions:</p>
          <div className="flex flex-wrap gap-2 mb-4">
            {["zerodha", "angel_one", "upstox", "dhan", "groww", "5paisa"].map((b) => (
              <Button key={b} size="sm" variant={broker === b ? "default" : "outline"}
                className="font-mono text-[10px] uppercase h-8"
                onClick={() => handleBroker(b)}
                data-testid={`broker-btn-${b}`}
              >
                {{zerodha:"Zerodha", angel_one:"Angel One", upstox:"Upstox", dhan:"Dhan", groww:"Groww", "5paisa":"5paisa"}[b]}
              </Button>
            ))}
          </div>
          {brokerLoading && <Loader2 className="w-4 h-4 animate-spin text-primary" />}
          {brokerData && !brokerLoading && (
            <div className="p-4 bg-secondary/30 border border-border space-y-3" data-testid="broker-steps">
              <p className="text-sm font-mono font-bold text-foreground">How to place this trade on {brokerData.broker_name}:</p>
              <ol className="space-y-2">
                {brokerData.steps.map((step, i) => (
                  <li key={`bstep-${i}`} className="flex gap-2 text-xs font-mono">
                    <span className="text-primary shrink-0">{i + 1}.</span>
                    <span className="text-foreground">{step}</span>
                  </li>
                ))}
              </ol>
              {brokerData.note && <p className="text-[10px] font-mono text-muted-foreground italic border-l-2 border-primary/30 pl-2">{brokerData.note}</p>}
              {brokerData.help_url && (
                <a href={brokerData.help_url} target="_blank" rel="noopener noreferrer" className="text-[10px] font-mono text-primary hover:underline flex items-center gap-1">
                  Broker documentation <ArrowRight className="w-3 h-3" />
                </a>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Entry Conditions */}
        <Card className="border-border bg-card lg:col-span-2">
          <CardHeader className="py-3 px-4 border-b border-border">
            <CardTitle className="text-sm font-mono flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-primary" /> ENTRY CONDITIONS
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 space-y-2">
            {entry.length > 0 ? entry.map((c, i) => (
              <ConditionRow key={`entry-${c.name}-${i}`} cond={c} index={i} />
            )) : (
              <p className="text-xs text-muted-foreground py-2">No entry conditions defined.</p>
            )}
          </CardContent>
        </Card>

        {/* Risk Management */}
        <Card className="border-border bg-card">
          <CardHeader className="py-3 px-4 border-b border-border">
            <CardTitle className="text-sm font-mono flex items-center gap-2">
              <Shield className="w-4 h-4 text-primary" /> RISK MANAGEMENT
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 space-y-2">
            {rm.stop_loss && (
              <RiskItem label="STOP LOSS" value={`${rm.stop_loss.value}% (${rm.stop_loss.type})`} icon={Target} color="text-destructive" />
            )}
            {rm.target_profit && (
              <RiskItem label="TARGET PROFIT" value={`${rm.target_profit.value}% (${rm.target_profit.type})`} icon={Target} color="text-primary" />
            )}
            {rm.trailing_stop_loss?.enabled && (
              <RiskItem label="TRAILING STOP" value={`${rm.trailing_stop_loss.value}%`} icon={TrendingUp} color="text-yellow-500" />
            )}
            {rm.time_based_exit?.enabled && (
              <RiskItem label="TIME EXIT" value={rm.time_based_exit.exit_time || "15:10"} icon={Clock} />
            )}
            {!rm.stop_loss && !rm.target_profit && !rm.trailing_stop_loss?.enabled && !rm.time_based_exit?.enabled && (
              <p className="text-xs text-muted-foreground py-2">No risk controls configured.</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Exit Conditions */}
      {exit.length > 0 && (
        <Card className="border-border bg-card">
          <CardHeader className="py-3 px-4 border-b border-border">
            <CardTitle className="text-sm font-mono">EXIT CONDITIONS</CardTitle>
          </CardHeader>
          <CardContent className="p-4 space-y-2">
            {exit.map((c, i) => <ConditionRow key={`exit-${c.name}-${i}`} cond={c} index={i} />)}
          </CardContent>
        </Card>
      )}

      {/* Version History */}
      {versions.length > 0 && (
        <Card className="border-border bg-card">
          <CardHeader className="py-3 px-4 border-b border-border cursor-pointer" onClick={() => setShowVersions(!showVersions)}>
            <CardTitle className="text-sm font-mono flex items-center gap-2">
              <History className="w-4 h-4 text-primary" />
              VERSION HISTORY ({versions.length})
              <ChevronRight className={`w-3 h-3 ml-auto transition-transform ${showVersions ? "rotate-90" : ""}`} />
            </CardTitle>
          </CardHeader>
          {showVersions && (
            <CardContent className="p-4 space-y-3" data-testid="version-history">
              {versions.map((v) => (
                <div key={`v-${v.version}`} className="flex items-start gap-3 p-3 bg-secondary/20 border border-border">
                  <div className="w-8 h-8 bg-primary/15 border border-primary/20 flex items-center justify-center shrink-0">
                    <span className="text-xs font-mono font-bold text-primary">{v.version}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-mono text-foreground">Version {v.version}</p>
                    <p className="text-[10px] font-mono text-muted-foreground">{new Date(v.created_at).toLocaleString()}</p>
                    {v.changed_fields?.length > 0 && (
                      <p className="text-[10px] font-mono text-muted-foreground mt-1">
                        Changed: {v.changed_fields.join(", ")}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </CardContent>
          )}
        </Card>
      )}

      {/* Raw JSON Preview */}
      <Card className="border-border bg-card">
        <CardHeader className="py-3 px-4 border-b border-border cursor-pointer" data-testid="json-toggle">
          <CardTitle className="text-sm font-mono text-muted-foreground flex items-center gap-2">
            RAW STRATEGY JSON
            <ChevronRight className="w-3 h-3" />
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <pre className="text-[10px] font-mono text-muted-foreground overflow-auto whitespace-pre-wrap max-h-64 p-3 bg-secondary/20 border border-border" data-testid="strategy-json">
            {JSON.stringify(strategy, null, 2)}
          </pre>
        </CardContent>
      </Card>
    </div>
  );
}
