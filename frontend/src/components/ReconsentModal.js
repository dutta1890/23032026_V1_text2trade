import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Loader2, FileText, CheckCircle2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL + "/api/v1";

const DOC_LABELS = {
  terms: "Terms of Service",
  privacy: "Privacy Policy",
  disclaimer: "Risk Disclaimer",
};

export default function ReconsentModal() {
  const { token, logout } = useAuth();
  const [pending, setPending] = useState({});
  const [loading, setLoading] = useState(true);
  const [currentDoc, setCurrentDoc] = useState(null);
  const [docContent, setDocContent] = useState("");
  const [accepting, setAccepting] = useState(false);
  const [accepted, setAccepted] = useState(new Set());

  const checkConsent = useCallback(async () => {
    if (!token) return;
    try {
      const res = await axios.get(`${API}/legal/consent-status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.data.all_accepted) {
        setPending({});
      } else {
        setPending(res.data.pending);
        // Auto-open first pending doc
        const types = Object.keys(res.data.pending);
        if (types.length > 0 && !currentDoc) {
          loadDocument(types[0], res.data.pending[types[0]]);
        }
      }
    } catch {
      setPending({});
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { checkConsent(); }, [checkConsent]);

  const loadDocument = async (docType) => {
    setCurrentDoc(docType);
    try {
      const res = await axios.get(`${API}/legal/${docType}`);
      setDocContent(res.data.content_md);
    } catch {
      setDocContent("Failed to load document.");
    }
  };

  const handleAccept = async () => {
    if (!currentDoc || !pending[currentDoc]) return;
    setAccepting(true);
    try {
      await axios.post(`${API}/legal/accept`, {
        document_type: currentDoc,
        document_version: pending[currentDoc],
      }, { headers: { Authorization: `Bearer ${token}` } });

      const newAccepted = new Set(accepted);
      newAccepted.add(currentDoc);
      setAccepted(newAccepted);

      const remainingTypes = Object.keys(pending).filter((t) => !newAccepted.has(t));
      if (remainingTypes.length > 0) {
        loadDocument(remainingTypes[0]);
      } else {
        // All accepted — re-check and close
        await checkConsent();
      }
    } catch {
      // Ignore errors
    } finally {
      setAccepting(false);
    }
  };

  if (loading) return null;

  const pendingTypes = Object.keys(pending).filter((t) => !accepted.has(t));
  if (pendingTypes.length === 0) return null;

  return (
    <div className="fixed inset-0 z-[100] bg-black/80 flex items-center justify-center p-4" data-testid="reconsent-modal">
      <div className="bg-card border border-border w-full max-w-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="p-5 border-b border-border">
          <h2 className="font-mono font-bold text-foreground text-lg">Updated Legal Documents</h2>
          <p className="text-xs text-muted-foreground font-mono mt-1">
            We've updated our policies. Please review and accept to continue using Text2trade.
          </p>
          {/* Tabs */}
          <div className="flex gap-2 mt-3">
            {Object.keys(pending).map((t) => (
              <button
                key={t}
                onClick={() => loadDocument(t)}
                className={`px-3 py-1.5 text-[10px] font-mono uppercase border transition-colors flex items-center gap-1.5 ${
                  currentDoc === t
                    ? "border-primary text-primary"
                    : accepted.has(t)
                    ? "border-green-500/30 text-green-400"
                    : "border-border text-muted-foreground hover:text-foreground"
                }`}
                data-testid={`reconsent-tab-${t}`}
              >
                {accepted.has(t) ? <CheckCircle2 className="w-3 h-3" /> : <FileText className="w-3 h-3" />}
                {DOC_LABELS[t] || t}
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <ScrollArea className="flex-1 p-5 overflow-y-auto" style={{ maxHeight: "55vh" }}>
          <article className="prose prose-invert prose-sm max-w-none font-mono legal-content" data-testid="reconsent-content">
            <ReactMarkdown>{docContent}</ReactMarkdown>
          </article>
        </ScrollArea>

        {/* Footer */}
        <div className="p-4 border-t border-border flex items-center justify-between">
          <button
            onClick={logout}
            className="text-xs font-mono text-muted-foreground hover:text-destructive"
            data-testid="reconsent-logout"
          >
            Log out instead
          </button>
          {currentDoc && !accepted.has(currentDoc) ? (
            <Button
              onClick={handleAccept}
              disabled={accepting}
              className="font-mono text-xs uppercase gap-1.5"
              data-testid="reconsent-accept-btn"
            >
              {accepting ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle2 className="w-3 h-3" />}
              I Accept {DOC_LABELS[currentDoc]}
            </Button>
          ) : (
            <span className="text-xs font-mono text-green-400 flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" /> Accepted
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
