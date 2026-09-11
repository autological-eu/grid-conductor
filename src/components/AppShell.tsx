import { useState, type ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { DEFAULT_ZONE } from "@/lib/zones";
import { SettingsPopover } from "@/components/SettingsPopover";
import {
  Activity,
  BarChart3,
  BookOpen,
  Calculator,
  Clock,
  Droplet,
  LayoutDashboard,
  List,
  Menu,
  Sparkles,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Drawer, DrawerContent, DrawerTitle, DrawerTrigger } from "@/components/ui/drawer";
import { ThemeToggle } from "@/components/ThemeToggle";
import { ZoneSelector } from "@/components/ZoneSelector";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/", label: "Overview", icon: LayoutDashboard },
  { to: "/live", label: "Live Signals", icon: Activity },
  { to: "/forecast", label: "Forecast & Scheduler", icon: Clock },
  { to: "/footprint", label: "Footprint Calculator", icon: Calculator },
  { to: "/benchmark", label: "Benchmark & Siting", icon: BarChart3 },
  { to: "/concepts", label: "Partner Concepts", icon: Sparkles },
  { to: "/methodology", label: "Methodology & API", icon: BookOpen },
  { to: "/catalogue", label: "Signal Catalogue", icon: List },
] as const;

function Brand() {
  return (
    <Link
      to="/"
      search={(prev: { zone?: string }) => ({ zone: prev.zone ?? DEFAULT_ZONE })}
      className="flex items-center gap-2"
    >
      <span className="relative flex size-8 items-center justify-center rounded-lg bg-water/10">
        <Droplet className="size-4 text-water" />
        <Zap className="absolute right-1 bottom-1 size-2.5 text-amber" />
      </span>
      <span className="text-base font-semibold tracking-tight text-foreground">WaterTrace</span>
    </Link>
  );
}

function NavList({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav className="flex flex-col gap-1">
      {NAV.map(({ to, label, icon: Icon }) => (
        <Link
          key={to}
          to={to}
          search={(prev: { zone?: string }) => ({ zone: prev.zone ?? DEFAULT_ZONE })}
          onClick={onNavigate}
          activeOptions={{ exact: to === "/" }}
          className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
          activeProps={{ className: "bg-water/10 text-water font-medium hover:bg-water/10" }}
        >
          <Icon className="size-4" />
          {label}
        </Link>
      ))}
    </nav>
  );
}

function SiteFooter() {
  return (
    <footer className="border-t border-border px-6 py-6">
      <p className="text-xs leading-relaxed text-muted-foreground">
        Concept MVP · Powered by Electricity Maps data · Water factors: Macknick et al. 2012 (NREL)
        · Not an official Electricity Maps product
      </p>
    </footer>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-40 border-b border-border bg-background/90 backdrop-blur">
        <div className="flex h-16 items-center gap-3 px-4 md:px-6">
          <Drawer open={open} onOpenChange={setOpen}>
            <DrawerTrigger asChild>
              <Button variant="ghost" size="icon" className="md:hidden" aria-label="Open menu">
                <Menu className="size-5" />
              </Button>
            </DrawerTrigger>
            <DrawerContent className="p-4">
              <DrawerTitle className="px-3 pb-2 text-sm text-muted-foreground">Pages</DrawerTitle>
              <NavList onNavigate={() => setOpen(false)} />
            </DrawerContent>
          </Drawer>

          <Brand />

          <div className="ml-auto flex items-center gap-2">
            <ZoneSelector className="w-[150px] md:w-[220px]" />
            <SettingsPopover />
            <ThemeToggle />
          </div>
        </div>
      </header>

      <div className="flex">
        <aside className="hidden w-64 shrink-0 border-r border-border md:block">
          <div className="sticky top-16 p-4">
            <NavList />
          </div>
        </aside>

        <div className="flex min-h-[calc(100vh-4rem)] min-w-0 flex-1 flex-col">
          <main className={cn("flex-1 px-4 py-8 md:px-8")}>{children}</main>
          <SiteFooter />
        </div>
      </div>
    </div>
  );
}

export function PageHeader({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children?: ReactNode;
}) {
  return (
    <div className="mb-8 max-w-3xl">
      <h1 className="text-3xl font-semibold tracking-tight text-foreground">{title}</h1>
      {description ? <p className="mt-2 text-muted-foreground">{description}</p> : null}
      {children}
    </div>
  );
}

export function Placeholder({ label }: { label: string }) {
  return (
    <div className="flex h-40 items-center justify-center rounded-xl border border-dashed border-border text-sm text-muted-foreground">
      {label}
    </div>
  );
}
