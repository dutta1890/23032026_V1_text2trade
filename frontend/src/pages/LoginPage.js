/**
 * Text2trade Auth Page
 * ====================
 * Combined Login and Signup page with tab switching.
 * 
 * AUTHENTICATION FLOW (Plain English):
 * 1. User fills in email + password
 * 2. Clicks "Sign In" or "Sign Up"
 * 3. We send the data to the backend API
 * 4. If successful → store email in localStorage → redirect to Dashboard
 * 5. If error → show error message
 * 
 * localStorage is used to remember who's logged in (cleared on logout).
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
import { TrendingUp, ArrowLeft, Eye, EyeOff, Loader2 } from "lucide-react";
import axios from "axios";

// Backend API URL from environment
const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * Auth Page Component
 * Handles both Login and Signup with a tab interface.
 */
export default function LoginPage() {
  // Which tab is active: "login" or "signup"
  const [activeTab, setActiveTab] = useState("login");
  
  // Form input state
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  
  // UI state
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  
  // Navigation hook for redirect after auth
  const navigate = useNavigate();
  
  /**
   * Reset form when switching tabs
   */
  const handleTabSwitch = (tab) => {
    setActiveTab(tab);
    setError("");
    setEmail("");
    setPassword("");
    setConfirmPassword("");
  };
  
  /**
   * Handle Login form submission
   * 
   * Steps:
   * 1. Validate inputs (not empty)
   * 2. Send POST request to /api/login
   * 3. If success → save email to localStorage → go to Dashboard
   * 4. If error → show error message
   */
  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");
    
    if (!email.trim()) { setError("Email is required"); return; }
    if (!email.includes("@")) { setError("Please enter a valid email"); return; }
    if (!password.trim()) { setError("Password is required"); return; }
    
    setLoading(true);
    
    try {
      const response = await axios.post(`${API_URL}/v1/auth/login`, {
        email: email,
        password: password
      });
      
      // Store JWT tokens and email
      localStorage.setItem("accessToken", response.data.access_token);
      localStorage.setItem("refreshToken", response.data.refresh_token);
      localStorage.setItem("userEmail", email);
      
      navigate("/dashboard");
      
    } catch (err) {
      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError("Login failed. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };
  
  /**
   * Handle Signup form submission
   * 
   * Steps:
   * 1. Validate inputs (not empty, passwords match)
   * 2. Send POST request to /api/signup
   * 3. If success → save email to localStorage → go to Dashboard
   * 4. If error → show error message
   */
  const handleSignup = async (e) => {
    e.preventDefault();
    setError("");
    
    if (!email.trim()) { setError("Email is required"); return; }
    if (!email.includes("@")) { setError("Please enter a valid email"); return; }
    if (!password.trim()) { setError("Password is required"); return; }
    if (password.length < 8) { setError("Password must be at least 8 characters"); return; }
    if (!/\d/.test(password)) { setError("Password must contain at least 1 number"); return; }
    if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) { setError("Password must contain at least 1 special character"); return; }
    if (password !== confirmPassword) { setError("Passwords do not match"); return; }
    
    setLoading(true);
    
    try {
      await axios.post(`${API_URL}/v1/auth/register`, {
        email: email,
        password: password
      });
      
      // Auto-login after registration
      const loginRes = await axios.post(`${API_URL}/v1/auth/login`, {
        email: email,
        password: password
      });
      
      localStorage.setItem("accessToken", loginRes.data.access_token);
      localStorage.setItem("refreshToken", loginRes.data.refresh_token);
      localStorage.setItem("userEmail", email);
      
      navigate("/dashboard");
      
    } catch (err) {
      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError("Signup failed. Please try again.");
      }
    } finally {
      setLoading(false);
    }
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
        
        {/* Auth Card */}
        <Card className="border-border bg-card" data-testid="login-card">
          <CardHeader className="space-y-4">
            {/* Logo */}
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-primary flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-primary-foreground" />
              </div>
              <span className="font-mono font-bold text-lg">TEXT2TRADE</span>
            </div>
            
            {/* Tab Buttons */}
            <div className="flex border border-border">
              <button
                type="button"
                onClick={() => handleTabSwitch("login")}
                className={`flex-1 py-2 font-mono text-sm uppercase tracking-wider transition-colors ${
                  activeTab === "login" 
                    ? "bg-primary text-primary-foreground" 
                    : "bg-background text-muted-foreground hover:text-foreground"
                }`}
                data-testid="tab-login"
              >
                Sign In
              </button>
              <button
                type="button"
                onClick={() => handleTabSwitch("signup")}
                className={`flex-1 py-2 font-mono text-sm uppercase tracking-wider transition-colors ${
                  activeTab === "signup" 
                    ? "bg-primary text-primary-foreground" 
                    : "bg-background text-muted-foreground hover:text-foreground"
                }`}
                data-testid="tab-signup"
              >
                Sign Up
              </button>
            </div>
            
            {/* Title - changes based on tab */}
            <div>
              <CardTitle className="text-2xl font-bold">
                {activeTab === "login" ? "Welcome back" : "Create account"}
              </CardTitle>
              <CardDescription className="text-muted-foreground mt-1">
                {activeTab === "login" 
                  ? "Enter your credentials to access your account" 
                  : "Enter your details to create a new account"}
              </CardDescription>
            </div>
          </CardHeader>
          
          <CardContent>
            {/* Login Form */}
            {activeTab === "login" && (
              <form onSubmit={handleLogin} className="space-y-4" data-testid="login-form">
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
                  <label htmlFor="login-email" className="mono-label">
                    Email
                  </label>
                  <Input
                    id="login-email"
                    type="email"
                    placeholder="trader@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="bg-background border-border font-mono input-glow"
                    data-testid="login-email-input"
                    disabled={loading}
                  />
                </div>
                
                {/* Password field */}
                <div className="space-y-2">
                  <label htmlFor="login-password" className="mono-label">
                    Password
                  </label>
                  <div className="relative">
                    <Input
                      id="login-password"
                      type={showPassword ? "text" : "password"}
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="bg-background border-border font-mono pr-10 input-glow"
                      data-testid="login-password-input"
                      disabled={loading}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                      data-testid="login-toggle-password"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
                
                {/* Submit button */}
                <Button 
                  type="submit"
                  className="w-full font-mono text-sm uppercase tracking-wider btn-hover"
                  data-testid="login-submit-button"
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin mr-2" />
                      Signing In...
                    </>
                  ) : (
                    "Sign In"
                  )}
                </Button>
              </form>
            )}
            
            {/* Signup Form */}
            {activeTab === "signup" && (
              <form onSubmit={handleSignup} className="space-y-4" data-testid="signup-form">
                {/* Error message */}
                {error && (
                  <div 
                    className="p-3 border border-destructive/50 bg-destructive/10 text-destructive text-sm"
                    data-testid="signup-error"
                  >
                    {error}
                  </div>
                )}
                
                {/* Email field */}
                <div className="space-y-2">
                  <label htmlFor="signup-email" className="mono-label">
                    Email
                  </label>
                  <Input
                    id="signup-email"
                    type="email"
                    placeholder="trader@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="bg-background border-border font-mono input-glow"
                    data-testid="signup-email-input"
                    disabled={loading}
                  />
                </div>
                
                {/* Password field */}
                <div className="space-y-2">
                  <label htmlFor="signup-password" className="mono-label">
                    Password
                  </label>
                  <div className="relative">
                    <Input
                      id="signup-password"
                      type={showPassword ? "text" : "password"}
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="bg-background border-border font-mono pr-10 input-glow"
                      data-testid="signup-password-input"
                      disabled={loading}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                      data-testid="signup-toggle-password"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
                
                {/* Confirm Password field */}
                <div className="space-y-2">
                  <label htmlFor="signup-confirm-password" className="mono-label">
                    Confirm Password
                  </label>
                  <Input
                    id="signup-confirm-password"
                    type={showPassword ? "text" : "password"}
                    placeholder="••••••••"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="bg-background border-border font-mono input-glow"
                    data-testid="signup-confirm-password-input"
                    disabled={loading}
                  />
                </div>
                
                {/* Submit button */}
                <Button 
                  type="submit"
                  className="w-full font-mono text-sm uppercase tracking-wider btn-hover"
                  data-testid="signup-submit-button"
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin mr-2" />
                      Creating Account...
                    </>
                  ) : (
                    "Create Account"
                  )}
                </Button>
              </form>
            )}
            
            {/* Info text */}
            <p className="text-center text-xs text-muted-foreground mt-6">
              {activeTab === "login" 
                ? "Don't have an account? Click Sign Up above" 
                : "Already have an account? Click Sign In above"}
            </p>
          </CardContent>
        </Card>
        
        {/* Footer note */}
        <p className="text-center mt-6 mono-label">
          // TEXT2TRADE v1.1 - JWT AUTH
        </p>
      </div>
    </div>
  );
}
