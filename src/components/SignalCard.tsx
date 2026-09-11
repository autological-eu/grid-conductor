import type { ReactNode } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { DataBadge, type DataBadgeKind } from "@/components/DataBadge";
import { cn } from "@/lib/utils";

export interface SignalCardProps {
  id: string;
  title: string;
  value?: string | number;
  unit?: string;
  subtitle?: string;
  badge?: DataBadgeKind;
  chip?: ReactNode;
  className?: string;
  children?: ReactNode;
}

export function SignalCard({
  id,
  title,
  value = "—",
  unit,
  subtitle,
  badge,
  chip,
  className,
  children,
}: SignalCardProps) {
  return (
    <Card className={cn("h-full", className)}>
      <CardContent className="flex h-full flex-col gap-3 p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="rounded-md bg-secondary px-1.5 py-0.5 font-mono text-[11px] font-semibold text-secondary-foreground">
              {id}
            </span>
            <span className="text-sm font-medium text-foreground">{title}</span>
          </div>
          {badge ? <DataBadge kind={badge} /> : null}
        </div>

        <div className="flex items-baseline gap-1.5">
          <span className="text-4xl font-semibold tracking-tight text-foreground tabular-nums">
            {value}
          </span>
          {unit ? <span className="text-sm text-muted-foreground">{unit}</span> : null}
        </div>

        {subtitle ? <p className="text-sm text-muted-foreground">{subtitle}</p> : null}
        {chip ? <div>{chip}</div> : null}
        {children ? <div className="mt-auto pt-2">{children}</div> : null}
      </CardContent>
    </Card>
  );
}
