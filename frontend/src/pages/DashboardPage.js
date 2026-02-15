import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp, PlusCircle, FolderOpen, HelpCircle, LogOut, User, ChevronRight, Lightbulb, FileText, Settings, BarChart3, Zap, X, MessageCircle, Sparkles } from "lucide-react";
import StrategyBuilder from "@/components/StrategyBuilder";
import StrategyChat from "@/components/StrategyChat";
import NLStrategyInput from "@/components/NLStrategyInput";
import { explainStrategy } from "@/utils/explainStrategy";
import axios from "axios";

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Sidebar = ({ activePage, onPageChange, userEmail, onLogout }) => {
  const menuItems = [
    { id: "create", label: "Create Strategy", icon: PlusCircle },
    { id: "strategies", label: "My Strategies", icon: FolderOpen },
    { id: "help", label: "Help", icon: HelpCircle },
  ];

  return (
    <aside className="fixed left-0 top-0 bottom-0 w-64 bg-card border-r border-border flex flex-col" data-testid="dashboard-sidebar">
      <div className="p-6 border-b border-border">
        <Link to="/" className="flex items-center gap-2" data-testid="sidebar-logo">
          <div className="w-8 h-8 bg-primary flex items-center justify-center">
            <TrendingUp className="w-5 h-5 text-primary-foreground" />
          </div>
          <span className="font-mono font-bold text-lg text-foreground">TEXT2TRADE</span>
        </Link>
      </div>
      <nav className="flex-1 p-4" data-testid="sidebar-nav">
        <div className="space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = activePage === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onPageChange(item.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-colors ${isActive ? "bg-primary/10 text-primary border-l-2 border-primary" : "text-muted-foreground hover:text-foreground hover:bg-secondary"}`}
                data-testid={`sidebar-${item.id}`}
              >
                <Icon className="w-5 h-5" />
                <span className="font-mono text-sm uppercase tracking-wider">{item.label}</span>
              </button>
            );
          })}
        </div>
      </nav>
      <div className="p-4 border-t border-border">
        <div className="flex items-center gap-2 px-4 py-2 mb-2">
          <User className="w-4 h-4 text-muted-foreground" />
          <span className="text-xs text-muted-foreground truncate" data-testid="sidebar-user-email">{userEmail}</span>
        </div>
        <Button variant="ghost" onClick={onLogout} className="w-full justify-start gap-3 font-mono text-sm uppercase tracking-wider text-muted-foreground hover:text-destructive" data-testid="sidebar-logout">
          <LogOut className="w-5 h-5" />Logout
        </Button>
      </div>
    </aside>
  );
};

const PlaceholderCard = ({ icon: Icon, title, description, actionLabel, onClick, testId }) => (
  <Card className="border-border bg-card card-hover group cursor-pointer" data-testid={testId} onClick={onClick}>
    <CardHeader>
      <div className="flex items-start justify-between">
        <div className="w-12 h-12 bg-primary/10 flex items-center justify-center mb-4">
          <Icon className="w-6 h-6 text-primary" />
        </div>
        {actionLabel && <ChevronRight className="w-5 h-5 text-muted-foreground group-hover:text-primary transition-colors" />}
      </div>
      <CardTitle className="text-lg font-mono">{title}</CardTitle>
      <CardDescription className="text-muted-foreground">{description}</CardDescription>
    </CardHeader>
    {actionLabel && (
      <CardContent>
        <Button variant="outline" className="w-full font-mono text-xs uppercase tracking-wider">{actionLabel}</Button>
      </CardContent>
    )}
  </Card>
);

