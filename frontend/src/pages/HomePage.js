/**
 * Text2trade Home Page
 * ====================
 * Landing page with hero section and feature highlights.
 * No business logic - just static content and navigation.
 */

import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { TrendingUp, Zap, Shield, ArrowRight } from "lucide-react";

/**
 * Navigation Bar Component
 * Sticky header with glassmorphism effect.
 */
const Navbar = () => {
  return (
    <nav 
      className="fixed top-0 left-0 right-0 z-50 glass"
      data-testid="navbar"
    >
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        {/* Logo / Brand */}
        <Link 
          to="/" 
          className="flex items-center gap-2"
          data-testid="nav-logo"
        >
          <div className="w-8 h-8 bg-primary flex items-center justify-center">
            <TrendingUp className="w-5 h-5 text-primary-foreground" />
          </div>
          <span className="font-mono font-bold text-lg text-foreground">
            TEXT2TRADE
          </span>
        </Link>
        
        {/* Navigation Links */}
        <div className="flex items-center gap-4">
          <Link 
            to="/login"
            data-testid="nav-login-link"
          >
            <Button 
              variant="ghost" 
              className="font-mono text-sm uppercase tracking-wider"
            >
              Login
            </Button>
          </Link>
          <Link 
            to="/dashboard"
            data-testid="nav-dashboard-link"
          >
            <Button 
              className="font-mono text-sm uppercase tracking-wider btn-hover"
            >
              Dashboard
            </Button>
          </Link>
        </div>
      </div>
    </nav>
  );
};

/**
 * Feature Card Component
 * Displays a single feature with icon and description.
 */
const FeatureCard = ({ icon: Icon, title, description, testId }) => {
  return (
    <div 
      className="p-6 border border-border bg-card card-hover"
      data-testid={testId}
    >
      <div className="w-10 h-10 bg-primary/10 flex items-center justify-center mb-4">
        <Icon className="w-5 h-5 text-primary" />
      </div>
      <h3 className="font-mono font-bold text-lg mb-2 text-foreground">
        {title}
      </h3>
      <p className="text-sm text-muted-foreground leading-relaxed">
        {description}
      </p>
    </div>
  );
};

/**
 * Home Page Component
 * Main landing page with hero and features.
 */
export default function HomePage() {
  return (
    <div className="min-h-screen bg-background" data-testid="home-page">
      {/* Navigation */}
      <Navbar />
      
      {/* Hero Section */}
      <section className="pt-32 pb-20 px-6" data-testid="hero-section">
        <div className="max-w-7xl mx-auto">
          <div className="max-w-3xl">
            {/* Mono label */}
            <span className="mono-label text-primary mb-4 inline-block">
              // TRADING PLATFORM
            </span>
            
            {/* Main heading */}
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-foreground mb-6">
              Execute trades with
              <span className="text-primary block mt-2">precision</span>
            </h1>
            
            {/* Subheading */}
            <p className="text-base md:text-lg text-muted-foreground mb-8 max-w-xl leading-relaxed">
              Fast, minimal, and functional. Text2trade provides the tools you 
              need without the noise you don't.
            </p>
            
            {/* CTA Buttons */}
            <div className="flex flex-wrap gap-4">
              <Link to="/dashboard" data-testid="hero-cta-dashboard">
                <Button 
                  size="lg" 
                  className="font-mono text-sm uppercase tracking-wider btn-hover gap-2"
                >
                  Open Dashboard
                  <ArrowRight className="w-4 h-4" />
                </Button>
              </Link>
              <Link to="/login" data-testid="hero-cta-login">
                <Button 
                  variant="outline" 
                  size="lg"
                  className="font-mono text-sm uppercase tracking-wider"
                >
                  Login
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>
      
      {/* Features Section */}
      <section className="py-20 px-6 border-t border-border" data-testid="features-section">
        <div className="max-w-7xl mx-auto">
          {/* Section header */}
          <div className="mb-12">
            <span className="mono-label text-primary mb-4 inline-block">
              // FEATURES
            </span>
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-foreground">
              Built for speed
            </h2>
          </div>
          
          {/* Feature cards grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <FeatureCard 
              icon={Zap}
              title="Lightning Fast"
              description="Optimized for speed. Every millisecond counts when you're trading."
              testId="feature-speed"
            />
            <FeatureCard 
              icon={Shield}
              title="Secure"
              description="Enterprise-grade security to protect your assets and data."
              testId="feature-security"
            />
            <FeatureCard 
              icon={TrendingUp}
              title="Real-time Data"
              description="Live market data and instant execution for informed decisions."
              testId="feature-realtime"
            />
          </div>
        </div>
      </section>
      
      {/* Footer */}
      <footer className="py-8 px-6 border-t border-border" data-testid="footer">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <span className="mono-label">
            © 2026 Text2trade
          </span>
          <span className="mono-label">
            v0.1.0 // MVP SCAFFOLD
          </span>
        </div>
      </footer>
    </div>
  );
}
