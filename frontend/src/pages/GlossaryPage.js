import { useState, useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Search, BookOpen, ArrowLeft, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL + "/api/v1";

const CATEGORY_LABELS = {
  indicator: "Indicators",
  risk_management: "Risk Management",
  order_type: "Order Types",
  general: "General Concepts",
  strategy_concept: "Strategy Concepts",
};

const CATEGORY_COLORS = {
  indicator: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  risk_management: "bg-red-500/15 text-red-400 border-red-500/30",
  order_type: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  general: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  strategy_concept: "bg-purple-500/15 text-purple-400 border-purple-500/30",
};

export default function GlossaryPage() {
  const [entries, setEntries] = useState([]);
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    document.title = "Trading Glossary | Text2trade";
    axios
      .get(`${API}/knowledge`)
      .then((res) => setEntries(res.data.entries || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const categories = useMemo(() => {
    const cats = new Set(entries.map((e) => e.category));
    return ["all", ...Array.from(cats).sort()];
  }, [entries]);

  const filtered = useMemo(() => {
    let list = entries;
    if (activeCategory !== "all") {
      list = list.filter((e) => e.category === activeCategory);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (e) =>
          e.term.toLowerCase().includes(q) ||
          e.short_description.toLowerCase().includes(q) ||
          e.term_id.toLowerCase().includes(q)
      );
    }
    return list;
  }, [entries, search, activeCategory]);

  const grouped = useMemo(() => {
    const groups = {};
    filtered.forEach((e) => {
      if (!groups[e.category]) groups[e.category] = [];
      groups[e.category].push(e);
    });
    return groups;
  }, [filtered]);

  return (
    <div className="min-h-screen bg-background" data-testid="glossary-page">
      {/* Header */}
      <div className="border-b border-border bg-card">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
          <div className="flex items-center gap-3 mb-4">
            <Link to="/dashboard">
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                data-testid="glossary-back-btn"
              >
                <ArrowLeft className="w-4 h-4" />
              </Button>
            </Link>
            <div className="flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-primary" />
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
                Trading Glossary
              </h1>
            </div>
          </div>
          <p className="text-sm text-muted-foreground mb-5 ml-11">
            {entries.length} trading terms explained in plain language with
            real-world examples.
          </p>

          {/* Search + Filter */}
          <div className="flex flex-col sm:flex-row gap-3 ml-11">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search terms..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9 font-mono text-sm"
                data-testid="glossary-search"
              />
            </div>
            <div className="flex flex-wrap gap-1.5">
              {categories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setActiveCategory(cat)}
                  className={`px-2.5 py-1 text-[11px] font-mono border transition-colors ${
                    activeCategory === cat
                      ? "bg-primary/15 text-primary border-primary/40"
                      : "bg-secondary/30 text-muted-foreground border-border hover:border-primary/30"
                  }`}
                  data-testid={`glossary-filter-${cat}`}
                >
                  {cat === "all"
                    ? `All (${entries.length})`
                    : `${CATEGORY_LABELS[cat] || cat} (${
                        entries.filter((e) => e.category === cat).length
                      })`}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-5 h-5 border-2 border-primary border-t-transparent animate-spin rounded-full" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-20">
            <p className="text-muted-foreground font-mono text-sm">
              No terms match your search.
            </p>
          </div>
        ) : (
          <div className="space-y-8">
            {Object.entries(grouped)
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([category, terms]) => (
                <div key={category}>
                  <h2 className="text-xs font-mono font-bold text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-2">
                    <span
                      className={`inline-block px-2 py-0.5 border ${
                        CATEGORY_COLORS[category] || "bg-secondary text-foreground border-border"
                      }`}
                    >
                      {CATEGORY_LABELS[category] || category}
                    </span>
                    <span className="text-muted-foreground/50">
                      {terms.length} term{terms.length !== 1 ? "s" : ""}
                    </span>
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {terms.map((entry) => (
                      <Card
                        key={entry.term_id}
                        className="border-border bg-card hover:border-primary/30 transition-colors"
                        data-testid={`glossary-term-${entry.term_id}`}
                      >
                        <CardContent className="p-4">
                          <div className="flex items-start justify-between gap-2 mb-2">
                            <h3 className="font-mono text-sm font-bold text-foreground">
                              {entry.term}
                            </h3>
                            {entry.learn_more_url && (
                              <a
                                href={entry.learn_more_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-muted-foreground hover:text-primary transition-colors"
                              >
                                <ExternalLink className="w-3.5 h-3.5" />
                              </a>
                            )}
                          </div>
                          <p className="text-[12px] leading-relaxed text-muted-foreground mb-2">
                            {entry.short_description}
                          </p>
                          {entry.example && (
                            <div className="bg-secondary/30 border border-border/50 p-2.5 mt-2">
                              <p className="text-[10px] font-mono text-muted-foreground/70 uppercase mb-1">
                                Example
                              </p>
                              <p className="text-[11px] leading-relaxed text-muted-foreground italic">
                                {entry.example}
                              </p>
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              ))}
          </div>
        )}
      </div>
    </div>
  );
}