const CreateStrategyContent = ({ onStartBuilder }) => (
  <div className="space-y-8">
    <div>
      <h1 className="text-3xl font-bold tracking-tight text-foreground">Create Strategy</h1>
      <p className="text-muted-foreground mt-2">Build a new trading strategy from scratch or use a template.</p>
    </div>
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <PlaceholderCard icon={PlusCircle} title="Blank Strategy" description="Start from scratch with a blank canvas. Full control over every parameter." actionLabel="Create Blank" onClick={onStartBuilder} testId="card-blank-strategy" />
      <PlaceholderCard icon={Lightbulb} title="Use Template" description="Choose from pre-built strategy templates to get started quickly." actionLabel="Browse Templates" testId="card-use-template" />
      <PlaceholderCard icon={FileText} title="Import Strategy" description="Import an existing strategy from a file or another platform." actionLabel="Import" testId="card-import-strategy" />
    </div>
    <Card className="border-border bg-secondary/30" data-testid="card-info">
      <CardContent className="p-6">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 bg-primary/10 flex items-center justify-center flex-shrink-0">
            <Zap className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h3 className="font-mono font-bold text-foreground mb-1">Quick Tip</h3>
            <p className="text-sm text-muted-foreground">New to strategy creation? Start with a template and customize it to learn how different parameters affect trading behavior.</p>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
);

