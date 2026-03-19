import { Card, CardContent } from "@/components/ui/card";

const Bone = ({ className = "" }) => (
  <div className={`bg-secondary/60 animate-pulse ${className}`} />
);

export function PageSkeleton() {
  return (
    <div className="space-y-6 animate-fade-in" data-testid="page-skeleton">
      <div className="space-y-2">
        <Bone className="h-8 w-64" />
        <Bone className="h-4 w-40" />
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[...Array(4)].map((_, i) => (
          <Card key={i} className="border-border bg-card">
            <CardContent className="p-4 space-y-2">
              <Bone className="h-3 w-16" />
              <Bone className="h-8 w-20" />
            </CardContent>
          </Card>
        ))}
      </div>
      <div className="space-y-3">
        {[...Array(3)].map((_, i) => (
          <Card key={i} className="border-border bg-card">
            <CardContent className="p-4 flex items-center gap-4">
              <Bone className="h-10 w-10" />
              <div className="flex-1 space-y-2">
                <Bone className="h-4 w-48" />
                <Bone className="h-3 w-32" />
              </div>
              <Bone className="h-8 w-20" />
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

export function TableSkeleton({ rows = 5, cols = 4 }) {
  return (
    <div className="space-y-2" data-testid="table-skeleton">
      <div className="flex gap-4 p-3">
        {[...Array(cols)].map((_, i) => <Bone key={i} className="h-3 flex-1" />)}
      </div>
      {[...Array(rows)].map((_, i) => (
        <div key={i} className="flex gap-4 p-3 border-t border-border/30">
          {[...Array(cols)].map((_, j) => <Bone key={j} className="h-4 flex-1" />)}
        </div>
      ))}
    </div>
  );
}

export function CardSkeleton() {
  return (
    <Card className="border-border bg-card" data-testid="card-skeleton">
      <CardContent className="p-5 space-y-3">
        <Bone className="h-4 w-32" />
        <Bone className="h-6 w-20" />
        <Bone className="h-3 w-40" />
      </CardContent>
    </Card>
  );
}
