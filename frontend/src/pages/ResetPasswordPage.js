import { useState, useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loader2, CheckCircle, ArrowLeft } from "lucide-react";
import axios from "axios";

const API = process.env.REACT_APP_BACKEND_URL + "/api/v1";

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const [token, setToken] = useState(searchParams.get("token") || "");
  const [newPassword, setNewPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { document.title = "Reset Password | Text2trade"; }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (newPassword !== confirm) {
      setError("Passwords do not match");
      return;
    }
    setLoading(true);
    try {
      await axios.post(`${API}/auth/reset-password`, { token, new_password: newPassword });
      setDone(true);
    } catch (err) {
      setError(err.response?.data?.detail || "Reset failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4" data-testid="reset-password-page">
      <Card className="w-full max-w-md border-border bg-card">
        <CardContent className="p-8">
          <h1 className="text-xl font-mono font-bold text-foreground mb-2">Reset Password</h1>

          {!done ? (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="mono-label text-[10px] mb-1 block">RESET TOKEN</label>
                <Input value={token} onChange={(e) => setToken(e.target.value)} required
                  className="font-mono text-xs" placeholder="Paste your reset token"
                  data-testid="reset-token-input"
                />
              </div>
              <div>
                <label className="mono-label text-[10px] mb-1 block">NEW PASSWORD</label>
                <Input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required
                  className="font-mono text-xs" placeholder="Min 8 chars, 1 number, 1 special"
                  data-testid="reset-newpw-input"
                />
              </div>
              <div>
                <label className="mono-label text-[10px] mb-1 block">CONFIRM PASSWORD</label>
                <Input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required
                  className="font-mono text-xs"
                  data-testid="reset-confirmpw-input"
                />
              </div>
              {error && <p className="text-xs text-destructive font-mono">{error}</p>}
              <Button type="submit" className="w-full font-mono text-xs uppercase gap-2" disabled={loading} data-testid="reset-submit-btn">
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                {loading ? "Resetting..." : "Reset Password"}
              </Button>
            </form>
          ) : (
            <div className="space-y-4 text-center" data-testid="reset-success">
              <CheckCircle className="w-10 h-10 text-primary mx-auto" />
              <p className="font-mono text-sm font-bold text-foreground">Password reset successful</p>
              <Button asChild className="w-full font-mono text-xs uppercase">
                <Link to="/login">Go to Login</Link>
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
