import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp, Loader2, ArrowLeft } from "lucide-react";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (password !== confirm) { setError("Passwords don't match"); return; }
    if (password.length < 8) { setError("Password must be at least 8 characters"); return; }
    setLoading(true);
    try {
      await register(email, password);
      navigate("/login", { replace: true });
    } catch (err) {
      setError(err.response?.data?.detail || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4" data-testid="register-page">
      <Card className="w-full max-w-sm border-border bg-card">
        <CardHeader className="text-center pb-2">
          <Link to="/" className="flex items-center justify-center gap-2 mb-4">
            <TrendingUp className="w-6 h-6 text-primary" />
            <span className="font-mono font-bold text-foreground tracking-wide">TEXT2TRADE</span>
          </Link>
          <CardTitle className="font-mono text-lg">Create Account</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <p className="text-xs text-destructive font-mono text-center p-2 bg-destructive/10 border border-destructive/30" data-testid="register-error">{error}</p>
            )}
            <div>
              <label className="mono-label text-[10px] mb-1 block">EMAIL</label>
              <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required className="font-mono text-sm" data-testid="register-email-input" />
            </div>
            <div>
              <label className="mono-label text-[10px] mb-1 block">PASSWORD</label>
              <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required className="font-mono text-sm" data-testid="register-password-input" />
            </div>
            <div>
              <label className="mono-label text-[10px] mb-1 block">CONFIRM PASSWORD</label>
              <Input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required className="font-mono text-sm" data-testid="register-confirm-input" />
            </div>
            <Button type="submit" className="w-full font-mono text-xs uppercase tracking-wider" disabled={loading} data-testid="register-submit-button">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Create Account"}
            </Button>
          </form>
          <p className="text-center text-xs text-muted-foreground mt-4">
            Already have an account? <Link to="/login" className="text-primary hover:underline" data-testid="link-to-login">Sign In</Link>
          </p>
          <Link to="/" className="flex items-center justify-center gap-1 text-xs text-muted-foreground mt-3 hover:text-foreground">
            <ArrowLeft className="w-3 h-3" /> Back to home
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
