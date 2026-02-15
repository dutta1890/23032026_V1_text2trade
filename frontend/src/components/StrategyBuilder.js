import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ChevronLeft, ChevronRight, Check, TrendingUp, Loader2 } from "lucide-react";
import axios from "axios";

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STEPS = ["Market", "Instrument", "Timeframe", "Entry", "Exit", "Risk"];

const MARKETS = [
  { value: "crypto", label: "Crypto" },
  { value: "forex", label: "Forex" },
  { value: "stocks", label: "Stocks" },
];

const EXCHANGES = {
  crypto: ["binance", "coinbase", "kraken"],
  forex: ["oanda", "forex.com"],
  stocks: ["nasdaq", "nyse"],
};

const TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"];

const OPERATORS = [
  { value: ">", label: "Greater than (>)" },
  { value: "<", label: "Less than (<)" },
  { value: ">=", label: "Greater or equal (>=)" },
  { value: "<=", label: "Less or equal (<=)" },
  { value: "==", label: "Equal (==)" },
  { value: "crosses_above", label: "Crosses above" },
  { value: "crosses_below", label: "Crosses below" },
  { value: "bullish_cross", label: "Bullish cross" },
  { value: "bearish_cross", label: "Bearish cross" },
];

const INDICATORS = [
  { value: "RSI", label: "RSI", type: "rsi" },
  { value: "SMA", label: "SMA", type: "ma" },
  { value: "EMA", label: "EMA", type: "ma" },
  { value: "MACD", label: "MACD", type: "macd" },
];

const initialStrategy = {
  metadata: { name: "", description: "" },
  market: { type: "", exchange: "" },
  instrument: { symbol: "", base: "", quote: "" },
  timeframe: { interval: "" },
  entry_conditions: [],
  exit_conditions: [],
  risk_management: { stop_loss: "", take_profit: "" },
};

