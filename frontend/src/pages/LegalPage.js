import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { TrendingUp, ArrowLeft, Loader2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL + "/api/v1";

const TITLES = {
  terms: "Terms of Service",
  privacy: "Privacy Policy",
  disclaimer: "Risk Disclaimer",
};

export default function LegalPage() {
  const { docType } = useParams();
  const [content, setContent] = useState("");
  const [version, setVersion] = useState("");
  const [effectiveDate, setEffectiveDate] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const endpoint = docType === "disclaimer" ? "disclaimer" : docType;
    axios
      .get(`${API}/legal/${endpoint}`)
      .then((res) => {
        setContent(res.data.content_md);
        setVersion(res.data.version);
        setEffectiveDate(res.data.effective_date);
      })
      .catch(() => setContent("# Document not found"))
      .finally(() => setLoading(false));
  }, [docType]);

  return (
    <div className="min-h-screen bg-background">
      <nav className="border-b border-border bg-card px-6 py-4 flex items-center gap-4">
        <Link to="/" className="flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-primary" />
          <span className="font-mono font-bold text-foreground">Text2trade</span>
        </Link>
        <span className="text-muted-foreground">/</span>
        <span className="font-mono text-sm text-muted-foreground">{TITLES[docType] || "Legal"}</span>
      </nav>

      <div className="max-w-3xl mx-auto p-6 sm:p-10">
        <Link to="/" className="inline-flex items-center gap-1 text-xs font-mono text-muted-foreground hover:text-primary mb-6">
          <ArrowLeft className="w-3 h-3" /> Back to home
        </Link>

        {loading ? (
          <div className="flex justify-center py-20"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>
        ) : (
          <>
            {version && (
              <p className="text-[10px] font-mono text-muted-foreground mb-4" data-testid="legal-version">
                Version {version} {effectiveDate && `| Effective ${new Date(effectiveDate).toLocaleDateString()}`}
              </p>
            )}
            <article className="prose prose-invert prose-sm max-w-none font-mono legal-content" data-testid="legal-content">
              <ReactMarkdown>{content}</ReactMarkdown>
            </article>
          </>
        )}
      </div>

      <footer className="border-t border-border px-6 py-4 text-center">
        <div className="flex items-center justify-center gap-4 text-[10px] font-mono text-muted-foreground">
          <Link to="/legal/terms" className="hover:text-primary">Terms</Link>
          <span>|</span>
          <Link to="/legal/privacy" className="hover:text-primary">Privacy</Link>
          <span>|</span>
          <Link to="/legal/disclaimer" className="hover:text-primary">Disclaimer</Link>
        </div>
      </footer>
    </div>
  );
}
