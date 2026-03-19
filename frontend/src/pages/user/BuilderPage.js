import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useApi } from "@/hooks/useApi";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Send, Loader2, CheckCircle, AlertTriangle, Sparkles, Copy, Check,
  Save, Play, Activity, BookOpen, X
} from "lucide-react";

/* ---------- Chat ---------- */
const ChatBubble = ({ role, content }) => {
  const isUser = role === "user";
  let parsed = null;
  if (!isUser) {
    try { parsed = typeof content === "string" ? JSON.parse(content) : content; } catch { parsed = null; }
  }
  const msg = parsed?.message || parsed?.explanation || content;
  const modeIcon = parsed?.mode === "strategy" ? <CheckCircle className="w-3 h-3 text-primary" /> :
    parsed?.mode === "error" ? <AlertTriangle className="w-3 h-3 text-destructive" /> : null;

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div className={`max-w-[85%] px-3 py-2 text-sm ${isUser ? "bg-primary/15 border border-primary/30" : "bg-secondary/60 border border-border"}`}>
        {!isUser && modeIcon && <div className="flex items-center gap-1 mb-1">{modeIcon}<span className="mono-label text-[10px] uppercase">{parsed?.mode}</span></div>}
        <p className="text-foreground whitespace-pre-wrap">{msg}</p>
        {parsed?.fields_needed?.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {parsed.fields_needed.map((f, i) => (
              <span key={i} className="text-[10px] font-mono px-1.5 py-0.5 bg-primary/10 text-primary border border-primary/20">{f}</span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

/* ---------- Risk Editor ---------- */
const RiskEditor = ({ draft, onChange }) => {
  if (!draft) return null;
  const rm = draft.risk_management || {};
  const update = (key, val) => onChange({ ...draft, risk_management: { ...rm, [key]: val } });

  return (
    <div className="space-y-3 p-3 bg-secondary/20 border border-border" data-testid="risk-editor">
      <h4 className="mono-label text-[10px]">RISK CONTROLS</h4>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="mono-label text-[10px] mb-1 block">Stop Loss %</label>
          <Input type="number" step="0.1" className="h-8 font-mono text-xs" value={rm.stop_loss?.value || ""} onChange={(e) => update("stop_loss", { type: "percentage", value: parseFloat(e.target.value) || 0 })} data-testid="risk-sl" />
        </div>
        <div>
          <label className="mono-label text-[10px] mb-1 block">Target Profit %</label>
          <Input type="number" step="0.1" className="h-8 font-mono text-xs" value={rm.target_profit?.value || ""} onChange={(e) => update("target_profit", { type: "percentage", value: parseFloat(e.target.value) || 0 })} data-testid="risk-tp" />
        </div>
      </div>
      <div className="flex items-center justify-between">
        <label className="mono-label text-[10px]">Trailing Stop Loss</label>
        <Switch checked={rm.trailing_stop_loss?.enabled || false} onCheckedChange={(v) => update("trailing_stop_loss", { ...rm.trailing_stop_loss, enabled: v, type: "percentage", value: rm.trailing_stop_loss?.value || 1.5, activation_profit: 0 })} data-testid="risk-tsl-toggle" />
      </div>
      {rm.trailing_stop_loss?.enabled && (
        <div>
          <label className="mono-label text-[10px] mb-1 block">TSL Value %</label>
          <Input type="number" step="0.1" className="h-8 font-mono text-xs" value={rm.trailing_stop_loss?.value || ""} onChange={(e) => update("trailing_stop_loss", { ...rm.trailing_stop_loss, value: parseFloat(e.target.value) || 0 })} data-testid="risk-tsl-value" />
        </div>
      )}
      <div className="flex items-center justify-between">
        <label className="mono-label text-[10px]">Time-based Exit</label>
        <Switch checked={rm.time_based_exit?.enabled || false} onCheckedChange={(v) => update("time_based_exit", { ...rm.time_based_exit, enabled: v, exit_time: rm.time_based_exit?.exit_time || "15:10" })} data-testid="risk-time-toggle" />
      </div>
    </div>
  );
};

/* ---------- Template Mini Card ---------- */
const TemplateMini = ({ t, onSelect }) => (
  <button onClick={() => onSelect(t)} className="text-left p-3 border border-border bg-card hover:border-primary/40 transition-colors" data-testid={`tmpl-${t.template_id?.slice(0, 8)}`}>
    <p className="font-mono text-xs font-bold text-foreground truncate">{t.name}</p>
    <span className="text-[10px] font-mono text-muted-foreground">{t.category}</span>
  </button>
);

/* ---------- Main Page ---------- */
export default function BuilderPage() {
  const api = useApi();
  const navigate = useNavigate();
  const [tab, setTab] = useState("chat");
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [draft, setDraft] = useState(null);
  const [finalized, setFinalized] = useState(null);
  const [finalizing, setFinalizing] = useState(false);
  const [backtesting, setBacktesting] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [templates, setTemplates] = useState([]);
  const [copied, setCopied] = useState(false);
  const chatEnd = useRef(null);

  useEffect(() => { startSession(); loadTemplates(); }, []);
  useEffect(() => { chatEnd.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const startSession = async () => {
    try {
      const res = await api.post("/session/start", {});
      setSessionId(res.data.session_id);
      setMessages([{ role: "assistant", content: JSON.stringify({ mode: "question", message: "Describe your trading idea. For example:\n- \"Buy RELIANCE when RSI crosses above 30\"\n- \"Golden cross strategy on INFY with 5% stop loss\"\n- \"Supertrend + RSI on TCS daily\"", fields_needed: [] }) }]);
    } catch { /* ignore */ }
  };

  const loadTemplates = async () => {
    try {
      const res = await api.get("/templates");
      setTemplates(res.data.templates || []);
    } catch { /* ignore */ }
  };

  const sendMessage = async () => {
    if (!input.trim() || !sessionId || sending) return;
    const userMsg = input.trim();
    setInput("");
    setMessages((p) => [...p, { role: "user", content: userMsg }]);
    setSending(true);
    try {
      const res = await api.post(`/session/${sessionId}/message`, { message: userMsg });
      setMessages((p) => [...p, { role: "assistant", content: res.data.content }]);
      if (res.data.strategy_draft) setDraft(res.data.strategy_draft);
    } catch (err) {
      setMessages((p) => [...p, { role: "assistant", content: JSON.stringify({ mode: "error", message: err.response?.data?.detail || "Error" }) }]);
    } finally {
      setSending(false);
    }
  };

  const handleFinalize = async () => {
    if (!sessionId) return;
    setFinalizing(true);
    try {
      const res = await api.post(`/session/${sessionId}/finalize`, {});
      setFinalized(res.data);
      setMessages((p) => [...p, { role: "assistant", content: JSON.stringify({ mode: "strategy", message: `Strategy saved! ID: ${res.data.strategy_id}` }) }]);
    } catch (err) {
      setMessages((p) => [...p, { role: "assistant", content: JSON.stringify({ mode: "error", message: err.response?.data?.detail || "Finalize failed" }) }]);
    } finally {
      setFinalizing(false);
    }
  };

  const handleBacktest = async () => {
    if (!finalized?.strategy_id) return;
    setBacktesting(true);
    try {
      navigate(`/backtest/${finalized.strategy_id}`);
    } finally {
      setBacktesting(false);
    }
  };

  const handleDeploy = async () => {
    if (!finalized?.strategy_id) return;
    setDeploying(true);
    try {
      await api.post("/paper-trade/deploy", { strategy_id: finalized.strategy_id, symbol: draft?.instrument?.symbol || "RELIANCE", timeframe: draft?.timeframe?.interval || "1d", initial_capital: 100000, lookback_days: 60 });
      navigate("/paper-trades");
    } catch { /* ignore */ } finally {
      setDeploying(false);
    }
  };

  const handleTemplateSelect = async (t) => {
    try {
      const res = await api.post(`/template/${t.template_id}/clone`, { symbol: t.instrument?.symbol });
      setFinalized({ strategy_id: res.data.strategy_id });
      setDraft(res.data.strategy);
      setTab("chat");
      setMessages((p) => [...p, { role: "assistant", content: JSON.stringify({ mode: "strategy", message: `Cloned "${t.name}" template. You can now backtest or deploy it.` }) }]);
    } catch { /* ignore */ }
  };

  const handleKeyDown = (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } };

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(draft, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-4" data-testid="builder-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">Strategy Builder</h1>
          <p className="text-sm text-muted-foreground mt-1">Build with AI or start from a template.</p>
        </div>
        {finalized && (
          <div className="flex gap-2">
            <Button size="sm" className="font-mono text-[10px] uppercase gap-1.5" onClick={handleBacktest} disabled={backtesting} data-testid="finalize-backtest-btn">
              <Play className="w-3 h-3" /> {backtesting ? "..." : "Backtest"}
            </Button>
            <Button size="sm" variant="outline" className="font-mono text-[10px] uppercase gap-1.5" onClick={handleDeploy} disabled={deploying} data-testid="finalize-deploy-btn">
              <Activity className="w-3 h-3" /> {deploying ? "..." : "Paper Trade"}
            </Button>
          </div>
        )}
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="bg-secondary/30 border border-border">
          <TabsTrigger value="chat" className="font-mono text-xs" data-testid="tab-chat"><Sparkles className="w-3 h-3 mr-1" /> AI Chat</TabsTrigger>
          <TabsTrigger value="templates" className="font-mono text-xs" data-testid="tab-templates"><BookOpen className="w-3 h-3 mr-1" /> Templates</TabsTrigger>
        </TabsList>

        <TabsContent value="templates" className="mt-4">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
            {templates.map((t) => <TemplateMini key={t.template_id} t={t} onSelect={handleTemplateSelect} />)}
          </div>
        </TabsContent>

        <TabsContent value="chat" className="mt-4">
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
            {/* Chat */}
            <Card className="border-border bg-card lg:col-span-3 flex flex-col" style={{ minHeight: "420px" }}>
              <CardContent className="flex-1 overflow-y-auto p-4" style={{ maxHeight: "340px" }}>
                {messages.map((m, i) => <ChatBubble key={i} role={m.role} content={m.content} />)}
                {sending && <div className="flex justify-start mb-3"><div className="bg-secondary/60 border border-border px-4 py-3"><Loader2 className="w-4 h-4 animate-spin text-primary" /></div></div>}
                <div ref={chatEnd} />
              </CardContent>
              <div className="p-3 border-t border-border flex gap-2">
                <Input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKeyDown} placeholder="Describe your trading idea..." disabled={sending || !!finalized} className="font-mono text-sm" data-testid="builder-chat-input" />
                <Button onClick={sendMessage} disabled={sending || !input.trim() || !!finalized} size="icon" data-testid="builder-send-btn"><Send className="w-4 h-4" /></Button>
              </div>
            </Card>

            {/* Preview + Risk */}
            <Card className="border-border bg-card lg:col-span-2 flex flex-col">
              <CardHeader className="py-3 px-4 border-b border-border">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-xs font-mono text-muted-foreground">STRATEGY</CardTitle>
                  <div className="flex items-center gap-2">
                    {draft && <Button variant="ghost" size="icon" className="h-6 w-6" onClick={handleCopyJson} data-testid="copy-json">{copied ? <Check className="w-3 h-3 text-primary" /> : <Copy className="w-3 h-3" />}</Button>}
                    {draft && !finalized && <Button size="sm" className="h-6 font-mono text-[10px] gap-1" onClick={handleFinalize} disabled={finalizing} data-testid="save-strategy-btn">{finalizing ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />} Save</Button>}
                    {finalized && <span className="text-[10px] font-mono text-primary flex items-center gap-1"><CheckCircle className="w-3 h-3" /> SAVED</span>}
                  </div>
                </div>
              </CardHeader>
              <CardContent className="flex-1 overflow-y-auto p-3 space-y-3" style={{ maxHeight: "380px" }}>
                {draft ? (
                  <>
                    <RiskEditor draft={draft} onChange={setDraft} />
                    <pre className="text-[10px] font-mono text-muted-foreground overflow-auto whitespace-pre-wrap p-2 bg-secondary/20 border border-border" data-testid="json-preview">{JSON.stringify(draft, null, 2)}</pre>
                  </>
                ) : (
                  <div className="flex items-center justify-center h-full text-muted-foreground">
                    <p className="text-sm font-mono text-center">Strategy preview will appear here<br />as the AI builds it.</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
