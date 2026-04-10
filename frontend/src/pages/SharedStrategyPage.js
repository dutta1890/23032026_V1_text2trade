import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Loader2, ArrowLeft, Copy, Shield, TrendingUp, Target, Clock, Eye, Users
} from "lucide-react";
import { toast } from "sonner";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL + "/api/v1";

const ConditionRow = ({ cond, index }) => (
  <div className="flex items-center gap-3 py-2.5 px-3 bg-secondary/20 border border-border">
    <span className="text-[10px] font-mono text-muted-foreground w-5 tabular-nums">{index + 1}</span>
    <span className="font-mono text-sm font-bold text-primary">{cond.name || "—"}</span>
    {cond.params && Object.keys(cond.params).length > 0 && (
      <span className="text-[10px] font-mono text-muted-foreground">
        ({Object.entries(cond.params).map(([k, v]) => `${k}=${v}`).join(", ")})
      </span>
    )}
    <span className="font-mono text-xs text-foreground">{cond.operator}</span>
    {cond.value != null && <span className="font-mono text-sm font-bold text-foreground tabular-nums">{cond.value}</span>}
  </div>
);

export default function SharedStrategyPage() {
  const { shareToken } = useParams();
  const navigate = useNavigate();
  const { isAuthenticated, token } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [cloning, setCloning] = useState(false);

  useEffect(() => {
    document.title = "Shared Strategy | Text2trade";
    axios.get(`${API}/shared/${shareToken}`)
      .then((r) => {
        setData(r.data);
        const name = r.data.strategy?.metadata?.name;
        if (name) document.title = `${name} | Text2trade`;
      })
      .catch(() => toast.error("Shared strategy not found"))
      .finally(() => setLoading(false));
  }, [shareToken]);

  const handleClone = async () => {
    if (!isAuthenticated) {
      toast.error("Login to clone this strategy");
      navigate("/login");
      return;
    }
    setCloning(true);
    try {
      const res = await axios.post(`${API}/shared/${shareToken}/clone`, {}, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.data.success) {
        toast.success("Strategy cloned to your account!");
        navigate(`/strategy/${res.data.strategy_id}`);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Clone failed");
    } finally {
      setCloning(false);
    }
  };

  if (loading) return <div className="min-h-screen bg-background flex items-center justify-center"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>;
  if (!data) return null;

  const s = data.strategy || {};
  const entry = s.entry_conditions || [];
  const exit = s.exit_conditions || [];
  const rm = s.risk_management || {};
  const meta = s.metadata || {};

  return (
    <div className="min-h-screen bg-background" data-testid="shared-strategy-page">
      <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-[10px] font-mono text-muted-foreground mb-1">SHARED STRATEGY</p>
            <h1 className="text-2xl font-bold text-foreground">{meta.name || "Unnamed"}</h1>
            <div className="flex flex-wrap items-center gap-3 mt-2 text-[10px] font-mono text-muted-foreground">
              <span className="px-1.5 py-0.5 bg-primary/10 text-primary border border-primary/20">{s.instrument?.symbol || "—"}</span>
              <span>{s.timeframe?.interval || "—"}</span>
              <span className="flex items-center gap-1"><Eye className="w-3 h-3" /> {data.views} views</span>
              <span className="flex items-center gap-1"><Users className="w-3 h-3" /> {data.clones} clones</span>
              <span>by {data.shared_by}</span>
            </div>
          </div>
          <Button onClick={handleClone} disabled={cloning} className="font-mono text-xs uppercase gap-2" data-testid="clone-shared-btn">
            {cloning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Copy className="w-4 h-4" />}
            {cloning ? "Cloning..." : "Clone to My Strategies"}
          </Button>
        </div>

        {meta.description && <p className="text-sm text-muted-foreground">{meta.description}</p>}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Entry */}
          <Card className="border-border bg-card lg:col-span-2">
            <CardHeader className="py-3 px-4 border-b border-border">
              <CardTitle className="text-sm font-mono flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-primary" /> ENTRY CONDITIONS
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 space-y-2">
              {entry.length > 0 ? entry.map((c, i) => <ConditionRow key={`entry-${c.name}-${i}`} cond={c} index={i} />) : <p className="text-xs text-muted-foreground">None</p>}
            </CardContent>
          </Card>
          {/* Risk */}
          <Card className="border-border bg-card">
            <CardHeader className="py-3 px-4 border-b border-border">
              <CardTitle className="text-sm font-mono flex items-center gap-2">
                <Shield className="w-4 h-4 text-primary" /> RISK
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 space-y-2">
              {rm.stop_loss && <div className="p-2 bg-secondary/20 border border-border"><p className="mono-label text-[10px]">STOP LOSS</p><p className="font-mono text-sm font-bold text-destructive">{rm.stop_loss.value}%</p></div>}
              {rm.target_profit && <div className="p-2 bg-secondary/20 border border-border"><p className="mono-label text-[10px]">TARGET</p><p className="font-mono text-sm font-bold text-primary">{rm.target_profit.value}%</p></div>}
              {rm.trailing_stop_loss?.enabled && <div className="p-2 bg-secondary/20 border border-border"><p className="mono-label text-[10px]">TRAILING SL</p><p className="font-mono text-sm font-bold text-yellow-500">{rm.trailing_stop_loss.value}%</p></div>}
              {!rm.stop_loss && !rm.target_profit && <p className="text-xs text-muted-foreground">No risk controls</p>}
            </CardContent>
          </Card>
        </div>

        {/* Exit */}
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

        {!isAuthenticated && (
          <Card className="border-primary/30 bg-primary/5">
            <CardContent className="p-5 text-center">
              <p className="font-mono text-sm text-foreground mb-2">Want to use this strategy?</p>
              <Button asChild className="font-mono text-xs uppercase"><a href="/login">Login to Clone</a></Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