const MyStrategiesContent = ({ strategies, onCreateNew, onOpenChat }) => (
  <div className="space-y-8">
    <div className="flex items-center justify-between">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">My Strategies</h1>
        <p className="text-muted-foreground mt-2">Manage and monitor your trading strategies.</p>
      </div>
      <Button className="font-mono text-xs uppercase tracking-wider gap-2" onClick={onCreateNew}>
        <PlusCircle className="w-4 h-4" />New Strategy
      </Button>
    </div>
    {strategies.length === 0 ? (
      <Card className="border-border border-dashed bg-card/50" data-testid="strategies-empty-state">
        <CardContent className="p-12 text-center">
          <div className="w-16 h-16 bg-secondary flex items-center justify-center mx-auto mb-4">
            <FolderOpen className="w-8 h-8 text-muted-foreground" />
          </div>
          <h3 className="font-mono font-bold text-lg text-foreground mb-2">No Strategies Yet</h3>
          <p className="text-sm text-muted-foreground mb-6 max-w-md mx-auto">You haven't created any strategies. Create your first strategy to start automating your trades.</p>
          <Button className="font-mono text-xs uppercase tracking-wider gap-2" onClick={onCreateNew}>
            <PlusCircle className="w-4 h-4" />Create Your First Strategy
          </Button>
        </CardContent>
      </Card>
    ) : (
      <div className="space-y-4">
        {strategies.map((s, i) => (
          <Card key={s.id || i} className="border-border bg-card" data-testid={`strategy-card-${i}`}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <h3 className="font-mono font-bold text-foreground">{s.metadata?.name || "Unnamed"}</h3>
                  <p className="text-xs text-muted-foreground font-mono mt-1">
                    {s.market?.type} / {s.instrument?.symbol} / {s.timeframe?.interval}
                  </p>
                  <p className="text-sm text-muted-foreground mt-2">{explainStrategy(s)}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" onClick={() => onOpenChat(s)} data-testid={`chat-btn-${i}`}>
                    <MessageCircle className="w-4 h-4 mr-1" /> Ask AI
                  </Button>
                  <span className="mono-label text-primary">DRAFT</span>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    )}
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <Card className="border-border bg-card" data-testid="stat-active"><CardContent className="p-6"><span className="mono-label">Active</span><p className="text-3xl font-mono font-bold text-foreground mt-2">0</p></CardContent></Card>
      <Card className="border-border bg-card" data-testid="stat-paused"><CardContent className="p-6"><span className="mono-label">Paused</span><p className="text-3xl font-mono font-bold text-foreground mt-2">0</p></CardContent></Card>
      <Card className="border-border bg-card" data-testid="stat-total"><CardContent className="p-6"><span className="mono-label">Total</span><p className="text-3xl font-mono font-bold text-foreground mt-2">{strategies.length}</p></CardContent></Card>
    </div>
  </div>
);

const HelpContent = () => (
  <div className="space-y-8">
    <div>
      <h1 className="text-3xl font-bold tracking-tight text-foreground">Help & Support</h1>
      <p className="text-muted-foreground mt-2">Find answers and get support for Text2trade.</p>
    </div>
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <PlaceholderCard icon={FileText} title="Documentation" description="Read the full documentation to learn how to use all features." actionLabel="View Docs" testId="card-documentation" />
      <PlaceholderCard icon={Lightbulb} title="Getting Started" description="New to Text2trade? Follow our step-by-step beginner's guide." actionLabel="Start Guide" testId="card-getting-started" />
      <PlaceholderCard icon={BarChart3} title="Strategy Examples" description="Explore example strategies to understand different approaches." actionLabel="View Examples" testId="card-examples" />
      <PlaceholderCard icon={Settings} title="FAQ" description="Find answers to frequently asked questions." actionLabel="View FAQ" testId="card-faq" />
    </div>
    <Card className="border-border bg-card" data-testid="card-support">
      <CardContent className="p-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 bg-primary/10 flex items-center justify-center flex-shrink-0">
              <HelpCircle className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h3 className="font-mono font-bold text-foreground mb-1">Need More Help?</h3>
              <p className="text-sm text-muted-foreground">Can't find what you're looking for? Contact our support team.</p>
            </div>
          </div>
          <Button variant="outline" className="font-mono text-xs uppercase tracking-wider">Contact Support</Button>
        </div>
      </CardContent>
    </Card>
  </div>
);

export default function DashboardPage() {
  const [activePage, setActivePage] = useState("create");
  const [userEmail, setUserEmail] = useState(null);
  const [showBuilder, setShowBuilder] = useState(false);
  const [strategies, setStrategies] = useState([]);
  const [chatStrategy, setChatStrategy] = useState(null);
  const navigate = useNavigate();

  const fetchStrategies = async () => {
    try {
      const res = await axios.get(`${API_URL}/strategies`);
      setStrategies(res.data.strategies || []);
    } catch (err) {
      console.error("Fetch failed:", err);
    }
  };

  useEffect(() => {
    const email = localStorage.getItem("userEmail");
    if (!email) { navigate("/login"); } else { setUserEmail(email); fetchStrategies(); }
  }, [navigate]);

  const handleLogout = () => { localStorage.removeItem("userEmail"); navigate("/login"); };
  const handlePageChange = (pageId) => { setActivePage(pageId); setShowBuilder(false); setChatStrategy(null); };
  const handleStartBuilder = () => setShowBuilder(true);
  const handleCloseBuilder = () => setShowBuilder(false);
  const handleSaveStrategy = (strategy) => {
    setStrategies(prev => [...prev, strategy]);
    setShowBuilder(false);
    setActivePage("strategies");
  };
  const handleOpenChat = (s) => setChatStrategy(s);
  const handleCloseChat = () => setChatStrategy(null);

  const renderContent = () => {
    if (showBuilder) {
      return (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-foreground">Strategy Builder</h1>
              <p className="text-muted-foreground mt-2">Configure your trading strategy step by step.</p>
            </div>
            <Button variant="ghost" size="icon" onClick={handleCloseBuilder} data-testid="btn-close-builder">
              <X className="w-5 h-5" />
            </Button>
          </div>
          <Card className="border-border bg-card">
            <CardContent className="p-6">
              <StrategyBuilder onClose={handleCloseBuilder} onSave={handleSaveStrategy} />
            </CardContent>
          </Card>
        </div>
      );
    }
    switch (activePage) {
      case "create": return <CreateStrategyContent onStartBuilder={handleStartBuilder} />;
      case "strategies": return <MyStrategiesContent strategies={strategies} onCreateNew={handleStartBuilder} onOpenChat={handleOpenChat} />;
      case "help": return <HelpContent />;
      default: return <CreateStrategyContent onStartBuilder={handleStartBuilder} />;
    }
  };

  if (!userEmail) return null;

  return (
    <div className="min-h-screen bg-background" data-testid="dashboard-page">
      <Sidebar activePage={activePage} onPageChange={handlePageChange} userEmail={userEmail} onLogout={handleLogout} />
      <main className="ml-64 min-h-screen p-8" data-testid="dashboard-main-content">
        <div className="max-w-5xl">{renderContent()}</div>
        {chatStrategy && (
          <div className="max-w-5xl mt-6">
            <StrategyChat strategy={chatStrategy} onClose={handleCloseChat} />
          </div>
        )}
        <div className="max-w-5xl mt-12 pt-8 border-t border-border">
          <div className="flex items-center justify-between">
            <span className="mono-label">// TEXT2TRADE v0.5.0</span>
            <span className="mono-label">AI EXPLAINER ENABLED</span>
          </div>
        </div>
      </main>
    </div>
  );
}
