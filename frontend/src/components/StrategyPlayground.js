import { useState, useRef, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Send, Sparkles, Loader2, CheckCircle, AlertTriangle, X, Copy, Check, Save
} from "lucide-react";
import axios from "axios";

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

const getAuthHeaders = () => {
  const token = localStorage.getItem("accessToken");
  return { headers: { Authorization: `Bearer ${token}` } };
};

const ChatBubble = ({ role, content, mode }) => {
  const isUser = role === "user";
  let parsed = null;
  if (!isUser && typeof content === "string") {
    try { parsed = JSON.parse(content); } catch { parsed = null; }
  } else if (!isUser && typeof content === "object") {
    parsed = content;
  }

  const displayMessage = parsed?.message || parsed?.explanation || content;
  const modeIcon = parsed?.mode === "strategy" ? <CheckCircle className="w-3.5 h-3.5 text-primary" /> :
    parsed?.mode === "error" ? <AlertTriangle className="w-3.5 h-3.5 text-destructive" /> : null;

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`} data-testid={`chat-bubble-${role}`}>
      <div className={`max-w-[85%] px-4 py-2.5 ${isUser ? "bg-primary/15 border border-primary/30" : "bg-secondary/60 border border-border"}`}>
        {!isUser && modeIcon && (
          <div className="flex items-center gap-1.5 mb-1">
            {modeIcon}
            <span className="mono-label text-[10px] uppercase">{parsed?.mode}</span>
          </div>
        )}
        <p className="text-sm text-foreground whitespace-pre-wrap">{displayMessage}</p>
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

const StrategyJsonPreview = ({ draft }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(draft, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!draft) return (
    <div className="flex items-center justify-center h-full text-muted-foreground">
      <p className="text-sm font-mono text-center">Strategy JSON will appear here<br />as the AI builds it.</p>
    </div>
  );

  return (
    <div className="relative h-full">
      <Button variant="ghost" size="icon" className="absolute top-0 right-0 z-10" onClick={handleCopy} data-testid="copy-json-btn">
        {copied ? <Check className="w-4 h-4 text-primary" /> : <Copy className="w-4 h-4" />}
      </Button>
      <pre className="text-xs font-mono text-foreground overflow-auto h-full p-1 whitespace-pre-wrap" data-testid="strategy-json-preview">
        {JSON.stringify(draft, null, 2)}
      </pre>
    </div>
  );
};

export default function StrategyPlayground({ onClose, onStrategyCreated }) {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [strategyDraft, setStrategyDraft] = useState(null);
  const [finalizing, setFinalizing] = useState(false);
  const [finalized, setFinalized] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    startSession();
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const startSession = async () => {
    try {
      const res = await axios.post(`${API_URL}/v1/session/start`, {}, getAuthHeaders());
      setSessionId(res.data.session_id);
      setMessages([{
        role: "assistant",
        content: JSON.stringify({
          mode: "question",
          message: "Welcome to the Strategy Playground! Describe your trading idea and I'll help you build a structured strategy.\n\nFor example:\n- \"Buy RELIANCE when RSI crosses above 30\"\n- \"Golden cross strategy on INFY with 5% stop loss\"\n- \"Supertrend buy signal on TCS daily\"",
          fields_needed: []
        })
      }]);
    } catch (err) {
      console.error("Failed to start session:", err);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || !sessionId || sending) return;
    const userMsg = input.trim();
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: userMsg }]);
    setSending(true);

    try {
      const res = await axios.post(
        `${API_URL}/v1/session/${sessionId}/message`,
        { message: userMsg },
        getAuthHeaders()
      );
      const data = res.data;
      setMessages(prev => [...prev, { role: "assistant", content: data.content }]);
      if (data.strategy_draft) {
        setStrategyDraft(data.strategy_draft);
      }
    } catch (err) {
      const errMsg = err.response?.data?.detail || "Failed to send message.";
      setMessages(prev => [...prev, {
        role: "assistant",
        content: JSON.stringify({ mode: "error", message: errMsg })
      }]);
    } finally {
      setSending(false);
    }
  };

  const handleFinalize = async () => {
    if (!sessionId || finalizing) return;
    setFinalizing(true);
    try {
      const res = await axios.post(`${API_URL}/v1/session/${sessionId}/finalize`, {}, getAuthHeaders());
      setFinalized(true);
      setMessages(prev => [...prev, {
        role: "assistant",
        content: JSON.stringify({
          mode: "strategy",
          message: `Strategy saved! ID: ${res.data.strategy_id}. ${res.data.message}`
        })
      }]);
      if (onStrategyCreated) onStrategyCreated();
    } catch (err) {
      const errMsg = err.response?.data?.detail || "Failed to finalize strategy.";
      setMessages(prev => [...prev, {
        role: "assistant",
        content: JSON.stringify({ mode: "error", message: errMsg })
      }]);
    } finally {
      setFinalizing(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="space-y-4" data-testid="strategy-playground">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-primary/20 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h2 className="text-lg font-mono font-bold text-foreground">AI Strategy Playground</h2>
            <p className="text-xs text-muted-foreground">Chat with AI to build your strategy in real-time</p>
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} data-testid="close-playground">
          <X className="w-5 h-5" />
        </Button>
      </div>

      {/* Main Content: Chat + JSON Preview */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4" style={{ minHeight: "480px" }}>
        {/* Chat Panel */}
        <Card className="border-border bg-card lg:col-span-3 flex flex-col">
          <CardHeader className="py-3 px-4 border-b border-border">
            <CardTitle className="text-xs font-mono text-muted-foreground">CONVERSATION</CardTitle>
          </CardHeader>
          <CardContent className="flex-1 overflow-y-auto p-4 space-y-0" style={{ maxHeight: "380px" }}>
            {messages.map((m, i) => (
              <ChatBubble key={i} role={m.role} content={m.content} />
            ))}
            {sending && (
              <div className="flex justify-start mb-3">
                <div className="bg-secondary/60 border border-border px-4 py-3">
                  <Loader2 className="w-4 h-4 animate-spin text-primary" />
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </CardContent>
          <div className="p-3 border-t border-border">
            <div className="flex gap-2">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={finalized ? "Strategy finalized. Start a new session." : "Describe your trading idea..."}
                disabled={sending || finalized || !sessionId}
                className="font-mono text-sm"
                data-testid="playground-chat-input"
              />
              <Button onClick={sendMessage} disabled={sending || !input.trim() || finalized} size="icon" data-testid="playground-send-btn">
                <Send className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </Card>

        {/* JSON Preview Panel */}
        <Card className="border-border bg-card lg:col-span-2 flex flex-col">
          <CardHeader className="py-3 px-4 border-b border-border">
            <div className="flex items-center justify-between">
              <CardTitle className="text-xs font-mono text-muted-foreground">STRATEGY JSON</CardTitle>
              {strategyDraft && !finalized && (
                <Button size="sm" onClick={handleFinalize} disabled={finalizing} className="font-mono text-[10px] uppercase gap-1.5 h-7" data-testid="finalize-strategy-btn">
                  {finalizing ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
                  {finalizing ? "Saving..." : "Save Strategy"}
                </Button>
              )}
              {finalized && (
                <span className="text-[10px] font-mono text-primary flex items-center gap-1">
                  <CheckCircle className="w-3 h-3" /> SAVED
                </span>
              )}
            </div>
          </CardHeader>
          <CardContent className="flex-1 overflow-hidden p-3" style={{ maxHeight: "420px" }}>
            <StrategyJsonPreview draft={strategyDraft} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
