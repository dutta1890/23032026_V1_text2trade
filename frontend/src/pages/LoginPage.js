/**
 * Text2trade Login Page
 * =====================
 * Static login form mockup.
 * No actual authentication logic - just UI scaffold.
 * Form has basic client-side validation for UX demo.
 */

import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle 
} from "@/components/ui/card";
import { TrendingUp, ArrowLeft, Eye, EyeOff } from "lucide-react";

/**
 * Login Page Component
 * Static form mockup with basic validation feedback.
 */
export default function LoginPage() {
  // State for form inputs (mockup only)
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  
  // Navigation hook for redirect after "login"
  const navigate = useNavigate();
  
  /**
   * Handle form submission
   * This is a mockup - just validates and redirects to dashboard.
   * No actual authentication happens.
   */
  const handleSubmit = (e) => {
    e.preventDefault();
    setError("");
    
    // Basic validation (mockup)
    if (!email.trim()) {
      setError("Email is required");
      return;
    }
    
    if (!password.trim()) {
      setError("Password is required");
      return;
    }
    
    // Email format check (basic)
    if (!email.includes("@")) {
      setError("Please enter a valid email");
      return;
    }
    
    // Mockup success - redirect to dashboard
    // In a real app, this would call an auth API
    navigate("/dashboard");
  };
  
  return (
    <div 
      className="min-h-screen bg-background flex items-center justify-center px-6 py-12"
      data-testid="login-page"
    >
      <div className="w-full max-w-md">
        {/* Back to home link */}
        <Link 
          to="/" 
          className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground mb-8 transition-colors"
          data-testid="login-back-link"
        >
          <ArrowLeft className="w-4 h-4" />
          <span className="text-sm">Back to home</span>
        </Link>
        
        {/* Login Card */}
        <Card className="border-border bg-card" data-testid="login-card">
          <CardHeader className="space-y-4">
            {/* Logo */}
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-primary flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-primary-foreground" />
              </div>
              <span className="font-mono font-bold text-lg">TEXT2TRADE</span>
            </div>
            
            {/* Title */}
            <div>
              <CardTitle className="text-2xl font-bold">
                Welcome back
              </CardTitle>
              <CardDescription className="text-muted-foreground mt-1">
                Enter your credentials to access your account
              </CardDescription>
            </div>
          </CardHeader>
          
          <CardContent>
            {/* Login Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Error message */}
              {error && (
                <div 
                  className="p-3 border border-destructive/50 bg-destructive/10 text-destructive text-sm"
                  data-testid="login-error"
                >
                  {error}
                </div>
              )}
              
              {/* Email field */}
              <div className="space-y-2">
                <label 
                  htmlFor="email" 
                  className="mono-label"
                >
                  Email
                </label>
                <Input
                  id="email"
                  type="email"
                  placeholder="trader@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="bg-background border-border font-mono input-glow"
                  data-testid="login-email-input"
                />
              </div>
              
              {/* Password field */}
              <div className="space-y-2">
                <label 
                  htmlFor="password" 
                  className="mono-label"
                >
                  Password
                </label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="bg-background border-border font-mono pr-10 input-glow"
                    data-testid="login-password-input"
                  />
                  {/* Toggle password visibility */}
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                    data-testid="login-toggle-password"
                  >
                    {showPassword ? (
                      <EyeOff className="w-4 h-4" />
                    ) : (
                      <Eye className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>
              
              {/* Submit button */}
              <Button 
                type="submit"
                className="w-full font-mono text-sm uppercase tracking-wider btn-hover"
                data-testid="login-submit-button"
              >
                Sign In
              </Button>
            </form>
            
            {/* Divider */}
            <div className="relative my-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-border"></div>
              </div>
              <div className="relative flex justify-center">
                <span className="bg-card px-2 mono-label">OR</span>
              </div>
            </div>
            
            {/* Additional info */}
            <p className="text-center text-sm text-muted-foreground">
              Don't have an account?{" "}
              <span className="text-primary cursor-pointer link-underline">
                Contact admin
              </span>
            </p>
          </CardContent>
        </Card>
        
        {/* Footer note */}
        <p className="text-center mt-6 mono-label">
          // DEMO MODE - NO AUTH REQUIRED
        </p>
      </div>
    </div>
  );
}
