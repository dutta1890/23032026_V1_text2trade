import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { X, Loader2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL + "/api/v1";

const TITLES = {
  terms: "Terms of Service",
  privacy: "Privacy Policy",
  disclaimer: "Risk Disclaimer",
};

export default function LegalDocModal({ docType, onClose }) {
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!docType) return;
    setLoading(true);
    axios
      .get(`${API}/legal/${docType}`)
      .then((res) => setContent(res.data.content_md))
      .catch(() => setContent("Failed to load document."))
      .finally(() => setLoading(false));
  }, [docType]);

  if (!docType) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-card border border-border w-full max-w-2xl max-h-[80vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
        data-testid={`legal-modal-${docType}`}
      >
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h3 className="font-mono font-bold text-foreground">{TITLES[docType] || docType}</h3>
          <button onClick={onClose} data-testid="close-legal-modal">
            <X className="w-4 h-4 text-muted-foreground hover:text-foreground" />
          </button>
        </div>
        <ScrollArea className="flex-1 p-5 overflow-y-auto" style={{ maxHeight: "65vh" }}>
          {loading ? (
            <div className="flex justify-center py-10"><Loader2 className="w-5 h-5 animate-spin text-primary" /></div>
          ) : (
            <article className="prose prose-invert prose-sm max-w-none font-mono legal-content">
              <ReactMarkdown>{content}</ReactMarkdown>
            </article>
          )}
        </ScrollArea>
        <div className="p-3 border-t border-border flex justify-end">
          <Button variant="outline" size="sm" onClick={onClose} className="font-mono text-xs">
            Close
          </Button>
        </div>
      </div>
    </div>
  );
}
