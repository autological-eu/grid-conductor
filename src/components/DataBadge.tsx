import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide whitespace-nowrap",
  {
    variants: {
      kind: {
        live: "border-teal/30 bg-teal/10 text-teal",
        assumption: "border-amber/30 bg-amber/10 text-amber",
        mock: "border-concept/30 bg-concept/10 text-concept",
      },
    },
    defaultVariants: { kind: "live" },
  },
);

const LABELS = {
  live: "Live",
  assumption: "Assumption",
  mock: "Concept · Mock data",
} as const;

export type DataBadgeKind = keyof typeof LABELS;

export interface DataBadgeProps extends VariantProps<typeof badgeVariants> {
  kind: DataBadgeKind;
  className?: string;
  label?: string;
}

export function DataBadge({ kind, className, label }: DataBadgeProps) {
  return <span className={cn(badgeVariants({ kind }), className)}>{label ?? LABELS[kind]}</span>;
}

export function ProfilesChip({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border border-amber/30 bg-amber/10 px-2 py-0.5 text-[10px] font-medium text-amber whitespace-nowrap",
        className,
      )}
    >
      profiles: illustrative
    </span>
  );
}
