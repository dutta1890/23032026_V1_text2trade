import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { TrendingUp, CheckCircle2, ArrowLeft } from "lucide-react";
import axios from "axios";
import { extractApiError } from "@/utils/apiError";

const API = process.env.REACT_APP_BACKEND_URL + "/api/v1";

export default function ResetPasswordPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [email, setEmail] = useState(searchParams.get("email") || "");
  const [otp, setOtp] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !otp || !password) { setError("All fields are required"); return; }
    if (password !== confirmPassword) { setError("Passwords don't match"); return; }
    if (password.length < 8) { setError("Password must be at least 8 characters"); return; }
    setLoading(true);
    setError("");
    try {
      await axios.post(`${API}/auth/reset-password`, { email, otp, new_password: password });
      setSuccess(true);
    } catch (err) {
      setError(extractApiError(err, "Reset failed. Check your OTP."));
    } finally { setLoading(false); }
  };

  if (success) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <Card className="w-full max-w-md border-border bg-card" data-testid="reset-success">
          <CardContent className="p-6 sm:p-8 text-center">
            <CheckCircle2 className="w-10 h-10 text-primary mx-auto mb-4" />
            <h2 className="font-bold text-foreground mb-2">Password Reset</h2>
            <p className="text-xs text-muted-foreground font-mono mb-4">Your password has been reset successfully.</p>
            <Button onClick={() => navigate("/login")} className="font-mono text-xs uppercase" data-testid="go-login-btn">
              Go to Login
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <Card className="w-full max-w-md border-border bg-card" data-testid="reset-form">
        <CardContent className="p-6 sm:p-8">
          <div className="flex items-center gap-2 mb-6">
            <TrendingUp className="w-5 h-5 text-primary" />
            <span className="font-mono font-bold text-foreground">Text2trade</span>
          </div>
          <h1 className="text-xl font-bold text-foreground mb-1">Reset Password</h1>
          <p className="text-xs text-muted-foreground mb-6 font-mono">Enter the 6-digit OTP sent to your email and set a new password.</p>

          {error && <div className="bg-destructive/10 border border-destructive/30 text-destructive text-xs font-mono p-3 mb-4" data-testid="reset-error">{error}</div>}

          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label className="text-[10px] text-muted-foreground font-mono block mb-1">EMAIL</label>
              <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com" className="font-mono text-sm" data-testid="reset-email" />
            </div>
            <div>
              <label className="text-[10px] text-muted-foreground font-mono block mb-1">6-DIGIT OTP</label>
              <Input value={otp} onChange={(e) => setOtp(e.target.value)} maxLength={6}
                placeholder="123456" className="font-mono text-sm tracking-[0.3em] text-center" data-testid="reset-otp" />
            </div>
            <div>
              <label className="text-[10px] text-muted-foreground font-mono block mb-1">NEW PASSWORD</label>
              <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                placeholder="Min 8 characters" className="font-mono text-sm" data-testid="reset-password" />
            </div>
            <div>
              <label className="text-[10px] text-muted-foreground font-mono block mb-1">CONFIRM PASSWORD</label>
              <Input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)}
                className="font-mono text-sm" data-testid="reset-confirm" />
            </div>
            <Button type="submit" disabled={loading} className="w-full font-mono text-xs uppercase" data-testid="reset-submit">
              {loading ? "Resetting..." : "Reset Password"}
            </Button>
          </form>
          <p className="mt-4 text-center text-xs text-muted-foreground font-mono">
            <Link to="/login" className="text-primary hover:underline flex items-center gap-1 justify-center">
              <ArrowLeft className="w-3 h-3" /> Back to login
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
