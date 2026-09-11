import { AlertTriangle, Info } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useSettings } from "@/stores/settings";

export function ChartSkeleton({ height = 260 }: { height?: number }) {
  return <Skeleton className="w-full rounded-xl" style={{ height }} />;
}

export function CardsSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {Array.from({ length: count }).map((_, i) => (
        <Skeleton key={i} className="h-40 rounded-xl" />
      ))}
    </div>
  );
}

export function ErrorCard({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const setMode = useSettings((s) => s.setMode);
  const message = error instanceof Error ? error.message : String(error);
  return (
    <Card className="border-coral/40 bg-coral/5">
      <CardContent className="space-y-3 p-5">
        <div className="flex items-center gap-2 text-coral">
          <AlertTriangle className="h-4 w-4" />
          <span className="text-sm font-medium">Could not load live data</span>
        </div>
        <p className="font-mono text-xs break-words text-muted-foreground">{message}</p>
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="secondary"
            onClick={() => {
              setMode("fast");
              onRetry?.();
            }}
          >
            Try fast mode
          </Button>
          {onRetry ? (
            <Button size="sm" variant="ghost" onClick={onRetry}>
              Retry
            </Button>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}

export function ConceptBanner() {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-amber/30 bg-amber/10 px-4 py-3 text-sm text-foreground">
      <Info className="mt-0.5 h-4 w-4 shrink-0 text-amber" />
      <span>
        Concept MVP: factors are literature medians; cooling profiles are illustrative. Not for
        compliance filing.
      </span>
    </div>
  );
}
