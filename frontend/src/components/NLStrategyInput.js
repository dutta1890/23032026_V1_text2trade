import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Loader2, Sparkles, Check, X, AlertCircle } from "lucide-react";
import axios from "axios";

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function NLStrategyInput({ onConfirm, onCancel }) {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [parsed, setParsed] = useState(null);
  const [error, setError] = useState("");

  const handleParse = async () => {
    if (!text.trim()) return;
    setLoading(true);
    setError("");
    setParsed(null);
    
    try {
      const res = await axios.post(`${API_URL}/parse-strategy`, { text });
      if (res.data.success && res.data.parsed) {
        setParsed(res.data.parsed);
      } else {
        setError(res.data.error || "Failed to parse strategy");
      }
    } catch (err) {
      setError("Parse request failed");
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = () => {
    if (parsed) onConfirm?.(parsed);
  };

  const formatCondition = (c) => `${c.name}(${JSON.stringify(c.params || {})}) ${c.operator} ${c.value}`;

  return (
    <div className="space-y-4" data-testid="nl-strategy-input">
      <div className="space-y-2">
        <label className="mono-label">Describe your strategy</label>
        <Textarea
          placeholder="e.g., Buy when RSI drops below 30, sell when RSI goes above 70. Use 2% stop loss and 5% target."
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={4}
          className="font-mono text-sm"
          disabled={loading}
          data-testid="nl-input"
        />
      </div>

      <Button onClick={handleParse} disabled={loading || !text.trim()} className="gap-2" data-testid="nl-parse-btn">
        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
        {loading ? "Parsing..." : "Parse Strategy"}
      </Button>

      {error && (
        <div className="p-3 bg-destructive/10 border border-destructive/50 text-destructive text-sm flex items-center gap-2" data-testid="nl-error">
          <AlertCircle className="w-4 h-4" /> {error}
        </div>
      )}

      {parsed && (
        <Card className="border-primary/50 bg-primary/5" data-testid="nl-preview">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-mono">Extracted Strategy</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div>
              <span className="mono-label">Entry Conditions</span>
              {parsed.entry_conditions?.length > 0 ? (
                <ul className="mt-1 space-y-1">
                  {parsed.entry_conditions.map((c, i) => (
                    <li key={i} className="font-mono text-xs text-foreground">{formatCondition(c)}</li>
                  ))}
                </ul>
              ) : <p className="text-muted-foreground text-xs">None specified</p>}
            </div>

            <div>
              <span className="mono-label">Exit Conditions</span>
              {parsed.exit_conditions?.length > 0 ? (
                <ul className="mt-1 space-y-1">
                  {parsed.exit_conditions.map((c, i) => (
                    <li key={i} className="font-mono text-xs text-foreground">{formatCondition(c)}</li>
                  ))}
                </ul>
              ) : <p className="text-muted-foreground text-xs">None specified</p>}
            </div>

            <div>
              <span className="mono-label">Risk Management</span>
              <p className="font-mono text-xs text-foreground mt-1">
                SL: {parsed.risk_management?.stop_loss ?? "—"}% | TP: {parsed.risk_management?.take_profit ?? parsed.risk_management?.target ?? "—"}%
              </p>
            </div>

            <div className="flex gap-2 pt-2 border-t border-border">
              <Button size="sm" onClick={handleConfirm} className="gap-1" data-testid="nl-confirm-btn">
                <Check className="w-4 h-4" /> Use This
              </Button>
              <Button size="sm" variant="outline" onClick={() => setParsed(null)} data-testid="nl-edit-btn">
                Edit
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="flex justify-end">
        <Button variant="ghost" onClick={onCancel} data-testid="nl-cancel-btn">
          <X className="w-4 h-4 mr-1" /> Cancel
        </Button>
      </div>
    </div>
  );
}
