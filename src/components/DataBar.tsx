import { Link } from "@tanstack/react-router";

export function DataBar({ step }: { step: 1 | 2 | 3 }) {
  const steps = [
    { n: 1, label: "Choose bottleneck", hint: "Click a highlighted border on the map" },
    { n: 2, label: "Simulate scenarios", hint: "Build scenarios in the left panel" },
    { n: 3, label: "Evaluate opportunity", hint: "Review results in the right panel" },
  ] as const;

  return (
    <header className="flex flex-wrap items-center gap-3 lg:gap-6 border-b border-border bg-card px-5 py-3">
      <div className="shrink-0">
        <h1 className="text-lg font-bold leading-tight tracking-tight">Grid Conductor</h1>
        <p className="text-xs text-muted-foreground">Fast ENTSO-E screening workbench&nbsp;</p>
      </div>

      <ol className="hidden flex-1 items-center justify-center gap-0 md:flex">
        {steps.map((s, i) => {
          const active = step === s.n;
          const done = step > s.n;
          return (
            <li key={s.n} className="flex items-center">
              {i > 0 && (
                <div
                  className={`h-px w-8 ${done || active ? "bg-primary" : "bg-border"}`}
                  aria-hidden
                />
              )}
              <div
                className={`flex items-center gap-2 rounded-lg px-3 py-1.5 ${
                  active ? "bg-[#39FF14] ring-1 ring-[#39FF14] shadow-sm" : ""
                }`}
                title={s.hint}
                aria-current={active ? "step" : undefined}
              >
                <span
                  className={`flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-semibold ${
                    active
                      ? "bg-black/80 text-[#39FF14]"
                      : done
                        ? "bg-primary/20 text-primary"
                        : "bg-muted text-muted-foreground"
                  }`}
                >
                  {s.n}
                </span>
                <span
                  className={`text-xs font-medium ${
                    active ? "text-black" : done ? "text-foreground" : "text-muted-foreground"
                  }`}
                >
                  {s.label}
                </span>
              </div>
            </li>
          );
        })}
      </ol>

      <Link
        to="/targets"
        className="shrink-0 rounded-md px-2 py-1 text-sm text-muted-foreground hover:bg-muted hover:text-foreground"
      >
        European targets
      </Link>
      <Link
        to="/docs"
        className="shrink-0 rounded-md px-2 py-1 text-sm text-muted-foreground hover:bg-muted hover:text-foreground"
      >
        Research
      </Link>
    </header>
  );
}
