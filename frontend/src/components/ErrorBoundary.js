import { Component } from "react";
import { Button } from "@/components/ui/button";
import { AlertTriangle, RefreshCw } from "lucide-react";

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error("ErrorBoundary caught:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-center justify-center min-h-[400px] px-4" data-testid="error-boundary">
          <div className="text-center max-w-md">
            <AlertTriangle className="w-10 h-10 text-destructive mx-auto mb-4" />
            <h2 className="text-xl font-mono font-bold text-foreground mb-2">Something went wrong</h2>
            <p className="text-sm text-muted-foreground mb-4">
              {this.state.error?.message || "An unexpected error occurred."}
            </p>
            <Button
              variant="outline"
              className="font-mono text-xs uppercase gap-2"
              onClick={() => { this.setState({ hasError: false, error: null }); window.location.reload(); }}
              data-testid="error-reload-btn"
            >
              <RefreshCw className="w-3 h-3" /> Reload Page
            </Button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
