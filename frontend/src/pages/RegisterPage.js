import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { TrendingUp, Play, UserPlus, ArrowRight } from "lucide-react";
import axios from "axios";
import { extractApiError } from "@/utils/apiError";

const API = process.env.REACT_APP_BACKEND_URL + "/api/v1";

export default function RegisterPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleRegister = async (startDemo) => {
    setError("");
    if (!email || !password) { setError("Email and password are required"); return; }
    if (password !== confirmPassword) { setError("Passwords do not match"); return; }
    if (password.length < 8) { setError("Password must be at least 8 characters"); return; }

    setLoading(true);
    try {
      await axios.post(`${API}/auth/register`, { email, password, start_demo: startDemo });
      const userData = await login(email, password);
      navigate(userData?.role === "admin" ? "/admin" : "/dashboard");
    } catch (err) {
      setError(extractApiError(err, "Registration failed"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <Card className="w-full max-w-md border-border bg-card" data-testid="register-card">
        <CardContent className="p-6 sm:p-8">
          <div className="flex items-center gap-2 mb-6">
            <TrendingUp className="w-5 h-5 text-primary" />
            <span className="font-mono font-bold text-foreground">Text2trade</span>
          </div>

          <h1 className="text-xl font-bold text-foreground mb-1">Create Your Account</h1>
          <p className="text-xs text-muted-foreground mb-6 font-mono">Start building AI-powered trading strategies</p>

          {error && (
            <div className="bg-destructive/10 border border-destructive/30 text-destructive text-xs font-mono p-3 mb-4" data-testid="register-error">
              {error}
            </div>
          )}

          <div className="space-y-3 mb-6">
            <div>
              <label className="text-[10px] text-muted-foreground font-mono block mb-1">EMAIL</label>
              <Input
                type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com" className="font-mono text-sm"
                data-testid="register-email"
              />
            </div>
            <div>
              <label className="text-[10px] text-muted-foreground font-mono block mb-1">PASSWORD</label>
              <Input
                type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                placeholder="Min 8 characters" className="font-mono text-sm"
                data-testid="register-password"
              />
            </div>
            <div>
              <label className="text-[10px] text-muted-foreground font-mono block mb-1">CONFIRM PASSWORD</label>
              <Input
                type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Repeat password" className="font-mono text-sm"
                data-testid="register-confirm-password"
              />
            </div>
          </div>

          {/* Dual CTAs */}
          <div className="space-y-3">
            <Button
              onClick={() => handleRegister(true)} disabled={loading}
              className="w-full font-mono text-xs uppercase gap-2 h-11"
              data-testid="register-demo-btn"
            >
              <Play className="w-3.5 h-3.5" />
              {loading ? "Creating..." : "Start Free Demo"}
            </Button>
            <div className="relative">
              <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-border" /></div>
              <div className="relative flex justify-center"><span className="px-2 bg-card text-[10px] text-muted-foreground font-mono">or</span></div>
            </div>
            <Button
              variant="outline" onClick={() => handleRegister(false)} disabled={loading}
              className="w-full font-mono text-xs uppercase gap-2 h-10"
              data-testid="register-real-btn"
            >
              <UserPlus className="w-3.5 h-3.5" />
              Create Account
            </Button>
          </div>

          <div className="mt-4 p-3 border border-border bg-card/50">
            <p className="text-[10px] text-muted-foreground font-mono leading-relaxed">
              <span className="text-primary font-bold">Demo mode</span> gives you 10,000 virtual capital, 3 pre-built strategies, and a guided tour. You can switch to real mode anytime.
            </p>
          </div>

          <p className="mt-5 text-center text-xs text-muted-foreground font-mono">
            Already have an account?{" "}
            <Link to="/login" className="text-primary hover:underline" data-testid="login-link">Sign in</Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
