import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import { Checkbox } from "@/components/ui/checkbox";
import { AlertTriangle, ExternalLink, Loader2 } from "lucide-react";

const BROKERS = [
  { id: "zerodha", name: "Zerodha Kite", url: "https://kite.zerodha.com/", desc: "Opens Zerodha Kite web trading platform" },
  { id: "angel_one", name: "Angel One", url: "https://trade.angelone.in/", desc: "Opens Angel One web trading platform" },
  { id: "upstox", name: "Upstox", url: "https://pro.upstox.com/", desc: "Opens Upstox Pro web trading platform" },
  { id: "dhan", name: "Dhan", url: "https://web.dhan.co/", desc: "Opens Dhan web trading platform" },
  { id: "groww", name: "Groww", url: "https://groww.in/stocks", desc: "Opens Groww stocks section" },
  { id: "5paisa", name: "5paisa", url: "https://trade.5paisa.com/", desc: "Opens 5paisa web trading platform" },
];

export default function BrokerModal({
  open,
  onClose,
  symbol = "",
  strategyId = "",
  api = null,
  preferredBroker = "",
  disclaimerDismissed = false,
  onPreferenceChange = null,
}) {
  const [step, setStep] = useState(disclaimerDismissed ? "select" : "disclaimer");
  const [dontShowAgain, setDontShowAgain] = useState(false);
  const [logging, setLogging] = useState(false);

  useEffect(() => {
    if (open) {
      setStep(disclaimerDismissed ? "select" : "disclaimer");
    }
  }, [open, disclaimerDismissed]);

  const handleAcceptDisclaimer = () => {
    if (dontShowAgain && onPreferenceChange) {
      onPreferenceChange(true);
    }
    setStep("select");
  };

  const handleBrokerClick = async (broker) => {
    // Log to audit trail if api available
    if (api) {
      setLogging(true);
      try {
        await api.post("/broker-link/generate", {
          broker: broker.id,
          symbol,
          strategy_id: strategyId,
        });
      } catch {
        // non-blocking — still open the link
      }
      setLogging(false);
    }
    window.open(broker.url, "_blank", "noopener,noreferrer");
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-lg bg-card border-border" data-testid="broker-modal">
        {step === "disclaimer" ? (
          <>
            <DialogHeader>
              <div className="flex items-center gap-2 mb-1">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
                <DialogTitle className="font-mono text-base">Important</DialogTitle>
              </div>
              <DialogDescription className="text-xs text-muted-foreground sr-only">Broker link disclaimer</DialogDescription>
            </DialogHeader>
            <div className="space-y-3 py-2" data-testid="broker-disclaimer">
              <p className="text-sm text-foreground">
                Clicking will open your broker's website. You must review and confirm the order yourself.
                We do not execute trades.
              </p>
              <ul className="text-xs text-muted-foreground space-y-1.5 list-disc pl-4">
                <li>Verify symbol, quantity, and price before confirming</li>
                <li>Ensure sufficient funds in your broker account</li>
                <li>Our backtest has known limitations (see methodology)</li>
                <li>Past performance does not guarantee future results</li>
              </ul>
              <div className="flex items-center gap-2 pt-2">
                <Checkbox
                  id="dont-show"
                  checked={dontShowAgain}
                  onCheckedChange={setDontShowAgain}
                  data-testid="dont-show-checkbox"
                />
                <label htmlFor="dont-show" className="text-xs font-mono text-muted-foreground cursor-pointer">
                  Don't show this again
                </label>
              </div>
            </div>
            <DialogFooter className="gap-2">
              <Button variant="outline" size="sm" className="font-mono text-xs" onClick={onClose} data-testid="disclaimer-cancel">
                Cancel
              </Button>
              <Button size="sm" className="font-mono text-xs" onClick={handleAcceptDisclaimer} data-testid="disclaimer-continue">
                Continue to Broker
              </Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle className="font-mono text-base">Execute on Your Broker</DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground">
                Select your broker to open their trading platform
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-2 py-2" data-testid="broker-list">
              {BROKERS.map((b) => (
                <button
                  key={b.id}
                  onClick={() => handleBrokerClick(b)}
                  disabled={logging}
                  className={`w-full flex items-center justify-between p-3 border transition-colors text-left ${
                    preferredBroker === b.id
                      ? "border-primary bg-primary/10"
                      : "border-border bg-secondary/20 hover:border-primary/50 hover:bg-secondary/40"
                  }`}
                  data-testid={`broker-option-${b.id}`}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-bold text-foreground">{b.name}</span>
                      {preferredBroker === b.id && (
                        <span className="text-[9px] font-mono text-primary px-1 py-0.5 bg-primary/15 border border-primary/30">
                          PREFERRED
                        </span>
                      )}
                    </div>
                    <p className="text-[10px] font-mono text-muted-foreground mt-0.5">{b.desc}</p>
                  </div>
                  <ExternalLink className="w-4 h-4 text-muted-foreground shrink-0 ml-2" />
                </button>
              ))}
            </div>
            {logging && (
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Loader2 className="w-3 h-3 animate-spin" /> Opening...
              </div>
            )}
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