export default function StrategyBuilder({ onClose, onSave }) {
  const [step, setStep] = useState(0);
  const [strategy, setStrategy] = useState(initialStrategy);
  const [entryIndicator, setEntryIndicator] = useState({ type: "RSI", period: "14", short: "9", long: "21", fast: "12", slow: "26", signal: "9", operator: "<", value: "30" });
  const [exitIndicator, setExitIndicator] = useState({ enabled: false, type: "RSI", period: "14", short: "9", long: "21", fast: "12", slow: "26", signal: "9", operator: ">", value: "70" });
  const [saving, setSaving] = useState(false);

  const getIndicatorType = (name) => INDICATORS.find(i => i.value === name)?.type || "rsi";

  const updateStrategy = (section, field, value) => {
    setStrategy(prev => ({
      ...prev,
      [section]: { ...prev[section], [field]: value }
    }));
  };

  const nextStep = () => step < STEPS.length - 1 && setStep(step + 1);
  const prevStep = () => step > 0 && setStep(step - 1);

  const buildCondition = (ind) => {
    const indType = getIndicatorType(ind.type);
    let params = {};
    if (indType === "rsi") params = { period: parseInt(ind.period) };
    else if (indType === "ma") params = { short: parseInt(ind.short), long: parseInt(ind.long) };
    else if (indType === "macd") params = { fast: parseInt(ind.fast), slow: parseInt(ind.slow), signal: parseInt(ind.signal) };
    
    return {
      name: ind.type,
      params,
      operator: ind.operator,
      value: ind.type === "RSI" ? parseFloat(ind.value) : null
    };
  };

  const formatIndicator = (ind) => {
    const indType = getIndicatorType(ind.type);
    if (indType === "rsi") return `${ind.type}(${ind.period})`;
    if (indType === "ma") return `${ind.type}(${ind.short}/${ind.long})`;
    if (indType === "macd") return `MACD(${ind.fast}/${ind.slow}/${ind.signal})`;
    return ind.type;
  };

  const handleSave = async () => {
    const entry_conditions = [buildCondition(entryIndicator)];
    const exit_conditions = exitIndicator.enabled ? [buildCondition(exitIndicator)] : [];

    const finalStrategy = {
      version: "1.0",
      ...strategy,
      entry_conditions,
      exit_conditions,
      filters: [],
      risk_management: {
        stop_loss: parseFloat(strategy.risk_management.stop_loss) || null,
        take_profit: parseFloat(strategy.risk_management.take_profit) || null
      }
    };

    setSaving(true);
    try {
      const res = await axios.post(`${API_URL}/strategy`, finalStrategy);
      onSave?.(res.data.strategy);
    } catch (err) {
      console.error("Save failed:", err);
    } finally {
      setSaving(false);
    }
  };

  const renderStep = () => {
    switch (step) {
      case 0: // Market
        return (
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="mono-label">Market Type</label>
              <Select value={strategy.market.type} onValueChange={(v) => updateStrategy("market", "type", v)}>
                <SelectTrigger data-testid="select-market-type"><SelectValue placeholder="Select market" /></SelectTrigger>
                <SelectContent>
                  {MARKETS.map(m => <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            {strategy.market.type && (
              <div className="space-y-2">
                <label className="mono-label">Exchange</label>
                <Select value={strategy.market.exchange} onValueChange={(v) => updateStrategy("market", "exchange", v)}>
                  <SelectTrigger data-testid="select-exchange"><SelectValue placeholder="Select exchange" /></SelectTrigger>
                  <SelectContent>
                    {EXCHANGES[strategy.market.type]?.map(e => <SelectItem key={e} value={e}>{e.toUpperCase()}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>
        );

      case 1: // Instrument
        return (
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="mono-label">Symbol</label>
              <Input
                placeholder="BTCUSDT"
                value={strategy.instrument.symbol}
                onChange={(e) => updateStrategy("instrument", "symbol", e.target.value.toUpperCase())}
                className="font-mono"
                data-testid="input-symbol"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="mono-label">Base</label>
                <Input
                  placeholder="BTC"
                  value={strategy.instrument.base}
                  onChange={(e) => updateStrategy("instrument", "base", e.target.value.toUpperCase())}
                  className="font-mono"
                  data-testid="input-base"
                />
              </div>
              <div className="space-y-2">
                <label className="mono-label">Quote</label>
                <Input
                  placeholder="USDT"
                  value={strategy.instrument.quote}
                  onChange={(e) => updateStrategy("instrument", "quote", e.target.value.toUpperCase())}
                  className="font-mono"
                  data-testid="input-quote"
                />
              </div>
            </div>
          </div>
        );

      case 2: // Timeframe
        return (
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="mono-label">Timeframe</label>
              <Select value={strategy.timeframe.interval} onValueChange={(v) => updateStrategy("timeframe", "interval", v)}>
                <SelectTrigger data-testid="select-timeframe"><SelectValue placeholder="Select timeframe" /></SelectTrigger>
                <SelectContent>
                  {TIMEFRAMES.map(tf => <SelectItem key={tf} value={tf}>{tf}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="mono-label">Strategy Name</label>
              <Input
                placeholder="My RSI Strategy"
                value={strategy.metadata.name}
                onChange={(e) => updateStrategy("metadata", "name", e.target.value)}
                data-testid="input-strategy-name"
              />
            </div>
          </div>
        );

      case 3: // Entry
        return (
          <div className="space-y-4">
            <Card className="border-primary/50 bg-primary/5">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-mono flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-primary" /> Entry Condition
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <label className="mono-label">Indicator</label>
                  <Select value={entryIndicator.type} onValueChange={(v) => setEntryIndicator(p => ({ ...p, type: v }))}>
                    <SelectTrigger data-testid="select-entry-indicator"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {INDICATORS.map(ind => <SelectItem key={ind.value} value={ind.value}>{ind.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                {getIndicatorType(entryIndicator.type) === "rsi" && (
                  <div className="space-y-2">
                    <label className="mono-label">Period</label>
                    <Input
                      type="number"
                      value={entryIndicator.period}
                      onChange={(e) => setEntryIndicator(p => ({ ...p, period: e.target.value }))}
                      className="font-mono"
                      data-testid="input-entry-period"
                    />
                  </div>
                )}
                {getIndicatorType(entryIndicator.type) === "ma" && (
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <label className="mono-label">Short Period</label>
                      <Input
                        type="number"
                        value={entryIndicator.short}
                        onChange={(e) => setEntryIndicator(p => ({ ...p, short: e.target.value }))}
                        className="font-mono"
                        data-testid="input-entry-short"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="mono-label">Long Period</label>
                      <Input
                        type="number"
                        value={entryIndicator.long}
                        onChange={(e) => setEntryIndicator(p => ({ ...p, long: e.target.value }))}
                        className="font-mono"
                        data-testid="input-entry-long"
                      />
                    </div>
                  </div>
                )}
                {getIndicatorType(entryIndicator.type) === "macd" && (
                  <div className="grid grid-cols-3 gap-3">
                    <div className="space-y-2">
                      <label className="mono-label">Fast</label>
                      <Input
                        type="number"
                        value={entryIndicator.fast}
                        onChange={(e) => setEntryIndicator(p => ({ ...p, fast: e.target.value }))}
                        className="font-mono"
                        data-testid="input-entry-fast"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="mono-label">Slow</label>
                      <Input
                        type="number"
                        value={entryIndicator.slow}
                        onChange={(e) => setEntryIndicator(p => ({ ...p, slow: e.target.value }))}
                        className="font-mono"
                        data-testid="input-entry-slow"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="mono-label">Signal</label>
                      <Input
                        type="number"
                        value={entryIndicator.signal}
                        onChange={(e) => setEntryIndicator(p => ({ ...p, signal: e.target.value }))}
                        className="font-mono"
                        data-testid="input-entry-signal"
                      />
                    </div>
                  </div>
                )}
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="mono-label">Operator</label>
                    <Select value={entryIndicator.operator} onValueChange={(v) => setEntryIndicator(p => ({ ...p, operator: v }))}>
                      <SelectTrigger data-testid="select-entry-operator"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {OPERATORS.map(op => <SelectItem key={op.value} value={op.value}>{op.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  {getIndicatorType(entryIndicator.type) === "rsi" && (
                    <div className="space-y-2">
                      <label className="mono-label">Value</label>
                      <Input
                        type="number"
                        value={entryIndicator.value}
                        onChange={(e) => setEntryIndicator(p => ({ ...p, value: e.target.value }))}
                        className="font-mono"
                        data-testid="input-entry-value"
                      />
                    </div>
                  )}
                </div>
                <p className="text-xs text-muted-foreground">
                  Entry when {formatIndicator(entryIndicator)} {entryIndicator.operator} {entryIndicator.type === "RSI" ? entryIndicator.value : "price"}
                </p>
              </CardContent>
            </Card>
          </div>
        );

      case 4: // Exit
        return (
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="exit-enabled"
                checked={exitIndicator.enabled}
                onChange={(e) => setExitIndicator(p => ({ ...p, enabled: e.target.checked }))}
                className="w-4 h-4 accent-primary"
                data-testid="checkbox-exit-enabled"
              />
              <label htmlFor="exit-enabled" className="mono-label cursor-pointer">Enable Indicator Exit</label>
            </div>
            {exitIndicator.enabled && (
              <Card className="border-destructive/50 bg-destructive/5">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-mono">Exit Condition</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <label className="mono-label">Indicator</label>
                    <Select value={exitIndicator.type} onValueChange={(v) => setExitIndicator(p => ({ ...p, type: v }))}>
                      <SelectTrigger data-testid="select-exit-indicator"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {INDICATORS.map(ind => <SelectItem key={ind.value} value={ind.value}>{ind.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  {getIndicatorType(exitIndicator.type) === "rsi" && (
                    <div className="space-y-2">
                      <label className="mono-label">Period</label>
                      <Input
                        type="number"
                        value={exitIndicator.period}
                        onChange={(e) => setExitIndicator(p => ({ ...p, period: e.target.value }))}
                        className="font-mono"
                        data-testid="input-exit-period"
                      />
                    </div>
                  )}
                  {getIndicatorType(exitIndicator.type) === "ma" && (
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <label className="mono-label">Short Period</label>
                        <Input
                          type="number"
                          value={exitIndicator.short}
                          onChange={(e) => setExitIndicator(p => ({ ...p, short: e.target.value }))}
                          className="font-mono"
                          data-testid="input-exit-short"
                        />
                      </div>
                      <div className="space-y-2">
                        <label className="mono-label">Long Period</label>
                        <Input
                          type="number"
                          value={exitIndicator.long}
                          onChange={(e) => setExitIndicator(p => ({ ...p, long: e.target.value }))}
                          className="font-mono"
                          data-testid="input-exit-long"
                        />
                      </div>
                    </div>
                  )}
                  {getIndicatorType(exitIndicator.type) === "macd" && (
                    <div className="grid grid-cols-3 gap-3">
                      <div className="space-y-2">
                        <label className="mono-label">Fast</label>
                        <Input
                          type="number"
                          value={exitIndicator.fast}
                          onChange={(e) => setExitIndicator(p => ({ ...p, fast: e.target.value }))}
                          className="font-mono"
                          data-testid="input-exit-fast"
                        />
                      </div>
                      <div className="space-y-2">
                        <label className="mono-label">Slow</label>
                        <Input
                          type="number"
                          value={exitIndicator.slow}
                          onChange={(e) => setExitIndicator(p => ({ ...p, slow: e.target.value }))}
                          className="font-mono"
                          data-testid="input-exit-slow"
                        />
                      </div>
                      <div className="space-y-2">
                        <label className="mono-label">Signal</label>
                        <Input
                          type="number"
                          value={exitIndicator.signal}
                          onChange={(e) => setExitIndicator(p => ({ ...p, signal: e.target.value }))}
                          className="font-mono"
                          data-testid="input-exit-signal"
                        />
                      </div>
                    </div>
                  )}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <label className="mono-label">Operator</label>
                      <Select value={exitIndicator.operator} onValueChange={(v) => setExitIndicator(p => ({ ...p, operator: v }))}>
                        <SelectTrigger data-testid="select-exit-operator"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {OPERATORS.map(op => <SelectItem key={op.value} value={op.value}>{op.label}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </div>
                    {exitIndicator.type === "RSI" && (
                      <div className="space-y-2">
                        <label className="mono-label">Value</label>
                        <Input
                          type="number"
                          value={exitIndicator.value}
                          onChange={(e) => setExitIndicator(p => ({ ...p, value: e.target.value }))}
                          className="font-mono"
                          data-testid="input-exit-value"
                        />
                      </div>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Exit when {formatIndicator(exitIndicator)} {exitIndicator.operator} {exitIndicator.type === "RSI" ? exitIndicator.value : "price"}
                  </p>
                </CardContent>
              </Card>
            )}
            {!exitIndicator.enabled && (
              <p className="text-sm text-muted-foreground">Exit will be based on risk management (stop loss / target) only.</p>
            )}
          </div>
        );

      case 5: // Risk
        return (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="mono-label">Stop Loss (%)</label>
                <Input
                  type="number"
                  placeholder="2"
                  value={strategy.risk_management.stop_loss}
                  onChange={(e) => updateStrategy("risk_management", "stop_loss", e.target.value)}
                  className="font-mono"
                  data-testid="input-stop-loss"
                />
              </div>
              <div className="space-y-2">
                <label className="mono-label">Take Profit (%)</label>
                <Input
                  type="number"
                  placeholder="5"
                  value={strategy.risk_management.take_profit}
                  onChange={(e) => updateStrategy("risk_management", "take_profit", e.target.value)}
                  className="font-mono"
                  data-testid="input-take-profit"
                />
              </div>
            </div>
            <Card className="border-border bg-secondary/30">
              <CardContent className="p-4">
                <h4 className="font-mono font-bold text-sm mb-2">Strategy Summary</h4>
                <div className="space-y-1 text-xs text-muted-foreground font-mono">
                  <p>Name: {strategy.metadata.name || "Unnamed"}</p>
                  <p>Market: {strategy.market.type} / {strategy.market.exchange}</p>
                  <p>Symbol: {strategy.instrument.symbol}</p>
                  <p>Timeframe: {strategy.timeframe.interval}</p>
                  <p>Entry: {formatIndicator(entryIndicator)} {entryIndicator.operator} {entryIndicator.type === "RSI" ? entryIndicator.value : "price"}</p>
                  {exitIndicator.enabled && <p>Exit: {formatIndicator(exitIndicator)} {exitIndicator.operator} {exitIndicator.type === "RSI" ? exitIndicator.value : "price"}</p>}
                  <p>SL: {strategy.risk_management.stop_loss || "-"}% / TP: {strategy.risk_management.take_profit || "-"}%</p>
                </div>
              </CardContent>
            </Card>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="space-y-6" data-testid="strategy-builder">
      {/* Progress */}
      <div className="flex items-center gap-2">
        {STEPS.map((s, i) => (
          <div key={s} className="flex items-center">
            <div
              className={`w-8 h-8 flex items-center justify-center text-xs font-mono ${
                i < step ? "bg-primary text-primary-foreground" :
                i === step ? "bg-primary text-primary-foreground" :
                "bg-secondary text-muted-foreground"
              }`}
            >
              {i < step ? <Check className="w-4 h-4" /> : i + 1}
            </div>
            {i < STEPS.length - 1 && <div className={`w-8 h-0.5 ${i < step ? "bg-primary" : "bg-secondary"}`} />}
          </div>
        ))}
      </div>

      {/* Step Title */}
      <div>
        <h2 className="text-xl font-bold">{STEPS[step]}</h2>
        <p className="text-sm text-muted-foreground">Step {step + 1} of {STEPS.length}</p>
      </div>

      {/* Content */}
      <div className="min-h-[280px]">{renderStep()}</div>

      {/* Navigation */}
      <div className="flex items-center justify-between pt-4 border-t border-border">
        <Button variant="outline" onClick={onClose} data-testid="btn-cancel">Cancel</Button>
        <div className="flex gap-2">
          {step > 0 && (
            <Button variant="outline" onClick={prevStep} data-testid="btn-prev">
              <ChevronLeft className="w-4 h-4 mr-1" /> Back
            </Button>
          )}
          {step < STEPS.length - 1 ? (
            <Button onClick={nextStep} data-testid="btn-next">
              Next <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          ) : (
            <Button onClick={handleSave} disabled={saving} data-testid="btn-save">
              {saving ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : <Check className="w-4 h-4 mr-1" />}
              {saving ? "Saving..." : "Save Strategy"}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
