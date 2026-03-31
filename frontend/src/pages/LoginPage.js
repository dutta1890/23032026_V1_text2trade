import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp, Loader2, ArrowLeft, Eye, EyeOff } from "lucide-react";
import { extractApiError } from "@/utils/apiError";
import LegalFooter from "@/components/LegalFooter";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const decoded = await login(email, password);
      if (decoded?.role === "admin") {
        navigate("/admin/dashboard", { replace: true });
      } else {
        navigate("/dashboard", { replace: true });
      }
    } catch (err) {
      setError(extractApiError(err, "Login failed"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4" data-testid="login-page">
      <Card className="w-full max-w-sm border-border bg-card">
        <CardHeader className="text-center pb-2">
          <Link to="/" className="flex items-center justify-center gap-2 mb-4">
            <TrendingUp className="w-6 h-6 text-primary" />
            <span className="font-mono font-bold text-foreground tracking-wide">TEXT2TRADE</span>
          </Link>
          <CardTitle className="font-mono text-lg">Sign In</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <p className="text-xs text-destructive font-mono text-center p-2 bg-destructive/10 border border-destructive/30" data-testid="login-error">{error}</p>
            )}
            <div>
              <label className="mono-label text-[10px] mb-1 block">EMAIL</label>
              <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required className="font-mono text-sm" data-testid="login-email-input" />
            </div>
            <div>
              <label className="mono-label text-[10px] mb-1 block">PASSWORD</label>
              <div className="relative">
                <Input type={showPassword ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} required className="font-mono text-sm pr-9" data-testid="login-password-input" />
                <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors" data-testid="login-toggle-password">
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
            <Button type="submit" className="w-full font-mono text-xs uppercase tracking-wider" disabled={loading} data-testid="login-submit-button">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Sign In"}
            </Button>
          </form>
          <p className="text-center text-xs text-muted-foreground mt-4">
            No account? <Link to="/register" className="text-primary hover:underline" data-testid="link-to-register">Register</Link>
            <span className="mx-2">·</span>
            <Link to="/forgot-password" className="text-primary hover:underline" data-testid="link-to-forgot">Forgot Password?</Link>
          </p>
          <Link to="/" className="flex items-center justify-center gap-1 text-xs text-muted-foreground mt-3 hover:text-foreground">
            <ArrowLeft className="w-3 h-3" /> Back to home
          </Link>
          <div className="mt-4"><LegalFooter /></div>
        </CardContent>
      </Card>
    </div>
  );
}
