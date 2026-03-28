import { useAuth } from "@/context/AuthContext";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Clock } from "lucide-react";

export default function SessionExpiredModal() {
  const { sessionExpired, dismissSessionExpired } = useAuth();
  const navigate = useNavigate();

  if (!sessionExpired) return null;

  return (
    <div className="fixed inset-0 z-[200] bg-black/80 flex items-center justify-center p-4" data-testid="session-expired-modal">
      <Card className="w-full max-w-sm border-border bg-card">
        <CardContent className="p-8 text-center">
          <Clock className="w-10 h-10 text-amber-400 mx-auto mb-4" />
          <h2 className="text-lg font-mono font-bold text-foreground mb-2">Session Expired</h2>
          <p className="text-xs text-muted-foreground font-mono mb-6">
            Your session has expired. Please log in again to continue.
          </p>
          <Button
            className="w-full font-mono text-xs uppercase"
            onClick={() => { dismissSessionExpired(); navigate("/login"); }}
            data-testid="session-expired-login-btn"
          >
            Log In
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
