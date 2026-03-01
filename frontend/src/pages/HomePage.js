import { useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { TrendingUp, Zap, Brain, BarChart3, ArrowRight, Check, AlertCircle } from "lucide-react";
import axios from "axios";

const API_URL = process.env.REACT_APP_BACKEND_URL + "/api";

const Navbar = () => (
  <nav className="fixed top-0 left-0 right-0 z-50 glass" data-testid="navbar">
    <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
      <Link to="/" className="flex items-center gap-2" data-testid="nav-logo">
        <div className="w-8 h-8 bg-primary flex items-center justify-center">
          <TrendingUp className="w-5 h-5 text-primary-foreground" />
        </div>
        <span className="font-mono font-bold text-lg text-foreground">TEXT2TRADE</span>
      </Link>
      <div className="flex items-center gap-4">
        <Link to="/login">
          <Button variant="ghost" className="font-mono text-sm uppercase tracking-wider">Login</Button>
        </Link>
        <Link to="/dashboard">
          <Button className="font-mono text-sm uppercase tracking-wider btn-hover">Dashboard</Button>
        </Link>
      </div>
    </div>
  </nav>
);

const FeatureItem = ({ icon: Icon, title, description }) => (
  <div className="flex gap-4">
    <div className="w-10 h-10 bg-primary/10 flex items-center justify-center flex-shrink-0">
      <Icon className="w-5 h-5 text-primary" />
    </div>
    <div>
      <h3 className="font-mono font-bold text-foreground mb-1">{title}</h3>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  </div>
);

const WaitlistForm = () => {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState(null); // null, 'success', 'error'
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email) return;
    
    setLoading(true);
    try {
      await axios.post(`${API_URL}/waitlist`, { email });
      setStatus("success");
      setEmail("");
    } catch (err) {
      setStatus("error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mt-8 p-6 border border-border bg-card" data-testid="waitlist-form">
      <p className="mono-label text-primary mb-2">// JOIN WAITLIST</p>
      <p className="text-sm text-muted-foreground mb-4">Get early access when we launch new features.</p>
      
      {status === "success" ? (
        <div className="flex items-center gap-2 text-primary" data-testid="waitlist-success">
          <Check className="w-5 h-5" />
          <span className="font-mono text-sm">You're on the list.</span>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            type="email"
            placeholder="your@email.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="font-mono flex-1"
            data-testid="waitlist-email-input"
            required
          />
          <Button type="submit" disabled={loading} className="font-mono" data-testid="waitlist-submit">
            {loading ? "..." : "Join"}
          </Button>
        </form>
      )}
      {status === "error" && (
        <div className="flex items-center gap-2 text-destructive mt-2" data-testid="waitlist-error">
          <AlertCircle className="w-4 h-4" />
          <span className="text-sm">Something went wrong. Try again.</span>
        </div>
      )}
    </div>
  );
};

export default function HomePage() {
  return (
    <div className="min-h-screen bg-background" data-testid="home-page">
      <Navbar />
      
      {/* Hero Section */}
      <section className="pt-32 pb-16 px-6" data-testid="hero-section">
        <div className="max-w-7xl mx-auto">
          <div className="max-w-2xl">
            <span className="mono-label text-primary mb-4 inline-block">// STRATEGY BUILDER</span>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-foreground mb-6">
              Build trading strategies
              <span className="text-primary block mt-2">without code</span>
            </h1>
            <p className="text-base md:text-lg text-muted-foreground mb-8 leading-relaxed">
              Text2trade lets you create, backtest, and analyze trading strategies using plain language or a visual builder. No programming required.
            </p>
            
            <div className="flex flex-wrap gap-4">
              <Link to="/dashboard" data-testid="hero-cta-dashboard">
                <Button size="lg" className="font-mono text-sm uppercase tracking-wider btn-hover gap-2">
                  Try it now <ArrowRight className="w-4 h-4" />
                </Button>
              </Link>
            </div>

            <WaitlistForm />
          </div>
        </div>
      </section>
      
      {/* Features Section */}
      <section className="py-16 px-6 border-t border-border" data-testid="features-section">
        <div className="max-w-7xl mx-auto">
          <span className="mono-label text-primary mb-4 inline-block">// WHAT YOU CAN DO</span>
          <h2 className="text-2xl md:text-3xl font-bold tracking-tight text-foreground mb-8">Features</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <FeatureItem 
              icon={Brain}
              title="Natural Language Input"
              description="Describe your strategy in plain English. AI converts it to executable rules."
            />
            <FeatureItem 
              icon={Zap}
              title="Visual Strategy Builder"
              description="Step-by-step form to configure indicators, entry/exit rules, and risk management."
            />
            <FeatureItem 
              icon={BarChart3}
              title="Historical Backtesting"
              description="Test SMA/EMA strategies against real market data. Other indicators use simulation."
            />
            <FeatureItem 
              icon={TrendingUp}
              title="Multiple Indicators"
              description="RSI, SMA, EMA, MACD, Stochastic for signals. ADX for filtering. ATR for stop loss."
            />
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-16 px-6 border-t border-border" data-testid="how-section">
        <div className="max-w-7xl mx-auto">
          <span className="mono-label text-primary mb-4 inline-block">// HOW IT WORKS</span>
          <h2 className="text-2xl md:text-3xl font-bold tracking-tight text-foreground mb-8">Three steps</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-4 border border-border">
              <span className="font-mono text-3xl font-bold text-primary">01</span>
              <h3 className="font-mono font-bold text-foreground mt-2 mb-1">Define</h3>
              <p className="text-sm text-muted-foreground">Use the builder or describe in plain text what triggers a trade.</p>
            </div>
            <div className="p-4 border border-border">
              <span className="font-mono text-3xl font-bold text-primary">02</span>
              <h3 className="font-mono font-bold text-foreground mt-2 mb-1">Backtest</h3>
              <p className="text-sm text-muted-foreground">Run against historical data to see potential performance.</p>
            </div>
            <div className="p-4 border border-border">
              <span className="font-mono text-3xl font-bold text-primary">03</span>
              <h3 className="font-mono font-bold text-foreground mt-2 mb-1">Analyze</h3>
              <p className="text-sm text-muted-foreground">AI explains your strategy and identifies potential risks.</p>
            </div>
          </div>
        </div>
      </section>
      
      {/* Footer */}
      <footer className="py-8 px-6 border-t border-border" data-testid="footer">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <span className="mono-label">© 2026 Text2trade</span>
          <span className="mono-label">v0.2.0</span>
        </div>
      </footer>
    </div>
  );
}
