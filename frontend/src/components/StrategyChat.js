import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MessageCircle, Send, Loader2, X } from "lucide-react";
import axios from "axios";

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function StrategyChat({ strategy, onClose }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);

  const handleAsk = async () => {
    if (!question.trim() || loading) return;
    setLoading(true);
    setAnswer("");
    try {
      const res = await axios.post(`${API_URL}/explain`, { strategy, question });
      setAnswer(res.data.answer);
    } catch (err) {
      setAnswer("Error: Could not get response.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="border-border bg-card" data-testid="strategy-chat">
      <CardHeader className="pb-2 flex flex-row items-center justify-between">
        <CardTitle className="text-sm font-mono flex items-center gap-2">
          <MessageCircle className="w-4 h-4 text-primary" /> Strategy Explainer AI
        </CardTitle>
        <Button variant="ghost" size="icon" onClick={onClose} data-testid="chat-close">
          <X className="w-4 h-4" />
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <Input
            placeholder="Ask about this strategy..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAsk()}
            disabled={loading}
            className="font-mono text-sm"
            data-testid="chat-input"
          />
          <Button onClick={handleAsk} disabled={loading || !question.trim()} data-testid="chat-send">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </Button>
        </div>
        {answer && (
          <div className="p-3 bg-secondary/50 text-sm text-foreground" data-testid="chat-answer">
            {answer}
          </div>
        )}
        <p className="text-xs text-muted-foreground">No memory. Each question is independent.</p>
      </CardContent>
    </Card>
  );
}
