import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { TrendingUp, ArrowLeft, Mail } from "lucide-react";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL + "/api/v1";

export default function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email) { setError("Enter your email"); return; }
    setLoading(true);
    setError("");
    try {
      await axios.post(`${API}/auth/forgot-password`, { email });
      setSent(true);
    } catch (err) {
      setError(err.response?.data?.detail || "Something went wrong");
    } finally { setLoading(false); }
  };

  if (sent) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <Card className="w-full max-w-md border-border bg-card" data-testid="forgot-success">
          <CardContent className="p-6 sm:p-8 text-center">
            <Mail className="w-10 h-10 text-primary mx-auto mb-4" />
            <h2 className="font-bold text-foreground mb-2">Check Your Email</h2>
            <p className="text-xs text-muted-foreground font-mono mb-4">
              If an account with <span className="text-foreground">{email}</span> exists, we've sent a 6-digit OTP. It expires in 15 minutes.
            </p>
            <Button onClick={() => navigate(`/reset-password?email=${encodeURIComponent(email)}`)} className="font-mono text-xs uppercase gap-1.5" data-testid="enter-otp-btn">
              Enter OTP
            </Button>
            <p className="mt-4 text-[10px] text-muted-foreground font-mono">
              <Link to="/login" className="text-primary hover:underline">Back to login</Link>
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <Card className="w-full max-w-md border-border bg-card" data-testid="forgot-form">
        <CardContent className="p-6 sm:p-8">
          <div className="flex items-center gap-2 mb-6">
            <TrendingUp className="w-5 h-5 text-primary" />
            <span className="font-mono font-bold text-foreground">Text2trade</span>
          </div>
          <h1 className="text-xl font-bold text-foreground mb-1">Forgot Password</h1>
          <p className="text-xs text-muted-foreground mb-6 font-mono">Enter your email and we'll send a 6-digit OTP to reset your password.</p>

          {error && <div className="bg-destructive/10 border border-destructive/30 text-destructive text-xs font-mono p-3 mb-4" data-testid="forgot-error">{error}</div>}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-[10px] text-muted-foreground font-mono block mb-1">EMAIL</label>
              <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com" className="font-mono text-sm" data-testid="forgot-email" />
            </div>
            <Button type="submit" disabled={loading} className="w-full font-mono text-xs uppercase" data-testid="forgot-submit">
              {loading ? "Sending..." : "Send OTP"}
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
