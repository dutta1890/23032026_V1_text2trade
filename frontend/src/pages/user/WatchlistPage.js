import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useApi } from "@/hooks/useApi";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Loader2, Eye, Trash2, Bookmark, Clock, Search, Hammer
} from "lucide-react";
import { toast } from "sonner";
import { PageSkeleton } from "@/components/LoadingSkeleton";

export default function WatchlistPage() {
  const api = useApi();
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [removing, setRemoving] = useState(null);

  useEffect(() => {
    document.title = "Watchlist | Text2trade";
    api.get("/watchlist")
      .then((r) => setItems(r.data.watchlist || []))
      .finally(() => setLoading(false));
  }, []);

  const handleRemove = async (itemId) => {
    setRemoving(itemId);
    try {
      await api.del(`/watchlist/${itemId}`);
      setItems((p) => p.filter((x) => x.item_id !== itemId));
      toast.success("Removed from watchlist");
    } catch {
      toast.error("Failed to remove");
    } finally {
      setRemoving(null);
    }
  };

  if (loading) return <PageSkeleton />;

  return (
    <div className="space-y-6" data-testid="watchlist-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">Watchlist</h1>
          <p className="text-sm text-muted-foreground mt-1">Saved stocks from screener scans.</p>
        </div>
        <Button variant="outline" size="sm" className="font-mono text-xs uppercase gap-1.5" onClick={() => navigate("/screener")} data-testid="go-screener-btn">
          <Search className="w-3 h-3" /> Scan Stocks
        </Button>
      </div>

      {items.length === 0 ? (
        <Card className="border-border border-dashed bg-card/50" data-testid="empty-watchlist">
          <CardContent className="p-8 text-center">
            <Bookmark className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
            <h3 className="font-mono font-bold text-foreground mb-1">No stocks watched</h3>
            <p className="text-xs text-muted-foreground mb-4">Run a screener scan and add matching stocks to your watchlist.</p>
            <Button size="sm" className="font-mono text-xs uppercase gap-1.5" onClick={() => navigate("/screener")}>
              <Search className="w-3 h-3" /> Go to Screener
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {items.map((item) => (
            <Card key={item.item_id} className="border-border bg-card hover:border-primary/30 transition-colors" data-testid={`watchlist-item-${item.symbol}`}>
              <CardContent className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-4 flex-1 min-w-0">
                  <div className="w-10 h-10 flex items-center justify-center bg-primary/10 border border-primary/20 shrink-0">
                    <span className="font-mono text-[10px] font-bold text-primary">{item.symbol?.slice(0, 3)}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-mono font-bold text-sm text-foreground">{item.symbol}</p>
                    <div className="flex flex-wrap items-center gap-2 mt-0.5">
                      {item.preset_name && (
                        <span className="text-[10px] font-mono px-1.5 py-0.5 bg-blue-500/10 text-blue-400 border border-blue-500/20">{item.preset_name}</span>
                      )}
                      {item.note && <span className="text-[10px] text-muted-foreground font-mono truncate">{item.note}</span>}
                    </div>
                    {item.indicator_values && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {Object.entries(item.indicator_values).filter(([k]) => k !== "close").slice(0, 4).map(([k, v]) => (
                          <span key={k} className="text-[10px] font-mono px-1 py-0.5 bg-secondary/40 text-muted-foreground">
                            {k}: {typeof v === "number" ? v.toFixed(2) : v}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2 ml-2 shrink-0">
                  <span className="text-[10px] font-mono text-muted-foreground flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {item.created_at ? new Date(item.created_at).toLocaleDateString() : "—"}
                  </span>
                  <Button variant="outline" size="sm" className="h-7 font-mono text-[10px] gap-1" onClick={() => navigate(`/build?symbol=${item.symbol}`)} data-testid={`build-${item.symbol}`}>
                    <Hammer className="w-3 h-3" /> Build
                  </Button>
                  <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive" onClick={() => handleRemove(item.item_id)} disabled={removing === item.item_id} data-testid={`remove-${item.symbol}`}>
                    {removing === item.item_id ? <Loader2 className="w-3 h-3 animate-spin" /> : <Trash2 className="w-3 h-3" />}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
