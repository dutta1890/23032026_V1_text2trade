import { useEffect } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { ArrowLeft, AlertTriangle } from "lucide-react";

export default function NotFoundPage() {
  useEffect(() => { document.title = "404 | Text2trade"; }, []);

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4" data-testid="not-found-page">
      <div className="text-center max-w-md">
        <AlertTriangle className="w-12 h-12 text-yellow-500 mx-auto mb-4" />
        <h1 className="text-5xl font-mono font-bold text-foreground mb-2">404</h1>
        <p className="text-lg font-mono text-muted-foreground mb-6">Page not found. The route you requested doesn't exist.</p>
        <div className="flex gap-3 justify-center">
          <Button asChild className="font-mono text-xs uppercase gap-2">
            <Link to="/dashboard"><ArrowLeft className="w-3 h-3" /> Dashboard</Link>
          </Button>
          <Button variant="outline" asChild className="font-mono text-xs uppercase">
            <Link to="/">Home</Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
