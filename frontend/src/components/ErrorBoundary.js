import { Component } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { AlertTriangle, LayoutDashboard, FileText, ChevronDown, ChevronUp } from "lucide-react";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL + "/api/v1";

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null, reported: false, showDetails: false };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    this.reportCrash(error, errorInfo);
  }

  reportCrash = async (error, errorInfo) => {
    try {
      const userRaw = localStorage.getItem("t2t_user");
      const user = userRaw ? JSON.parse(userRaw) : null;

      await axios.post(`${API}/diagnostics/frontend-crash`, {
        error_message: error?.message || String(error),
        component_stack: errorInfo?.componentStack || "",
        page_url: window.location.href,
        browser_info: navigator.userAgent,
        user_id: user?.user_id || null,
        timestamp: new Date().toISOString(),
      });
      this.setState({ reported: true });
    } catch {
      // Crash report failed — don't crash the crash handler
    }
  };

  render() {
    if (this.state.hasError) {
      const { error, errorInfo, reported, showDetails } = this.state;
      return (
        <div className="min-h-screen bg-background flex items-center justify-center p-4" data-testid="error-boundary">
          <Card className="w-full max-w-lg border-border bg-card">
            <CardContent className="p-8 text-center">
              <AlertTriangle className="w-12 h-12 text-destructive mx-auto mb-4" />
              <h2 className="text-xl font-mono font-bold text-foreground mb-2">Something went wrong</h2>
              <p className="text-sm text-muted-foreground font-mono mb-6">
                {reported
                  ? "Our team has been notified. We're looking into it."
                  : "An unexpected error occurred."}
              </p>

              <div className="flex items-center justify-center gap-3 mb-4">
                <Button
                  className="font-mono text-xs uppercase gap-2"
                  onClick={() => { window.location.href = "/dashboard"; }}
                  data-testid="error-go-dashboard"
                >
                  <LayoutDashboard className="w-3.5 h-3.5" /> Go to Dashboard
                </Button>
                <Button
                  variant="outline"
                  className="font-mono text-xs uppercase gap-2"
                  onClick={() => this.setState((s) => ({ showDetails: !s.showDetails }))}
                  data-testid="error-report-details"
                >
                  <FileText className="w-3.5 h-3.5" />
                  Report Details
                  {showDetails ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                </Button>
              </div>

              {showDetails && (
                <div className="text-left mt-4 p-4 bg-background border border-border overflow-auto max-h-64" data-testid="error-details-panel">
                  <p className="text-xs font-mono text-destructive mb-2 break-all">{error?.message || "Unknown error"}</p>
                  {errorInfo?.componentStack && (
                    <pre className="text-[10px] font-mono text-muted-foreground whitespace-pre-wrap break-all">
                      {errorInfo.componentStack}
                    </pre>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      );
    }
    return this.props.children;
  }
}
