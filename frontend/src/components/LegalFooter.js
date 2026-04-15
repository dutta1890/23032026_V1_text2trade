import { Link } from "react-router-dom";

const APP_VERSION = process.env.REACT_APP_VERSION || "0.2.1";

export default function LegalFooter() {
  return (
    <div className="flex items-center justify-center gap-4 text-[10px] font-mono text-muted-foreground" data-testid="legal-footer">
      <Link to="/legal/terms" className="hover:text-primary transition-colors">Terms</Link>
      <span className="text-border">|</span>
      <Link to="/legal/privacy" className="hover:text-primary transition-colors">Privacy</Link>
      <span className="text-border">|</span>
      <Link to="/legal/disclaimer" className="hover:text-primary transition-colors">Disclaimer</Link>
      <span className="text-border">|</span>
      <Link to="/compliance" className="hover:text-primary transition-colors">Compliance</Link>
      <span className="text-border">|</span>
      <span data-testid="app-version">v{APP_VERSION}</span>
    </div>
  );
}
