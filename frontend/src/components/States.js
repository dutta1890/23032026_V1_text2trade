import { Card, CardContent } from "@/components/ui/card";

export function EmptyState({ icon: Icon, title, description, testId, children }) {
  return (
    <Card className="border-border border-dashed bg-card/50" data-testid={testId || "empty-state"}>
      <CardContent className="p-10 text-center">
        {Icon && <Icon className="w-10 h-10 text-muted-foreground mx-auto mb-3" />}
        <h3 className="font-mono font-bold text-foreground mb-1">{title}</h3>
        {description && <p className="text-xs text-muted-foreground font-mono">{description}</p>}
        {children && <div className="mt-4">{children}</div>}
      </CardContent>
    </Card>
  );
}

export function ErrorState({ message, onRetry, testId }) {
  return (
    <Card className="border-destructive/30 bg-destructive/5" data-testid={testId || "error-state"}>
      <CardContent className="p-6 text-center">
        <p className="text-xs font-mono text-destructive mb-3">{message || "Something went wrong."}</p>
        {onRetry && (
          <button onClick={onRetry} className="text-xs font-mono text-primary hover:underline" data-testid="retry-btn">
            Try again
          </button>
        )}
      </CardContent>
    </Card>
  );
}
