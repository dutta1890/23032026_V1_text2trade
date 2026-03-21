import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ArrowLeft, Loader2, CheckCircle } from "lucide-react";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL + "/api/v1";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [resetToken, setResetToken] = useState("");
  const [error, setError] = useState("");

  useEffect(() => { document.title = "Forgot Password | Text2trade"; }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await axios.post(`${API}/auth/forgot-password`, { email });
      setSent(true);
      if (res.data.reset_token) setResetToken(res.data.reset_token);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to send reset link");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4" data-testid="forgot-password-page">
      <Card className="w-full max-w-md border-border bg-card">
        <CardContent className="p-8">
          <h1 className="text-xl font-mono font-bold text-foreground mb-2">Forgot Password</h1>
          <p className="text-xs text-muted-foreground font-mono mb-6">
            Enter your email and we'll generate a reset token.
          </p>

          {!sent ? (
            <form onSubmit={handleSubmit} className="space-y-4">
              <Input
                type="email" placeholder="your@email.com" value={email}
                onChange={(e) => setEmail(e.target.value)} required
                className="font-mono text-xs"
                data-testid="forgot-email-input"
              />
              {error && <p className="text-xs text-destructive font-mono">{error}</p>}
              <Button type="submit" className="w-full font-mono text-xs uppercase gap-2" disabled={loading} data-testid="forgot-submit-btn">
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                {loading ? "Sending..." : "Send Reset Token"}
              </Button>
            </form>
          ) : (
            <div className="space-y-4" data-testid="forgot-success">
              <div className="flex items-center gap-2 text-primary">
                <CheckCircle className="w-5 h-5" />
                <p className="text-sm font-mono font-bold">Reset token generated</p>
              </div>
              {resetToken && (
                <div className="p-3 bg-secondary/30 border border-border">
                  <p className="mono-label text-[10px] mb-1">YOUR RESET TOKEN (valid 1 hour)</p>
                  <p className="font-mono text-xs text-primary break-all" data-testid="reset-token-display">{resetToken}</p>
                </div>
              )}
              <Button asChild variant="outline" className="w-full font-mono text-xs uppercase">
                <Link to={`/reset-password${resetToken ? `?token=${resetToken}` : ""}`}>
                  Reset Password
                </Link>
              </Button>
            </div>
          )}

          <div className="mt-6 text-center">
            <Link to="/login" className="text-xs font-mono text-primary hover:underline flex items-center justify-center gap-1">
              <ArrowLeft className="w-3 h-3" /> Back to Login
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
